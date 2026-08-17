"""Behavioral learning rule: nudges `ComputationalProfileParams` from one
interaction's *outcome* -- never from any fingerprint/biometric feature.

Like the rest of this codebase's designed heuristics (`app.brain.neuromodulation`,
`app.brain.hallucination`), the per-parameter target functions below are a
documented control law, not a validated psychometric model: each target is a
one-line, inspectable rule tied to a real signal already produced by the
pipeline (pathway chosen, hallucination risk, cross-sample agreement,
optional explicit user feedback). Every update is a small, bounded
exponential-moving-average step -- one interaction never swings a profile
far, and `evidence_status` on the stored profile stays `"computational_model"`
regardless of how many interactions have been recorded.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.profile.params import ComputationalProfileParams

_LEARNING_RATE = 0.05
_CATEGORY_LEARNING_RATE = 0.08  # a single category accumulates fewer interactions, so it adapts a bit faster
_STRONG_NEGATIVE_FEEDBACK_VERIFICATION_TARGET = 0.85


def _ema(old: float, target: float, rate: float) -> float:
    return old + rate * (target - old)


@dataclass
class InteractionOutcome:
    pathway: str  # "DIRECT" | "ANALYTICAL" | "CREATIVE" | "VERIFY"
    hallucination_risk: float  # 0-1, from this turn's HallucinationRiskOut.score
    task_complexity: float  # 0-1, from this turn's TaskAnalysis.complexity / 100
    uncertainty_agreement: float | None = None  # 0-100, from UncertaintyResult.response_agreement if sampled
    feedback_score: float | None = None  # 0-1 explicit user rating (1 = correct/useful), if given


def _targets(outcome: InteractionOutcome) -> dict[str, float]:
    exploration_target = 1.0 if outcome.pathway == "CREATIVE" else 0.3
    control_target = 1.0 if outcome.pathway in ("ANALYTICAL", "VERIFY") else 0.35

    verification_target = outcome.hallucination_risk
    if outcome.feedback_score is not None and outcome.feedback_score < 0.5:
        # Explicit "that was wrong/unhelpful" feedback is a stronger, more
        # direct verification-need signal than the passive risk proxy alone.
        verification_target = max(verification_target, _STRONG_NEGATIVE_FEEDBACK_VERIFICATION_TARGET)

    if outcome.uncertainty_agreement is not None:
        uncertainty_target = 1.0 - (outcome.uncertainty_agreement / 100.0)
    else:
        uncertainty_target = outcome.hallucination_risk

    return {
        "attention_baseline": outcome.task_complexity,
        "working_memory_baseline": 0.5 * outcome.task_complexity + 0.5 * control_target,
        "cognitive_control": control_target,
        "exploration": exploration_target,
        "exploitation": 1.0 - exploration_target,
        "memory_retrieval": 1.0 - outcome.hallucination_risk,
        "uncertainty_sensitivity": uncertainty_target,
        "salience_sensitivity": 0.5 * outcome.task_complexity + 0.5 * outcome.hallucination_risk,
        "verification_strength": verification_target,
    }


def apply_interaction(
    params: ComputationalProfileParams, outcome: InteractionOutcome, rate: float = _LEARNING_RATE
) -> ComputationalProfileParams:
    """Returns a new, clamped `ComputationalProfileParams` nudged toward
    this interaction's outcome targets. Pure function -- persistence is the
    caller's job (see `app.profile.service.ProfileService.record_interaction`)."""
    targets = _targets(outcome)
    current = params.to_dict()
    updated = {name: _ema(current[name], targets[name], rate) for name in current}
    return ComputationalProfileParams.from_dict(updated)


def apply_interaction_to_category(
    category_params: ComputationalProfileParams, outcome: InteractionOutcome
) -> ComputationalProfileParams:
    return apply_interaction(category_params, outcome, rate=_CATEGORY_LEARNING_RATE)
