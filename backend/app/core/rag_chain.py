"""RAG chain implementation with streaming output."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.retriever import semantic_search
from app.models.schemas import Message


async def rag_query(
    question: str, top_k: int, history: list[Message] | None = None
) -> AsyncGenerator[str, None]:
    """Stream a context-grounded answer and then a sources payload marker."""
    settings = get_settings()
    contexts = semantic_search(question, top_k=top_k)

    if contexts:
        context_text = "\n\n".join(
            f"[{item['doc_id']} p.{item['page']}] {item['text']}" for item in contexts
        )
    else:
        context_text = "No relevant context found."

    sources = [
        {"doc_id": item["doc_id"], "page": item["page"], "score": item["score"]}
        for item in contexts
    ]

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    history_messages = (history or [])[-10:]
    messages = [
        {
            "role": "system",
            "content": (
                "You are a retrieval-augmented assistant. "
                "Answer ONLY using the provided context. "
                "If the context is insufficient, "
                "say you do not have enough context. "
                "Always cite sources inline using [doc_id p.N]."
            ),
        },
        *(
            {"role": item.role, "content": item.content}
            for item in history_messages
        ),
        {
            "role": "user",
            "content": f"Question: {question}\n\nContext:\n{context_text}",
        },
    ]

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        stream=True,
        temperature=0,
        messages=messages,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta

    yield "__SOURCES__" + json.dumps(sources)
