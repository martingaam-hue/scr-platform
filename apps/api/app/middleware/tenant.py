"""Multi-tenant middleware and query helpers.

The middleware initializes request.state.org_id. The actual value is set by
the get_current_user dependency (or set_tenant_context). The tenant_filter()
helper ensures all queries are scoped to the current org.
"""

import uuid

from starlette.types import ASGIApp, Receive, Scope, Send
from sqlalchemy.sql import Select


class TenantMiddleware:
    """Pure ASGI middleware that initializes tenant state on each request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            scope.setdefault("state", {})
            scope["state"].setdefault("org_id", None)
            scope["state"].setdefault("user_id", None)
        await self.app(scope, receive, send)


def tenant_filter(stmt: Select, org_id: uuid.UUID, model: type) -> Select:
    """Append org_id filter to a SQLAlchemy select statement.

    Usage:
        stmt = select(Project)
        stmt = tenant_filter(stmt, current_user.org_id, Project)
    """
    if hasattr(model, "org_id"):
        return stmt.where(model.org_id == org_id)  # type: ignore[attr-defined]
    return stmt
