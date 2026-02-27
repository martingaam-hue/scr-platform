"""Collaboration service: comment and activity business logic."""

import re
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.collaboration import Activity, Comment
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

EDIT_WINDOW_MINUTES = 15
MENTION_PATTERN = re.compile(r"@([\w][\w.]*[\w]|[\w]+)")


# ── Mention helpers ──────────────────────────────────────────────────────────


def parse_mentions(content: str) -> list[str]:
    """Extract @mention tokens from content."""
    return MENTION_PATTERN.findall(content)


async def resolve_mention_users(
    db: AsyncSession, org_id: uuid.UUID, tokens: list[str]
) -> list[User]:
    """Look up users by matching tokens against full_name (case-insensitive) within org."""
    if not tokens:
        return []

    stmt = select(User).where(
        User.org_id == org_id,
        User.is_active.is_(True),
        User.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    org_users = result.scalars().all()

    matched = []
    tokens_lower = {t.lower() for t in tokens}
    for user in org_users:
        name_parts = user.full_name.lower().split()
        # Match full name (joined with .), first name, or last name
        name_joined = ".".join(name_parts)
        if (
            name_joined in tokens_lower
            or any(part in tokens_lower for part in name_parts)
        ):
            matched.append(user)
    return matched


# ── Comment Service ──────────────────────────────────────────────────────────


async def create_comment(
    db: AsyncSession,
    current_user: CurrentUser,
    entity_type: str,
    entity_id: uuid.UUID,
    content: str,
    parent_id: uuid.UUID | None = None,
) -> Comment:
    """Create a comment, parse mentions, and return the new comment."""
    # Validate parent exists and belongs to same entity
    if parent_id:
        parent = await db.get(Comment, parent_id)
        if not parent or parent.org_id != current_user.org_id:
            raise ValueError("Parent comment not found")
        if parent.entity_type != entity_type or parent.entity_id != entity_id:
            raise ValueError("Parent comment belongs to a different entity")
        if parent.parent_id is not None:
            raise ValueError("Replies can only be one level deep")

    # Parse mentions
    tokens = parse_mentions(content)
    mentioned_users = await resolve_mention_users(db, current_user.org_id, tokens)
    mentions_data = None
    if mentioned_users:
        mentions_data = {
            "users": [
                {"user_id": str(u.id), "full_name": u.full_name}
                for u in mentioned_users
            ]
        }

    comment = Comment(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        parent_id=parent_id,
        content=content,
        mentions=mentions_data,
    )
    db.add(comment)
    await db.flush()
    return comment


async def list_comments(
    db: AsyncSession,
    org_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
) -> tuple[list[Comment], dict[uuid.UUID, User]]:
    """Get all comments for an entity with user info. Returns (comments, user_map)."""
    stmt = select(Comment).where(
        Comment.entity_type == entity_type,
        Comment.entity_id == entity_id,
    )
    stmt = tenant_filter(stmt, org_id, Comment)
    stmt = stmt.order_by(Comment.created_at.asc())
    result = await db.execute(stmt)
    comments = list(result.scalars().all())

    # Load user info
    user_ids = {c.user_id for c in comments}
    user_map: dict[uuid.UUID, User] = {}
    if user_ids:
        user_stmt = select(User).where(User.id.in_(user_ids))
        user_result = await db.execute(user_stmt)
        for u in user_result.scalars().all():
            user_map[u.id] = u

    return comments, user_map


async def update_comment(
    db: AsyncSession,
    comment_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> Comment | None:
    """Update comment content. Only author, within 15 min of creation."""
    comment = await db.get(Comment, comment_id)
    if not comment:
        return None
    if comment.user_id != user_id:
        raise PermissionError("Only the author can edit this comment")

    elapsed = (datetime.now(timezone.utc) - comment.created_at.replace(tzinfo=timezone.utc)).total_seconds()
    if elapsed > EDIT_WINDOW_MINUTES * 60:
        raise ValueError(f"Comments can only be edited within {EDIT_WINDOW_MINUTES} minutes")

    comment.content = content
    # Re-parse mentions
    tokens = parse_mentions(content)
    if tokens:
        mentioned_users = await resolve_mention_users(db, comment.org_id, tokens)
        if mentioned_users:
            comment.mentions = {
                "users": [
                    {"user_id": str(u.id), "full_name": u.full_name}
                    for u in mentioned_users
                ]
            }
    await db.flush()
    return comment


async def delete_comment(
    db: AsyncSession,
    comment_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
) -> bool:
    """Delete a comment by replacing content. Author or admin only."""
    comment = await db.get(Comment, comment_id)
    if not comment:
        return False
    if comment.user_id != user_id and role != UserRole.ADMIN:
        raise PermissionError("Only the author or an admin can delete this comment")

    comment.content = "[deleted]"
    comment.mentions = None
    await db.flush()
    return True


async def resolve_comment(
    db: AsyncSession,
    comment_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Comment | None:
    """Toggle is_resolved on a comment."""
    comment = await db.get(Comment, comment_id)
    if not comment or comment.org_id != org_id:
        return None
    comment.is_resolved = not comment.is_resolved
    await db.flush()
    return comment


# ── Activity Service ─────────────────────────────────────────────────────────


async def record_activity(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    description: str,
    changes: dict | None = None,
) -> Activity:
    """Record an activity event."""
    activity = Activity(
        org_id=org_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        description=description,
        changes=changes,
    )
    db.add(activity)
    await db.flush()
    return activity


async def get_entity_activity(
    db: AsyncSession,
    org_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Activity], int, dict[uuid.UUID, User]]:
    """Get activity for a specific entity with user info."""
    base = select(Activity).where(
        Activity.entity_type == entity_type,
        Activity.entity_id == entity_id,
    )
    base = tenant_filter(base, org_id, Activity)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(Activity.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    activities = list(result.scalars().all())

    # Load users
    user_ids = {a.user_id for a in activities if a.user_id}
    user_map: dict[uuid.UUID, User] = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in user_result.scalars().all():
            user_map[u.id] = u

    return activities, total, user_map


async def get_activity_feed(
    db: AsyncSession,
    org_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Activity], int, dict[uuid.UUID, User]]:
    """Get all activities for an org (personal feed)."""
    base = select(Activity)
    base = tenant_filter(base, org_id, Activity)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(Activity.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    activities = list(result.scalars().all())

    user_ids = {a.user_id for a in activities if a.user_id}
    user_map: dict[uuid.UUID, User] = {}
    if user_ids:
        user_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in user_result.scalars().all():
            user_map[u.id] = u

    return activities, total, user_map
