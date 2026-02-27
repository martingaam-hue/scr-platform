"""Tests for auth dependency functions."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from jose import JWTError

from app.auth.dependencies import (
    get_current_user,
    require_org_access,
    require_permission,
    require_role,
)
from app.models.enums import UserRole
from app.schemas.auth import CurrentUser
from tests.conftest import SAMPLE_CLERK_ID, SAMPLE_ORG_ID, SAMPLE_USER_ID


class TestRequireRole:
    """Test the require_role dependency factory."""

    @pytest.mark.anyio
    async def test_allowed_role_passes(self):
        checker = require_role([UserRole.ADMIN, UserRole.MANAGER])
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.ADMIN,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        # Mock get_current_user by overriding the default dependency
        result = await checker(current_user=user)
        assert result.role == UserRole.ADMIN

    @pytest.mark.anyio
    async def test_disallowed_role_raises_403(self):
        checker = require_role([UserRole.ADMIN])
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.VIEWER,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        with pytest.raises(HTTPException) as exc:
            await checker(current_user=user)
        assert exc.value.status_code == 403

    @pytest.mark.anyio
    async def test_analyst_in_analyst_list_passes(self):
        checker = require_role([UserRole.ANALYST, UserRole.MANAGER, UserRole.ADMIN])
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.ANALYST,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        result = await checker(current_user=user)
        assert result.role == UserRole.ANALYST


class TestRequirePermission:
    """Test the require_permission dependency factory."""

    @pytest.mark.anyio
    async def test_admin_has_delete_project(self):
        checker = require_permission("delete", "project")
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.ADMIN,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        result = await checker(current_user=user)
        assert result.role == UserRole.ADMIN

    @pytest.mark.anyio
    async def test_viewer_cannot_delete_project(self):
        checker = require_permission("delete", "project")
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.VIEWER,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        with pytest.raises(HTTPException) as exc:
            await checker(current_user=user)
        assert exc.value.status_code == 403


class TestRequireOrgAccess:
    """Test the require_org_access dependency."""

    @pytest.mark.anyio
    async def test_same_org_passes(self):
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.ADMIN,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        result = await require_org_access(org_id=SAMPLE_ORG_ID, current_user=user)
        assert result.org_id == SAMPLE_ORG_ID

    @pytest.mark.anyio
    async def test_different_org_raises_403(self):
        user = CurrentUser(
            user_id=SAMPLE_USER_ID,
            org_id=SAMPLE_ORG_ID,
            role=UserRole.ADMIN,
            email="test@example.com",
            external_auth_id=SAMPLE_CLERK_ID,
        )
        other_org = uuid.uuid4()
        with pytest.raises(HTTPException) as exc:
            await require_org_access(org_id=other_org, current_user=user)
        assert exc.value.status_code == 403
