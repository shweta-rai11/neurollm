"""Unit tests for app.brain.regions (predicted + measured region profiles)."""
from __future__ import annotations

from app.brain.regions import RegionScores, compute_brain_regions
from tests._helpers import activation_summary, task, uncertainty

_REGION_FIELDS = ["language", "memory", "reasoning", "uncertainty", "verification"]


def _assert_in_range(regions: RegionScores) -> None:
    for field in _REGION_FIELDS:
        value = getattr(regions, field)
        assert 0 <= value <= 100, f"{field}={value} out of [0, 100]"


def test_predicted_only_when_no_activation_available():
    result = compute_brain_regions("What is the capital of France?", task(), None, None)
    assert result.measured is None
    _assert_in_range(result.predicted)


def test_measured_present_when_activation_available():
    result = compute_brain_regions(
        "What is the capital of France?", task(), activation_summary(), uncertainty(score=20, agreement=80)
    )
    assert result.measured is not None
    _assert_in_range(result.measured)


def test_reasoning_task_yields_higher_predicted_reasoning():
    low = compute_brain_regions("hi", task(logical_reasoning=5, complexity=5, planning=5), None, None)
    high = compute_brain_regions(
        "Explain step by step why this proof holds and derive the result.",
        task(logical_reasoning=90, complexity=90, planning=80),
        None,
        None,
    )
    assert high.predicted.reasoning > low.predicted.reasoning


def test_memory_measured_inherits_predicted_when_no_retrieval_pathway():
    t = task(context_dependency=70, factuality_requirement=60)
    result = compute_brain_regions("query", t, activation_summary(), None)
    assert result.measured.memory == result.predicted.memory


def test_high_late_layer_growth_yields_higher_measured_reasoning():
    low_growth = compute_brain_regions(
        "q", task(), activation_summary(hidden_norm_growth_ratio=-0.5, late_layer_attention_entropy=0.1), None
    )
    high_growth = compute_brain_regions(
        "q", task(), activation_summary(hidden_norm_growth_ratio=1.0, late_layer_attention_entropy=0.9), None
    )
    assert high_growth.measured.reasoning > low_growth.measured.reasoning


def test_high_token_entropy_yields_higher_measured_uncertainty():
    confident = compute_brain_regions(
        "q", task(), activation_summary(token_entropy_normalized=0.05, mean_prob_margin=0.9), None
    )
    uncertain = compute_brain_regions(
        "q", task(), activation_summary(token_entropy_normalized=0.9, mean_prob_margin=0.05), None
    )
    assert uncertain.measured.uncertainty > confident.measured.uncertainty


def test_extreme_inputs_stay_clamped():
    extreme_task = task(
        complexity=100, logical_reasoning=100, creativity=100, planning=100,
        context_dependency=100, verification_requirement=100, risk=100,
        ambiguity=100, factuality_requirement=100,
    )
    result = compute_brain_regions(
        "x" * 500, extreme_task, activation_summary(token_entropy_normalized=1.0, mean_prob_margin=0.0), uncertainty(100, 0)
    )
    _assert_in_range(result.predicted)
    _assert_in_range(result.measured)
