"""Global-state aggregation: confidence, uncertainty, difficulty, verification need.

This module rolls task-analysis and uncertainty-engine outputs up into the
four top-level "AI Cognitive State" meters shown at the center of the
dashboard.
"""
from __future__ import annotations

from app.models.schemas import GlobalState, TaskAnalysis, UncertaintyResult


def _clamp(x: float) -> int:
    return int(round(max(0.0, min(100.0, x))))


def compute_global_state(
    task: TaskAnalysis,
    uncertainty: UncertaintyResult | None,
) -> GlobalState:
    if uncertainty is not None:
        uncertainty_score = 0.7 * uncertainty.semantic_uncertainty_score + 0.3 * task.ambiguity
        confidence = 0.7 * uncertainty.response_agreement + 0.3 * (100 - task.risk)
    else:
        # No multi-sample uncertainty run: fall back to task-derived proxy only.
        uncertainty_score = 0.6 * task.ambiguity + 0.4 * task.risk
        confidence = 100 - uncertainty_score

    difficulty = 0.5 * task.complexity + 0.3 * task.logical_reasoning + 0.2 * task.planning

    verification_need = 0.5 * task.verification_requirement + 0.3 * task.factuality_requirement + 0.2 * uncertainty_score

    return GlobalState(
        confidence=_clamp(confidence),
        uncertainty=_clamp(uncertainty_score),
        difficulty=_clamp(difficulty),
        verification_need=_clamp(verification_need),
    )
