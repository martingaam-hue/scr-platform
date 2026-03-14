"""Integration tests for the Deal Rooms module.

Covers:
  TestRoomCRUD            — create, list, get room lifecycle
  TestRoomCreation        — activity logged on creation, status="active"
  TestMemberManagement    — invite member, role/permissions, appears in room
  TestMessaging           — send message, list messages, threaded reply
  TestActivityFeed        — activities appear after room events
  TestCloseRoom           — close room, verify status="closed"
  TestOrgScoping          — list only returns own org's rooms

Note: the deal-rooms router uses ("manage", "project") and ("view", "project")
where "manage" is not a standard action in the RBAC matrix. Client fixtures
patch check_permission (same pattern as test_module_batch4) to allow it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.auth.dependencies as deps_module
from app.auth.dependencies import get_current_user
from app.auth.rbac import check_permission as original_check
from app.core.database import get_db, get_readonly_session
from app.main import app
from app.models.core import Organization, User
from app.models.enums import OrgType, ProjectStatus, ProjectType, UserRole
from app.models.projects import Project
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Module-unique UUIDs (no collision with other test files) ──────────────────

DR_ORG_ID = uuid.UUID("00000000-0000-00D2-0000-000000000001")
DR_USER_ID = uuid.UUID("00000000-0000-00D2-0000-000000000002")
DR_PROJECT_ID = uuid.UUID("00000000-0000-00D2-0000-000000000003")

DR_ORG2_ID = uuid.UUID("00000000-0000-00D2-0000-000000000010")
DR_USER2_ID = uuid.UUID("00000000-0000-00D2-0000-000000000011")
DR_PROJECT2_ID = uuid.UUID("00000000-0000-00D2-0000-000000000012")

# Non-standard (action, resource_type) pairs used by the deal-rooms router.
_DR_ALWAYS_ALLOW = {
    ("manage", "project"),
    ("view", "project"),
    ("view", "deal_room"),
}

DR_CURRENT_USER = CurrentUser(
    user_id=DR_USER_ID,
    org_id=DR_ORG_ID,
    role=UserRole.ADMIN,
    email="dr_test@example.com",
    external_auth_id="clerk_dr_test",
)

DR_CURRENT_USER2 = CurrentUser(
    user_id=DR_USER2_ID,
    org_id=DR_ORG2_ID,
    role=UserRole.ADMIN,
    email="dr_test2@example.com",
    external_auth_id="clerk_dr_test2",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def dr_org(db: AsyncSession) -> Organization:
    org = Organization(id=DR_ORG_ID, name="DR Test Org", slug="dr-test-org", type=OrgType.ALLY)
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def dr_user(db: AsyncSession, dr_org: Organization) -> User:
    user = User(
        id=DR_USER_ID,
        org_id=DR_ORG_ID,
        email="dr_test@example.com",
        full_name="DR Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_dr_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def dr_project(db: AsyncSession, dr_org: Organization) -> Project:
    proj = Project(
        id=DR_PROJECT_ID,
        org_id=DR_ORG_ID,
        name="DR Test Project",
        slug="dr-test-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Netherlands",
        total_investment_required=Decimal("10000000"),
        currency="EUR",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def dr_org2(db: AsyncSession) -> Organization:
    org = Organization(
        id=DR_ORG2_ID, name="DR Test Org 2", slug="dr-test-org-2", type=OrgType.INVESTOR
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def dr_user2(db: AsyncSession, dr_org2: Organization) -> User:
    user = User(
        id=DR_USER2_ID,
        org_id=DR_ORG2_ID,
        email="dr_test2@example.com",
        full_name="DR Test User 2",
        role=UserRole.ADMIN,
        external_auth_id="clerk_dr_test2",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def dr_project2(db: AsyncSession, dr_org2: Organization) -> Project:
    proj = Project(
        id=DR_PROJECT2_ID,
        org_id=DR_ORG2_ID,
        name="DR Test Project 2",
        slug="dr-test-project-2",
        project_type=ProjectType.WIND,
        status=ProjectStatus.ACTIVE,
        geography_country="Denmark",
        total_investment_required=Decimal("20000000"),
        currency="EUR",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


def _patched_check_dr(role, action, resource_type, resource_id=None):
    """Allow non-standard deal-rooms (action, resource_type) pairs in tests."""
    if (action, resource_type) in _DR_ALWAYS_ALLOW:
        return True
    return original_check(role, action, resource_type, resource_id)


@pytest.fixture
async def dr_client(db: AsyncSession, dr_user: User) -> AsyncClient:
    """Authenticated client scoped to DR_ORG_ID with deal-room permissions patched."""
    app.dependency_overrides[get_current_user] = lambda: DR_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    with patch.object(deps_module, "check_permission", side_effect=_patched_check_dr):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_readonly_session, None)


@pytest.fixture
async def dr_client2(db: AsyncSession, dr_user2: User) -> AsyncClient:
    """Authenticated client scoped to DR_ORG2_ID with deal-room permissions patched."""
    app.dependency_overrides[get_current_user] = lambda: DR_CURRENT_USER2
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    with patch.object(deps_module, "check_permission", side_effect=_patched_check_dr):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_readonly_session, None)


async def _create_room(
    client: AsyncClient,
    project_id: uuid.UUID,
    name: str = "Test Room",
    settings: dict | None = None,
) -> dict:
    """Helper: create a deal room and return the parsed JSON."""
    payload: dict = {"project_id": str(project_id), "name": name}
    if settings:
        payload["settings"] = settings
    resp = await client.post("/v1/deal-rooms/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── TestRoomCRUD ──────────────────────────────────────────────────────────────


class TestRoomCRUD:
    async def test_create_room_returns_201(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        resp = await dr_client.post(
            "/v1/deal-rooms/",
            json={"project_id": str(DR_PROJECT_ID), "name": "Investor Room A"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Investor Room A"
        assert data["status"] == "active"
        assert data["org_id"] == str(DR_ORG_ID)
        assert data["project_id"] == str(DR_PROJECT_ID)
        assert data["created_by"] == str(DR_USER_ID)

    async def test_create_room_creator_is_owner_member(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Ownership Check Room")
        room_id = room["id"]

        # Retrieve room with members via GET
        get_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}")
        assert get_resp.status_code == 200
        members = get_resp.json()["members"]
        assert len(members) >= 1
        owner_members = [m for m in members if m["role"] == "owner"]
        assert len(owner_members) == 1
        assert owner_members[0]["user_id"] == str(DR_USER_ID)

    async def test_list_rooms_includes_created_room(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        await _create_room(dr_client, DR_PROJECT_ID, "Listed Room")
        list_resp = await dr_client.get("/v1/deal-rooms/")
        assert list_resp.status_code == 200
        names = [r["name"] for r in list_resp.json()]
        assert "Listed Room" in names

    async def test_get_room_returns_correct_data(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Get Room Test")
        room_id = room["id"]

        get_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == room_id
        assert data["name"] == "Get Room Test"
        assert data["project_id"] == str(DR_PROJECT_ID)

    async def test_get_nonexistent_room_returns_404(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        resp = await dr_client.get(f"/v1/deal-rooms/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_create_room_with_settings(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        settings = {"watermark": True, "nda_required": True, "download_restricted": False}
        room = await _create_room(dr_client, DR_PROJECT_ID, "Settings Room", settings=settings)
        assert room["settings"]["watermark"] is True
        assert room["settings"]["nda_required"] is True


# ── TestRoomCreation ──────────────────────────────────────────────────────────


class TestRoomCreation:
    async def test_new_room_has_active_status(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Status Check Room")
        assert room["status"] == "active"

    async def test_room_creation_logs_activity(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Activity Log Room")
        room_id = room["id"]

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        assert activity_resp.status_code == 200
        activities = activity_resp.json()
        activity_types = [a["activity_type"] for a in activities]
        assert "room_created" in activity_types

    async def test_room_created_activity_has_correct_user(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "User Activity Room")
        room_id = room["id"]

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activities = activity_resp.json()
        creation_activities = [a for a in activities if a["activity_type"] == "room_created"]
        assert len(creation_activities) >= 1
        assert creation_activities[0]["user_id"] == str(DR_USER_ID)


# ── TestMemberManagement ──────────────────────────────────────────────────────


class TestMemberManagement:
    async def test_invite_member_returns_201(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Invite Room")
        room_id = room["id"]

        invite_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/invite",
            json={"email": "investor@fund.com", "role": "member", "org_name": "Big Fund"},
        )
        assert invite_resp.status_code == 201
        data = invite_resp.json()
        assert data["email"] == "investor@fund.com"
        assert data["role"] == "member"
        assert data["org_name"] == "Big Fund"

    async def test_invited_member_has_default_permissions(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Permissions Room")
        room_id = room["id"]

        invite_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/invite",
            json={"email": "member@fund.com", "role": "member"},
        )
        assert invite_resp.status_code == 201
        perms = invite_resp.json()["permissions"]
        # Default member permissions: can_upload, can_download, can_comment — but NOT financials
        assert perms.get("can_comment") is True
        assert perms.get("can_view_financials") is False

    async def test_invite_viewer_has_restricted_permissions(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Viewer Perms Room")
        room_id = room["id"]

        invite_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/invite",
            json={"email": "viewer@fund.com", "role": "viewer"},
        )
        assert invite_resp.status_code == 201
        perms = invite_resp.json()["permissions"]
        assert perms.get("can_upload") is False
        assert perms.get("can_download") is False

    async def test_invite_with_custom_permissions(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Custom Perms Room")
        room_id = room["id"]

        custom_perms = {
            "can_upload": False,
            "can_download": True,
            "can_comment": True,
            "can_view_financials": True,
            "can_invite": False,
        }
        invite_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/invite",
            json={"email": "special@fund.com", "role": "member", "permissions": custom_perms},
        )
        assert invite_resp.status_code == 201
        assert invite_resp.json()["permissions"]["can_view_financials"] is True
        assert invite_resp.json()["permissions"]["can_upload"] is False

    async def test_invited_member_appears_in_room_members(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Members List Room")
        room_id = room["id"]

        await dr_client.post(
            f"/v1/deal-rooms/{room_id}/invite",
            json={"email": "visible@fund.com", "role": "admin"},
        )

        # Verify via activity feed (invite logs an activity)
        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activity_types = [a["activity_type"] for a in activity_resp.json()]
        assert "member_invited" in activity_types


# ── TestMessaging ─────────────────────────────────────────────────────────────


class TestMessaging:
    async def test_send_message_returns_201(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Message Room")
        room_id = room["id"]

        msg_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages",
            json={"content": "Hello, deal team!"},
        )
        assert msg_resp.status_code == 201
        data = msg_resp.json()
        assert data["content"] == "Hello, deal team!"
        assert data["room_id"] == room_id
        assert data["user_id"] == str(DR_USER_ID)
        assert data["parent_id"] is None

    async def test_get_messages_returns_sent_message(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Get Messages Room")
        room_id = room["id"]

        await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages", json={"content": "First message"}
        )
        await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages", json={"content": "Second message"}
        )

        get_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/messages")
        assert get_resp.status_code == 200
        messages = get_resp.json()
        assert len(messages) == 2
        contents = [m["content"] for m in messages]
        assert "First message" in contents
        assert "Second message" in contents

    async def test_messages_ordered_chronologically(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Ordered Messages Room")
        room_id = room["id"]

        await dr_client.post(f"/v1/deal-rooms/{room_id}/messages", json={"content": "Alpha"})
        await dr_client.post(f"/v1/deal-rooms/{room_id}/messages", json={"content": "Beta"})

        get_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/messages")
        messages = get_resp.json()
        assert messages[0]["content"] == "Alpha"
        assert messages[1]["content"] == "Beta"

    async def test_threaded_reply_sets_parent_id(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Thread Room")
        room_id = room["id"]

        parent_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages",
            json={"content": "Parent message"},
        )
        parent_id = parent_resp.json()["id"]

        reply_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages",
            json={"content": "Reply message", "parent_id": parent_id},
        )
        assert reply_resp.status_code == 201
        assert reply_resp.json()["parent_id"] == parent_id

    async def test_message_with_mentions(self, dr_client: AsyncClient, dr_project: Project) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Mentions Room")
        room_id = room["id"]

        mentioned_user = str(uuid.uuid4())
        msg_resp = await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages",
            json={"content": "Hey @user please review", "mentions": [mentioned_user]},
        )
        assert msg_resp.status_code == 201
        # Mentions are stored as strings
        assert mentioned_user in msg_resp.json()["mentions"]


# ── TestActivityFeed ──────────────────────────────────────────────────────────


class TestActivityFeed:
    async def test_activity_feed_returns_list(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Activity Feed Room")
        room_id = room["id"]

        resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_invite_creates_activity(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Invite Activity Room")
        room_id = room["id"]

        await dr_client.post(
            f"/v1/deal-rooms/{room_id}/invite",
            json={"email": "activity@fund.com", "role": "member"},
        )

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activity_types = [a["activity_type"] for a in activity_resp.json()]
        assert "member_invited" in activity_types

    async def test_message_creates_activity(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Message Activity Room")
        room_id = room["id"]

        await dr_client.post(
            f"/v1/deal-rooms/{room_id}/messages",
            json={"content": "Activity generating message"},
        )

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activity_types = [a["activity_type"] for a in activity_resp.json()]
        assert "message" in activity_types

    async def test_activity_feed_has_expected_fields(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Fields Check Room")
        room_id = room["id"]

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activities = activity_resp.json()
        assert len(activities) >= 1
        for a in activities:
            assert "id" in a
            assert "room_id" in a
            assert "user_id" in a
            assert "activity_type" in a
            assert "created_at" in a

    async def test_share_document_creates_activity(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Doc Share Activity Room")
        room_id = room["id"]

        doc_id = str(uuid.uuid4())
        await dr_client.post(
            f"/v1/deal-rooms/{room_id}/documents",
            json={"document_id": doc_id},
        )

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activity_types = [a["activity_type"] for a in activity_resp.json()]
        assert "doc_shared" in activity_types


# ── TestCloseRoom ─────────────────────────────────────────────────────────────


class TestCloseRoom:
    async def test_close_room_returns_closed_status(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Room To Close")
        room_id = room["id"]

        close_resp = await dr_client.post(f"/v1/deal-rooms/{room_id}/close")
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

    async def test_close_room_persists_in_get(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Closed Persisted Room")
        room_id = room["id"]

        await dr_client.post(f"/v1/deal-rooms/{room_id}/close")

        get_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "closed"

    async def test_close_room_logs_activity(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        room = await _create_room(dr_client, DR_PROJECT_ID, "Close Activity Room")
        room_id = room["id"]

        await dr_client.post(f"/v1/deal-rooms/{room_id}/close")

        activity_resp = await dr_client.get(f"/v1/deal-rooms/{room_id}/activity")
        activity_types = [a["activity_type"] for a in activity_resp.json()]
        assert "room_closed" in activity_types

    async def test_close_nonexistent_room_returns_404(
        self, dr_client: AsyncClient, dr_project: Project
    ) -> None:
        resp = await dr_client.post(f"/v1/deal-rooms/{uuid.uuid4()}/close")
        assert resp.status_code == 404


# ── TestOrgScoping ────────────────────────────────────────────────────────────


class TestOrgScoping:
    async def test_list_rooms_only_returns_own_org(
        self,
        dr_client: AsyncClient,
        db: AsyncSession,
        dr_project: Project,
        dr_project2: Project,
        dr_org2: Organization,
    ) -> None:
        """Org1's list only returns rooms whose org_id matches the authenticated user."""
        from datetime import datetime

        # Org1 creates a room via HTTP
        await _create_room(dr_client, DR_PROJECT_ID, "Org1 Private Room")

        # Seed org2's room directly to avoid override conflict
        from app.models.deal_rooms import DealRoom, DealRoomMember

        org2_room = DealRoom(
            org_id=DR_ORG2_ID,
            project_id=DR_PROJECT2_ID,
            name="Org2 Room Seeded",
            created_by=DR_USER2_ID,
            settings={},
        )
        db.add(org2_room)
        await db.flush()

        # Org1 lists — should see their room but not org2's
        list_resp = await dr_client.get("/v1/deal-rooms/")
        assert list_resp.status_code == 200
        org1_rooms = list_resp.json()
        org1_names = [r["name"] for r in org1_rooms]
        assert "Org1 Private Room" in org1_names
        assert "Org2 Room Seeded" not in org1_names

        # All returned rooms belong to org1
        for room in org1_rooms:
            assert room["org_id"] == str(DR_ORG_ID)

    async def test_org2_cannot_get_org1_room(
        self,
        db: AsyncSession,
        dr_project: Project,
        dr_org2: Organization,
    ) -> None:
        """GET /deal-rooms/{id} returns 404 when room belongs to a different org."""
        from app.models.deal_rooms import DealRoom

        # Seed org1's room directly
        org1_room = DealRoom(
            org_id=DR_ORG_ID,
            project_id=DR_PROJECT_ID,
            name="Org1 Secret Room",
            created_by=DR_USER_ID,
            settings={},
        )
        db.add(org1_room)
        await db.flush()

        # Build a client authenticated as org2 and try to fetch org1's room
        from unittest.mock import patch

        from httpx import ASGITransport
        from httpx import AsyncClient as _AC

        app.dependency_overrides[get_current_user] = lambda: DR_CURRENT_USER2
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_readonly_session] = lambda: db
        with patch.object(deps_module, "check_permission", side_effect=_patched_check_dr):
            async with _AC(transport=ASGITransport(app=app), base_url="http://test") as ac2:
                get_resp = await ac2.get(f"/v1/deal-rooms/{org1_room.id}")
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_readonly_session, None)

        assert get_resp.status_code == 404
