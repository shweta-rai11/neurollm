"""The 9 computational parameters of an Individual Computational Profile
(product spec section 5), plus the fixed task-category list (sections 8/14).

Every field defaults to 0.5 ("neutral") -- there is no fingerprint-derived
starting bias for any of these. They only move via `app.profile.learning`,
driven by observed interaction outcomes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

TASK_CATEGORIES: tuple[str, ...] = (
    "mathematics",
    "coding",
    "scientific_reasoning",
    "factual_retrieval",
    "creative_generation",
    "decision_making",
    "social_reasoning",
    "planning",
    "ambiguous",
)

_PARAM_NAMES = (
    "attention_baseline",
    "working_memory_baseline",
    "cognitive_control",
    "exploration",
    "exploitation",
    "memory_retrieval",
    "uncertainty_sensitivity",
    "salience_sensitivity",
    "verification_strength",
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class ComputationalProfileParams:
    attention_baseline: float = 0.5
    working_memory_baseline: float = 0.5
    cognitive_control: float = 0.5
    exploration: float = 0.5
    exploitation: float = 0.5
    memory_retrieval: float = 0.5
    uncertainty_sensitivity: float = 0.5
    salience_sensitivity: float = 0.5
    verification_strength: float = 0.5

    def clamped(self) -> "ComputationalProfileParams":
        return ComputationalProfileParams(**{k: _clamp01(v) for k, v in asdict(self).items()})

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "ComputationalProfileParams":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known}).clamped()

    @classmethod
    def param_names(cls) -> tuple[str, ...]:
        return _PARAM_NAMES


def neutral_profile() -> ComputationalProfileParams:
    return ComputationalProfileParams()
