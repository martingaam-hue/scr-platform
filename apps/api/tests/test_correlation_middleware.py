"""Unit tests for CorrelationIdMiddleware — no DB or network required."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import structlog
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.correlation import CorrelationIdMiddleware

_HEADER = "X-Correlation-ID"


def _make_app() -> TestClient:
    async def handler(request: Request) -> PlainTextResponse:
        cid = request.state.correlation_id
        return PlainTextResponse(cid)

    app = Starlette(routes=[Route("/", handler)])
    app.add_middleware(CorrelationIdMiddleware)
    return TestClient(app, raise_server_exceptions=True)


# ── ID generation ──────────────────────────────────────────────────────────────


class TestCorrelationIdGeneration:
    def test_generates_id_when_header_absent(self):
        client = _make_app()
        resp = client.get("/")
        assert resp.headers.get(_HEADER)
        # Must be a valid UUID
        uuid.UUID(resp.headers[_HEADER])

    def test_uses_caller_supplied_id(self):
        client = _make_app()
        supplied = str(uuid.uuid4())
        resp = client.get("/", headers={_HEADER: supplied})
        assert resp.headers[_HEADER] == supplied

    def test_echoes_id_in_response(self):
        client = _make_app()
        resp = client.get("/")
        assert _HEADER in resp.headers

    def test_different_requests_get_different_ids(self):
        client = _make_app()
        ids = {client.get("/").headers[_HEADER] for _ in range(5)}
        assert len(ids) == 5  # all unique

    def test_id_stored_on_request_state(self):
        """Handler can read correlation_id from request.state."""
        client = _make_app()
        supplied = str(uuid.uuid4())
        resp = client.get("/", headers={_HEADER: supplied})
        assert resp.text == supplied


# ── structlog binding ──────────────────────────────────────────────────────────


class TestStructlogBinding:
    def test_correlation_id_bound_during_request(self):
        bound: dict = {}

        async def handler(request: Request) -> PlainTextResponse:
            bound.update(structlog.contextvars.get_contextvars())
            return PlainTextResponse("ok")

        from starlette.applications import Starlette
        from starlette.routing import Route

        app = Starlette(routes=[Route("/", handler)])
        app.add_middleware(CorrelationIdMiddleware)
        client = TestClient(app)
        supplied = str(uuid.uuid4())
        client.get("/", headers={_HEADER: supplied})
        assert bound.get("correlation_id") == supplied

    def test_contextvars_cleared_after_request(self):
        """Ensure no context bleed between requests."""
        from starlette.applications import Starlette
        from starlette.routing import Route

        async def handler(request: Request) -> PlainTextResponse:
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", handler)])
        app.add_middleware(CorrelationIdMiddleware)
        client = TestClient(app)
        client.get("/", headers={_HEADER: "first-id"})
        # After the request, contextvars must be empty
        ctx = structlog.contextvars.get_contextvars()
        assert "correlation_id" not in ctx

    def test_no_bleed_between_sequential_requests(self):
        seen: list[str] = []

        async def handler(request: Request) -> PlainTextResponse:
            seen.append(structlog.contextvars.get_contextvars().get("correlation_id", ""))
            return PlainTextResponse("ok")

        from starlette.applications import Starlette
        from starlette.routing import Route

        app = Starlette(routes=[Route("/", handler)])
        app.add_middleware(CorrelationIdMiddleware)
        client = TestClient(app)

        id1, id2 = str(uuid.uuid4()), str(uuid.uuid4())
        client.get("/", headers={_HEADER: id1})
        client.get("/", headers={_HEADER: id2})
        assert seen == [id1, id2]


# ── Non-HTTP scopes ────────────────────────────────────────────────────────────


class TestNonHttpScope:
    def test_websocket_passthrough(self):
        """Middleware must not interfere with non-HTTP scopes."""
        called: list[bool] = []

        async def handler(scope, receive, send):
            called.append(True)

        from starlette.types import Scope, Receive, Send

        async def _noop_receive():
            pass  # pragma: no cover

        async def _noop_send(msg):
            pass  # pragma: no cover

        import asyncio

        mw = CorrelationIdMiddleware(handler)
        asyncio.run(mw({"type": "lifespan"}, _noop_receive, _noop_send))
        assert called == [True]


# ── Celery signal logic ────────────────────────────────────────────────────────


class TestCelerySignals:
    def test_inject_adds_correlation_id_to_headers(self):
        from app.core.celery_app import _inject_correlation_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id="test-cid-123")
        headers: dict = {}
        _inject_correlation_id(headers=headers)
        assert headers["correlation_id"] == "test-cid-123"
        structlog.contextvars.clear_contextvars()

    def test_inject_skips_when_no_context(self):
        from app.core.celery_app import _inject_correlation_id

        structlog.contextvars.clear_contextvars()
        headers: dict = {}
        _inject_correlation_id(headers=headers)
        assert "correlation_id" not in headers

    def test_bind_reads_from_task_headers(self):
        from app.core.celery_app import _bind_correlation_id

        task = type("T", (), {"request": type("R", (), {"headers": {"correlation_id": "req-abc"}})()})()
        structlog.contextvars.clear_contextvars()
        _bind_correlation_id(task=task)
        ctx = structlog.contextvars.get_contextvars()
        assert ctx["correlation_id"] == "req-abc"
        assert ctx["service"] == "worker"
        structlog.contextvars.clear_contextvars()

    def test_bind_generates_id_when_no_header(self):
        from app.core.celery_app import _bind_correlation_id

        task = type("T", (), {"request": type("R", (), {"headers": {}})()})()
        structlog.contextvars.clear_contextvars()
        _bind_correlation_id(task=task)
        ctx = structlog.contextvars.get_contextvars()
        assert ctx.get("correlation_id")
        uuid.UUID(ctx["correlation_id"])  # valid UUID
        structlog.contextvars.clear_contextvars()

    def test_postrun_clears_context(self):
        from app.core.celery_app import _clear_correlation_id

        structlog.contextvars.bind_contextvars(correlation_id="abc", service="worker")
        _clear_correlation_id()
        assert structlog.contextvars.get_contextvars() == {}


# ── configure_logging ──────────────────────────────────────────────────────────


class TestConfigureLogging:
    def test_merge_contextvars_in_processor_chain(self):
        from app.core.logging import configure_logging

        configure_logging("api")
        cfg = structlog.get_config()
        names = [getattr(p, "__name__", repr(p)) for p in cfg["processors"]]
        assert any("merge_contextvars" in n for n in names)

    def test_service_bound_globally(self):
        from app.core.logging import configure_logging

        structlog.contextvars.clear_contextvars()
        configure_logging("test-service")
        assert structlog.contextvars.get_contextvars().get("service") == "test-service"
        structlog.contextvars.clear_contextvars()
