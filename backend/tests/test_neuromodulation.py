"""Unit tests for app.brain.neuromodulation.compute_neuromodulation."""
from __future__ import annotations

from app.brain.neuromodulation import NeuromodulatorSignals, compute_neuromodulation
from tests._helpers import activation_summary, task, uncertainty

_FIELDS = ["dopamine_like", "serotonin_like", "norepinephrine_like", "acetylcholine_like"]


def _assert_in_range(signals: NeuromodulatorSignals) -> None:
    for field in _FIELDS:
        value = getattr(signals, field)
        assert 0 <= value <= 100, f"{field}={value} out of [0, 100]"


def test_high_agreement_and_low_ambiguity_yields_high_serotonin_like():
    signals = compute_neuromodulation(task(ambiguity=5), None, uncertainty(score=5, agreement=95))
    assert signals.serotonin_like > 70


def test_high_context_dependency_yields_high_acetylcholine_like():
    signals = compute_neuromodulation(task(context_dependency=90, verification_requirement=90), None, None)
    assert signals.acetylcholine_like > 70


def test_high_token_entropy_yields_higher_norepinephrine_like():
    calm = compute_neuromodulation(task(risk=10, ambiguity=10), activation_summary(token_entropy_normalized=0.05), None)
    alert = compute_neuromodulation(task(risk=10, ambiguity=10), activation_summary(token_entropy_normalized=0.95), None)
    assert alert.norepinephrine_like > calm.norepinephrine_like


def test_falls_back_to_defaults_without_activation_or_uncertainty():
    signals = compute_neuromodulation(task(), None, None)
    _assert_in_range(signals)


def test_all_signals_within_bounds_across_varied_inputs():
    cases = [
        (task(), None, None),
        (task(risk=100, ambiguity=100), activation_summary(token_entropy_normalized=1.0, mean_prob_margin=0.0), uncertainty(100, 0)),
        (task(risk=0, ambiguity=0), activation_summary(token_entropy_normalized=0.0, mean_prob_margin=1.0), uncertainty(0, 100)),
        (task(context_dependency=100, verification_requirement=100), None, None),
    ]
    for t, act, unc in cases:
        _assert_in_range(compute_neuromodulation(t, act, unc))
