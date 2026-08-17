"""POST /chat -- the main analyze+respond+route pipeline."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.activations.features import ActivationSummary
from app.brain.pipeline import run_pipeline
from app.database.database import get_db
from app.database.models import AnalysisRecord
from app.models.profile_schemas import ExplanationEntryOut, ProfileInfluence
from app.models.schemas import ChatMetadata, ChatRequest, ChatResponse, HallucinationRiskOut, ResearchDetails, RetrievalSource
from app.profile.learning import InteractionOutcome
from app.profile.service import ProfileNotFoundError, ProfileService

router = APIRouter()


def _estimate_tokens(text: str) -> int:
    """Rough word-count-based token estimate (not exact -- no real
    tokenizer is used here when a live API doesn't hand back usage)."""
    return max(1, len(text.split()))


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    start = time.perf_counter()

    profile_service = ProfileService(db)
    profile_params = None
    if req.profile_id is not None:
        try:
            profile_params = profile_service.get_params(req.profile_id)
        except ProfileNotFoundError:
            raise HTTPException(status_code=404, detail=f"profile {req.profile_id} not found")

    result = await run_pipeline(
        query=req.query,
        model=req.model,
        uncertainty_mode=req.uncertainty_mode,
        num_samples=req.num_samples,
        research_mode=req.research_mode,
        profile=profile_params,
    )

    duration_ms = int((time.perf_counter() - start) * 1000)

    profile_influence: ProfileInfluence | None = None
    if req.profile_id is not None:
        profile_service.record_interaction(
            profile_id=req.profile_id,
            query=req.query,
            task_category=result.task_category.category,
            outcome=InteractionOutcome(
                pathway=result.pathway,
                hallucination_risk=result.hallucination_risk.score,
                task_complexity=result.task.complexity / 100.0,
                uncertainty_agreement=float(result.uncertainty.response_agreement) if result.uncertainty else None,
            ),
        )
        profile_influence = ProfileInfluence(
            applied=result.profile_applied,
            task_category=result.task_category.category,
            task_category_confidence=result.task_category.confidence,
            candidate_systems=result.task_category.candidate_systems,
            explanation=[ExplanationEntryOut(question=e.question, answer=e.answer) for e in result.explanation.entries],
            disclaimer=result.explanation.disclaimer,
        )

    research: ResearchDetails | None = None
    if req.research_mode and result.activation_capture is not None and result.activation_summary is not None:
        research = ResearchDetails(
            num_layers=result.activation_capture.num_layers,
            layer_hidden_norms=result.activation_capture.layer_hidden_norms,
            layer_attention_entropy=result.activation_capture.layer_attention_entropy,
            token_entropies=result.activation_capture.token_entropies,
            token_prob_margins=result.activation_capture.token_prob_margins,
            activation_features=dict(zip(ActivationSummary.feature_names(), result.activation_summary.as_feature_vector())),
            probe_prediction=result.probe_prediction,
            verifier_raw_text=result.verifier_raw_text,
            retrieval_raw_text=result.retrieval_raw_text or None,
            retrieval_sources=[RetrievalSource(title=r.title, snippet=r.snippet, url=r.url) for r in result.retrieval_results],
            routing_reason=result.routing_reason,
        )

    metadata = ChatMetadata(
        model=req.model,
        duration_ms=duration_ms,
        input_tokens=_estimate_tokens(req.query),
        output_tokens=_estimate_tokens(result.answer),
        provider=result.provider_label,
    )

    record = AnalysisRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        kind="chat",
        query=req.query,
        model=req.model,
        provider=result.provider_label,
        answer=result.answer,
        pathway=result.pathway,
        hallucination_risk=result.hallucination_risk.score,
        task_analysis_json=result.task.model_dump_json(),
        cognitive_state_json=result.cognitive_state.model_dump_json(),
        uncertainty_json=result.uncertainty.model_dump_json() if result.uncertainty else None,
        duration_ms=duration_ms,
    )
    db.add(record)
    db.commit()

    return ChatResponse(
        answer=result.answer,
        pathway=result.pathway,
        hallucination_risk=HallucinationRiskOut(score=result.hallucination_risk.score, components=result.hallucination_risk.components),
        cognitive_state=result.cognitive_state,
        uncertainty=result.uncertainty,
        task_analysis=result.task,
        recommendations=result.cognitive_state.recommendations,
        metadata=metadata,
        research=research,
        profile_influence=profile_influence,
    )
