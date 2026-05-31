"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for chat endpoint."""

    question: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)


class SourceInfo(BaseModel):
    """Source citation details."""

    doc_id: str
    page: int
    score: float


class ChatResponse(BaseModel):
    """Non-streaming chat response model."""

    answer: str
    sources: list[SourceInfo] = Field(default_factory=list)


class DocumentInfo(BaseModel):
    """Document ingest response model."""

    doc_id: str
    chunks: int
