"""Retriever implementation for semantic search."""

from __future__ import annotations

from typing import Any

from app.core.embeddings import get_collection


def semantic_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return semantic search results with normalized confidence scores."""
    if not query.strip():
        return []

    results = get_collection().query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    payload: list[dict[str, Any]] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        if not metadata:
            continue
        payload.append(
            {
                "text": text,
                "doc_id": metadata.get("doc_id", "unknown"),
                "page": metadata.get("page", 1),
                "score": round(1 - float(distance), 3),
            }
        )
    return payload
