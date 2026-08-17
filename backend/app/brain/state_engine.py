"""Cognitive-state engine: composes region profiles, neuromodulation,
global-state meters, interpretation, and recommendations into one
`CognitiveState` API object.

This module is deliberately pure/synchronous -- it takes already-computed
pieces (task analysis, region profile, neuromodulation, hallucination risk,
uncertainty, and the executive controller's chosen pathway) and assembles
them. The async orchestration (generation, activation capture, and the
VERIFY pathway's provider calls) happens in `app/api/routes_chat.py`, which
is the only place that needs to talk to a live model.
"""
from __future__ import annotations

from app.brain.hallucination import HallucinationRisk
from app.brain.neuromodulation import NeuromodulatorSignals as NeuromodulatorSignalsData
from app.brain.regions import BrainRegions as BrainRegionsData
from app.cognitive_state.recommendations import build_recommendations
from app.cognitive_state.risk_model import compute_global_state
from app.models.schemas import (
    BrainRegions,
    CognitiveState,
    GlobalState,
    HallucinationRiskOut,
    NeuromodulatorSignals,
    RegionScores,
    StateInterpretation,
    TaskAnalysis,
    UncertaintyResult,
)

_HIGH = 70
_LOW = 40


def _describe(value: int) -> str:
    if value >= _HIGH:
        return "High"
    if value <= _LOW:
        return "Low"
    return "Medium"


def _determine_modes(task: TaskAnalysis, global_state: GlobalState, pathway: str) -> list[str]:
    modes: list[str] = []

    if pathway == "ANALYTICAL":
        modes.append("ANALYTICAL")
    elif pathway == "CREATIVE":
        modes.append("EXPLORATORY")
    elif pathway == "VERIFY":
        modes.append("VERIFICATION-DRIVEN")

    if task.complexity > 75:
        modes.append("HIGH COMPLEXITY")

    if global_state.uncertainty > 80:
        modes.append("UNSTABLE")
    elif global_state.uncertainty < 30:
        modes.append("STABLE")

    if global_state.verification_need > 70:
        modes.append("HIGH VERIFICATION REQUIREMENT")

    if task.risk > 55:
        modes.append("ELEVATED RISK")

    if not modes:
        modes.append("NOMINAL")

    return modes


def _determine_status(global_state: GlobalState, pathway: str) -> str:
    if pathway == "VERIFY":
        return "HIGH HALLUCINATION RISK — VERIFICATION TRIGGERED"
    if global_state.uncertainty > 70:
        return "HIGH UNCERTAINTY — VERIFICATION RECOMMENDED"
    if global_state.difficulty > 75:
        return "HIGH DIFFICULTY"
    if global_state.confidence > 75 and global_state.uncertainty < 35:
        return "STABLE / HIGH CONFIDENCE"
    return "NOMINAL"


def _interpretation_text(
    pathway: str,
    modes: list[str],
    uncertainty: UncertaintyResult | None,
    hrs: HallucinationRisk,
) -> str:
    if pathway == "VERIFY":
        return (
            f"Hallucination-risk score {hrs.score:.2f} triggered the verification pathway: "
            "self-consistency and a self-verification pass were run before finalizing the answer."
        )
    if uncertainty is not None and uncertainty.unique_semantic_clusters > 1:
        return (
            f"The model produced {uncertainty.candidate_count} candidate responses that fell into "
            f"{uncertainty.unique_semantic_clusters} distinct semantic clusters "
            f"({uncertainty.response_agreement}% agreement)."
        )
    if "HIGH COMPLEXITY" in modes:
        return "The task requires multi-step reasoning or planning, which increases the chance of an incomplete or partially incorrect answer."
    if "EXPLORATORY" in modes:
        return "The task is open-ended with many acceptable answers rather than one correct answer."
    return "No strong risk or disagreement signals were detected for this task."


def _to_region_scores(data) -> RegionScores:
    return RegionScores(
        language=data.language,
        memory=data.memory,
        reasoning=data.reasoning,
        uncertainty=data.uncertainty,
        verification=data.verification,
    )


def build_cognitive_state(
    task: TaskAnalysis,
    region_profile: BrainRegionsData,
    neuromod: NeuromodulatorSignalsData,
    hrs: HallucinationRisk,
    uncertainty: UncertaintyResult | None,
    pathway: str,
) -> CognitiveState:
    brain_regions = BrainRegions(
        predicted=_to_region_scores(region_profile.predicted),
        measured=_to_region_scores(region_profile.measured) if region_profile.measured is not None else None,
    )
    neuromodulation = NeuromodulatorSignals(
        dopamine_like=neuromod.dopamine_like,
        serotonin_like=neuromod.serotonin_like,
        norepinephrine_like=neuromod.norepinephrine_like,
        acetylcholine_like=neuromod.acetylcholine_like,
    )

    global_state = compute_global_state(task, uncertainty)
    modes = _determine_modes(task, global_state, pathway)
    status = _determine_status(global_state, pathway)

    contributing_signals = {
        "semantic_disagreement": _describe(uncertainty.semantic_uncertainty_score) if uncertainty else "N/A (single sample)",
        "task_factuality": _describe(task.factuality_requirement),
        "ambiguity": _describe(task.ambiguity),
        "context_dependency": _describe(task.context_dependency),
        "risk": _describe(task.risk),
        "hallucination_risk": _describe(int(round(hrs.score * 100))),
    }

    interpretation = StateInterpretation(
        modes=modes,
        status=status,
        contributing_signals=contributing_signals,
        interpretation=_interpretation_text(pathway, modes, uncertainty, hrs),
    )

    recommendations = build_recommendations(task, global_state, pathway, uncertainty)

    return CognitiveState(
        brain_regions=brain_regions,
        neuromodulation=neuromodulation,
        global_state=global_state,
        interpretation=interpretation,
        recommendations=recommendations,
    )
