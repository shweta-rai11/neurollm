"""Unit tests for app.probes.infer, using a tiny synthetic pre-fit pipeline
(no real model load / no data/benchmark.json dependency)."""
from __future__ import annotations

import json

import pytest

from app.probes import infer as infer_module
from app.probes.feature_builder import FEATURE_NAMES, build_feature_vector
from tests._helpers import activation_summary, task


@pytest.fixture()
def fitted_probe(tmp_path, monkeypatch):
    import joblib
    from sklearn.linear_model import LogisticRegression

    n_features = len(FEATURE_NAMES)
    X = [[0.0] * n_features, [1.0] * n_features, [0.0] * n_features, [1.0] * n_features]
    y = ["factual", "creative", "factual", "creative"]

    clf = LogisticRegression(max_iter=200)
    clf.fit(X, y)

    model_path = tmp_path / "probe_pipeline.joblib"
    meta_path = tmp_path / "probe_meta.json"
    joblib.dump(clf, model_path)
    meta_path.write_text(json.dumps({
        "probe_type": "logistic_regression",
        "test_accuracy": 1.0,
        "n_train": 4,
        "n_test": 0,
        "categories": ["factual", "creative"],
        "trained_at": "test",
        "feature_names": FEATURE_NAMES,
    }))

    monkeypatch.setattr(infer_module, "_MODEL_PATH", model_path)
    monkeypatch.setattr(infer_module, "_META_PATH", meta_path)
    monkeypatch.setattr(infer_module, "_pipeline", None)
    monkeypatch.setattr(infer_module, "_meta", None)
    monkeypatch.setattr(infer_module, "_load_attempted", False)
    return clf


def test_is_unavailable_with_no_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(infer_module, "_MODEL_PATH", tmp_path / "missing.joblib")
    monkeypatch.setattr(infer_module, "_META_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(infer_module, "_pipeline", None)
    monkeypatch.setattr(infer_module, "_meta", None)
    monkeypatch.setattr(infer_module, "_load_attempted", False)

    assert infer_module.is_available() is False
    assert infer_module.predict_category(task(), activation_summary()) is None


def test_predicts_category_with_probabilities(fitted_probe):
    assert infer_module.is_available() is True
    prediction = infer_module.predict_category(task(), activation_summary())

    assert prediction is not None
    assert prediction.predicted_category in {"factual", "creative"}
    assert abs(sum(prediction.probabilities.values()) - 1.0) < 1e-6
    assert 0.0 <= prediction.confidence <= 1.0
    assert prediction.probe_type == "logistic_regression"


def test_build_feature_vector_length_matches_names():
    vector = build_feature_vector(task(), activation_summary())
    assert len(vector) == len(FEATURE_NAMES)


def test_build_feature_vector_without_activation_zero_fills():
    vector = build_feature_vector(task(), None)
    assert vector[-1] == 0.0  # has_activation flag
