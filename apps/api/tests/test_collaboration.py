"""Comprehensive tests for the Collaboration & Notifications modules."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.collaboration import Activity, Comment
from app.models.core import Notification, Organization, User
from app.models.enums import NotificationType, OrgType, UserRole
from app.modules.collaboration import service as collab_service
from app.modules.notifications import service as notif_service
from app.schemas.auth import CurrentUser

# ── Test Data ────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
USER2_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
VIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")
ENTITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")

ADMIN_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="admin@example.com",
    external_auth_id="user_test_admin",
)

ANALYST_USER = CurrentUser(
    user_id=USER2_ID,
    org_id=ORG_ID,
    role=UserRole.ANALYST,
    email="analyst@example.com",
    external_auth_id="user_test_analyst",
)

VIEWER_USER = CurrentUser(
    user_id=VIEWER_USER_ID,
    org_id=ORG_ID,
    role=UserRole.VIEWER,
    email="viewer@example.com",
    external_auth_id="user_test_viewer",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user
    return _override


@pytest.fixture
async def seed_data(db: AsyncSession) -> None:
    """Seed Organization and Users."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.INVESTOR)
    db.add(org)
    other_org = Organization(
        id=OTHER_ORG_ID, name="Other Org", slug="other-org", type=OrgType.ALLY
    )
    db.add(other_org)
    user = User(
        id=USER_ID, org_id=ORG_ID, email="admin@example.com",
        full_name="Admin User", role=UserRole.ADMIN,
        external_auth_id="user_test_admin", is_active=True,
    )
    db.add(user)
    user2 = User(
        id=USER2_ID, org_id=ORG_ID, email="analyst@example.com",
        full_name="Analyst User", role=UserRole.ANALYST,
        external_auth_id="user_test_analyst", is_active=True,
    )
    db.add(user2)
    viewer = User(
        id=VIEWER_USER_ID, org_id=ORG_ID, email="viewer@example.com",
        full_name="Viewer User", role=UserRole.VIEWER,
        external_auth_id="user_test_viewer", is_active=True,
    )
    db.add(viewer)
    await db.flush()


# ── Comment Service Tests ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_comment(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Test comment"
    )
    assert comment.content == "Test comment"
    assert comment.entity_type == "project"
    assert comment.entity_id == ENTITY_ID
    assert comment.org_id == ORG_ID
    assert comment.parent_id is None


@pytest.mark.anyio
async def test_create_threaded_reply(db: AsyncSession, seed_data):
    parent = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Parent comment"
    )
    reply = await collab_service.create_comment(
        db, ANALYST_USER, "project", ENTITY_ID, "Reply", parent_id=parent.id
    )
    assert reply.parent_id == parent.id


@pytest.mark.anyio
async def test_reply_depth_limit(db: AsyncSession, seed_data):
    parent = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Parent"
    )
    reply = await collab_service.create_comment(
        db, ANALYST_USER, "project", ENTITY_ID, "Reply", parent_id=parent.id
    )
    with pytest.raises(ValueError, match="one level deep"):
        await collab_service.create_comment(
            db, ADMIN_USER, "project", ENTITY_ID, "Nested reply", parent_id=reply.id
        )


@pytest.mark.anyio
async def test_list_comments_threaded(db: AsyncSession, seed_data):
    parent = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Parent comment"
    )
    await collab_service.create_comment(
        db, ANALYST_USER, "project", ENTITY_ID, "Reply 1", parent_id=parent.id
    )
    await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Reply 2", parent_id=parent.id
    )

    comments, user_map = await collab_service.list_comments(db, ORG_ID, "project", ENTITY_ID)
    assert len(comments) == 3
    assert len(user_map) >= 2


@pytest.mark.anyio
async def test_update_comment_by_author(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Original"
    )
    updated = await collab_service.update_comment(db, comment.id, USER_ID, "Edited")
    assert updated is not None
    assert updated.content == "Edited"


@pytest.mark.anyio
async def test_update_comment_by_non_author_fails(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Original"
    )
    with pytest.raises(PermissionError, match="Only the author"):
        await collab_service.update_comment(db, comment.id, USER2_ID, "Edited")


@pytest.mark.anyio
async def test_update_comment_after_edit_window_fails(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Original"
    )
    # Manually set created_at to 20 minutes ago
    comment.created_at = datetime.utcnow() - timedelta(minutes=20)
    await db.flush()

    with pytest.raises(ValueError, match="within 15 minutes"):
        await collab_service.update_comment(db, comment.id, USER_ID, "Too late")


@pytest.mark.anyio
async def test_delete_comment_by_author(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "To delete"
    )
    result = await collab_service.delete_comment(db, comment.id, USER_ID, UserRole.ANALYST)
    assert result is True
    assert comment.content == "[deleted]"


@pytest.mark.anyio
async def test_delete_comment_by_admin(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ANALYST_USER, "project", ENTITY_ID, "To delete"
    )
    result = await collab_service.delete_comment(db, comment.id, USER_ID, UserRole.ADMIN)
    assert result is True
    assert comment.content == "[deleted]"


@pytest.mark.anyio
async def test_delete_comment_by_non_author_non_admin_fails(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "To delete"
    )
    with pytest.raises(PermissionError, match="Only the author or an admin"):
        await collab_service.delete_comment(db, comment.id, USER2_ID, UserRole.ANALYST)


@pytest.mark.anyio
async def test_resolve_comment_toggle(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Resolve me"
    )
    assert comment.is_resolved is False
    resolved = await collab_service.resolve_comment(db, comment.id, ORG_ID)
    assert resolved.is_resolved is True
    unresolved = await collab_service.resolve_comment(db, comment.id, ORG_ID)
    assert unresolved.is_resolved is False


@pytest.mark.anyio
async def test_resolve_comment_wrong_org(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Resolve me"
    )
    result = await collab_service.resolve_comment(db, comment.id, OTHER_ORG_ID)
    assert result is None


# ── Mention Tests ────────────────────────────────────────────────────────────


def test_parse_mentions():
    assert collab_service.parse_mentions("Hello @john how are you?") == ["john"]
    assert collab_service.parse_mentions("@admin.user and @analyst") == ["admin.user", "analyst"]
    assert collab_service.parse_mentions("No mentions here") == []


@pytest.mark.anyio
async def test_mention_parsing_in_comment(db: AsyncSession, seed_data):
    comment = await collab_service.create_comment(
        db, ADMIN_USER, "project", ENTITY_ID, "Hey @Analyst what do you think?"
    )
    assert comment.mentions is not None
    assert len(comment.mentions["users"]) == 1
    assert comment.mentions["users"][0]["full_name"] == "Analyst User"


# ── Activity Service Tests ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_record_activity(db: AsyncSession, seed_data):
    activity = await collab_service.record_activity(
        db, ORG_ID, USER_ID, "project", ENTITY_ID,
        "created", "Created project",
    )
    assert activity.action == "created"
    assert activity.entity_type == "project"


@pytest.mark.anyio
async def test_get_entity_activity(db: AsyncSession, seed_data):
    for i in range(5):
        await collab_service.record_activity(
            db, ORG_ID, USER_ID, "project", ENTITY_ID,
            "updated", f"Update {i}",
        )
    activities, total, user_map = await collab_service.get_entity_activity(
        db, ORG_ID, "project", ENTITY_ID, page=1, page_size=3
    )
    assert total == 5
    assert len(activities) == 3


@pytest.mark.anyio
async def test_get_activity_feed(db: AsyncSession, seed_data):
    entity2_id = uuid.uuid4()
    await collab_service.record_activity(
        db, ORG_ID, USER_ID, "project", ENTITY_ID, "created", "Created"
    )
    await collab_service.record_activity(
        db, ORG_ID, USER_ID, "portfolio", entity2_id, "updated", "Updated"
    )
    activities, total, user_map = await collab_service.get_activity_feed(
        db, ORG_ID, page=1, page_size=20
    )
    assert total == 2
    assert len(activities) == 2


# ── Notification Service Tests ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_notification(db: AsyncSession, seed_data):
    notification = await notif_service.create_notification(
        db, ORG_ID, USER_ID,
        NotificationType.INFO, "Test", "Test notification",
    )
    assert notification.title == "Test"
    assert notification.is_read is False


@pytest.mark.anyio
async def test_list_notifications(db: AsyncSession, seed_data):
    for i in range(5):
        await notif_service.create_notification(
            db, ORG_ID, USER_ID,
            NotificationType.INFO, f"Notif {i}", f"Message {i}",
        )
    notifications, total = await notif_service.list_notifications(
        db, USER_ID, page=1, page_size=3
    )
    assert total == 5
    assert len(notifications) == 3


@pytest.mark.anyio
async def test_list_notifications_filter_by_type(db: AsyncSession, seed_data):
    await notif_service.create_notification(
        db, ORG_ID, USER_ID, NotificationType.INFO, "Info", "Info msg"
    )
    await notif_service.create_notification(
        db, ORG_ID, USER_ID, NotificationType.MENTION, "Mention", "Mention msg"
    )
    notifications, total = await notif_service.list_notifications(
        db, USER_ID, type=NotificationType.MENTION
    )
    assert total == 1
    assert notifications[0].type == NotificationType.MENTION


@pytest.mark.anyio
async def test_mark_read(db: AsyncSession, seed_data):
    notification = await notif_service.create_notification(
        db, ORG_ID, USER_ID, NotificationType.INFO, "Test", "Msg"
    )
    assert notification.is_read is False
    success = await notif_service.mark_read(db, notification.id, USER_ID)
    assert success is True
    assert notification.is_read is True


@pytest.mark.anyio
async def test_mark_read_wrong_user(db: AsyncSession, seed_data):
    notification = await notif_service.create_notification(
        db, ORG_ID, USER_ID, NotificationType.INFO, "Test", "Msg"
    )
    success = await notif_service.mark_read(db, notification.id, USER2_ID)
    assert success is False


@pytest.mark.anyio
async def test_mark_all_read(db: AsyncSession, seed_data):
    for _ in range(3):
        await notif_service.create_notification(
            db, ORG_ID, USER_ID, NotificationType.INFO, "T", "M"
        )
    count = await notif_service.mark_all_read(db, USER_ID)
    assert count == 3
    unread = await notif_service.get_unread_count(db, USER_ID)
    assert unread == 0


@pytest.mark.anyio
async def test_get_unread_count(db: AsyncSession, seed_data):
    for _ in range(4):
        await notif_service.create_notification(
            db, ORG_ID, USER_ID, NotificationType.INFO, "T", "M"
        )
    count = await notif_service.get_unread_count(db, USER_ID)
    assert count == 4


@pytest.mark.anyio
async def test_notify_mentions_skips_self(db: AsyncSession, seed_data):
    notifications = await notif_service.notify_mentions(
        db, ORG_ID, USER_ID, "Hey @Admin check this", "project", ENTITY_ID
    )
    # Admin mentioned self → should be skipped
    assert len(notifications) == 0


@pytest.mark.anyio
async def test_notify_mentions_creates_notification(db: AsyncSession, seed_data):
    notifications = await notif_service.notify_mentions(
        db, ORG_ID, USER_ID, "Hey @Analyst check this", "project", ENTITY_ID
    )
    assert len(notifications) == 1
    assert notifications[0].user_id == USER2_ID
    assert notifications[0].type == NotificationType.MENTION


# ── Comment API Tests ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_api_create_comment(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ANALYST_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = await client.post("/collaboration/comments", json={
            "entity_type": "project",
            "entity_id": str(ENTITY_ID),
            "content": "API comment",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "API comment"
        assert data["author"]["full_name"] == "Analyst User"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_list_comments(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ANALYST_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        # Create a comment first
        await client.post("/collaboration/comments", json={
            "entity_type": "project",
            "entity_id": str(ENTITY_ID),
            "content": "First comment",
        })
        resp = await client.get(
            "/collaboration/comments",
            params={"entity_type": "project", "entity_id": str(ENTITY_ID)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_update_comment(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ANALYST_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        create_resp = await client.post("/collaboration/comments", json={
            "entity_type": "project",
            "entity_id": str(ENTITY_ID),
            "content": "Original",
        })
        comment_id = create_resp.json()["id"]
        resp = await client.put(f"/collaboration/comments/{comment_id}", json={
            "content": "Updated",
        })
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_delete_comment(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ANALYST_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        create_resp = await client.post("/collaboration/comments", json={
            "entity_type": "project",
            "entity_id": str(ENTITY_ID),
            "content": "To delete",
        })
        comment_id = create_resp.json()["id"]
        resp = await client.delete(f"/collaboration/comments/{comment_id}")
        assert resp.status_code == 204
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_resolve_comment(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ANALYST_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        create_resp = await client.post("/collaboration/comments", json={
            "entity_type": "project",
            "entity_id": str(ENTITY_ID),
            "content": "Resolve me",
        })
        comment_id = create_resp.json()["id"]
        resp = await client.post(f"/collaboration/comments/{comment_id}/resolve")
        assert resp.status_code == 200
        assert resp.json()["is_resolved"] is True
    finally:
        app.dependency_overrides.clear()


# ── RBAC Tests ───────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_viewer_can_view_comments(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = await client.get(
            "/collaboration/comments",
            params={"entity_type": "project", "entity_id": str(ENTITY_ID)},
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_viewer_cannot_create_comment(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = await client.post("/collaboration/comments", json={
            "entity_type": "project",
            "entity_id": str(ENTITY_ID),
            "content": "Should fail",
        })
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_viewer_cannot_edit_comment(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        resp = await client.put(f"/collaboration/comments/{uuid.uuid4()}", json={
            "content": "Should fail",
        })
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ── Notification API Tests ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_api_list_notifications(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        # Create some notifications
        await notif_service.create_notification(
            db, ORG_ID, USER_ID, NotificationType.INFO, "Test", "Msg"
        )
        resp = await client.get("/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_unread_count(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        await notif_service.create_notification(
            db, ORG_ID, USER_ID, NotificationType.INFO, "Test", "Msg"
        )
        resp = await client.get("/notifications/unread-count")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_mark_all_read(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        await notif_service.create_notification(
            db, ORG_ID, USER_ID, NotificationType.INFO, "Test", "Msg"
        )
        resp = await client.put("/notifications/read-all")
        assert resp.status_code == 200
        assert resp.json()["marked_read"] >= 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_mark_single_read(client: AsyncClient, db: AsyncSession, seed_data):
    app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
    app.dependency_overrides[get_db] = lambda: db
    try:
        notification = await notif_service.create_notification(
            db, ORG_ID, USER_ID, NotificationType.INFO, "Test", "Msg"
        )
        resp = await client.put(f"/notifications/{notification.id}/read")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
    finally:
        app.dependency_overrides.clear()
