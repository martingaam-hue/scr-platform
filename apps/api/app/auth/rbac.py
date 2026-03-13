"""RBAC permission matrix and checker.

Roles inherit cumulatively: viewer < analyst < manager < admin.
Permissions are (action, resource_type) tuples in a set for O(1) lookup.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from app.models.enums import UserRole

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ── Actions ───────────────────────────────────────────────────────────────


class Action:
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    RUN_ANALYSIS = "run_analysis"
    MANAGE_TEAM = "manage_team"
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_BILLING = "manage_billing"
    EXPORT = "export"


# ── Resource Types ────────────────────────────────────────────────────────


class Resource:
    PROJECT = "project"
    PORTFOLIO = "portfolio"
    DOCUMENT = "document"
    REPORT = "report"
    ANALYSIS = "analysis"
    TEAM = "team"
    SETTINGS = "settings"
    BILLING = "billing"
    AUDIT_LOG = "audit_log"
    MATCH = "match"
    LISTING = "listing"
    CONVERSATION = "conversation"
    COMMENT = "comment"
    RISK = "risk"


# ── Role hierarchy (higher = more privilege) ──────────────────────────────

ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.ANALYST: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
}

# ── Per-role permission sets ──────────────────────────────────────────────

_VIEWER_PERMS: set[tuple[str, str]] = {
    (Action.VIEW, Resource.PROJECT),
    (Action.VIEW, Resource.PORTFOLIO),
    (Action.VIEW, Resource.DOCUMENT),
    (Action.VIEW, Resource.REPORT),
    (Action.VIEW, Resource.ANALYSIS),
    (Action.VIEW, Resource.MATCH),
    (Action.VIEW, Resource.LISTING),
    (Action.VIEW, Resource.CONVERSATION),
    (Action.VIEW, Resource.COMMENT),
    (Action.VIEW, Resource.RISK),
    (Action.DOWNLOAD, Resource.DOCUMENT),
    (Action.DOWNLOAD, Resource.REPORT),
}

_ANALYST_EXTRA: set[tuple[str, str]] = {
    (Action.EDIT, Resource.PROJECT),
    (Action.EDIT, Resource.PORTFOLIO),
    (Action.EDIT, Resource.DOCUMENT),
    (Action.UPLOAD, Resource.DOCUMENT),
    (Action.CREATE, Resource.REPORT),
    (Action.RUN_ANALYSIS, Resource.ANALYSIS),
    (Action.CREATE, Resource.CONVERSATION),
    (Action.CREATE, Resource.COMMENT),
    (Action.EDIT, Resource.COMMENT),
    (Action.EXPORT, Resource.REPORT),
    (Action.CREATE, Resource.RISK),
    (Action.EDIT, Resource.RISK),
}

_MANAGER_EXTRA: set[tuple[str, str]] = {
    (Action.CREATE, Resource.PROJECT),
    (Action.CREATE, Resource.PORTFOLIO),
    (Action.DELETE, Resource.DOCUMENT),
    (Action.MANAGE_TEAM, Resource.TEAM),
    (Action.CREATE, Resource.MATCH),
    (Action.CREATE, Resource.LISTING),
    (Action.EDIT, Resource.LISTING),
}

_ADMIN_EXTRA: set[tuple[str, str]] = {
    (Action.DELETE, Resource.PROJECT),
    (Action.DELETE, Resource.PORTFOLIO),
    (Action.DELETE, Resource.REPORT),
    (Action.DELETE, Resource.LISTING),
    (Action.DELETE, Resource.COMMENT),
    (Action.MANAGE_SETTINGS, Resource.SETTINGS),
    (Action.MANAGE_BILLING, Resource.BILLING),
    (Action.VIEW, Resource.AUDIT_LOG),
}

# ── Cumulative permission matrix ──────────────────────────────────────────

PERMISSION_MATRIX: dict[UserRole, set[tuple[str, str]]] = {
    UserRole.VIEWER: _VIEWER_PERMS,
    UserRole.ANALYST: _VIEWER_PERMS | _ANALYST_EXTRA,
    UserRole.MANAGER: _VIEWER_PERMS | _ANALYST_EXTRA | _MANAGER_EXTRA,
    UserRole.ADMIN: _VIEWER_PERMS | _ANALYST_EXTRA | _MANAGER_EXTRA | _ADMIN_EXTRA,
}


# ── Public API ────────────────────────────────────────────────────────────


def check_permission(
    role: UserRole,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,  # reserved for future object-level checks
) -> bool:
    """Check if a role has permission for an action on a resource type."""
    perms = PERMISSION_MATRIX.get(role)
    if perms is None:
        return False
    return (action, resource_type) in perms


async def check_object_permission(
    db: "AsyncSession",
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    role: UserRole,
    resource_type: str,
    resource_id: uuid.UUID,
    required_level: str = "viewer",
) -> bool:
    """Object-level permission check via ResourceOwnership table.

    Fast-path: admin and manager roles always pass — no ownership record needed.
    For viewer/analyst: requires an explicit, non-expired ownership record with
    a permission_level >= required_level.
    """
    # Managers and admins bypass object-level checks entirely.
    if ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY[UserRole.MANAGER]:
        return True

    from app.models.resource_ownership import PermissionLevel, ResourceOwnership

    _level_order: dict[str, int] = {
        PermissionLevel.VIEWER.value: 0,
        PermissionLevel.EDITOR.value: 1,
        PermissionLevel.OWNER.value: 2,
    }

    now = datetime.utcnow()
    stmt = select(ResourceOwnership).where(
        ResourceOwnership.user_id == user_id,
        ResourceOwnership.org_id == org_id,
        ResourceOwnership.resource_type == resource_type,
        ResourceOwnership.resource_id == resource_id,
        ResourceOwnership.is_deleted.is_(False),
        or_(ResourceOwnership.expires_at.is_(None), ResourceOwnership.expires_at > now),
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        return False

    record_rank = _level_order.get(record.permission_level, -1)
    required_rank = _level_order.get(required_level, 999)
    return record_rank >= required_rank


def get_permissions_for_role(role: UserRole) -> dict[str, list[str]]:
    """Return permissions grouped by resource type (for API responses)."""
    perms = PERMISSION_MATRIX.get(role, set())
    result: dict[str, list[str]] = {}
    for action, resource in sorted(perms):
        result.setdefault(resource, []).append(action)
    return result
