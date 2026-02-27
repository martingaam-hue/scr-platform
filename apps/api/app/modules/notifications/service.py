"""Notification service: create, list, mark-read, SSE push."""

import uuid

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.core import Notification, User
from app.models.enums import NotificationType
from app.modules.collaboration.service import parse_mentions, resolve_mention_users
from app.modules.notifications.sse import sse_manager

logger = structlog.get_logger()


async def create_notification(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    message: str,
    link: str | None = None,
) -> Notification:
    """Create a notification and push it via SSE."""
    notification = Notification(
        org_id=org_id,
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
    )
    db.add(notification)
    await db.flush()

    # Push SSE event
    await sse_manager.push(user_id, {
        "type": "notification",
        "data": {
            "id": str(notification.id),
            "type": type.value,
            "title": title,
            "message": message,
            "link": link,
        },
    })

    return notification


async def notify_mentions(
    db: AsyncSession,
    org_id: uuid.UUID,
    author_user_id: uuid.UUID,
    content: str,
    entity_type: str,
    entity_id: uuid.UUID,
    entity_label: str | None = None,
) -> list[Notification]:
    """Parse @mentions in content and create MENTION notifications (skip author self-mention)."""
    tokens = parse_mentions(content)
    if not tokens:
        return []

    mentioned_users = await resolve_mention_users(db, org_id, tokens)
    notifications = []
    for user in mentioned_users:
        if user.id == author_user_id:
            continue  # Skip self-mention

        # Load author name
        author_result = await db.execute(select(User).where(User.id == author_user_id))
        author = author_result.scalar_one_or_none()
        author_name = author.full_name if author else "Someone"

        label = entity_label or entity_type
        notification = await create_notification(
            db,
            org_id=org_id,
            user_id=user.id,
            type=NotificationType.MENTION,
            title=f"{author_name} mentioned you",
            message=f"You were mentioned in a comment on {label}",
            link=f"/{entity_type}/{entity_id}",
        )
        notifications.append(notification)

    return notifications


async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    type: NotificationType | None = None,
    is_read: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Notification], int]:
    """List notifications for a user with optional filters."""
    base = select(Notification).where(Notification.user_id == user_id)

    if type is not None:
        base = base.where(Notification.type == type)
    if is_read is not None:
        base = base.where(Notification.is_read == is_read)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(Notification.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    notifications = list(result.scalars().all())

    return notifications, total


async def mark_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Mark a single notification as read."""
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        return False
    notification.is_read = True
    await db.flush()
    return True


async def mark_all_read(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Mark all unread notifications as read. Returns count updated."""
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def get_unread_count(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Get unread notification count for a user."""
    stmt = select(func.count()).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    result = await db.execute(stmt)
    return result.scalar() or 0
