"""Loads the trained probe pipeline (see `train.py`) and predicts a question
category from a query's task and activation features. Returns `None` (never a
fabricated prediction) when no trained probe artifact exists yet."""
from __future__ import annotations

import json
from pathlib import Path

from app.activations.features import ActivationSummary
from app.models.schemas import ProbePrediction, TaskAnalysis
from app.probes.feature_builder import build_feature_vector

_SAVED_DIR = Path(__file__).parent / "saved"
_MODEL_PATH = _SAVED_DIR / "probe_pipeline.joblib"
_META_PATH = _SAVED_DIR / "probe_meta.json"

_pipeline = None
_meta: dict | None = None
_load_attempted = False


def _load() -> None:
    global _pipeline, _meta, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    if not _MODEL_PATH.exists() or not _META_PATH.exists():
        return
    import joblib

    _pipeline = joblib.load(_MODEL_PATH)
    _meta = json.loads(_META_PATH.read_text())


def is_available() -> bool:
    _load()
    return _pipeline is not None


def get_meta() -> dict | None:
    _load()
    return _meta


def predict_category(task: TaskAnalysis, activation: ActivationSummary) -> ProbePrediction | None:
    _load()
    if _pipeline is None:
        return None

    vector = build_feature_vector(task, activation)
    proba = _pipeline.predict_proba([vector])[0]
    classes = _pipeline.classes_
    probabilities = {str(c): float(p) for c, p in zip(classes, proba)}
    best_idx = int(max(range(len(proba)), key=lambda i: proba[i]))

    return ProbePrediction(
        predicted_category=str(classes[best_idx]),
        confidence=float(proba[best_idx]),
        probabilities=probabilities,
        probe_type=(_meta or {}).get("probe_type", "unknown"),
    )
