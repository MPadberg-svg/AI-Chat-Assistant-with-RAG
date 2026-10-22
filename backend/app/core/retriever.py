"""Semantic search over the document collection."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.embeddings import embed_query, get_collection


def semantic_search(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    """Return the most relevant chunks for ``query``.

    Queries are embedded with the same model used at ingestion time and passed
    to Chroma as vectors. Passing raw text would make Chroma use its built-in
    embedding function (a 384-dimension MiniLM model) against the 1536-dimension
    OpenAI vectors stored in the collection, which cannot work.

    The collection uses cosine space, so ``score = 1 - distance`` is a real
    0..1 similarity.
    """
    settings = get_settings()
    cleaned = query.strip()
    if not cleaned:
        return []

    limit = top_k or settings.top_k
    results = get_collection().query(
        query_embeddings=[embed_query(cleaned)],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    payload: list[dict[str, Any]] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        if not metadata or text is None:
            continue
        score = round(min(1.0, max(0.0, 1.0 - float(distance))), 3)
        if score < settings.min_relevance_score:
            continue
        payload.append(
            {
                "text": text,
                "doc_id": metadata.get("doc_id", "unknown"),
                "filename": metadata.get("filename")
                or metadata.get("doc_id", "unknown"),
                "page": metadata.get("page", 1),
                "score": score,
            }
        )
    return payload
