"""Document retrieval: vector search fused with BM25 keyword search."""

from __future__ import annotations

import math
from typing import Any

from app.core.bm25 import BM25Index, reciprocal_rank_fusion
from app.core.config import get_settings
from app.core.embeddings import (
    all_chunk_texts,
    corpus_generation,
    embed_query,
    get_collection,
)

_RRF_K = 60
_bm25_cache: BM25Index | None = None
_bm25_generation: int | None = None


def _clamp(value: float) -> float:
    """Clamp a similarity into the 0..1 range."""
    return round(min(1.0, max(0.0, value)), 3)


def _cosine(left: list[float], right: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _to_payload(
    text: str | None, metadata: dict[str, Any] | None, score: float
) -> dict[str, Any] | None:
    """Build one search result, or None when the record is unusable."""
    if not metadata or text is None:
        return None
    doc_id = metadata.get("doc_id", "unknown")
    return {
        "text": text,
        "doc_id": doc_id,
        "filename": metadata.get("filename") or doc_id,
        "page": metadata.get("page", 1),
        "score": score,
    }


def _get_bm25_index() -> BM25Index:
    """Return a BM25 index, rebuilt whenever the corpus changes."""
    global _bm25_cache, _bm25_generation
    generation = corpus_generation()
    if _bm25_cache is None or _bm25_generation != generation:
        _bm25_cache = BM25Index(all_chunk_texts())
        _bm25_generation = generation
    return _bm25_cache


def _vector_search(query: str, limit: int, min_score: float) -> list[dict[str, Any]]:
    """Pure vector search over the cosine collection."""
    results = get_collection().query(
        query_embeddings=[embed_query(query)],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    payload: list[dict[str, Any]] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        score = _clamp(1.0 - float(distance))
        if score < min_score:
            continue
        item = _to_payload(text, metadata, score)
        if item:
            payload.append(item)
    return payload


def _hybrid_search(query: str, limit: int, min_score: float) -> list[dict[str, Any]]:
    """Fuse vector and BM25 rankings with reciprocal rank fusion.

    Both retrievers contribute candidates; the fused ranking decides the order.
    Because the citation panel reports a cosine similarity, every returned
    chunk gets its true cosine score: directly from the vector search when it
    ranked there, and computed from the stored embedding otherwise.
    """
    collection = get_collection()
    pool = max(limit * 4, 20)
    query_vector = [float(value) for value in embed_query(query)]

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=pool,
        include=["documents", "metadatas", "distances"],
    )
    vector_ids = list((results.get("ids") or [[]])[0])
    vector_documents = list((results.get("documents") or [[]])[0])
    vector_metadatas = list((results.get("metadatas") or [[]])[0])
    vector_distances = list((results.get("distances") or [[]])[0])

    known: dict[str, tuple[str | None, dict[str, Any] | None, float]] = {}
    for chunk_id, text, metadata, distance in zip(
        vector_ids, vector_documents, vector_metadatas, vector_distances
    ):
        known[chunk_id] = (text, metadata, _clamp(1.0 - float(distance)))

    lexical = _get_bm25_index().search(query, limit=pool)
    fused = reciprocal_rank_fusion(
        [vector_ids, [chunk_id for chunk_id, _ in lexical]], k=_RRF_K
    )
    selected = [chunk_id for chunk_id, _ in fused][:limit]

    missing = [chunk_id for chunk_id in selected if chunk_id not in known]
    if missing:
        fetched = collection.get(
            ids=missing, include=["documents", "metadatas", "embeddings"]
        )
        embeddings = fetched.get("embeddings")
        for index, chunk_id in enumerate(fetched.get("ids") or []):
            text = (fetched.get("documents") or [None])[index]
            metadata = (fetched.get("metadatas") or [None])[index]
            vector = embeddings[index] if embeddings is not None else None
            score = (
                _cosine(query_vector, [float(value) for value in vector])
                if vector
                else 0.0
            )
            known[chunk_id] = (text, metadata, _clamp(score))

    payload: list[dict[str, Any]] = []
    for chunk_id in selected:
        text, metadata, score = known.get(chunk_id, (None, None, 0.0))
        if score < min_score:
            continue
        item = _to_payload(text, metadata, score)
        if item:
            payload.append(item)
    return payload


def semantic_search(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    """Return the most relevant chunks for ``query``.

    Queries are embedded with the same model used at ingestion time and passed
    to Chroma as vectors. Passing raw text would make Chroma use its built-in
    embedding function (a 384-dimension MiniLM model) against the 1536-dimension
    OpenAI vectors stored in the collection, which cannot work.

    With ``HYBRID_SEARCH`` enabled (the default) the vector ranking is fused
    with a BM25 keyword ranking, which recovers exact matches such as error
    codes and names that embeddings tend to blur. The collection uses cosine
    space, so the reported ``score`` is always a real 0..1 similarity.
    """
    settings = get_settings()
    cleaned = query.strip()
    if not cleaned:
        return []

    limit = top_k or settings.top_k
    if settings.hybrid_search:
        return _hybrid_search(cleaned, limit, settings.min_relevance_score)
    return _vector_search(cleaned, limit, settings.min_relevance_score)


def reset_index_cache() -> None:
    """Drop the cached BM25 index (used by tests and after bulk changes)."""
    global _bm25_cache, _bm25_generation
    _bm25_cache = None
    _bm25_generation = None
