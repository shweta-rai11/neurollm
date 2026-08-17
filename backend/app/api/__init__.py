"""Aggregate API router -- mounted at /api by app.main."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    routes_analysis,
    routes_biometric,
    routes_chat,
    routes_experiments,
    routes_history,
    routes_profile,
    routes_system,
)

api_router = APIRouter()
api_router.include_router(routes_chat.router)
api_router.include_router(routes_analysis.router)
api_router.include_router(routes_experiments.router)
api_router.include_router(routes_history.router)
api_router.include_router(routes_system.router)
api_router.include_router(routes_biometric.router)
api_router.include_router(routes_profile.router)
