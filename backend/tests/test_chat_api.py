"""Tests for the streaming chat endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.core.rag_chain import StreamEvent
from app.main import app

client = TestClient(app)


def _fake_rag(events: list[StreamEvent]):
    async def generator(question, top_k, history):
        for event in events:
            yield event

    return generator


def test_newlines_survive_the_sse_framing(monkeypatch) -> None:
    """Regression: a newline-only token must not be swallowed by the frame.

    ``data: {chunk}\\n\\n`` produced an empty payload for ``chunk="\\n"``, which
    the client discarded, collapsing every markdown paragraph and code fence.
    """
    monkeypatch.setattr(
        chat_module,
        "rag_query",
        _fake_rag(
            [
                StreamEvent("token", "Item one."),
                StreamEvent("token", "\n\nItem two."),
                StreamEvent("sources", "[]"),
            ]
        ),
    )

    response = client.post("/api/chat", json={"question": "hi"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"

    body = response.text
    assert "event: token\ndata: Item one.\n\n" in body
    # A blank line inside the chunk becomes its own data field, so the client
    # can rejoin the lines and recover "\n\n".
    assert "event: token\ndata: \ndata: \ndata: Item two.\n\n" in body
    assert "event: sources\ndata: []\n\n" in body


def test_error_events_are_framed(monkeypatch) -> None:
    """Errors are delivered as a normal SSE event."""
    monkeypatch.setattr(
        chat_module,
        "rag_query",
        _fake_rag([StreamEvent("error", '{"message": "boom"}')]),
    )

    response = client.post("/api/chat", json={"question": "hi"})

    assert response.status_code == 200
    assert 'event: error\ndata: {"message": "boom"}\n\n' in response.text


def test_blank_question_is_rejected() -> None:
    """Whitespace-only questions should fail validation."""
    for payload in ({"question": ""}, {"question": "   "}):
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 422


def test_invalid_top_k_is_rejected() -> None:
    """top_k is bounded."""
    assert (
        client.post("/api/chat", json={"question": "hi", "top_k": 99}).status_code
        == 422
    )


def test_history_role_is_validated() -> None:
    """Only user/assistant roles are accepted."""
    response = client.post(
        "/api/chat",
        json={"question": "hi", "history": [{"role": "system", "content": "x"}]},
    )
    assert response.status_code == 422
