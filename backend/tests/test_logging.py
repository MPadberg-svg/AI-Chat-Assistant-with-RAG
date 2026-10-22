"""Tests for request-scoped logging."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app import main as main_module
from app.core import logging as app_logging
from app.core.logging import (
    REQUEST_ID_HEADER,
    RequestIdFilter,
    configure_logging,
    current_request_id,
    new_request_id,
    reset_request_id,
    set_request_id,
)
from app.main import app

client = TestClient(app)


def test_new_request_id_is_unique_and_short() -> None:
    first = new_request_id()
    second = new_request_id()

    assert first != second
    assert len(first) == 12


def test_request_id_is_scoped_to_the_context() -> None:
    assert current_request_id() == "-"

    token = set_request_id("abc123")
    try:
        assert current_request_id() == "abc123"
    finally:
        reset_request_id(token)

    assert current_request_id() == "-"


def test_filter_injects_the_request_id() -> None:
    token = set_request_id("req-42")
    try:
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None)
        assert RequestIdFilter().filter(record) is True
        assert record.request_id == "req-42"
    finally:
        reset_request_id(token)


def test_filter_preserves_an_explicit_request_id() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None)
    record.request_id = "explicit"

    RequestIdFilter().filter(record)

    assert record.request_id == "explicit"


def test_configure_logging_is_idempotent() -> None:
    root = logging.getLogger()

    configure_logging()
    installed = len(root.handlers)
    configure_logging()
    configure_logging()

    assert len(root.handlers) == installed
    assert sum(getattr(h, "_request_aware", False) for h in root.handlers) == 1


def test_responses_carry_a_request_id_header() -> None:
    response = client.get("/api/health")

    assert response.status_code in (200, 503)
    assert len(response.headers[REQUEST_ID_HEADER]) == 12


def test_incoming_request_id_is_echoed() -> None:
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "trace-me-123"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-me-123"


def test_request_id_is_present_on_rejected_requests(monkeypatch) -> None:
    """Auth failures must be traceable too."""
    from types import SimpleNamespace

    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(auth_enabled=True, api_token="secret"),
    )
    monkeypatch.setattr(main_module, "rate_limiter", None)

    response = client.get("/api/documents")

    assert response.status_code == 401
    assert REQUEST_ID_HEADER in response.headers


def test_configured_format_includes_request_id() -> None:
    assert "%(request_id)s" in app_logging.LOG_FORMAT
