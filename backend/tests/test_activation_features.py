"""Unit tests for app.activations.features.summarize (synthetic tensors --
no real model load required)."""
from __future__ import annotations

from app.activations.extractor import ActivationCapture
from app.activations.features import summarize


def _capture(**overrides) -> ActivationCapture:
    base = dict(
        num_layers=12,
        vocab_size=50000,
        num_prompt_tokens=10,
        num_generated_tokens=6,
        layer_hidden_norms=[float(i) for i in range(1, 14)],  # 13 = num_layers+1, monotonically increasing
        layer_attention_entropy=[0.9 - 0.05 * i for i in range(12)],  # decreasing with depth
        token_entropies=[0.1, 0.2, 0.15, 0.3, 0.25, 0.2],
        token_prob_margins=[0.8, 0.7, 0.75, 0.6, 0.65, 0.7],
        token_top1_probs=[0.9, 0.85, 0.88, 0.8, 0.82, 0.85],
    )
    base.update(overrides)
    return ActivationCapture(**base)


def test_summary_fields_finite_and_bounded():
    summary = summarize(_capture())
    assert summary.token_entropy_normalized >= 0.0
    assert summary.num_generated_tokens == 6
    assert len(summary.as_feature_vector()) == len(summary.feature_names())


def test_growth_ratio_positive_when_late_norms_exceed_early():
    summary = summarize(_capture(layer_hidden_norms=[1.0] * 4 + [10.0] * 5))
    assert summary.hidden_norm_growth_ratio > 0


def test_growth_ratio_negative_when_late_norms_below_early():
    summary = summarize(_capture(layer_hidden_norms=[10.0] * 4 + [1.0] * 5))
    assert summary.hidden_norm_growth_ratio < 0


def test_empty_capture_does_not_crash():
    summary = summarize(_capture(
        num_generated_tokens=0,
        layer_hidden_norms=[],
        layer_attention_entropy=[],
        token_entropies=[],
        token_prob_margins=[],
        token_top1_probs=[],
    ))
    assert summary.mean_token_entropy == 0.0
    assert summary.token_entropy_normalized == 0.0
    assert summary.mean_prob_margin == 0.0


def test_high_token_entropy_normalizes_toward_one_for_large_vocab():
    import math

    vocab_size = 1000
    max_entropy = math.log(vocab_size)
    summary = summarize(_capture(vocab_size=vocab_size, token_entropies=[max_entropy] * 3))
    assert summary.token_entropy_normalized > 0.95
