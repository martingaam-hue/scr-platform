"""Correlation ID middleware — generates and propagates X-Correlation-ID.

For every HTTP request:
- Reads ``X-Correlation-ID`` from the incoming headers (caller-supplied ID).
- If absent, generates a fresh UUID4.
- Stores the ID in ``scope["state"]["correlation_id"]`` (accessible via
  ``request.state.correlation_id`` in route handlers).
- Binds ``correlation_id`` to the structlog contextvars context so every log
  line emitted during the request lifetime carries it automatically.
- Echoes the ID back as ``X-Correlation-ID`` in the response so clients can
  match their own trace ID or log the server-generated one.
- Clears the structlog contextvars when the request finishes to prevent
  context bleed across requests on the same event-loop worker.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

_HEADER = b"x-correlation-id"
_HEADER_STR = "X-Correlation-ID"


class CorrelationIdMiddleware:
    """Pure ASGI middleware — no BaseHTTPMiddleware overhead."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # ── Resolve correlation ID ────────────────────────────────────────────
        raw_headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        raw_cid = raw_headers.get(_HEADER, b"")
        correlation_id = raw_cid.decode("ascii", errors="replace") if raw_cid else str(uuid.uuid4())

        # ── Expose on request.state ───────────────────────────────────────────
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        # ── Bind to structlog contextvars (clears previous request's vars) ────
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # ── Echo ID in response headers ───────────────────────────────────────
        async def _send(message: dict) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(_HEADER_STR, correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            structlog.contextvars.clear_contextvars()
