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


# ------------------------------------------------------------------ hybrid search


def _hybrid_collection(fake_collection, ids, documents, metadatas, distances):
    fake_collection.query_result = {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }
    return fake_collection


def test_hybrid_search_fuses_vector_and_lexical_rankings(
    monkeypatch, fake_collection, settings_stub
):
    """An exact keyword hit that the vector search missed should surface."""
    settings_stub.hybrid_search = True
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        retriever,
        "all_chunk_texts",
        lambda: {
            "chunk-1": "generic deployment notes",
            "chunk-2": "error ERR_CONN_REFUSED appears when the proxy is down",
        },
    )
    monkeypatch.setattr(retriever, "corpus_generation", lambda: 1)
    _hybrid_collection(
        fake_collection,
        ["chunk-1"],
        ["generic deployment notes"],
        [{"doc_id": "doc-a", "filename": "a.txt", "page": 1}],
        [0.2],
    )
    for chunk_id, metadata in (
        ("chunk-1", {"doc_id": "doc-a", "filename": "a.txt", "page": 1}),
        ("chunk-2", {"doc_id": "doc-b", "filename": "b.txt", "page": 1}),
    ):
        fake_collection.records.append(
            {"id": chunk_id, "document": "", "metadata": metadata}
        )
    monkeypatch.setattr(retriever, "get_collection", lambda: fake_collection)

    results = retriever.semantic_search("ERR_CONN_REFUSED", top_k=2)

    ids = [result["doc_id"] for result in results]
    assert "doc-b" in ids, "the BM25-only chunk must be retrieved"
    assert all(0.0 <= result["score"] <= 1.0 for result in results)


def test_hybrid_scores_lexical_only_hits_with_cosine(
    monkeypatch, fake_collection, settings_stub
):
    """Chunks found only by BM25 still report a true cosine similarity."""
    settings_stub.hybrid_search = True
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        retriever, "all_chunk_texts", lambda: {"chunk-2": "ERR_CONN_REFUSED"}
    )
    monkeypatch.setattr(retriever, "corpus_generation", lambda: 2)
    _hybrid_collection(fake_collection, [], [], [], [])
    fake_collection.records.append(
        {
            "id": "chunk-2",
            "document": "ERR_CONN_REFUSED appears",
            "metadata": {"doc_id": "doc-b", "filename": "b.txt", "page": 2},
            "embedding": [0.5, 0.5],
        }
    )
    monkeypatch.setattr(retriever, "get_collection", lambda: fake_collection)

    results = retriever.semantic_search("ERR_CONN_REFUSED", top_k=1)

    assert results
    # cos([1, 0], [0.5, 0.5]) == 0.707
    assert results[0]["score"] == 0.707
    assert results[0]["filename"] == "b.txt"
    assert results[0]["page"] == 2


def test_hybrid_skips_chunks_that_no_longer_exist(
    monkeypatch, fake_collection, settings_stub
):
    """A stale lexical entry must not produce a result with no document."""
    settings_stub.hybrid_search = True
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [1.0, 0.0])
    monkeypatch.setattr(
        retriever, "all_chunk_texts", lambda: {"ghost": "ERR_CONN_REFUSED"}
    )
    monkeypatch.setattr(retriever, "corpus_generation", lambda: 3)
    _hybrid_collection(fake_collection, [], [], [], [])
    monkeypatch.setattr(retriever, "get_collection", lambda: fake_collection)

    assert retriever.semantic_search("ERR_CONN_REFUSED", top_k=1) == []


def test_hybrid_disabled_uses_vector_only(monkeypatch, fake_collection, settings_stub):
    settings_stub.hybrid_search = False
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [0.1])
    monkeypatch.setattr(
        retriever, "all_chunk_texts", lambda: pytest_fail("BM25 must not be built")
    )
    _collection_with_results(
        monkeypatch, fake_collection, ["text"], [{"doc_id": "d", "page": 1}], [0.1]
    )

    assert len(retriever.semantic_search("q", top_k=1)) == 1


def test_bm25_index_is_rebuilt_when_the_corpus_changes(
    monkeypatch, fake_collection, settings_stub
):
    """The cached index must follow the corpus generation counter."""
    settings_stub.hybrid_search = True
    monkeypatch.setattr(retriever, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(retriever, "embed_query", lambda text: [1.0, 0.0])
    _hybrid_collection(fake_collection, [], [], [], [])
    monkeypatch.setattr(retriever, "get_collection", lambda: fake_collection)

    builds: list[int] = []

    def corpus() -> dict[str, str]:
        builds.append(1)
        return {"chunk-1": "alpha"}

    state = {"generation": 1}
    monkeypatch.setattr(retriever, "all_chunk_texts", corpus)
    monkeypatch.setattr(retriever, "corpus_generation", lambda: state["generation"])

    retriever.semantic_search("alpha")
    retriever.semantic_search("alpha")
    assert len(builds) == 1, "index should be reused for an unchanged corpus"

    state["generation"] = 2
    retriever.semantic_search("alpha")
    assert len(builds) == 2, "index should rebuild after the corpus changes"
