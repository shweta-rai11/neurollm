"""FastAPI application entry point."""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import api_router
from app.config import settings
from app.database.database import init_db

logger = logging.getLogger("ai_brain")

# The built frontend (frontend/dist, produced by `npm run build`) is served
# directly by this FastAPI app so the whole thing -- UI and API -- is one
# process on one port instead of two separate dev servers. This directory is
# absent in a bare backend-only checkout/test run, which is fine: the app
# still works as an API-only service in that case (see the catch-all route
# below, which returns 404 for non-API paths when it's missing).
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose declared Content-Length exceeds the configured
    limit, before the body is read into memory.

    `/api/biometric/*` (fingerprint image upload) gets a much larger cap --
    see `settings.max_fingerprint_image_bytes` -- since a real image upload
    would never fit in the default 64KB JSON-request cap. Every other route
    keeps the default cap unchanged.
    """

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            limit = (
                settings.max_fingerprint_image_bytes
                if request.url.path.startswith("/api/biometric/")
                else settings.max_request_body_bytes
            )
            try:
                if int(content_length) > limit:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "request body too large"},
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter keyed by client IP.

    This state lives entirely in process memory, so it resets on restart and
    is not shared across multiple worker processes/instances. That's
    adequate for local/demo use but is NOT a distributed rate limiter.
    """

    def __init__(self, app):
        super().__init__(app)
        self._window_seconds = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[client_host]

        while hits and now - hits[0] > self._window_seconds:
            hits.popleft()

        if len(hits) >= settings.rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={"error": "rate limit exceeded"},
            )

        hits.append(now)
        return await call_next(request)


# Middleware added first ends up outermost (runs first on the way in), so
# the body-size check runs before the rate limiter consumes a request slot
# for a request that would be rejected anyway.
app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log only the exception type/message -- never request headers or
    # anything that could contain API keys/secrets. The query text itself
    # is not a secret and is fine to appear in logs elsewhere (e.g. in
    # provider-layer logging), but this handler intentionally logs nothing
    # from the request beyond the path.
    logger.error("Unhandled exception on %s: %s: %s", request.url.path, type(exc).__name__, exc)
    return JSONResponse(status_code=500, content={"error": "internal server error"})


app.include_router(api_router, prefix="/api")


_RESERVED_TOP_LEVEL_PATHS = {"api", "docs", "openapi.json", "redoc"}

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        """SPA fallback: serve a matching static file (favicon, etc.) if one
        exists, otherwise index.html so client-side routing (react-router)
        handles the path -- e.g. a hard refresh on /question-lab still works.
        `/api/*`, `/docs`, `/openapi.json`, `/redoc` never reach here because
        FastAPI matches those routes (registered above/by the framework)
        first; the top-level check below is a second, explicit guard.
        """
        top_level = full_path.split("/", 1)[0]
        if top_level in _RESERVED_TOP_LEVEL_PATHS:
            from fastapi import HTTPException

            raise HTTPException(status_code=404)

        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

else:

    @app.get("/")
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.version,
            "health": "/api/health",
            "docs": "/docs",
            "note": "frontend/dist not found -- run `npm run build` in frontend/ to serve the UI from this app, or run `npm run dev` separately.",
        }
