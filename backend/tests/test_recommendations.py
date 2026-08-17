"""Unit tests for app.cognitive_state.recommendations.build_recommendations."""
from __future__ import annotations

from app.cognitive_state.recommendations import build_recommendations
from app.cognitive_state.risk_model import compute_global_state
from tests._helpers import task, uncertainty

_VALID_SEVERITIES = {"info", "caution", "warning"}


def _build(t, unc=None, pathway="DIRECT"):
    global_state = compute_global_state(t, unc)
    return build_recommendations(t, global_state, pathway, unc)


def test_high_risk_yields_warning_with_human_review_language():
    recs = _build(task(risk=80))
    warning_recs = [r for r in recs if r.severity == "warning"]
    assert warning_recs, "expected at least one warning-severity recommendation"
    assert any("human review" in r.detail.lower() for r in warning_recs)


def test_high_creativity_yields_info_alternatives_recommendation():
    recs = _build(task(creativity=80))
    info_recs = [r for r in recs if r.severity == "info"]
    assert info_recs, "expected at least one info-severity recommendation"
    assert any("alternative" in r.title.lower() or "alternative" in r.detail.lower() for r in info_recs)


def test_verify_pathway_yields_leading_warning_recommendation():
    recs = _build(task(), pathway="VERIFY")
    assert recs[0].title == "Do not treat this as a confident answer"
    assert recs[0].severity == "warning"


def test_every_recommendation_has_valid_fields_across_scenarios():
    scenarios = [
        (task(), None, "DIRECT"),
        (task(risk=90), None, "DIRECT"),
        (task(creativity=90), None, "CREATIVE"),
        (task(complexity=90, logical_reasoning=90, planning=90), None, "ANALYTICAL"),
        (task(context_dependency=90), None, "DIRECT"),
        (task(), uncertainty(score=5, agreement=95), "DIRECT"),
        (task(), uncertainty(score=95, agreement=5), "VERIFY"),
    ]
    for t, unc, pathway in scenarios:
        recs = _build(t, unc, pathway)
        assert recs, "build_recommendations should never return an empty list"
        for rec in recs:
            assert rec.title and rec.title.strip()
            assert rec.detail and rec.detail.strip()
            assert rec.severity in _VALID_SEVERITIES
