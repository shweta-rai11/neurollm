"""Tests for app.profile.learning -- the behavioral EMA update rule.
Verifies bounded, correct-direction movement; never asserts a fingerprint
feature is involved (there is none in this module's inputs at all)."""
from __future__ import annotations

from app.profile.learning import InteractionOutcome, apply_interaction
from app.profile.params import neutral_profile


def test_high_hallucination_risk_pushes_verification_strength_up():
    outcome = InteractionOutcome(pathway="VERIFY", hallucination_risk=0.9, task_complexity=0.5)
    updated = apply_interaction(neutral_profile(), outcome)
    assert updated.verification_strength > 0.5


def test_low_hallucination_risk_pushes_verification_strength_down():
    outcome = InteractionOutcome(pathway="DIRECT", hallucination_risk=0.05, task_complexity=0.5)
    updated = apply_interaction(neutral_profile(), outcome)
    assert updated.verification_strength < 0.5


def test_negative_feedback_strongly_raises_verification_strength_even_with_low_risk():
    low_risk_no_feedback = apply_interaction(
        neutral_profile(), InteractionOutcome(pathway="DIRECT", hallucination_risk=0.1, task_complexity=0.5)
    )
    low_risk_bad_feedback = apply_interaction(
        neutral_profile(),
        InteractionOutcome(pathway="DIRECT", hallucination_risk=0.1, task_complexity=0.5, feedback_score=0.0),
    )
    assert low_risk_bad_feedback.verification_strength > low_risk_no_feedback.verification_strength


def test_creative_pathway_raises_exploration_and_lowers_exploitation():
    updated = apply_interaction(
        neutral_profile(), InteractionOutcome(pathway="CREATIVE", hallucination_risk=0.2, task_complexity=0.3)
    )
    assert updated.exploration > 0.5
    assert updated.exploitation < 0.5


def test_single_interaction_moves_params_by_a_bounded_small_step():
    outcome = InteractionOutcome(pathway="VERIFY", hallucination_risk=1.0, task_complexity=1.0, feedback_score=0.0)
    updated = apply_interaction(neutral_profile(), outcome)
    for name, value in updated.to_dict().items():
        assert abs(value - 0.5) < 0.2, f"{name} moved too far in a single interaction: {value}"


def test_repeated_interactions_converge_toward_target_without_exceeding_bounds():
    params = neutral_profile()
    outcome = InteractionOutcome(pathway="VERIFY", hallucination_risk=1.0, task_complexity=1.0)
    for _ in range(200):
        params = apply_interaction(params, outcome)
    assert 0.0 <= params.verification_strength <= 1.0
    assert params.verification_strength > 0.9
