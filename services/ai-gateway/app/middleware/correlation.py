"""Correlation ID middleware for the AI Gateway service.

Reads ``X-Correlation-ID`` from inbound requests (set by the API layer) and
binds it to structlog contextvars so every log line the AI Gateway emits
during that request carries the same ID as the originating API request.
Echoes the ID back in the response header.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

_HEADER = b"x-correlation-id"
_HEADER_STR = "X-Correlation-ID"


class CorrelationIdMiddleware:
    """Pure ASGI middleware — mirrors the API-side implementation."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        raw_cid = raw_headers.get(_HEADER, b"")
        correlation_id = raw_cid.decode("ascii", errors="replace") if raw_cid else str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        async def _send(message: dict) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(_HEADER_STR, correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            structlog.contextvars.clear_contextvars()
