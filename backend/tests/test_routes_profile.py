"""Integration tests for /api/chat with profile_id, and /api/profile/*."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._helpers import synthetic_fingerprint_bytes


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def profile_id(client):
    data = synthetic_fingerprint_bytes(seed=27)
    resp = client.post(
        "/api/biometric/enroll",
        files={"file": ("fp.png", data, "image/png")},
        data={"finger_label": "right_index", "consent": "true"},
    )
    assert resp.status_code == 200
    return resp.json()["profile_id"]


def test_chat_without_profile_id_has_no_profile_influence(client):
    resp = client.post("/api/chat", json={"query": "What is the capital of France?", "model": "mock"})
    assert resp.status_code == 200
    assert resp.json()["profile_influence"] is None


def test_chat_with_unknown_profile_id_404s(client):
    resp = client.post("/api/chat", json={"query": "Hello", "model": "mock", "profile_id": "does-not-exist"})
    assert resp.status_code == 404


def test_chat_with_profile_id_attaches_influence_and_records_interaction(client, profile_id):
    resp = client.post(
        "/api/chat",
        json={"query": "Solve for x: 2x + 3 = 11", "model": "mock", "uncertainty_mode": True, "num_samples": 3, "profile_id": profile_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    influence = body["profile_influence"]
    assert influence["applied"] is True
    assert influence["task_category"]
    assert len(influence["candidate_systems"]) > 0
    assert "not a biological measurement" in influence["disclaimer"] or "not measure" in influence["disclaimer"]

    evo = client.get(f"/api/profile/{profile_id}/evolution")
    assert evo.status_code == 200
    assert evo.json()["n_interactions"] >= 1


def test_evolution_starts_at_neutral_defaults(client):
    data = synthetic_fingerprint_bytes(seed=30)
    fresh_profile_id = client.post(
        "/api/biometric/enroll",
        files={"file": ("fp.png", data, "image/png")},
        data={"finger_label": "left_thumb", "consent": "true"},
    ).json()["profile_id"]

    evo = client.get(f"/api/profile/{fresh_profile_id}/evolution").json()
    assert all(v == 0.5 for v in evo["initial"].values())
    assert evo["current"] == evo["initial"]
    assert evo["n_interactions"] == 0


def test_feedback_updates_profile_params(client, profile_id):
    client.post(
        "/api/chat",
        json={"query": "Is Paris the capital of France?", "model": "mock", "profile_id": profile_id},
    )

    # There's no interaction id in the /api/chat response by design (it's an
    # internal learning record, not an answer field) -- look it up directly,
    # same as a real feedback UI would via a "was this helpful?" affordance
    # tied to a specific stored interaction.
    from app.database.database import SessionLocal
    from app.database.models import ProfileInteraction

    db = SessionLocal()
    try:
        interaction = (
            db.query(ProfileInteraction)
            .filter(ProfileInteraction.profile_id == profile_id)
            .order_by(ProfileInteraction.id.desc())
            .first()
        )
        assert interaction is not None
        interaction_id = interaction.id
    finally:
        db.close()

    resp = client.post(f"/api/profile/{profile_id}/feedback", json={"interaction_id": interaction_id, "feedback_score": 0.0})
    assert resp.status_code == 200
    assert 0.0 <= resp.json()["updated_parameters"]["verification_strength"] <= 1.0


def test_feedback_unknown_interaction_404s(client, profile_id):
    resp = client.post(f"/api/profile/{profile_id}/feedback", json={"interaction_id": 999999, "feedback_score": 1.0})
    assert resp.status_code == 404


def test_counterfactual_runs_baseline_and_override(client, profile_id):
    resp = client.post(
        "/api/profile/counterfactual",
        json={
            "query": "Should I take this new job offer?",
            "model": "mock",
            "profile_id": profile_id,
            "overrides": {"verification_strength": 1.0, "exploration": 0.0},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["baseline"]["parameters_used"] != body["counterfactual"]["parameters_used"]
    assert "not a claim about the user's real cognition" in body["note"]


def test_counterfactual_without_profile_id_uses_neutral_baseline(client):
    resp = client.post(
        "/api/profile/counterfactual",
        json={"query": "Write a short poem about the sea.", "model": "mock", "overrides": {"exploration": 1.0}},
    )
    assert resp.status_code == 200
    assert resp.json()["baseline"]["parameters_used"]["exploration"] == 0.5


def test_research_compare_reports_three_conditions(client, profile_id):
    resp = client.post(
        "/api/profile/research/compare",
        json={"profile_id": profile_id, "model": "mock", "categories": ["factual"], "limit_per_category": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    labels = {c["condition"] for c in body["conditions"]}
    assert labels == {"A", "B", "C"}
    assert body["honest_summary"]


def test_research_compare_without_profile_id_states_c_equals_b(client):
    resp = client.post(
        "/api/profile/research/compare",
        json={"model": "mock", "categories": ["factual"], "limit_per_category": 1},
    )
    assert resp.status_code == 200
    assert "by construction" in resp.json()["honest_summary"]
