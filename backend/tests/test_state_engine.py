"""Unit tests for app.brain.state_engine.build_cognitive_state."""
from __future__ import annotations

from app.brain.hallucination import compute_initial_risk
from app.brain.neuromodulation import compute_neuromodulation
from app.brain.regions import BrainRegions, RegionScores
from app.brain.state_engine import build_cognitive_state
from tests._helpers import task, uncertainty

_NEUTRAL_REGION_PROFILE = BrainRegions(predicted=RegionScores(20, 20, 20, 20, 20), measured=None)


def _state(t, hrs, unc, pathway):
    neuromod = compute_neuromodulation(t, None, unc)
    return build_cognitive_state(t, _NEUTRAL_REGION_PROFILE, neuromod, hrs, unc, pathway)


def test_verify_pathway_yields_verification_driven_mode_and_status():
    t = task()
    hrs = compute_initial_risk(0.9, 0.9, 0.9)
    state = _state(t, hrs, None, "VERIFY")

    assert "VERIFICATION-DRIVEN" in state.interpretation.modes
    assert "VERIFICATION TRIGGERED" in state.interpretation.status
    assert any(r.title == "Do not treat this as a confident answer" for r in state.recommendations)


def test_analytical_pathway_yields_analytical_mode():
    t = task()
    hrs = compute_initial_risk(0.05, 0.05, 0.05)
    state = _state(t, hrs, None, "ANALYTICAL")
    assert "ANALYTICAL" in state.interpretation.modes


def test_creative_pathway_yields_exploratory_mode():
    t = task()
    hrs = compute_initial_risk(0.05, 0.05, 0.05)
    state = _state(t, hrs, None, "CREATIVE")
    assert "EXPLORATORY" in state.interpretation.modes


def test_high_uncertainty_low_verification_yields_exact_status():
    t = task(ambiguity=20, verification_requirement=0, factuality_requirement=0)
    unc = uncertainty(score=100, agreement=0, clusters=5)
    hrs = compute_initial_risk(0.05, 0.05, 0.05)
    state = _state(t, hrs, unc, "DIRECT")
    assert state.global_state.uncertainty > 70
    assert state.global_state.verification_need < 50
    assert "HIGH UNCERTAINTY" in state.interpretation.status


def test_recommendations_never_empty():
    t = task(
        complexity=0, logical_reasoning=0, creativity=0, planning=0,
        context_dependency=0, verification_requirement=0, risk=0,
        ambiguity=0, factuality_requirement=0,
    )
    hrs = compute_initial_risk(0.0, 0.0, 0.0)
    state = _state(t, hrs, None, "DIRECT")
    assert len(state.recommendations) >= 1


def test_brain_regions_and_neuromodulation_pass_through_to_response():
    t = task()
    hrs = compute_initial_risk(0.1, 0.1, 0.1)
    state = _state(t, hrs, None, "DIRECT")
    assert state.brain_regions.predicted.reasoning == 20
    assert state.brain_regions.measured is None
    assert 0 <= state.neuromodulation.serotonin_like <= 100
