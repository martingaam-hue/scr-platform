"""Auth package: dependencies, RBAC, Clerk integration."""

from app.auth.dependencies import get_current_user, require_permission, require_role
from app.auth.rbac import check_permission, get_permissions_for_role

__all__ = [
    "check_permission",
    "get_current_user",
    "get_permissions_for_role",
    "require_permission",
    "require_role",
]
