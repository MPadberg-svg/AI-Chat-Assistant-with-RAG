"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.core.config import get_settings
from app.core.embeddings import get_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up dependencies on startup."""
    get_settings()
    app.state.chroma_status = "disconnected"
    try:
        get_collection().count()
        app.state.chroma_status = "connected"
    except Exception:
        raise
    yield


app = FastAPI(title="RAG Chat Assistant", lifespan=lifespan)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")


@app.get("/api/health")
async def health_check(request: Request) -> dict[str, str]:
    """Health check endpoint."""
    chroma_status = getattr(request.app.state, "chroma_status", "disconnected")
    return {"status": "ok", "chroma": chroma_status}
