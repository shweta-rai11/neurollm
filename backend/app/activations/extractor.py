"""Extracts real hidden-state, attention, and logit activations from a local
Hugging Face causal LM while it answers a prompt.

Design constraints (see README, "No fabricated numbers"):
  - Every field on `ActivationCapture` is read directly off model tensors
    produced by an actual forward/generate call. Nothing here is hardcoded
    or simulated.
  - Raw tensors never leave this module -- `capture()` reduces them to plain
    Python floats before returning, so callers (schemas, DB, JSON responses)
    never need to know about torch.

Two passes are used:
  1. `model.generate(..., output_scores=True)` -- the *actual* logits used to
     sample each generated token, giving real per-token entropy/probability
     margins with no extra cost.
  2. One additional forward pass over the full (prompt + generated) sequence
     with `output_hidden_states=True, output_attentions=True`, read only at
     the generated-token positions -- i.e. what the model attended to *while
     producing the answer*, not the prompt-only encoding.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ActivationCapture:
    num_layers: int
    vocab_size: int
    num_prompt_tokens: int
    num_generated_tokens: int
    # len == num_layers + 1 (embedding output + each transformer block),
    # mean L2 norm of the hidden state over generated-token positions.
    layer_hidden_norms: list[float]
    # len == num_layers, mean *position-normalized* attention entropy
    # (entropy / ln(num_keys_visible)) over generated-token query positions.
    layer_attention_entropy: list[float]
    # len == num_generated_tokens
    token_entropies: list[float]
    token_prob_margins: list[float]
    token_top1_probs: list[float]


class ActivationExtractor(Protocol):
    """Interface the rest of the app depends on -- tests substitute a fake
    implementation so the suite never has to download/load the real model
    (mirrors how `app.llm.get_provider` lets tests force `MockProvider`)."""

    def capture(self, prompt: str, max_new_tokens: int = 200) -> tuple[str, ActivationCapture]:
        """Generate a response to `prompt`; return (answer_text, capture)."""
        ...


class LocalHFActivationExtractor:
    """Wraps an already-loaded Qwen2.5-Instruct-family model + tokenizer."""

    def __init__(self, model, tokenizer, device: str) -> None:
        self._model = model
        self._tokenizer = tokenizer
        self._device = device

    def _encode(self, prompt: str):
        """Returns an input_ids tensor on `self._device`. Pinned to
        `return_dict=True` and explicit key access -- some transformers
        versions return a bare tensor from `apply_chat_template(...,
        return_tensors="pt")`, others a BatchEncoding; this normalizes both."""
        messages = [{"role": "user", "content": prompt}]
        encoded = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self._device)
        return encoded["input_ids"]

    def generate_text(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.8) -> str:
        """Fast path used for multi-sample uncertainty sweeps: no hidden-state/
        attention capture, just the generated text (still a real model call)."""
        import torch

        input_ids = self._encode(prompt)

        with torch.no_grad():
            out_ids = self._model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        generated = out_ids[:, input_ids.shape[1]:]
        return self._tokenizer.decode(generated[0], skip_special_tokens=True).strip()

    def capture(self, prompt: str, max_new_tokens: int = 200) -> tuple[str, ActivationCapture]:
        import torch

        input_ids = self._encode(prompt)
        num_prompt_tokens = int(input_ids.shape[1])

        with torch.no_grad():
            gen_out = self._model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                output_scores=True,
                return_dict_in_generate=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        full_ids = gen_out.sequences
        generated_ids = full_ids[:, num_prompt_tokens:]
        answer = self._tokenizer.decode(generated_ids[0], skip_special_tokens=True).strip()

        token_entropies: list[float] = []
        token_prob_margins: list[float] = []
        token_top1_probs: list[float] = []
        for step_logits in gen_out.scores:
            probs = torch.softmax(step_logits[0].float(), dim=-1)
            top2 = torch.topk(probs, k=2)
            entropy = -(probs * probs.clamp_min(1e-12).log()).sum().item()
            token_entropies.append(entropy)
            token_top1_probs.append(top2.values[0].item())
            token_prob_margins.append((top2.values[0] - top2.values[1]).item())

        with torch.no_grad():
            fwd_out = self._model(full_ids, output_hidden_states=True, output_attentions=True)

        seq_len = int(full_ids.shape[1])
        gen_start = max(0, num_prompt_tokens - 1)  # hidden_states[t] predicts token t+1
        gen_end = seq_len - 1

        layer_hidden_norms: list[float] = []
        for layer_hidden in fwd_out.hidden_states:
            segment = layer_hidden[0, gen_start:gen_end, :]
            layer_hidden_norms.append(segment.float().norm(dim=-1).mean().item() if segment.shape[0] else 0.0)

        layer_attention_entropy: list[float] = []
        for layer_attn in fwd_out.attentions:
            segment = layer_attn[0, :, gen_start:gen_end, :]  # [heads, positions, keys]
            if segment.shape[1] == 0:
                layer_attention_entropy.append(0.0)
                continue
            probs = segment.float().clamp_min(1e-12)
            raw_entropy = -(probs * probs.log()).sum(dim=-1)  # [heads, positions]
            keys_visible = torch.arange(gen_start, gen_end, device=segment.device).float() + 1.0
            max_entropy = keys_visible.clamp_min(2.0).log()  # [positions]
            normalized = raw_entropy / max_entropy.unsqueeze(0)
            layer_attention_entropy.append(normalized.mean().item())

        return answer, ActivationCapture(
            num_layers=len(fwd_out.attentions),
            vocab_size=int(getattr(self._model.config, "vocab_size", len(self._tokenizer))),
            num_prompt_tokens=num_prompt_tokens,
            num_generated_tokens=len(token_entropies),
            layer_hidden_norms=layer_hidden_norms,
            layer_attention_entropy=layer_attention_entropy,
            token_entropies=token_entropies,
            token_prob_margins=token_prob_margins,
            token_top1_probs=token_top1_probs,
        )
