"""Audit logging middleware.

Captures all mutating HTTP operations (POST/PUT/PATCH/DELETE) and writes to
audit_logs asynchronously via fire-and-forget tasks. Uses its own DB session
to decouple from the request lifecycle.
"""

import asyncio
import uuid

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.database import async_session_factory
from app.models.core import AuditLog

logger = structlog.get_logger()

AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

AUDIT_EXEMPT_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/webhook",
})


class AuditMiddleware:
    """Pure ASGI middleware that logs mutating operations to audit_logs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        method = request.method

        if method not in AUDITED_METHODS:
            await self.app(scope, receive, send)
            return

        path = request.url.path
        if any(path.startswith(exempt) for exempt in AUDIT_EXEMPT_PATHS):
            await self.app(scope, receive, send)
            return

        # Capture response status
        response_status = 0

        async def capture_send(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, capture_send)

        # Only audit successful mutations (2xx)
        if 200 <= response_status < 300:
            asyncio.create_task(
                self._write_audit_log(scope, request, method, path)
            )

    async def _write_audit_log(
        self, scope: dict, request: Request, method: str, path: str
    ) -> None:
        """Write audit log in a separate DB session (fire-and-forget)."""
        try:
            state = scope.get("state", {})
            org_id = state.get("org_id")
            user_id = state.get("user_id")

            if not org_id or not user_id:
                return  # Skip unauthenticated requests

            action = _method_to_action(method)
            entity_type, entity_id = _parse_entity_from_path(path)

            # Client IP (handle proxies)
            ip_address = request.headers.get("x-forwarded-for")
            if ip_address:
                ip_address = ip_address.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host

            user_agent = request.headers.get("user-agent", "")[:500]

            async with async_session_factory() as session:
                audit_entry = AuditLog(
                    org_id=org_id,
                    user_id=user_id,
                    action=f"{action}:{entity_type}",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                session.add(audit_entry)
                await session.commit()

        except Exception:
            logger.exception("audit_log_write_failed", path=path)


def _method_to_action(method: str) -> str:
    return {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method, method.lower())


def _parse_entity_from_path(path: str) -> tuple[str, uuid.UUID | None]:
    """Extract entity type and optional entity ID from URL path.

    Examples:
        /auth/me/preferences -> ("preference", None)
        /api/projects/550e8400-... -> ("project", UUID(...))
        /api/projects -> ("project", None)
    """
    parts = [p for p in path.strip("/").split("/") if p]
    entity_type = "unknown"
    entity_id = None

    # Skip common prefixes
    if parts and parts[0] in ("api", "v1"):
        parts = parts[1:]

    if parts:
        entity_type = parts[0].rstrip("s")  # naive de-pluralize

    if len(parts) >= 2:
        try:
            entity_id = uuid.UUID(parts[1])
        except ValueError:
            pass

    return entity_type, entity_id
