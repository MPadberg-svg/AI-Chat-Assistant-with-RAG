"""Tests for RAG chain streaming behavior."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core import rag_chain


class FakeChunk:
    """OpenAI stream chunk stub."""

    def __init__(self, text: str) -> None:
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=text))]


class FakeStream:
    """Async iterable stream for test tokens."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.tokens):
            raise StopAsyncIteration
        token = self.tokens[self._index]
        self._index += 1
        return FakeChunk(token)


class FakeCompletions:
    """Fake completions API."""

    async def create(self, **kwargs):
        return FakeStream(["Hello", " world"])


class FakeChat:
    """Fake chat API."""

    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeClient:
    """Fake AsyncOpenAI client."""

    def __init__(self, **kwargs) -> None:
        self.chat = FakeChat()


@pytest.mark.asyncio
async def test_rag_query_streams_text_and_sources(monkeypatch) -> None:
    """rag_query should stream answer chunks then source marker payload."""
    monkeypatch.setattr(
        rag_chain,
        "semantic_search",
        lambda _query, top_k: [
            {"text": "ctx", "doc_id": "file.txt", "page": 2, "score": 0.87},
        ],
    )
    monkeypatch.setattr(rag_chain, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(
        rag_chain, "get_settings", lambda: SimpleNamespace(openai_api_key="test")
    )

    parts = [part async for part in rag_chain.rag_query("question", 5)]

    assert "".join(parts[:-1]) == "Hello world"
    assert parts[-1].startswith("__SOURCES__")
    sources = json.loads(parts[-1].split("__SOURCES__", 1)[1])
    assert sources[0]["doc_id"] == "file.txt"
    assert sources[0]["page"] == 2


@pytest.mark.asyncio
async def test_rag_query_no_context(monkeypatch) -> None:
    """rag_query should handle empty context gracefully."""
    monkeypatch.setattr(
        rag_chain, "semantic_search", lambda _query, top_k: []
    )
    monkeypatch.setattr(rag_chain, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(
        rag_chain, "get_settings", lambda: SimpleNamespace(openai_api_key="test")
    )

    parts = [part async for part in rag_chain.rag_query("question", 5)]

    assert parts[-1].startswith("__SOURCES__")
    sources = json.loads(parts[-1].split("__SOURCES__", 1)[1])
    assert sources == []
