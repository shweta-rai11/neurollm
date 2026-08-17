"""Unit tests for app.brain.executive_controller."""
from __future__ import annotations

import pytest

from app.brain import executive_controller
from app.brain.executive_controller import Pathway, run_verification_pathway, select_pathway
from app.brain.hallucination import compute_initial_risk
from app.brain.neuromodulation import compute_neuromodulation
from app.brain.regions import RegionScores
from app.models.schemas import CandidateResponse
from app.retrieval.brave_search import SearchResult
from tests._helpers import task, uncertainty


def _neutral_neuromod():
    return compute_neuromodulation(task(), None, None)


def test_high_hallucination_risk_routes_to_verify():
    hrs = compute_initial_risk(0.95, 0.95, 0.95)
    decision = select_pathway(task(), RegionScores(50, 50, 50, 50, 50), hrs, _neutral_neuromod())
    assert decision.pathway == Pathway.VERIFY


def test_low_risk_high_reasoning_routes_to_analytical():
    hrs = compute_initial_risk(0.05, 0.05, 0.05)
    t = task(logical_reasoning=90, complexity=80, creativity=5)
    decision = select_pathway(t, RegionScores(50, 50, 90, 20, 50), hrs, _neutral_neuromod())
    assert decision.pathway == Pathway.ANALYTICAL


def test_low_risk_high_creativity_routes_to_creative():
    hrs = compute_initial_risk(0.05, 0.05, 0.05)
    t = task(creativity=90, logical_reasoning=10)
    decision = select_pathway(t, RegionScores(50, 50, 10, 20, 50), hrs, _neutral_neuromod())
    assert decision.pathway == Pathway.CREATIVE


def test_low_signals_route_to_direct():
    hrs = compute_initial_risk(0.05, 0.05, 0.05)
    decision = select_pathway(task(), RegionScores(20, 20, 20, 20, 20), hrs, _neutral_neuromod())
    assert decision.pathway == Pathway.DIRECT


def test_high_norepinephrine_like_lowers_effective_hrs_threshold():
    """Same borderline HRS score should be more likely to trigger VERIFY
    when the norepinephrine-like (alertness) signal is elevated -- this is
    the neuromodulation-feeds-back-into-routing requirement."""
    borderline_hrs = compute_initial_risk(0.5, 0.5, 0.5)
    calm = compute_neuromodulation(task(risk=0, ambiguity=0), None, uncertainty(score=0, agreement=100))
    alert = compute_neuromodulation(task(risk=100, ambiguity=100), None, uncertainty(score=100, agreement=0))

    calm_decision = select_pathway(task(), RegionScores(20, 20, 20, 20, 20), borderline_hrs, calm)
    alert_decision = select_pathway(task(), RegionScores(20, 20, 20, 20, 20), borderline_hrs, alert)

    assert alert_decision.hrs_threshold_used <= calm_decision.hrs_threshold_used


class _FakeProvider:
    def __init__(self, verifier_response: str):
        self._verifier_response = verifier_response

    async def generate(self, query: str) -> str:
        return self._verifier_response

    async def generate_multiple(self, query: str, n: int) -> list[str]:
        return [self._verifier_response] * n

    def get_model_info(self) -> dict:
        return {"name": "fake", "provider": "fake", "description": "test double"}


def _make_uncertainty_with_candidates():
    candidates = [
        CandidateResponse(text="Paris", cluster_id=0),
        CandidateResponse(text="Paris, France", cluster_id=0),
        CandidateResponse(text="Lyon", cluster_id=1),
    ]
    return uncertainty(score=60, agreement=40, clusters=2, candidates=candidates)


@pytest.fixture(autouse=True)
def _retrieval_unavailable_by_default(monkeypatch):
    """conftest.py already forces BRAVE_SEARCH_API_KEY empty, but
    `retrieval_is_available` is imported into this module's namespace, so
    patch it here too for tests that don't explicitly enable retrieval."""
    monkeypatch.setattr(executive_controller, "retrieval_is_available", lambda: False)


@pytest.mark.asyncio
async def test_verification_pathway_returns_direct_answer_when_verifier_agrees():
    unc = _make_uncertainty_with_candidates()
    hrs = compute_initial_risk(0.5, 0.5, 0.5)
    provider = _FakeProvider("CONSISTENT. The candidates agree on Paris.")

    answer, refined, verifier_text, retrieval_text, search_results = await run_verification_pathway(
        provider, "What is the capital of France?", unc, hrs
    )

    assert "don't have strong evidence" not in answer
    assert refined.score <= hrs.score + 1e-9 or refined.score < 1.0
    assert "CONSISTENT" in verifier_text.upper()
    assert retrieval_text == ""
    assert search_results == []
    # inert (fixed at 0.0), not a computed value -- retrieval didn't run
    assert refined.components["retrieval_disagreement"] == 0.0


@pytest.mark.asyncio
async def test_verification_pathway_abstains_when_verifier_disagrees_and_risk_stays_high():
    unc = _make_uncertainty_with_candidates()
    hrs = compute_initial_risk(0.9, 0.9, 0.9)
    provider = _FakeProvider("INCONSISTENT. The candidates disagree.")

    answer, refined, _verifier_text, _retrieval_text, _search_results = await run_verification_pathway(
        provider, "obscure question", unc, hrs
    )

    # With a high initial HRS and a disagreeing verifier, the refined score
    # must stay well above the abstain threshold (0.65) even though the
    # blend can pull it slightly below the raw initial score.
    assert refined.score >= 0.65
    assert "don't have strong evidence" in answer


@pytest.mark.asyncio
async def test_verification_pathway_uses_retrieval_when_available(monkeypatch):
    monkeypatch.setattr(executive_controller, "retrieval_is_available", lambda: True)

    sample_results = [SearchResult(title="Paris", snippet="Capital of France", url="https://example.com/paris")]

    async def _fake_fact_check(provider, query, answer):
        return 0.1, "SUPPORTED. Matches the search results.", sample_results

    monkeypatch.setattr(executive_controller, "fact_check", _fake_fact_check)

    unc = _make_uncertainty_with_candidates()
    hrs = compute_initial_risk(0.5, 0.5, 0.5)
    provider = _FakeProvider("CONSISTENT. The candidates agree on Paris.")

    answer, refined, verifier_text, retrieval_text, search_results = await run_verification_pathway(
        provider, "What is the capital of France?", unc, hrs
    )

    assert search_results == sample_results
    assert "SUPPORTED" in retrieval_text.upper()
    assert "retrieval_disagreement" in refined.components
    assert refined.components["retrieval_disagreement"] == 0.1


@pytest.mark.asyncio
async def test_verification_pathway_abstention_note_mentions_retrieved_evidence_when_present(monkeypatch):
    monkeypatch.setattr(executive_controller, "retrieval_is_available", lambda: True)

    sample_results = [SearchResult(title="X", snippet="contradicts", url="https://example.com/x")]

    async def _fake_fact_check(provider, query, answer):
        return 0.9, "CONTRADICTED.", sample_results

    monkeypatch.setattr(executive_controller, "fact_check", _fake_fact_check)

    unc = _make_uncertainty_with_candidates()
    hrs = compute_initial_risk(0.9, 0.9, 0.9)
    provider = _FakeProvider("INCONSISTENT.")

    answer, refined, _verifier_text, _retrieval_text, _search_results = await run_verification_pathway(
        provider, "obscure question", unc, hrs
    )

    assert refined.score >= 0.65
    assert "retrieved evidence" in answer
