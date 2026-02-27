"""Notifications API router: list, read, stream (SSE), preferences."""

import asyncio
import json
import math
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.core import User
from app.models.enums import NotificationType
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
    UpdatePreferencesRequest,
)
from app.modules.notifications.sse import sse_manager
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Helper ───────────────────────────────────────────────────────────────────


def _notification_to_response(n) -> NotificationResponse:
    return NotificationResponse(
        id=n.id,
        type=n.type,
        title=n.title,
        message=n.message,
        link=n.link,
        is_read=n.is_read,
        created_at=n.created_at,
    )


# ── Fixed-path routes (before /{id}) ─────────────────────────────────────────


@router.get(
    "",
    response_model=NotificationListResponse,
)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: NotificationType | None = Query(None),
    is_read: bool | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    notifications, total = await service.list_notifications(
        db, current_user.user_id, type=type, is_read=is_read,
        page=page, page_size=page_size,
    )
    return NotificationListResponse(
        items=[_notification_to_response(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.put(
    "/read-all",
    response_model=dict,
)
async def mark_all_read(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    count = await service.mark_all_read(db, current_user.user_id)
    await db.commit()
    return {"marked_read": count}


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count."""
    count = await service.get_unread_count(db, current_user.user_id)
    return UnreadCountResponse(count=count)


@router.get(
    "/stream",
)
async def notification_stream(
    current_user: CurrentUser = Depends(get_current_user),
):
    """SSE stream for real-time notifications."""

    async def event_generator():
        queue = await sse_manager.connect(current_user.user_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.disconnect(current_user.user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.put(
    "/preferences",
    response_model=dict,
)
async def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences for the current user."""
    user_result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    prefs = user.preferences or {}
    notification_settings = prefs.get("notification_settings", {})
    notification_settings.update(body.preferences)
    prefs["notification_settings"] = notification_settings
    user.preferences = prefs
    await db.commit()
    return {"notification_settings": notification_settings}


# ── Parameterized routes (after fixed paths) ─────────────────────────────────


@router.put(
    "/{notification_id}/read",
    response_model=dict,
)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    success = await service.mark_read(db, notification_id, current_user.user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await db.commit()
    return {"success": True}
