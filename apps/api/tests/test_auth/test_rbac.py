"""Tests for the RBAC permission matrix and check_permission function."""

import uuid

import pytest

from app.auth.rbac import (
    Action,
    PERMISSION_MATRIX,
    Resource,
    check_permission,
    get_permissions_for_role,
)
from app.models.enums import UserRole


class TestPermissionMatrix:
    """Verify the static permission matrix is correctly built."""

    def test_all_roles_present(self):
        assert set(PERMISSION_MATRIX.keys()) == {
            UserRole.VIEWER,
            UserRole.ANALYST,
            UserRole.MANAGER,
            UserRole.ADMIN,
        }

    def test_role_hierarchy_sizes(self):
        """Higher roles have strictly more permissions than lower ones."""
        viewer_count = len(PERMISSION_MATRIX[UserRole.VIEWER])
        analyst_count = len(PERMISSION_MATRIX[UserRole.ANALYST])
        manager_count = len(PERMISSION_MATRIX[UserRole.MANAGER])
        admin_count = len(PERMISSION_MATRIX[UserRole.ADMIN])

        assert viewer_count < analyst_count
        assert analyst_count < manager_count
        assert manager_count < admin_count

    def test_viewer_is_subset_of_analyst(self):
        assert PERMISSION_MATRIX[UserRole.VIEWER].issubset(
            PERMISSION_MATRIX[UserRole.ANALYST]
        )

    def test_analyst_is_subset_of_manager(self):
        assert PERMISSION_MATRIX[UserRole.ANALYST].issubset(
            PERMISSION_MATRIX[UserRole.MANAGER]
        )

    def test_manager_is_subset_of_admin(self):
        assert PERMISSION_MATRIX[UserRole.MANAGER].issubset(
            PERMISSION_MATRIX[UserRole.ADMIN]
        )


class TestCheckPermission:
    """Test the check_permission function."""

    # ── Viewer permissions ────────────────────────────────────────────

    def test_viewer_can_view_projects(self):
        assert check_permission(UserRole.VIEWER, Action.VIEW, Resource.PROJECT) is True

    def test_viewer_can_download_documents(self):
        assert check_permission(UserRole.VIEWER, Action.DOWNLOAD, Resource.DOCUMENT) is True

    def test_viewer_cannot_create_projects(self):
        assert check_permission(UserRole.VIEWER, Action.CREATE, Resource.PROJECT) is False

    def test_viewer_cannot_edit_projects(self):
        assert check_permission(UserRole.VIEWER, Action.EDIT, Resource.PROJECT) is False

    def test_viewer_cannot_delete_anything(self):
        assert check_permission(UserRole.VIEWER, Action.DELETE, Resource.PROJECT) is False
        assert check_permission(UserRole.VIEWER, Action.DELETE, Resource.DOCUMENT) is False

    def test_viewer_cannot_manage_team(self):
        assert check_permission(UserRole.VIEWER, Action.MANAGE_TEAM, Resource.TEAM) is False

    # ── Analyst permissions ───────────────────────────────────────────

    def test_analyst_can_edit_projects(self):
        assert check_permission(UserRole.ANALYST, Action.EDIT, Resource.PROJECT) is True

    def test_analyst_can_upload_documents(self):
        assert check_permission(UserRole.ANALYST, Action.UPLOAD, Resource.DOCUMENT) is True

    def test_analyst_can_run_analyses(self):
        assert check_permission(UserRole.ANALYST, Action.RUN_ANALYSIS, Resource.ANALYSIS) is True

    def test_analyst_cannot_create_projects(self):
        assert check_permission(UserRole.ANALYST, Action.CREATE, Resource.PROJECT) is False

    def test_analyst_cannot_manage_team(self):
        assert check_permission(UserRole.ANALYST, Action.MANAGE_TEAM, Resource.TEAM) is False

    # ── Manager permissions ───────────────────────────────────────────

    def test_manager_can_create_projects(self):
        assert check_permission(UserRole.MANAGER, Action.CREATE, Resource.PROJECT) is True

    def test_manager_can_create_portfolios(self):
        assert check_permission(UserRole.MANAGER, Action.CREATE, Resource.PORTFOLIO) is True

    def test_manager_can_manage_team(self):
        assert check_permission(UserRole.MANAGER, Action.MANAGE_TEAM, Resource.TEAM) is True

    def test_manager_cannot_delete_projects(self):
        assert check_permission(UserRole.MANAGER, Action.DELETE, Resource.PROJECT) is False

    def test_manager_cannot_manage_billing(self):
        assert check_permission(UserRole.MANAGER, Action.MANAGE_BILLING, Resource.BILLING) is False

    # ── Admin permissions ─────────────────────────────────────────────

    def test_admin_can_delete_projects(self):
        assert check_permission(UserRole.ADMIN, Action.DELETE, Resource.PROJECT) is True

    def test_admin_can_manage_settings(self):
        assert check_permission(UserRole.ADMIN, Action.MANAGE_SETTINGS, Resource.SETTINGS) is True

    def test_admin_can_manage_billing(self):
        assert check_permission(UserRole.ADMIN, Action.MANAGE_BILLING, Resource.BILLING) is True

    def test_admin_can_view_audit_logs(self):
        assert check_permission(UserRole.ADMIN, Action.VIEW, Resource.AUDIT_LOG) is True

    def test_admin_inherits_all_lower_permissions(self):
        """Admin should have every permission that viewer, analyst, manager have."""
        for role in [UserRole.VIEWER, UserRole.ANALYST, UserRole.MANAGER]:
            for action, resource in PERMISSION_MATRIX[role]:
                assert check_permission(UserRole.ADMIN, action, resource) is True

    # ── Edge cases ────────────────────────────────────────────────────

    def test_nonexistent_action(self):
        assert check_permission(UserRole.ADMIN, "nonexistent", Resource.PROJECT) is False

    def test_nonexistent_resource(self):
        assert check_permission(UserRole.ADMIN, Action.VIEW, "nonexistent") is False

    def test_resource_id_param_accepted(self):
        """resource_id is reserved for future use; should not affect current checks."""
        result = check_permission(
            UserRole.ADMIN, Action.VIEW, Resource.PROJECT, resource_id=uuid.uuid4()
        )
        assert result is True


class TestGetPermissionsForRole:
    """Test the get_permissions_for_role helper."""

    def test_returns_dict_of_lists(self):
        perms = get_permissions_for_role(UserRole.VIEWER)
        assert isinstance(perms, dict)
        for key, val in perms.items():
            assert isinstance(key, str)
            assert isinstance(val, list)

    def test_viewer_has_view_actions(self):
        perms = get_permissions_for_role(UserRole.VIEWER)
        assert "view" in perms.get("project", [])
        assert "view" in perms.get("portfolio", [])

    def test_admin_has_more_resources_than_viewer(self):
        admin_perms = get_permissions_for_role(UserRole.ADMIN)
        viewer_perms = get_permissions_for_role(UserRole.VIEWER)
        assert len(admin_perms) >= len(viewer_perms)

    def test_admin_has_settings_resource(self):
        perms = get_permissions_for_role(UserRole.ADMIN)
        assert "settings" in perms
        assert "manage_settings" in perms["settings"]
