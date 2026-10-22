"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    """Chat history message model."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=20_000)


class ChatRequest(BaseModel):
    """Request payload for chat endpoint."""

    question: str = Field(..., min_length=1, max_length=4_000)
    top_k: int | None = Field(None, ge=1, le=20)
    history: list[Message] = Field(default_factory=list, max_length=100)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """Reject whitespace-only questions instead of billing an LLM call."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        return cleaned


class SourceInfo(BaseModel):
    """Source citation details."""

    doc_id: str
    page: int
    score: float


class DocumentSummary(BaseModel):
    """One ingested document."""

    doc_id: str
    filename: str
    chunks: int


class DocumentInfo(BaseModel):
    """Document ingest response model."""

    doc_id: str
    filename: str
    chunks: int
    duplicate: bool = False
