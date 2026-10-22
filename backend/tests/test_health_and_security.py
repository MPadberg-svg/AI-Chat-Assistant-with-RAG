"""Tests for the health endpoint and access controls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.api import documents as documents_module
from app.core.security import RateLimiter, extract_bearer_token, tokens_match
from app.main import app

client = TestClient(app)


# --------------------------------------------------------------------------- health


def test_health_reports_chunk_count(monkeypatch) -> None:
    """A reachable Chroma returns 200 with the live chunk count."""
    monkeypatch.setattr(main_module, "chunk_count", lambda: 42)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["chroma"] == "connected"
    assert response.json()["chunks"] == 42
    assert response.json()["version"]


def test_health_returns_503_when_chroma_is_down(monkeypatch) -> None:
    """A broken Chroma must not be reported as healthy."""

    def boom():
        raise RuntimeError("chroma down")

    monkeypatch.setattr(main_module, "chunk_count", boom)

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "chroma": "disconnected",
        "chunks": None,
        "version": main_module.__version__,
    }


# --------------------------------------------------------------------------- tokens


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer abc123", "abc123"),
        ("bearer abc123", "abc123"),
        ("Bearer   abc123  ", "abc123"),
        ("Basic abc123", None),
        ("abc123", None),
        ("", None),
        (None, None),
    ],
)
def test_extract_bearer_token(header, expected) -> None:
    assert extract_bearer_token(header) == expected


def test_tokens_match() -> None:
    assert tokens_match("secret", "secret")
    assert not tokens_match("secret", "other")
    assert not tokens_match("", "secret")
    assert not tokens_match(None, "secret")


# ------------------------------------------------------------------- rate limiting


def test_rate_limiter_allows_up_to_the_limit() -> None:
    """The limiter should allow exactly N hits per window."""
    now = [0.0]
    limiter = RateLimiter(2, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow("ip")
    assert limiter.allow("ip")
    assert not limiter.allow("ip")


def test_rate_limiter_window_slides() -> None:
    """Hits expire once the window has passed."""
    now = [0.0]
    limiter = RateLimiter(1, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow("ip")
    assert not limiter.allow("ip")
    now[0] = 61.0
    assert limiter.allow("ip")


def test_rate_limiter_is_per_client() -> None:
    """One client exhausting the limit must not block another."""
    limiter = RateLimiter(1, clock=lambda: 0.0)

    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")


def test_rate_limiter_disabled_when_limit_is_zero() -> None:
    """A zero limit means no limiting."""
    limiter = RateLimiter(0)
    assert all(limiter.allow("ip") for _ in range(100))


# --------------------------------------------------------------------------- middleware


def test_requests_are_rejected_without_a_token(monkeypatch) -> None:
    """When API_TOKEN is set, protected endpoints require it."""
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(auth_enabled=True, api_token="secret"),
    )
    monkeypatch.setattr(main_module, "rate_limiter", None)

    assert client.get("/api/documents").status_code == 401
    assert (
        client.get(
            "/api/documents", headers={"Authorization": "Bearer nope"}
        ).status_code
        == 401
    )


def test_valid_token_is_accepted(monkeypatch) -> None:
    """A correct bearer token passes through to the route."""
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(auth_enabled=True, api_token="secret"),
    )
    monkeypatch.setattr(main_module, "rate_limiter", None)
    monkeypatch.setattr(documents_module, "list_documents", lambda: [])

    response = client.get("/api/documents", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200


def test_health_stays_public(monkeypatch) -> None:
    """The health endpoint must remain reachable for container probes."""
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(auth_enabled=True, api_token="secret"),
    )
    monkeypatch.setattr(main_module, "rate_limiter", None)
    monkeypatch.setattr(main_module, "chunk_count", lambda: 1)

    assert client.get("/api/health").status_code == 200


def test_rate_limit_returns_429(monkeypatch) -> None:
    """Exceeding the per-client limit returns 429."""
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(auth_enabled=False, api_token=""),
    )
    monkeypatch.setattr(main_module, "rate_limiter", RateLimiter(1))
    monkeypatch.setattr(main_module, "chunk_count", lambda: 1)
    monkeypatch.setattr(documents_module, "list_documents", lambda: [])

    assert client.get("/api/health").status_code == 200  # public, not limited
    assert client.get("/api/documents").status_code == 200
    assert client.get("/api/documents").status_code == 429


# ------------------------------------------------------------------------ lifespan


def test_lifespan_marks_chroma_connected(monkeypatch) -> None:
    """Startup stores the live Chroma status on the app state."""
    from fastapi.testclient import TestClient as _TestClient

    monkeypatch.setattr(main_module, "chunk_count", lambda: 7)

    with _TestClient(app) as lifespan_client:
        assert lifespan_client.app.state.chroma_status == "connected"


def test_lifespan_starts_degraded_when_chroma_is_unavailable(monkeypatch) -> None:
    """A Chroma outage at boot must not prevent the app from starting."""
    from fastapi.testclient import TestClient as _TestClient

    def boom():
        raise RuntimeError("chroma down")

    monkeypatch.setattr(main_module, "chunk_count", boom)

    with _TestClient(app) as lifespan_client:
        assert lifespan_client.app.state.chroma_status == "disconnected"
        assert lifespan_client.get("/api/health").status_code == 503
