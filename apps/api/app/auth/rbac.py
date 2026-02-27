"""RBAC permission matrix and checker.

Roles inherit cumulatively: viewer < analyst < manager < admin.
Permissions are (action, resource_type) tuples in a set for O(1) lookup.
"""

import uuid

from app.models.enums import UserRole


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
    (Action.EXPORT, Resource.REPORT),
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


def get_permissions_for_role(role: UserRole) -> dict[str, list[str]]:
    """Return permissions grouped by resource type (for API responses)."""
    perms = PERMISSION_MATRIX.get(role, set())
    result: dict[str, list[str]] = {}
    for action, resource in sorted(perms):
        result.setdefault(resource, []).append(action)
    return result
