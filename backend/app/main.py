"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.core.config import __version__, get_settings
from app.core.embeddings import chunk_count
from app.core.logging import (
    REQUEST_ID_HEADER,
    configure_logging,
    new_request_id,
    reset_request_id,
    set_request_id,
)
from app.core.security import RateLimiter, extract_bearer_token, tokens_match

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise state on startup without refusing to boot if Chroma is down."""
    configure_logging()
    get_settings()
    app.state.chroma_status = "disconnected"
    try:
        await run_in_threadpool(chunk_count)
        app.state.chroma_status = "connected"
    except Exception:  # noqa: BLE001 - start degraded instead of crashing
        logger.exception("ChromaDB is unavailable at startup; serving in degraded mode")
    yield


app = FastAPI(title="RAG Chat Assistant", version=__version__, lifespan=lifespan)
settings = get_settings()
rate_limiter = (
    RateLimiter(settings.rate_limit_per_minute) if settings.rate_limit_enabled else None
)

PROTECTED_PREFIX = "/api"
PUBLIC_PATHS = {"/api/health"}


@app.middleware("http")
async def enforce_access_controls(request: Request, call_next):
    """Apply optional bearer-token auth and per-client rate limiting."""
    path = request.url.path
    is_protected = path.startswith(PROTECTED_PREFIX) and path not in PUBLIC_PATHS

    # Always let CORS preflight through; the browser sends no credentials there.
    if is_protected and request.method != "OPTIONS":
        if settings.auth_enabled:
            token = extract_bearer_token(request.headers.get("authorization"))
            if not tokens_match(token, settings.api_token):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        if rate_limiter is not None:
            client = request.client.host if request.client else "unknown"
            if not rate_limiter.allow(client):
                return JSONResponse({"detail": "Too many requests"}, status_code=429)

    return await call_next(request)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Tag each request with an id and log its outcome."""
    request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
    token = set_request_id(request_id)
    started = perf_counter()

    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 - re-raised after logging
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise
    else:
        duration_ms = (perf_counter() - started) * 1000
        logger.info(
            "%s %s -> %d (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        reset_request_id(token)


# Added last so it wraps the middleware above and CORS headers are still sent
# on 401/429 responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")


@app.get("/api/health")
async def health_check() -> JSONResponse:
    """Health check reporting live Chroma connectivity."""
    try:
        chunks = await run_in_threadpool(chunk_count)
    except Exception:  # noqa: BLE001 - report the failure instead of raising
        logger.exception("Health check could not reach ChromaDB")
        return JSONResponse(
            {
                "status": "degraded",
                "chroma": "disconnected",
                "chunks": None,
                "version": __version__,
            },
            status_code=503,
        )

    return JSONResponse(
        {
            "status": "ok",
            "chroma": "connected",
            "chunks": chunks,
            "version": __version__,
        }
    )
