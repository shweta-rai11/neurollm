"""Reduces a raw `ActivationCapture` into a bounded, real-valued feature
summary used by the virtual brain regions (`app.brain.regions`) and the
probes package (`app.probes`).

Layer-position heuristic used below: splitting the per-layer stack into
early/mid/late thirds and treating early/mid magnitude as more
lexical-processing-associated and late magnitude as more
abstraction/task-processing-associated is a common informal observation in
mechanistic-interpretability work, not a validated, per-model finding for
this specific model -- it is used here as a documented design heuristic for
the Language/Reasoning region split (see app/brain/regions.py), not as a
claim about what any specific layer "means".
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from app.activations.extractor import ActivationCapture


def _mean(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _thirds(values: list[float]) -> tuple[list[float], list[float], list[float]]:
    n = len(values)
    if n == 0:
        return [], [], []
    a = max(1, n // 3)
    b = max(a + 1, (2 * n) // 3)
    return values[:a], values[a:b], values[b:]


@dataclass
class ActivationSummary:
    early_layer_hidden_norm: float
    mid_layer_hidden_norm: float
    late_layer_hidden_norm: float
    hidden_norm_growth_ratio: float  # (late - early) / (early + eps); >0 = representation grows in magnitude with depth
    early_layer_attention_entropy: float
    late_layer_attention_entropy: float
    mean_attention_entropy: float
    mean_token_entropy: float
    max_token_entropy: float
    token_entropy_normalized: float  # mean_token_entropy / ln(vocab_size), in [0, ~1]
    mean_prob_margin: float
    min_prob_margin: float
    num_generated_tokens: int

    def as_feature_vector(self) -> list[float]:
        """Fixed-order numeric vector consumed by the probes (see probes/train.py)."""
        return [
            self.early_layer_hidden_norm,
            self.mid_layer_hidden_norm,
            self.late_layer_hidden_norm,
            self.hidden_norm_growth_ratio,
            self.early_layer_attention_entropy,
            self.late_layer_attention_entropy,
            self.mean_attention_entropy,
            self.mean_token_entropy,
            self.token_entropy_normalized,
            self.mean_prob_margin,
            self.min_prob_margin,
            float(self.num_generated_tokens),
        ]

    @staticmethod
    def feature_names() -> list[str]:
        return [
            "early_layer_hidden_norm", "mid_layer_hidden_norm", "late_layer_hidden_norm",
            "hidden_norm_growth_ratio", "early_layer_attention_entropy",
            "late_layer_attention_entropy", "mean_attention_entropy",
            "mean_token_entropy", "token_entropy_normalized",
            "mean_prob_margin", "min_prob_margin", "num_generated_tokens",
        ]


def summarize(capture: ActivationCapture) -> ActivationSummary:
    early_h, mid_h, late_h = _thirds(capture.layer_hidden_norms)
    early_a, _, late_a = _thirds(capture.layer_attention_entropy)

    early_norm = _mean(early_h)
    late_norm = _mean(late_h)
    growth_ratio = (late_norm - early_norm) / (early_norm + 1e-6)

    vocab_log = math.log(max(2, capture.vocab_size))
    mean_tok_entropy = _mean(capture.token_entropies)

    return ActivationSummary(
        early_layer_hidden_norm=early_norm,
        mid_layer_hidden_norm=_mean(mid_h),
        late_layer_hidden_norm=late_norm,
        hidden_norm_growth_ratio=growth_ratio,
        early_layer_attention_entropy=_mean(early_a),
        late_layer_attention_entropy=_mean(late_a),
        mean_attention_entropy=_mean(capture.layer_attention_entropy),
        mean_token_entropy=mean_tok_entropy,
        max_token_entropy=max(capture.token_entropies) if capture.token_entropies else 0.0,
        token_entropy_normalized=min(1.0, mean_tok_entropy / vocab_log) if vocab_log > 0 else 0.0,
        mean_prob_margin=_mean(capture.token_prob_margins),
        min_prob_margin=min(capture.token_prob_margins) if capture.token_prob_margins else 0.0,
        num_generated_tokens=capture.num_generated_tokens,
    )
