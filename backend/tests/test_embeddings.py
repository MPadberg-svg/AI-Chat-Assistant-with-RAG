"""Tests for document ingestion."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.core import embeddings


class FakeCollection:
    """Simple fake Chroma collection."""

    def __init__(self) -> None:
        self.payload: dict[str, object] = {}

    def add(self, **kwargs):
        self.payload = kwargs


class FakeEmbedder:
    """Simple fake embedding model."""

    def embed_documents(self, chunks):
        return [[0.1, 0.2] for _ in chunks]


def test_ingest_document_splits_and_stores(monkeypatch, tmp_path: Path) -> None:
    """ingest_document should split text and persist chunks with metadata."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("a" * 1200, encoding="utf-8")

    fake_collection = FakeCollection()

    monkeypatch.setattr(
        embeddings,
        "get_settings",
        lambda: SimpleNamespace(
            chunk_size=512, chunk_overlap=50, openai_api_key="test"
        ),
    )
    monkeypatch.setattr(embeddings, "_get_embeddings_model", lambda: FakeEmbedder())
    monkeypatch.setattr(embeddings, "get_collection", lambda: fake_collection)

    chunks = embeddings.ingest_document(str(file_path), "doc-1")

    assert chunks > 1
    assert fake_collection.payload["metadatas"][0]["doc_id"] == "doc-1"
    assert fake_collection.payload["metadatas"][0]["page"] == 1


def test_list_document_ids_deduplicates(monkeypatch) -> None:
    """list_document_ids should return sorted unique IDs."""

    class LocalCollection:
        def get(self, include):
            return {
                "metadatas": [
                    {"doc_id": "b"},
                    {"doc_id": "a"},
                    {"doc_id": "b"},
                ]
            }

    monkeypatch.setattr(embeddings, "get_collection", lambda: LocalCollection())

    assert embeddings.list_document_ids() == ["a", "b"]
