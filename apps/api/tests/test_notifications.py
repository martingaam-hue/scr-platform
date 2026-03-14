"""Tests for the notifications module: create, list, mark-read, bulk read-all, org scoping."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Notification
from app.models.enums import NotificationType
from app.modules.notifications import service as notif_service
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio

OTHER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000077")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID = SAMPLE_USER_ID,
    org_id: uuid.UUID = SAMPLE_ORG_ID,
    type: NotificationType = NotificationType.INFO,
    title: str = "Test Notification",
    message: str = "This is a test.",
    is_read: bool = False,
) -> Notification:
    """Directly insert a Notification row (bypasses SSE push)."""
    notif = Notification(
        org_id=org_id,
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        is_read=is_read,
    )
    db.add(notif)
    await db.flush()
    await db.refresh(notif)
    return notif


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_create_notification_returns_notification(db: AsyncSession, sample_org, sample_user):
    """create_notification stores the row and returns it (SSE push is a no-op in tests)."""
    with patch(
        "app.modules.notifications.service.sse_manager.push", new_callable=AsyncMock
    ) as mock_push:
        notif = await notif_service.create_notification(
            db,
            org_id=SAMPLE_ORG_ID,
            user_id=SAMPLE_USER_ID,
            type=NotificationType.ACTION_REQUIRED,
            title="Action Needed",
            message="Please review the document.",
            link="/documents/123",
        )

    assert notif.id is not None
    assert notif.title == "Action Needed"
    assert notif.type == NotificationType.ACTION_REQUIRED
    assert notif.is_read is False
    assert notif.link == "/documents/123"
    mock_push.assert_awaited_once()


async def test_list_notifications_unread_filter(db: AsyncSession, sample_org, sample_user):
    """list_notifications(is_read=False) returns only unread entries."""
    await _create_notification(db, title="Unread 1", is_read=False)
    await _create_notification(db, title="Unread 2", is_read=False)
    await _create_notification(db, title="Already Read", is_read=True)

    notifs, total = await notif_service.list_notifications(db, SAMPLE_USER_ID, is_read=False)

    titles = [n.title for n in notifs]
    assert "Unread 1" in titles
    assert "Unread 2" in titles
    assert "Already Read" not in titles
    assert total == len([t for t in titles])  # count matches list length


async def test_list_notifications_type_filter(db: AsyncSession, sample_org, sample_user):
    """list_notifications filters by notification type."""
    await _create_notification(db, type=NotificationType.WARNING, title="Warning Notif")
    await _create_notification(db, type=NotificationType.SYSTEM, title="System Notif")

    warnings, total = await notif_service.list_notifications(
        db, SAMPLE_USER_ID, type=NotificationType.WARNING
    )

    assert all(n.type == NotificationType.WARNING for n in warnings)
    titles = [n.title for n in warnings]
    assert "Warning Notif" in titles
    assert "System Notif" not in titles


async def test_mark_read_marks_single_notification(db: AsyncSession, sample_org, sample_user):
    """mark_read sets is_read=True for the target notification."""
    notif = await _create_notification(db, is_read=False)

    success = await notif_service.mark_read(db, notif.id, SAMPLE_USER_ID)
    assert success is True

    await db.refresh(notif)
    assert notif.is_read is True


async def test_mark_read_returns_false_for_wrong_user(db: AsyncSession, sample_org, sample_user):
    """mark_read returns False when the notification belongs to a different user."""
    notif = await _create_notification(db, user_id=SAMPLE_USER_ID)

    success = await notif_service.mark_read(db, notif.id, OTHER_USER_ID)
    assert success is False


async def test_mark_all_read_bulk_updates(db: AsyncSession, sample_org, sample_user):
    """mark_all_read updates all unread notifications for a user and returns the count."""
    for i in range(4):
        await _create_notification(db, title=f"Unread {i}", is_read=False)
    # One already read — should not inflate the count
    await _create_notification(db, title="Pre-read", is_read=True)

    count = await notif_service.mark_all_read(db, SAMPLE_USER_ID)
    assert count == 4

    # Verify unread count is now 0
    unread = await notif_service.get_unread_count(db, SAMPLE_USER_ID)
    assert unread == 0


async def test_get_unread_count_excludes_read(db: AsyncSession, sample_org, sample_user):
    """get_unread_count counts only unread notifications."""
    await _create_notification(db, title="Unread A", is_read=False)
    await _create_notification(db, title="Unread B", is_read=False)
    await _create_notification(db, title="Read C", is_read=True)

    count = await notif_service.get_unread_count(db, SAMPLE_USER_ID)
    assert count == 2


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_list_notifications_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/notifications returns paginated list with correct structure."""
    await _create_notification(db, title="HTTP Listed Notification")

    resp = await authenticated_client.get("/v1/notifications")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "total_pages" in data
    assert data["total"] >= 1


async def test_http_unread_count_endpoint(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/notifications/unread-count returns integer count."""
    await _create_notification(db, title="Unread for Count Test", is_read=False)

    resp = await authenticated_client.get("/v1/notifications/unread-count")

    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert data["count"] >= 1


async def test_http_mark_single_read(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/notifications/{id}/read marks the notification as read."""
    notif = await _create_notification(db, title="To Mark Read", is_read=False)

    resp = await authenticated_client.put(f"/v1/notifications/{notif.id}/read")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


async def test_http_mark_all_read(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/notifications/read-all marks all notifications read."""
    for i in range(3):
        await _create_notification(db, title=f"Bulk Read {i}", is_read=False)

    resp = await authenticated_client.put("/v1/notifications/read-all")

    assert resp.status_code == 200
    data = resp.json()
    assert "marked_read" in data
    assert data["marked_read"] >= 3


async def test_http_mark_read_404_for_unknown(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/notifications/{unknown}/read returns 404."""
    resp = await authenticated_client.put(f"/v1/notifications/{uuid.uuid4()}/read")
    assert resp.status_code == 404
