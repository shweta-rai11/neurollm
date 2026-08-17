"""Fixed-order feature vector shared by probe training (`train.py`) and
inference (`infer.py`): task heuristic scores (normalized to [0,1])
concatenated with real activation summary stats, plus a `has_activation`
flag so a probe could in principle be evaluated on heuristic-only input
without silently pretending activation features are present.
"""
from __future__ import annotations

from app.activations.features import ActivationSummary
from app.models.schemas import TaskAnalysis

TASK_FEATURE_NAMES = [
    "complexity", "logical_reasoning", "creativity", "planning",
    "context_dependency", "verification_requirement", "risk", "ambiguity",
    "factuality_requirement",
]

ACTIVATION_FEATURE_NAMES = ActivationSummary.feature_names()

FEATURE_NAMES = TASK_FEATURE_NAMES + ACTIVATION_FEATURE_NAMES + ["has_activation"]


def build_feature_vector(task: TaskAnalysis, activation: ActivationSummary | None) -> list[float]:
    task_features = [getattr(task, name) / 100.0 for name in TASK_FEATURE_NAMES]
    if activation is not None:
        activation_features = activation.as_feature_vector()
        has_activation = 1.0
    else:
        activation_features = [0.0] * len(ACTIVATION_FEATURE_NAMES)
        has_activation = 0.0
    return task_features + activation_features + [has_activation]
