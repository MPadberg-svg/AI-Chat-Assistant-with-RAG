"""Chat API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.rag_chain import StreamEvent, rag_query
from app.models.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    # Tell nginx and similar proxies not to buffer the stream.
    "X-Accel-Buffering": "no",
}


def format_sse(event: StreamEvent) -> str:
    """Encode an event as an SSE frame.

    Every physical line of the payload becomes its own ``data:`` field. Emitting
    a raw ``data: {chunk}\\n\\n`` breaks whenever the chunk itself contains a
    newline: the frame terminates early and the newline is discarded by the
    client (which is how markdown formatting used to be lost).
    """
    lines = [f"event: {event.event}"]
    lines.extend(f"data: {line}" for line in event.data.split("\n"))
    return "\n".join(lines) + "\n\n"


@router.post("")
async def chat(payload: ChatRequest) -> StreamingResponse:
    """Stream chat completions as server-sent events."""

    async def event_stream():
        async for event in rag_query(payload.question, payload.top_k, payload.history):
            yield format_sse(event)

    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers=SSE_HEADERS
    )
