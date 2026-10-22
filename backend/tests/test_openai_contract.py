"""Contract tests against the real OpenAI SDK.

The rest of the suite replaces ``OpenAI`` / ``AsyncOpenAI`` with fakes, which
means it would keep passing even if a version bump broke the SDK surface the
application actually relies on. These tests instead build real SDK clients and
mock only the HTTP transport, so request serialisation and response parsing are
exercised for real.

They are the regression guard for dependency upgrades such as openai 1.x -> 3.x.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from openai import AsyncOpenAI, OpenAI

from app.core import embeddings, rag_chain


class TransportRecorder:
    """Records request bodies while serving canned responses."""

    def __init__(
        self, response: httpx.Response | None = None, error: Exception | None = None
    ):
        self.response = response
        self.error = error
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            {
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": json.loads(request.content) if request.content else {},
            }
        )
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def embedding_payload(
    count: int, model: str = "text-embedding-3-small"
) -> dict[str, Any]:
    """Build an embeddings response in the shape the API returns."""
    return {
        "object": "list",
        "model": model,
        "data": [
            {"object": "embedding", "index": index, "embedding": [0.5, 0.25]}
            for index in range(count)
        ],
        "usage": {"prompt_tokens": count, "total_tokens": count},
    }


def chat_stream_content(tokens: list[str]) -> bytes:
    """Build an SSE body of chat completion chunks."""
    frames = []
    for token in tokens:
        chunk = {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "gpt-4o-mini",
            "choices": [
                {"index": 0, "delta": {"content": token}, "finish_reason": None}
            ],
        }
        frames.append(f"data: {json.dumps(chunk)}\n\n")
    frames.append("data: [DONE]\n\n")
    return "".join(frames).encode()


def error_response(status: int, message: str) -> httpx.Response:
    """Build an OpenAI-shaped error response."""
    return httpx.Response(
        status,
        json={
            "error": {"message": message, "type": "invalid_request_error", "code": None}
        },
    )


def install_sync_client(monkeypatch, recorder: TransportRecorder) -> None:
    """Point the embeddings module at a real SDK client with a mocked transport."""
    monkeypatch.setattr(
        embeddings,
        "get_openai_client",
        lambda: OpenAI(
            api_key="test-key",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(recorder)),
        ),
    )


def install_async_client(monkeypatch, recorder: TransportRecorder) -> None:
    """Point the RAG chain at a real async SDK client with a mocked transport."""
    monkeypatch.setattr(
        rag_chain,
        "get_async_client",
        lambda: AsyncOpenAI(
            api_key="test-key",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(recorder)),
        ),
    )


# ------------------------------------------------------------------ embeddings


def test_embed_texts_through_real_sdk(monkeypatch, settings_stub):
    """embed_texts must work against the real SDK's request/response models."""
    recorder = TransportRecorder(httpx.Response(200, json=embedding_payload(2)))
    install_sync_client(monkeypatch, recorder)
    monkeypatch.setattr(embeddings, "get_settings", lambda: settings_stub)
    settings_stub.embedding_batch_size = 10

    vectors = embeddings.embed_texts(["alpha", "beta"])

    assert vectors == [[0.5, 0.25], [0.5, 0.25]]
    body = recorder.requests[0]["body"]
    assert body["input"] == ["alpha", "beta"]
    assert body["model"] == "text-embedding-3-small"
    assert recorder.requests[0]["headers"]["authorization"] == "Bearer test-key"


def test_embed_texts_preserves_index_order_through_real_sdk(monkeypatch, settings_stub):
    """The SDK returns items keyed by index; results must stay aligned."""
    payload = embedding_payload(3)
    # Deliberately shuffled, as the API does not guarantee ordering.
    payload["data"] = [payload["data"][2], payload["data"][0], payload["data"][1]]
    payload["data"][0]["embedding"] = [3.0]
    payload["data"][1]["embedding"] = [1.0]
    payload["data"][2]["embedding"] = [2.0]

    recorder = TransportRecorder(httpx.Response(200, json=payload))
    install_sync_client(monkeypatch, recorder)
    monkeypatch.setattr(embeddings, "get_settings", lambda: settings_stub)
    settings_stub.embedding_batch_size = 10

    vectors = embeddings.embed_texts(["a", "b", "c"])

    assert [vector[0] for vector in vectors] == [1.0, 2.0, 3.0]


def test_embed_texts_batches_through_real_sdk(monkeypatch, settings_stub):
    """Batching must issue one request per batch with the right slice."""
    requests: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body["input"])
        return httpx.Response(200, json=embedding_payload(len(body["input"])))

    monkeypatch.setattr(
        embeddings,
        "get_openai_client",
        lambda: OpenAI(
            api_key="test-key",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        ),
    )
    monkeypatch.setattr(embeddings, "get_settings", lambda: settings_stub)
    settings_stub.embedding_batch_size = 2

    vectors = embeddings.embed_texts(["a", "b", "c", "d", "e"])

    assert len(vectors) == 5
    assert [len(batch) for batch in requests] == [2, 2, 1]


# --------------------------------------------------------------------- chat


async def _collect(question: str = "hi", top_k=None, history=None):
    return [event async for event in rag_chain.rag_query(question, top_k, history)]


async def test_chat_streaming_through_real_sdk(monkeypatch, settings_stub):
    """Streaming must parse the SDK's async stream into token events."""
    recorder = TransportRecorder(
        httpx.Response(
            200,
            content=chat_stream_content(["Hello", "\n\n", "world"]),
            headers={"content-type": "text/event-stream"},
        )
    )
    install_async_client(monkeypatch, recorder)
    monkeypatch.setattr(rag_chain, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(rag_chain, "semantic_search", lambda _query, _top_k: [])

    events = await _collect("what is this?")

    assert [event.event for event in events] == ["token", "token", "token", "sources"]
    assert "".join(event.data for event in events[:-1]) == "Hello\n\nworld"
    assert json.loads(events[-1].data) == []

    body = recorder.requests[0]["body"]
    assert body["stream"] is True
    assert body["model"] == settings_stub.openai_chat_model
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][-1]["role"] == "user"


async def test_chat_rate_limit_through_real_sdk(monkeypatch, settings_stub):
    """A 429 from the API must become a friendly error event, not a crash."""
    recorder = TransportRecorder(error_response(429, "Rate limit reached"))
    install_async_client(monkeypatch, recorder)
    monkeypatch.setattr(rag_chain, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(rag_chain, "semantic_search", lambda _query, _top_k: [])

    events = await _collect()

    assert len(events) == 1
    assert events[0].event == "error"
    assert "rate limited" in json.loads(events[0].data)["message"].lower()


async def test_chat_bad_request_through_real_sdk(monkeypatch, settings_stub):
    """A 400 is reported as a provider error rather than an unhandled crash."""
    recorder = TransportRecorder(error_response(400, "Invalid model"))
    install_async_client(monkeypatch, recorder)
    monkeypatch.setattr(rag_chain, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(rag_chain, "semantic_search", lambda _query, _top_k: [])

    events = await _collect()

    assert events[-1].event == "error"
    assert "returned an error" in json.loads(events[-1].data)["message"].lower()


async def test_chat_connection_failure_through_real_sdk(monkeypatch, settings_stub):
    """A transport failure surfaces as a connection error event."""
    recorder = TransportRecorder(error=httpx.ConnectError("no route to host"))
    install_async_client(monkeypatch, recorder)
    monkeypatch.setattr(rag_chain, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(rag_chain, "semantic_search", lambda _query, _top_k: [])

    events = await _collect()

    assert events[-1].event == "error"
    assert "could not reach" in json.loads(events[-1].data)["message"].lower()


# ------------------------------------------------------------------- clients


def test_async_client_is_cached(monkeypatch, settings_stub):
    """One client per process: building per request leaked connection pools."""
    monkeypatch.setattr(rag_chain, "get_settings", lambda: settings_stub)
    rag_chain.reset_async_client()

    first = rag_chain.get_async_client()
    second = rag_chain.get_async_client()

    assert first is second

    rag_chain.reset_async_client()
    assert rag_chain.get_async_client() is not first


def test_sync_client_is_cached(monkeypatch, settings_stub):
    """The embeddings client is cached the same way."""
    monkeypatch.setattr(embeddings, "get_settings", lambda: settings_stub)
    embeddings.get_openai_client.cache_clear()

    assert embeddings.get_openai_client() is embeddings.get_openai_client()

    embeddings.get_openai_client.cache_clear()


async def test_retrieval_api_failure_is_reported(monkeypatch, settings_stub):
    """If embedding the query fails, the client gets a search error, not a crash."""
    from openai import APIConnectionError
    import httpx

    def failing_search(_query, _top_k):
        raise APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com")
        )

    monkeypatch.setattr(rag_chain, "get_settings", lambda: settings_stub)
    monkeypatch.setattr(rag_chain, "semantic_search", failing_search)

    events = await _collect()

    assert events[-1].event == "error"
    assert "search service" in json.loads(events[-1].data)["message"].lower()
