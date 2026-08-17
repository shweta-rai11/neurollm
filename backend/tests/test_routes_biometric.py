"""Integration tests for /api/biometric/* -- same TestClient conventions as
tests/test_api_integration.py."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._helpers import synthetic_fingerprint_bytes


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _upload(client, seed, finger_label="right_index", consent="true"):
    data = synthetic_fingerprint_bytes(seed=seed)
    return client.post(
        "/api/biometric/enroll",
        files={"file": ("fp.png", data, "image/png")},
        data={"finger_label": finger_label, "consent": consent},
    )


def test_quality_check_returns_computed_fields(client):
    data = synthetic_fingerprint_bytes(seed=0)
    resp = client.post("/api/biometric/quality-check", files={"file": ("fp.png", data, "image/png")})
    assert resp.status_code == 200
    scan = resp.json()["scan"]
    assert scan["quality"]["quality_label"] in {"Good", "Fair", "Poor"}
    assert scan["pattern"] in {"arch", "loop", "whorl"}


def test_enroll_requires_consent(client):
    resp = _upload(client, seed=1, consent="false")
    assert resp.status_code == 400


def test_enroll_rejects_garbage_upload(client):
    resp = client.post(
        "/api/biometric/enroll",
        files={"file": ("fp.png", b"not an image", "image/png")},
        data={"finger_label": "right_index", "consent": "true"},
    )
    assert resp.status_code == 400


def test_enroll_creates_new_profile(client):
    resp = _upload(client, seed=2)
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_existing_profile"] is False
    assert body["virtual_brain_parameters"]["attention_baseline"] == 0.5


def test_same_fingerprint_matches_existing_profile(client):
    first = _upload(client, seed=4).json()
    second = _upload(client, seed=4).json()
    assert second["matched_existing_profile"] is True
    assert second["profile_id"] == first["profile_id"]


def test_different_fingerprint_creates_a_different_profile(client):
    a = _upload(client, seed=6).json()
    b = _upload(client, seed=14).json()
    assert a["profile_id"] != b["profile_id"]


def test_get_delete_export_reset_lifecycle(client):
    profile_id = _upload(client, seed=18).json()["profile_id"]

    resp = client.get(f"/api/biometric/profile/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["enrolled_finger_count"] == 1

    resp = client.get(f"/api/biometric/profile/{profile_id}/export")
    assert resp.status_code == 200
    export = resp.json()["export"]
    assert export["profile_id"] == profile_id
    assert "enrolled_fingers" in export
    # Privacy: export must never contain raw image/template bytes.
    assert "encrypted_template" not in str(export)

    resp = client.post(f"/api/biometric/profile/{profile_id}/reset")
    assert resp.status_code == 200
    assert client.get(f"/api/biometric/profile/{profile_id}").json()["enrolled_finger_count"] == 0

    resp = client.delete(f"/api/biometric/profile/{profile_id}")
    assert resp.status_code == 200
    assert client.get(f"/api/biometric/profile/{profile_id}").status_code == 404


def test_unknown_profile_returns_404(client):
    assert client.get("/api/biometric/profile/does-not-exist").status_code == 404
    assert client.delete("/api/biometric/profile/does-not-exist").status_code == 404
