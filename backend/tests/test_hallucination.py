"""Unit tests for app.brain.hallucination (Hallucination Risk Score)."""
from __future__ import annotations

from app.brain.hallucination import compute_initial_risk, refine_with_verifier


def test_score_bounded_in_zero_one():
    risk = compute_initial_risk(0.5, 0.5, 0.5)
    assert 0.0 <= risk.score <= 1.0


def test_low_signals_yield_low_risk():
    risk = compute_initial_risk(0.05, 0.05, 0.05)
    assert risk.score < 0.2


def test_high_signals_yield_high_risk():
    risk = compute_initial_risk(0.95, 0.95, 0.95)
    assert risk.score > 0.8


def test_retrieval_disagreement_weight_is_inert():
    """The MVP has no retrieval pathway -- passing retrieval_disagreement
    must not change the score (weight is fixed at 0, not just usually 0)."""
    without = compute_initial_risk(0.4, 0.4, 0.4, retrieval_disagreement=0.0)
    with_disagreement = compute_initial_risk(0.4, 0.4, 0.4, retrieval_disagreement=1.0)
    assert without.score == with_disagreement.score


def test_extreme_inputs_stay_clamped():
    risk = compute_initial_risk(2.0, -1.0, 5.0)
    assert 0.0 <= risk.score <= 1.0


def test_refine_with_verifier_disagreement_increases_score():
    base = compute_initial_risk(0.3, 0.3, 0.3)
    refined_agree = refine_with_verifier(base, verifier_disagreement=0.0)
    refined_disagree = refine_with_verifier(base, verifier_disagreement=1.0)
    assert refined_disagree.score > refined_agree.score
    assert "verifier_disagreement" in refined_disagree.components


def test_refine_with_verifier_stays_bounded():
    base = compute_initial_risk(0.9, 0.9, 0.9)
    refined = refine_with_verifier(base, verifier_disagreement=1.0)
    assert 0.0 <= refined.score <= 1.0


def test_refine_without_retrieval_matches_original_self_critique_only_blend():
    """Omitting retrieval_disagreement (its default) must reproduce the
    exact pre-retrieval behavior -- this is the backward-compatibility
    guarantee the retrieval feature was built on top of."""
    base = compute_initial_risk(0.4, 0.4, 0.4)
    explicit_none = refine_with_verifier(base, verifier_disagreement=0.6, retrieval_disagreement=None)
    omitted = refine_with_verifier(base, verifier_disagreement=0.6)
    assert explicit_none.score == omitted.score
    assert explicit_none.components == omitted.components
    # compute_initial_risk's components dict always carries a
    # retrieval_disagreement key (inert, fixed at 0.0 -- see hallucination.py's
    # module docstring); refine_with_verifier without real retrieval must
    # leave it untouched at that inert value, not blend in a computed one.
    assert omitted.components["retrieval_disagreement"] == 0.0


def test_refine_with_retrieval_disagreement_increases_score():
    base = compute_initial_risk(0.3, 0.3, 0.3)
    low_retrieval_disagreement = refine_with_verifier(base, verifier_disagreement=0.5, retrieval_disagreement=0.0)
    high_retrieval_disagreement = refine_with_verifier(base, verifier_disagreement=0.5, retrieval_disagreement=1.0)
    assert high_retrieval_disagreement.score > low_retrieval_disagreement.score
    assert "retrieval_disagreement" in high_retrieval_disagreement.components


def test_refine_with_retrieval_weighs_it_more_than_self_critique_alone():
    """Real external evidence should move the score more than self-critique
    alone would, for the same disagreement magnitude -- that's the whole
    point of adding retrieval (see hallucination.py module docstring)."""
    base = compute_initial_risk(0.3, 0.3, 0.3)
    self_critique_only = refine_with_verifier(base, verifier_disagreement=1.0)
    with_retrieval_agreeing = refine_with_verifier(base, verifier_disagreement=1.0, retrieval_disagreement=0.0)
    # Retrieval agreeing (low disagreement) while self-critique still flags
    # disagreement should pull the score down relative to self-critique-only,
    # since retrieval now carries the larger weight.
    assert with_retrieval_agreeing.score < self_critique_only.score


def test_refine_with_retrieval_stays_bounded():
    base = compute_initial_risk(0.9, 0.9, 0.9)
    refined = refine_with_verifier(base, verifier_disagreement=1.0, retrieval_disagreement=1.0)
    assert 0.0 <= refined.score <= 1.0
