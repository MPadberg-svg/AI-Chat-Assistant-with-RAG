"""Request-scoped logging.

Every request gets an id (from ``X-Request-ID`` when supplied, generated
otherwise) that is attached to each log line emitted while handling it, so a
user report can be traced through the logs.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"


def current_request_id() -> str:
    """Return the id of the request being handled."""
    return _request_id.get()


def set_request_id(value: str):
    """Bind a request id to the current context; returns a reset token."""
    return _request_id.set(value)


def reset_request_id(token) -> None:
    """Restore the previous request id."""
    _request_id.reset(token)


def new_request_id() -> str:
    """Generate a short, log-friendly request id."""
    return uuid.uuid4().hex[:12]


class RequestIdFilter(logging.Filter):
    """Inject the current request id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = current_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Install a request-aware stream handler once."""
    root = logging.getLogger()
    if any(getattr(handler, "_request_aware", False) for handler in root.handlers):
        return

    handler = logging.StreamHandler()
    handler._request_aware = True  # type: ignore[attr-defined]
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root.addHandler(handler)
    root.setLevel(level.upper())
