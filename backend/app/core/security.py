"""Optional authentication and rate limiting helpers.

Both features are opt-in via ``API_TOKEN`` and ``RATE_LIMIT_PER_MINUTE`` so
existing deployments keep working unchanged.
"""

from __future__ import annotations

import secrets
import time
from collections import deque
from threading import Lock
from typing import Callable


def extract_bearer_token(header: str | None) -> str | None:
    """Return the token from an ``Authorization: Bearer <token>`` header."""
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


def tokens_match(provided: str | None, expected: str) -> bool:
    """Constant-time token comparison."""
    if not provided:
        return False
    return secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


class RateLimiter:
    """Thread-safe fixed-window rate limiter keyed by client identity."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Record a hit for ``key`` and report whether it is within the limit."""
        if self.limit <= 0:
            return True

        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._hits.setdefault(key, deque())
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                return False
            timestamps.append(now)
            self._prune()
            return True

    def _prune(self) -> None:
        """Drop empty buckets so the mapping cannot grow without bound."""
        if len(self._hits) < 1024:
            return
        for key in [key for key, hits in self._hits.items() if not hits]:
            self._hits.pop(key, None)
