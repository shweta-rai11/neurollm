"""Local, open-weight Hugging Face model provider (Qwen2.5-1.5B-Instruct).

Unlike `MockProvider`/`OpenAIProvider`, this provider's internals are
genuinely inspectable: `get_activation_extractor()` returns an
`ActivationExtractor` that runs a real forward pass and reports hidden-state
/ attention / logit statistics (see `app.activations`). Research Mode uses
this provider specifically because its activations can be captured; the
mock/OpenAI providers cannot produce a `research` block for exactly that
reason (see routes_chat.py).

The model is loaded lazily (first request pays the cost) and cached at
module scope so repeated requests reuse the same weights. Device selection
prefers Apple MPS, falling back to CUDA, then CPU.
"""
from __future__ import annotations

import logging
import threading

from app.activations.extractor import ActivationExtractor, LocalHFActivationExtractor
from app.llm.provider import LLMProvider, LLMProviderError

logger = logging.getLogger("ai_brain")

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

_lock = threading.Lock()
_model = None
_tokenizer = None
_device: str | None = None


def _ensure_loaded() -> None:
    global _model, _tokenizer, _device
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise LLMProviderError(
                "local model dependencies not installed (torch/transformers)"
            ) from exc

        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        logger.info("Loading local model %s on %s ...", MODEL_NAME, device)
        try:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            # float16 and eager attention produced NaN/inf logits during
            # sampling on MPS (observed in local testing) -- bfloat16 has
            # float32's exponent range and doesn't exhibit this, at the
            # same memory cost as float16.
            dtype = torch.bfloat16 if device != "cpu" else torch.float32
            # "eager" attention is required for output_attentions=True -- the
            # default "sdpa" backend silently returns no attention weights,
            # which would make the attention-entropy signal a fabricated
            # zero instead of a real (if slower) measurement.
            model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=dtype, attn_implementation="eager")
            model.to(device)
            model.eval()
        except Exception as exc:  # noqa: BLE001 -- normalize into LLMProviderError per provider contract
            raise LLMProviderError(f"failed to load local model: {type(exc).__name__}") from exc

        logger.info("Local model %s loaded on %s.", MODEL_NAME, device)
        _model, _tokenizer, _device = model, tokenizer, device


def is_loaded() -> bool:
    return _model is not None


class LocalHFProvider(LLMProvider):
    """Real, inspectable open-weight provider used by Research Mode."""

    def __init__(self) -> None:
        self._extractor: LocalHFActivationExtractor | None = None

    def _extractor_instance(self) -> LocalHFActivationExtractor:
        _ensure_loaded()
        if self._extractor is None:
            self._extractor = LocalHFActivationExtractor(_model, _tokenizer, _device)
        return self._extractor

    def get_activation_extractor(self) -> ActivationExtractor:
        """Exposes the same extractor used internally -- callers that want a
        full ActivationCapture (research mode) call `.capture()` on this."""
        return self._extractor_instance()

    async def generate(self, query: str) -> str:
        extractor = self._extractor_instance()
        answer, _capture = extractor.capture(query)
        return answer

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        extractor = self._extractor_instance()
        return [extractor.generate_text(query, max_new_tokens=120) for _ in range(n)]

    def get_model_info(self) -> dict:
        return {
            "name": MODEL_NAME,
            "provider": "local_hf",
            "description": (
                "Local open-weight Qwen2.5-1.5B-Instruct model running on-device "
                "(MPS/CUDA/CPU) via Hugging Face Transformers. Hidden states, "
                "attention weights, and token logits are directly inspectable -- "
                "this is the provider Research Mode captures activations from."
            ),
        }
