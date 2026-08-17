"""POST /analyze and POST /uncertainty."""
from __future__ import annotations

from fastapi import APIRouter

from app.cognitive_state.task_analyzer import analyze_task
from app.cognitive_state.uncertainty import estimate_uncertainty
from app.llm import LLMProviderError, MockProvider, get_provider
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    UncertaintyRequest,
    UncertaintyResponse,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    return AnalyzeResponse(task_analysis=analyze_task(req.query))


@router.post("/uncertainty", response_model=UncertaintyResponse)
async def uncertainty(req: UncertaintyRequest) -> UncertaintyResponse:
    provider = get_provider(req.model)
    try:
        candidates = await provider.generate_multiple(req.query, req.num_samples)
    except LLMProviderError:
        provider = MockProvider()
        candidates = await provider.generate_multiple(req.query, req.num_samples)

    return UncertaintyResponse(uncertainty=estimate_uncertainty(candidates))
