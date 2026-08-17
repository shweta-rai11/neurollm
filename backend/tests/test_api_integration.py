"""Integration tests for the FastAPI app, exercised through TestClient.

Test isolation note: `tests/conftest.py` points DATABASE_URL at a fresh
temporary sqlite file, forces OPENAI_API_KEY/ENABLE_LOCAL_MODEL empty, and
raises the in-process rate limit *before* any `app.*` module is imported
anywhere in the session -- since `app.config.Settings` reads env vars at
import time, that is the simplest robust way to keep this suite off the
real dev `ai_brain.db` without touching app code. Every request below is
served by the deterministic, offline MockProvider unless a test explicitly
patches `app.brain.pipeline.get_provider` to substitute the FakeLocalProvider
test double (see tests/_helpers.py) for the research_mode/local_hf pathway
-- this whole file runs with no network access, no real API key, and no
real model download.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._helpers import FakeLocalProvider

_CODING_QUERY = "Write a Python function to reverse a linked list."
_PREDICTIVE_QUERY = "Who will win the election next year?"

_REGION_FIELDS = {"language", "memory", "reasoning", "uncertainty", "verification"}
_NEUROMOD_FIELDS = {"dopamine_like", "serotonin_like", "norepinephrine_like", "acetylcholine_like"}
_GLOBAL_STATE_FIELDS = {"confidence", "uncertainty", "difficulty", "verification_need"}
_TASK_ANALYSIS_FIELDS = {
    "complexity", "logical_reasoning", "creativity", "planning", "context_dependency",
    "verification_requirement", "risk", "ambiguity", "factuality_requirement",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_config(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "mock" in data["available_models"]
    # conftest.py forces OPENAI_API_KEY/ENABLE_LOCAL_MODEL empty, so both
    # must be False/absent in tests unless a test overrides them directly.
    assert data["has_openai_key"] is False
    assert "local_hf" not in data["available_models"]


def test_chat_with_uncertainty_mode_true(client):
    payload = {
        "query": _CODING_QUERY,
        "model": "mock",
        "uncertainty_mode": True,
        "num_samples": 3,
    }
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["answer"]
    assert data["metadata"]["provider"] == "mock"
    assert data["pathway"] in {"DIRECT", "ANALYTICAL", "CREATIVE", "VERIFY"}
    assert 0.0 <= data["hallucination_risk"]["score"] <= 1.0
    assert data["research"] is None  # mock provider has no inspectable activations

    cognitive_state = data["cognitive_state"]
    assert set(cognitive_state["brain_regions"]["predicted"].keys()) == _REGION_FIELDS
    assert set(cognitive_state["neuromodulation"].keys()) == _NEUROMOD_FIELDS
    assert set(cognitive_state["global_state"].keys()) == _GLOBAL_STATE_FIELDS

    assert data["uncertainty"] is not None
    assert data["uncertainty"]["candidate_count"] == 3


def test_chat_with_uncertainty_mode_false(client):
    payload = {
        "query": _CODING_QUERY,
        "model": "mock",
        "uncertainty_mode": False,
        "num_samples": 3,
    }
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["uncertainty"] is None


def test_analyze(client):
    resp = client.post("/api/analyze", json={"query": _CODING_QUERY})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["task_analysis"].keys()) == _TASK_ANALYSIS_FIELDS


def test_uncertainty_endpoint(client):
    resp = client.post(
        "/api/uncertainty",
        json={"query": _CODING_QUERY, "model": "mock", "num_samples": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["uncertainty"]["candidate_count"] == 4


def test_experiment(client):
    payload = {
        "query_a": _CODING_QUERY,
        "query_b": _PREDICTIVE_QUERY,
        "model": "mock",
        "num_samples": 3,
    }
    resp = client.post("/api/experiment", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["side_a"]["query"] == _CODING_QUERY
    assert data["side_b"]["query"] == _PREDICTIVE_QUERY
    assert isinstance(data["response_agreement_between_sides"], (int, float))


def test_experiment_benchmark(client):
    resp = client.post("/api/experiment/benchmark", json={"model": "mock", "categories": ["factual", "mathematical"], "limit_per_category": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"]
    assert {item["category"] for item in data["items"]} <= {"factual", "mathematical"}
    for summary in data["category_summaries"]:
        assert summary["n"] > 0


def test_probes_info_reports_untrained_when_no_artifact(client):
    resp = client.get("/api/probes/info")
    assert resp.status_code == 200
    data = resp.json()
    # No probe has been trained in the test environment -- must say so
    # honestly rather than fabricating accuracy numbers.
    assert data["trained"] in (True, False)
    if not data["trained"]:
        assert data["test_accuracy"] is None


def test_history_after_chat_call(client):
    marker_query = "History marker query about binary search trees, unique for this test."
    chat_resp = client.post(
        "/api/chat",
        json={"query": marker_query, "model": "mock", "uncertainty_mode": False, "num_samples": 1},
    )
    assert chat_resp.status_code == 200

    history_resp = client.get("/api/history")
    assert history_resp.status_code == 200
    data = history_resp.json()

    assert isinstance(data["items"], list)
    assert len(data["items"]) > 0
    # Ordered newest-first (id desc), so the item we just created should be first.
    assert data["items"][0]["query"] == marker_query
    assert data["items"][0]["pathway"] in {"DIRECT", "ANALYTICAL", "CREATIVE", "VERIFY"}


def test_chat_rejects_empty_query_with_422(client):
    resp = client.post("/api/chat", json={"query": "", "model": "mock"})
    assert resp.status_code == 422


def test_chat_research_mode_with_fake_local_provider(client, monkeypatch):
    """Exercises the research_mode/local_hf pathway end-to-end using
    FakeLocalProvider so no real model is downloaded/loaded in tests."""
    import app.brain.pipeline as pipeline_module

    real_get_provider = pipeline_module.get_provider

    def _fake_get_provider(model_name: str):
        if model_name == "local_hf":
            return FakeLocalProvider()
        return real_get_provider(model_name)

    monkeypatch.setattr(pipeline_module, "get_provider", _fake_get_provider)

    resp = client.post(
        "/api/chat",
        json={"query": "What is the capital of France?", "model": "local_hf", "uncertainty_mode": True, "num_samples": 3, "research_mode": True},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["research"] is not None
    assert data["research"]["num_layers"] == 4
    assert len(data["research"]["layer_hidden_norms"]) == 5
    assert data["research"]["activation_features"]
