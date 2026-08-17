"""GET /health and GET /config."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.llm.local_hf_provider import MODEL_NAME as LOCAL_MODEL_NAME
from app.models.schemas import ConfigResponse, HealthResponse, ProbeInfoResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.version)


@router.get("/config", response_model=ConfigResponse)
async def config() -> ConfigResponse:
    return ConfigResponse(
        available_models=settings.available_models,
        default_model=settings.default_model,
        default_num_samples=settings.default_num_samples,
        max_num_samples=settings.max_num_samples,
        has_openai_key=settings.has_openai_key,
        local_model_name=LOCAL_MODEL_NAME if settings.enable_local_model else None,
    )


@router.get("/probes/info", response_model=ProbeInfoResponse)
async def probes_info() -> ProbeInfoResponse:
    from app.probes.infer import get_meta, is_available

    if not is_available():
        return ProbeInfoResponse(trained=False)

    meta = get_meta() or {}
    return ProbeInfoResponse(
        trained=True,
        probe_type=meta.get("probe_type"),
        test_accuracy=meta.get("test_accuracy"),
        n_train=meta.get("n_train"),
        n_test=meta.get("n_test"),
        categories=meta.get("categories", []),
        trained_at=meta.get("trained_at"),
    )
