"""Object-level RBAC tests.

Tests cover:
  TestCheckObjectPermission — direct calls to check_object_permission()
    - Admin and manager fast-paths (no ownership record needed)
    - Analyst/viewer with a valid ownership record → allowed
    - Analyst/viewer without ownership record → denied
    - Expired ownership record → denied
    - Cross-org access attempt → denied

  TestRequireObjectPermissionDep — HTTP integration via ralph GET conversation
    - Admin: allowed even without ownership
    - Viewer with ownership: 200
    - Viewer without ownership: 403 when OBJECT_LEVEL_RBAC_ENABLED=True
    - Audit mode (flag=False): logs warning, returns 200 regardless
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import check_object_permission
from app.models.ai import AIConversation
from app.models.core import Organization, User
from app.models.enums import AIContextType, OrgType, UserRole
from app.models.resource_ownership import PermissionLevel, ResourceOwnership

pytestmark = pytest.mark.anyio

# ── Module-level UUIDs (no collision with other test modules) ─────────────────

OBJ_ORG_ID = uuid.UUID("00000000-0000-0000-00ba-000000000001")
OBJ_ADMIN_ID = uuid.UUID("00000000-0000-0000-00ba-000000000002")
OBJ_MANAGER_ID = uuid.UUID("00000000-0000-0000-00ba-000000000003")
OBJ_ANALYST_ID = uuid.UUID("00000000-0000-0000-00ba-000000000004")
OBJ_VIEWER_ID = uuid.UUID("00000000-0000-0000-00ba-000000000005")

OBJ_OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-00ba-000000000010")
OBJ_OTHER_USER_ID = uuid.UUID("00000000-0000-0000-00ba-000000000011")

OBJ_RESOURCE_ID = uuid.UUID("00000000-0000-0000-00ba-000000000020")
OBJ_CONV_ID = uuid.UUID("00000000-0000-0000-00ba-000000000030")


# ── Shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
async def obj_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=OBJ_ORG_ID,
        name="ObjRBAC Org",
        slug="obj-rbac-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def obj_other_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=OBJ_OTHER_ORG_ID,
        name="ObjRBAC Other Org",
        slug="obj-rbac-other-org",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


def _make_user(uid: uuid.UUID, role: UserRole, *, email: str) -> User:
    return User(
        id=uid,
        org_id=OBJ_ORG_ID,
        email=email,
        full_name=f"Test {role.value.title()}",
        role=role,
        external_auth_id=f"clerk_obj_{uid.hex[-8:]}",
        is_active=True,
    )


@pytest.fixture
async def obj_users(db: AsyncSession, obj_org: Organization) -> dict[str, User]:
    users = {
        "admin": _make_user(OBJ_ADMIN_ID, UserRole.ADMIN, email="obj-admin@test.example"),
        "manager": _make_user(OBJ_MANAGER_ID, UserRole.MANAGER, email="obj-manager@test.example"),
        "analyst": _make_user(OBJ_ANALYST_ID, UserRole.ANALYST, email="obj-analyst@test.example"),
        "viewer": _make_user(OBJ_VIEWER_ID, UserRole.VIEWER, email="obj-viewer@test.example"),
    }
    for u in users.values():
        db.add(u)
    await db.flush()
    return users


@pytest.fixture
async def obj_other_user(db: AsyncSession, obj_other_org: Organization) -> User:
    user = User(
        id=OBJ_OTHER_USER_ID,
        org_id=OBJ_OTHER_ORG_ID,
        email="obj-other@test.example",
        full_name="Cross Org User",
        role=UserRole.ANALYST,
        external_auth_id="clerk_obj_other",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def obj_conversation(db: AsyncSession, obj_users: dict) -> AIConversation:
    conv = AIConversation(
        id=OBJ_CONV_ID,
        org_id=OBJ_ORG_ID,
        user_id=OBJ_ADMIN_ID,
        context_type=AIContextType.GENERAL,
        title="Test RBAC Conversation",
    )
    db.add(conv)
    await db.flush()
    return conv


# ── Helper: create an ownership record ───────────────────────────────────────


async def _grant(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    level: PermissionLevel = PermissionLevel.VIEWER,
    expires_at: datetime | None = None,
) -> ResourceOwnership:
    rec = ResourceOwnership(
        user_id=user_id,
        org_id=OBJ_ORG_ID,
        resource_type=resource_type,
        resource_id=resource_id,
        permission_level=level.value,
        granted_by=OBJ_ADMIN_ID,
        expires_at=expires_at,
    )
    db.add(rec)
    await db.flush()
    return rec


# ── TestCheckObjectPermission ─────────────────────────────────────────────────


class TestCheckObjectPermission:
    async def test_admin_bypasses_without_ownership(self, db: AsyncSession, obj_users: dict):
        """Admin always passes — no ownership record required."""
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_ADMIN_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.ADMIN,
            resource_type="project",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is True

    async def test_manager_bypasses_without_ownership(self, db: AsyncSession, obj_users: dict):
        """Manager always passes — no ownership record required."""
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_MANAGER_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.MANAGER,
            resource_type="document",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is True

    async def test_analyst_with_ownership_allowed(self, db: AsyncSession, obj_users: dict):
        """Analyst with valid ownership record → allowed."""
        await _grant(
            db,
            user_id=OBJ_ANALYST_ID,
            resource_type="project",
            resource_id=OBJ_RESOURCE_ID,
        )
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_ANALYST_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.ANALYST,
            resource_type="project",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is True

    async def test_analyst_without_ownership_denied(self, db: AsyncSession, obj_users: dict):
        """Analyst without ownership record → denied."""
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_ANALYST_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.ANALYST,
            resource_type="project",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is False

    async def test_viewer_with_ownership_allowed(self, db: AsyncSession, obj_users: dict):
        """Viewer with valid ownership record → allowed."""
        await _grant(
            db,
            user_id=OBJ_VIEWER_ID,
            resource_type="deal_room",
            resource_id=OBJ_RESOURCE_ID,
        )
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_VIEWER_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.VIEWER,
            resource_type="deal_room",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is True

    async def test_viewer_without_ownership_denied(self, db: AsyncSession, obj_users: dict):
        """Viewer without ownership record → denied."""
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_VIEWER_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.VIEWER,
            resource_type="deal_room",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is False

    async def test_expired_ownership_denied(self, db: AsyncSession, obj_users: dict):
        """Ownership record whose expires_at is in the past → denied."""
        past = datetime.utcnow() - timedelta(hours=1)
        await _grant(
            db,
            user_id=OBJ_VIEWER_ID,
            resource_type="document",
            resource_id=OBJ_RESOURCE_ID,
            expires_at=past,
        )
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_VIEWER_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.VIEWER,
            resource_type="document",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is False

    async def test_cross_org_denied(self, db: AsyncSession, obj_users: dict, obj_other_user: User):
        """Ownership record in org A does not grant access when user is in org B."""
        # Grant ownership scoped to OBJ_OTHER_ORG_ID — but record stores that org
        cross_rec = ResourceOwnership(
            user_id=OBJ_OTHER_USER_ID,
            org_id=OBJ_OTHER_ORG_ID,
            resource_type="project",
            resource_id=OBJ_RESOURCE_ID,
            permission_level=PermissionLevel.OWNER.value,
            granted_by=OBJ_OTHER_USER_ID,
        )
        db.add(cross_rec)
        await db.flush()

        # Same user, same resource, but checked against OBJ_ORG_ID → no match
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_OTHER_USER_ID,
            org_id=OBJ_ORG_ID,  # different org than the grant
            role=UserRole.ANALYST,
            resource_type="project",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is False

    async def test_future_expiry_allowed(self, db: AsyncSession, obj_users: dict):
        """Ownership record whose expires_at is in the future → allowed."""
        future = datetime.utcnow() + timedelta(days=30)
        await _grant(
            db,
            user_id=OBJ_VIEWER_ID,
            resource_type="conversation",
            resource_id=OBJ_RESOURCE_ID,
            expires_at=future,
        )
        allowed = await check_object_permission(
            db=db,
            user_id=OBJ_VIEWER_ID,
            org_id=OBJ_ORG_ID,
            role=UserRole.VIEWER,
            resource_type="conversation",
            resource_id=OBJ_RESOURCE_ID,
        )
        assert allowed is True


# ── TestRequireObjectPermissionDep — HTTP integration ────────────────────────


@pytest.fixture
async def obj_viewer_client(
    db: AsyncSession, obj_users: dict, obj_conversation: AIConversation
) -> AsyncClient:
    """Authenticated client for a VIEWER role user."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app as _app
    from app.schemas.auth import CurrentUser

    current = CurrentUser(
        user_id=OBJ_VIEWER_ID,
        org_id=OBJ_ORG_ID,
        role=UserRole.VIEWER,
        email="obj-viewer@test.example",
        external_auth_id="clerk_obj_viewer",
    )
    _app.dependency_overrides[get_current_user] = lambda: current
    _app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def obj_admin_client(
    db: AsyncSession, obj_users: dict, obj_conversation: AIConversation
) -> AsyncClient:
    """Authenticated client for an ADMIN role user."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app as _app
    from app.schemas.auth import CurrentUser

    current = CurrentUser(
        user_id=OBJ_ADMIN_ID,
        org_id=OBJ_ORG_ID,
        role=UserRole.ADMIN,
        email="obj-admin@test.example",
        external_auth_id="clerk_obj_admin",
    )
    _app.dependency_overrides[get_current_user] = lambda: current
    _app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)


class TestRequireObjectPermissionDep:
    """HTTP-level tests via GET /v1/ralph/conversations/{id}."""

    _url = f"/v1/ralph/conversations/{OBJ_CONV_ID}"

    async def test_admin_bypasses_no_ownership(
        self, obj_admin_client: AsyncClient, obj_conversation: AIConversation
    ):
        """Admin gets the conversation even with no ownership record."""
        with patch("app.core.config.settings.OBJECT_LEVEL_RBAC_ENABLED", True):
            resp = await obj_admin_client.get(self._url)
        assert resp.status_code == 200

    async def test_viewer_with_ownership_allowed(
        self,
        obj_viewer_client: AsyncClient,
        db: AsyncSession,
        obj_users: dict,
        obj_conversation: AIConversation,
    ):
        """Viewer with an ownership record gets through when RBAC is enforced."""
        await _grant(
            db,
            user_id=OBJ_VIEWER_ID,
            resource_type="conversation",
            resource_id=OBJ_CONV_ID,
        )
        with patch("app.core.config.settings.OBJECT_LEVEL_RBAC_ENABLED", True):
            resp = await obj_viewer_client.get(self._url)
        assert resp.status_code == 200

    async def test_viewer_without_ownership_403_when_enforced(
        self,
        obj_viewer_client: AsyncClient,
        obj_conversation: AIConversation,
    ):
        """Viewer without ownership gets 403 when OBJECT_LEVEL_RBAC_ENABLED=True."""
        with patch("app.core.config.settings.OBJECT_LEVEL_RBAC_ENABLED", True):
            resp = await obj_viewer_client.get(self._url)
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    async def test_viewer_without_ownership_200_in_audit_mode(
        self,
        obj_viewer_client: AsyncClient,
        obj_conversation: AIConversation,
    ):
        """In audit mode (flag=False), missing ownership logs warning but allows access."""
        with patch("app.core.config.settings.OBJECT_LEVEL_RBAC_ENABLED", False):
            resp = await obj_viewer_client.get(self._url)
        # Audit mode: 200 even though there is no ownership record
        assert resp.status_code == 200

    async def test_enforcement_is_active(
        self,
        obj_viewer_client: AsyncClient,
        obj_conversation: AIConversation,
    ):
        """OBJECT_LEVEL_RBAC_ENABLED must be True — enforcement must be live.

        This test uses the real config value (no patch). If OBJECT_LEVEL_RBAC_ENABLED
        is False, a viewer without an ownership record would get 200 and this test
        would fail, signalling that enforcement is still in audit mode.
        """
        from app.core.config import settings as real_settings

        assert real_settings.OBJECT_LEVEL_RBAC_ENABLED is True, (
            "OBJECT_LEVEL_RBAC_ENABLED must be True — "
            "run app.scripts.seed_resource_ownership first, then set the flag."
        )
        # No ownership record granted — enforcement must reject
        resp = await obj_viewer_client.get(self._url)
        assert resp.status_code == 403, (
            f"Expected 403 (enforcement active) but got {resp.status_code}. "
            "Check that OBJECT_LEVEL_RBAC_ENABLED=True in config.py."
        )
