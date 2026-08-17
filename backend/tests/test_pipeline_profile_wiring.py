"""Regression guard for the Individual Computational Profile wiring into
app.brain: `profile=None` (the default) must behave exactly like the
pre-profile code, and a supplied profile must shift output only by the
documented, bounded amount -- never past [0, 100] / valid thresholds.
"""
from __future__ import annotations

from app.brain.executive_controller import _effective_hrs_threshold, select_pathway
from app.brain.hallucination import compute_initial_risk
from app.brain.neuromodulation import compute_neuromodulation
from app.brain.regions import predicted_profile
from app.profile.params import ComputationalProfileParams
from tests._helpers import task

_QUERY = "Explain step by step why the sky is blue."


def test_predicted_profile_omitted_and_explicit_none_are_identical():
    t = task()
    a = predicted_profile(_QUERY, t)
    b = predicted_profile(_QUERY, t, profile=None)
    assert a == b


def test_neuromodulation_omitted_and_explicit_none_are_identical():
    t = task()
    a = compute_neuromodulation(t, None, None)
    b = compute_neuromodulation(t, None, None, profile=None)
    assert a == b


def test_hrs_threshold_omitted_and_explicit_none_are_identical():
    from app.brain.neuromodulation import NeuromodulatorSignals

    neuromod = NeuromodulatorSignals(dopamine_like=50, serotonin_like=50, norepinephrine_like=50, acetylcholine_like=50)
    assert _effective_hrs_threshold(neuromod) == _effective_hrs_threshold(neuromod, profile=None)


def test_high_verification_strength_profile_lowers_hrs_threshold():
    from app.brain.neuromodulation import NeuromodulatorSignals

    neuromod = NeuromodulatorSignals(dopamine_like=50, serotonin_like=50, norepinephrine_like=50, acetylcholine_like=50)
    baseline = _effective_hrs_threshold(neuromod)
    cautious_profile = ComputationalProfileParams(verification_strength=1.0)
    cautious = _effective_hrs_threshold(neuromod, profile=cautious_profile)
    assert cautious < baseline
    assert baseline - cautious <= 0.075 + 1e-9


def test_region_scores_stay_within_bounds_with_extreme_profile():
    t = task(logical_reasoning=90, complexity=90, verification_requirement=90, factuality_requirement=90)
    extreme = ComputationalProfileParams(
        attention_baseline=1.0, working_memory_baseline=1.0, verification_strength=1.0,
        memory_retrieval=1.0, uncertainty_sensitivity=1.0,
    )
    result = predicted_profile(_QUERY, t, profile=extreme)
    for value in (result.language, result.memory, result.reasoning, result.uncertainty, result.verification):
        assert 0 <= value <= 100


def test_neutral_profile_params_produce_same_result_as_no_profile():
    """A profile at exactly 0.5 (neutral) everywhere contributes a zero
    delta by construction -- personalization should be a no-op until the
    profile has actually learned something."""
    t = task()
    neutral = ComputationalProfileParams()
    with_neutral = predicted_profile(_QUERY, t, profile=neutral)
    without = predicted_profile(_QUERY, t, profile=None)
    assert with_neutral == without


def test_select_pathway_accepts_optional_profile_without_error():
    t = task(risk=80, ambiguity=80)
    hrs = compute_initial_risk(0.9, 0.9, 0.9)
    from app.brain.neuromodulation import NeuromodulatorSignals
    from app.brain.regions import RegionScores

    neuromod = NeuromodulatorSignals(dopamine_like=50, serotonin_like=50, norepinephrine_like=50, acetylcholine_like=50)
    region = RegionScores(20, 20, 20, 20, 20)
    decision_no_profile = select_pathway(t, region, hrs, neuromod)
    decision_with_profile = select_pathway(t, region, hrs, neuromod, profile=ComputationalProfileParams())
    assert decision_no_profile.pathway == decision_with_profile.pathway
