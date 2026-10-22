"""Shared test fixtures and fakes."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")


class FakeCollection:
    """In-memory stand-in for a Chroma collection."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records: list[dict[str, Any]] = records or []
        self.deleted_where: dict[str, Any] | None = None
        self.last_add: dict[str, Any] | None = None
        self.last_query: dict[str, Any] | None = None
        self.query_result: dict[str, Any] | None = None

    def add(self, **kwargs: Any) -> None:
        self.last_add = kwargs
        for index, record_id in enumerate(kwargs.get("ids", [])):
            self.records.append(
                {
                    "id": record_id,
                    "document": kwargs["documents"][index],
                    "metadata": kwargs["metadatas"][index],
                }
            )

    def get(
        self, where: dict[str, Any] | None = None, limit: int | None = None, **_: Any
    ):
        matching = self.records
        if where:
            matching = [
                record
                for record in matching
                if all(record["metadata"].get(k) == v for k, v in where.items())
            ]
        if limit:
            matching = matching[:limit]
        return {
            "ids": [record["id"] for record in matching],
            "documents": [record["document"] for record in matching],
            "metadatas": [record["metadata"] for record in matching],
        }

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.last_query = kwargs
        if self.query_result is not None:
            return self.query_result
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def delete(self, where: dict[str, Any]) -> None:
        self.deleted_where = where
        self.records = [
            record
            for record in self.records
            if not all(record["metadata"].get(k) == v for k, v in where.items())
        ]

    def count(self) -> int:
        return len(self.records)


@pytest.fixture
def fake_collection() -> FakeCollection:
    """An empty fake collection."""
    return FakeCollection()


@pytest.fixture
def settings_stub() -> SimpleNamespace:
    """Settings object covering every field the application reads."""
    return SimpleNamespace(
        openai_api_key="test-key",
        openai_chat_model="gpt-4o-mini",
        openai_embedding_model="text-embedding-3-small",
        embedding_batch_size=2,
        chroma_persist_dir="./chroma_db",
        chroma_collection="documents_v2",
        legacy_chroma_collection="documents",
        chunk_size=100,
        chunk_overlap=10,
        top_k=5,
        min_relevance_score=0.0,
        max_history_messages=20,
        client_url="http://localhost:5173",
        extra_client_urls="",
        max_upload_bytes=20 * 1024 * 1024,
        api_token="",
        rate_limit_per_minute=0,
        cors_origins=["http://localhost:5173"],
        auth_enabled=False,
        rate_limit_enabled=False,
    )
