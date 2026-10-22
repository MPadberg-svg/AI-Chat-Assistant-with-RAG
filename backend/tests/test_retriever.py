"""Tests for semantic search."""

from __future__ import annotations

from app.core import retriever


def _collection_with_results(
    monkeypatch, fake_collection, documents, metadatas, distances
):
    fake_collection.query_result = {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }
    monkeypatch.setattr(retriever, "get_collection", lambda: fake_collection)
    return fake_collection


def test_query_uses_embeddings_not_raw_text(
    monkeypatch, fake_collection, settings_stub
):
    """Chroma must receive vectors produced by the ingestion model.

    Passing ``query_texts`` makes Chroma embed the query with its own 384-dim
    MiniLM model, which cannot be compared with 1536-dim OpenAI vectors.
    """
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [0.5, 0.25])
    collection = _collection_with_results(
        monkeypatch, fake_collection, ["chunk"], [{"doc_id": "d", "page": 1}], [0.2]
    )

    retriever.semantic_search("what is this?")

    assert "query_texts" not in collection.last_query
    assert collection.last_query["query_embeddings"] == [[0.5, 0.25]]


def test_scores_are_clamped_to_the_unit_interval(
    monkeypatch, fake_collection, settings_stub
):
    """cosine distance maps to a sane 0..1 confidence."""
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [0.1])
    _collection_with_results(
        monkeypatch,
        fake_collection,
        ["a", "b", "c"],
        [{"doc_id": "d", "page": 1}] * 3,
        [0.25, 0.0, 1.4],  # 1.4 would go negative if unclamped
    )

    results = retriever.semantic_search("q")

    assert [item["score"] for item in results] == [0.75, 1.0, 0.0]


def test_min_relevance_filters_results(monkeypatch, fake_collection, settings_stub):
    """Chunks below MIN_RELEVANCE_SCORE should be dropped."""
    settings_stub.min_relevance_score = 0.6
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [0.1])
    _collection_with_results(
        monkeypatch,
        fake_collection,
        ["good", "bad"],
        [{"doc_id": "d", "page": 1}] * 2,
        [0.1, 0.8],
    )

    results = retriever.semantic_search("q")

    assert [item["text"] for item in results] == ["good"]


def test_blank_query_short_circuits(monkeypatch, fake_collection, settings_stub):
    """Whitespace-only queries must not hit the embedding API."""
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(
        retriever, "embed_query", lambda text: pytest_fail("should not embed")
    )
    monkeypatch.setattr(retriever, "get_collection", lambda: fake_collection)

    assert retriever.semantic_search("   ") == []


def test_entries_without_metadata_are_skipped(
    monkeypatch, fake_collection, settings_stub
):
    """Defensive: Chroma can return None metadata."""
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [0.1])
    _collection_with_results(monkeypatch, fake_collection, ["text"], [None], [0.1])

    assert retriever.semantic_search("q") == []


def test_filename_falls_back_to_doc_id(monkeypatch, fake_collection, settings_stub):
    """Legacy chunks have no filename; the doc_id is used instead."""
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [0.1])
    _collection_with_results(
        monkeypatch,
        fake_collection,
        ["text"],
        [{"doc_id": "legacy-doc", "page": 3}],
        [0.1],
    )

    result = retriever.semantic_search("q")[0]

    assert result["filename"] == "legacy-doc"
    assert result["page"] == 3


def pytest_fail(message: str):
    raise AssertionError(message)
