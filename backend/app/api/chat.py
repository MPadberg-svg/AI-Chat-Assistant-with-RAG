"""Chat API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.rag_chain import rag_query
from app.models.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(payload: ChatRequest) -> StreamingResponse:
    """Stream chat completions as server-sent events."""

    async def event_stream():
        async for chunk in rag_query(payload.question, payload.top_k):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
