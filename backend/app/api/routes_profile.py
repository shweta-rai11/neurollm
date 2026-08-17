"""Individual Computational Profile lifecycle beyond enrollment: evolution
history, explicit feedback, the counterfactual ("What if?") simulator, and
the Condition A/B/C research-mode comparison (product spec sections 13, 15,
18).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes_experiments import _load_benchmark_items, _run_normal_condition, _score
from app.brain.pipeline import PipelineResult, run_pipeline
from app.database.database import get_db
from app.models.profile_schemas import (
    ConditionSummary,
    CounterfactualRequest,
    CounterfactualResponse,
    CounterfactualSide,
    EvolutionHistoryEntry,
    EvolutionResponse,
    FeedbackRequest,
    FeedbackResponse,
    ResearchCompareRequest,
    ResearchCompareResponse,
)
from app.profile.params import ComputationalProfileParams, neutral_profile
from app.profile.service import ProfileNotFoundError, ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{profile_id}/evolution", response_model=EvolutionResponse)
async def evolution(profile_id: str, db: Session = Depends(get_db)) -> EvolutionResponse:
    service = ProfileService(db)
    try:
        data = service.evolution_history(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"profile {profile_id} not found")

    return EvolutionResponse(
        initial=data["initial"],
        current=data["current"],
        task_profiles=data["task_profiles"],
        n_interactions=data["n_interactions"],
        history=[EvolutionHistoryEntry(**h) for h in data["history"]],
    )


@router.post("/{profile_id}/feedback", response_model=FeedbackResponse)
async def feedback(profile_id: str, req: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackResponse:
    service = ProfileService(db)
    try:
        updated = service.apply_feedback(profile_id, req.interaction_id, req.feedback_score)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FeedbackResponse(updated_parameters=updated.to_dict())


def _merge_overrides(base: ComputationalProfileParams, overrides) -> ComputationalProfileParams:
    merged = base.to_dict()
    for key, value in overrides.model_dump().items():
        if value is not None:
            merged[key] = value
    return ComputationalProfileParams.from_dict(merged)


async def _run_side(query: str, model: str, profile: ComputationalProfileParams | None) -> PipelineResult:
    return await run_pipeline(query=query, model=model, uncertainty_mode=True, num_samples=4, profile=profile)


@router.post("/counterfactual", response_model=CounterfactualResponse)
async def counterfactual(req: CounterfactualRequest, db: Session = Depends(get_db)) -> CounterfactualResponse:
    service = ProfileService(db)
    if req.profile_id is not None:
        try:
            baseline_params = service.get_params(req.profile_id)
        except ProfileNotFoundError:
            raise HTTPException(status_code=404, detail=f"profile {req.profile_id} not found")
    else:
        baseline_params = neutral_profile()

    counterfactual_params = _merge_overrides(baseline_params, req.overrides)

    baseline_result, counterfactual_result = await asyncio.gather(
        _run_side(req.query, req.model, baseline_params),
        _run_side(req.query, req.model, counterfactual_params),
    )

    def _side(result: PipelineResult, params: ComputationalProfileParams) -> CounterfactualSide:
        return CounterfactualSide(
            answer=result.answer,
            pathway=result.pathway,
            hallucination_risk=result.hallucination_risk.score,
            confidence=result.cognitive_state.global_state.confidence,
            uncertainty_agreement=float(result.uncertainty.response_agreement) if result.uncertainty else None,
            parameters_used=params.to_dict(),
        )

    baseline_side = _side(baseline_result, baseline_params)
    counterfactual_side = _side(counterfactual_result, counterfactual_params)

    return CounterfactualResponse(
        baseline=baseline_side,
        counterfactual=counterfactual_side,
        confidence_delta=counterfactual_side.confidence - baseline_side.confidence,
        hallucination_risk_delta=round(counterfactual_side.hallucination_risk - baseline_side.hallucination_risk, 4),
        pathway_changed=baseline_side.pathway != counterfactual_side.pathway,
    )


@router.post("/research/compare", response_model=ResearchCompareResponse)
async def research_compare(req: ResearchCompareRequest, db: Session = Depends(get_db)) -> ResearchCompareResponse:
    """Condition A (plain LLM) vs B (virtual brain, anonymous/default
    profile) vs C (virtual brain, fingerprint-linked enrolled profile).
    Reuses the same benchmark items and scoring helper as
    `/api/experiment/benchmark` rather than re-implementing them."""
    service = ProfileService(db)
    condition_c_params: ComputationalProfileParams | None = None
    if req.profile_id is not None:
        try:
            condition_c_params = service.get_params(req.profile_id)
        except ProfileNotFoundError:
            raise HTTPException(status_code=404, detail=f"profile {req.profile_id} not found")

    items = _load_benchmark_items(req.categories, req.limit_per_category)

    a_scores: list[bool] = []
    a_risk: list[float] = []
    b_scores: list[bool] = []
    b_risk: list[float] = []
    b_abstain = 0
    c_scores: list[bool] = []
    c_risk: list[float] = []
    c_abstain = 0

    for item in items:
        expected = item.get("expected_answer")
        match_type = item.get("match_type")

        a_answer, _ = await _run_normal_condition(item["query"], req.model)
        a_correct = _score(a_answer, expected, match_type)
        if a_correct is not None:
            a_scores.append(a_correct)

        b_result = await run_pipeline(query=item["query"], model=req.model, uncertainty_mode=True, num_samples=4, profile=None)
        b_correct = _score(b_result.answer, expected, match_type)
        if b_correct is not None:
            b_scores.append(b_correct)
        b_risk.append(b_result.hallucination_risk.score)
        if b_result.pathway == "VERIFY" and "don't have strong evidence" in b_result.answer:
            b_abstain += 1

        c_result = await run_pipeline(
            query=item["query"], model=req.model, uncertainty_mode=True, num_samples=4, profile=condition_c_params
        )
        c_correct = _score(c_result.answer, expected, match_type)
        if c_correct is not None:
            c_scores.append(c_correct)
        c_risk.append(c_result.hallucination_risk.score)
        if c_result.pathway == "VERIFY" and "don't have strong evidence" in c_result.answer:
            c_abstain += 1

    def _accuracy(scores: list[bool]) -> float | None:
        return (sum(scores) / len(scores)) if scores else None

    n = len(items)
    conditions = [
        ConditionSummary(
            condition="A", label="LLM only (no virtual brain)", n=n,
            accuracy=_accuracy(a_scores), mean_hallucination_risk=0.0, abstention_rate=0.0,
        ),
        ConditionSummary(
            condition="B", label="LLM and behavioral computational profile (anonymous)", n=n,
            accuracy=_accuracy(b_scores),
            mean_hallucination_risk=(sum(b_risk) / len(b_risk)) if b_risk else 0.0,
            abstention_rate=(b_abstain / n) if n else 0.0,
        ),
        ConditionSummary(
            condition="C", label="LLM and fingerprint-linked personalization and behavioral profile", n=n,
            accuracy=_accuracy(c_scores),
            mean_hallucination_risk=(sum(c_risk) / len(c_risk)) if c_risk else 0.0,
            abstention_rate=(c_abstain / n) if n else 0.0,
        ),
    ]

    b_acc, c_acc = conditions[1].accuracy, conditions[2].accuracy
    if req.profile_id is None:
        honest_summary = (
            "No fingerprint-linked profile was supplied, so Condition C used the same anonymous/default "
            "parameters as Condition B by construction -- this run cannot show a fingerprint-linked benefit."
        )
    elif b_acc is None or c_acc is None:
        honest_summary = (
            "The selected benchmark items don't include enough objectively-checkable answers to compare "
            "Condition B and C accuracy on this run."
        )
    elif abs(c_acc - b_acc) < 0.05:
        honest_summary = (
            f"Condition C (accuracy {c_acc:.0%}) showed no measurable predictive benefit over Condition B "
            f"(accuracy {b_acc:.0%}) on this sample -- the fingerprint-linked profile did not outperform "
            "behavioral history alone. Report this honestly rather than as a win."
        )
    else:
        direction = "higher" if c_acc > b_acc else "lower"
        honest_summary = (
            f"Condition C (accuracy {c_acc:.0%}) was {direction} than Condition B (accuracy {b_acc:.0%}) on this "
            "small sample -- not sufficient evidence of a validated effect; re-run with a larger benchmark before "
            "drawing conclusions."
        )

    return ResearchCompareResponse(conditions=conditions, honest_summary=honest_summary)
