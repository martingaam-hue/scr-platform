"""Collaboration API router: comments, activity feed."""

import math
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.collaboration import service
from app.modules.collaboration.schemas import (
    ActivityListResponse,
    ActivityResponse,
    CommentAuthor,
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    UpdateCommentRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _comment_to_response(comment, user_map: dict) -> CommentResponse:
    user = user_map.get(comment.user_id)
    author = CommentAuthor(
        user_id=comment.user_id,
        full_name=user.full_name if user else "Unknown",
        avatar_url=getattr(user, "avatar_url", None) if user else None,
    )
    return CommentResponse(
        id=comment.id,
        org_id=comment.org_id,
        user_id=comment.user_id,
        author=author,
        entity_type=comment.entity_type,
        entity_id=comment.entity_id,
        parent_id=comment.parent_id,
        content=comment.content,
        mentions=comment.mentions,
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
    )


def _build_threaded(comments, user_map: dict) -> list[CommentResponse]:
    """Build threaded comment list: top-level with nested replies."""
    top_level: list[CommentResponse] = []
    replies_map: dict[uuid.UUID, list[CommentResponse]] = {}

    for c in comments:
        resp = _comment_to_response(c, user_map)
        if c.parent_id is None:
            top_level.append(resp)
        else:
            replies_map.setdefault(c.parent_id, []).append(resp)

    for parent in top_level:
        parent.replies = replies_map.get(parent.id, [])

    return top_level


def _activity_to_response(activity, user_map: dict) -> ActivityResponse:
    user = user_map.get(activity.user_id) if activity.user_id else None
    return ActivityResponse(
        id=activity.id,
        org_id=activity.org_id,
        user_id=activity.user_id,
        user_name=user.full_name if user else None,
        user_avatar=getattr(user, "avatar_url", None) if user else None,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        action=activity.action,
        description=activity.description,
        changes=activity.changes,
        created_at=activity.created_at,
    )


# ── Comments ─────────────────────────────────────────────────────────────────


@router.post(
    "/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("create", "comment"))],
)
async def create_comment(
    body: CreateCommentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a comment on any entity."""
    try:
        comment = await service.create_comment(
            db,
            current_user,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            content=body.content,
            parent_id=body.parent_comment_id,
        )
        # Record activity
        await service.record_activity(
            db,
            org_id=current_user.org_id,
            user_id=current_user.user_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            action="comment_added",
            description=f"Added a comment",
        )
        await db.commit()

        # Build response with user info
        from app.models.core import User
        from sqlalchemy import select

        user_result = await db.execute(select(User).where(User.id == current_user.user_id))
        user = user_result.scalar_one_or_none()
        user_map = {current_user.user_id: user} if user else {}

        return _comment_to_response(comment, user_map)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/comments",
    response_model=CommentListResponse,
    dependencies=[Depends(require_permission("view", "comment"))],
)
async def list_comments(
    entity_type: str = Query(..., min_length=1),
    entity_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all comments for an entity, threaded."""
    comments, user_map = await service.list_comments(
        db, current_user.org_id, entity_type, entity_id
    )
    threaded = _build_threaded(comments, user_map)
    return CommentListResponse(items=threaded, total=len(comments))


@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    dependencies=[Depends(require_permission("edit", "comment"))],
)
async def update_comment(
    comment_id: uuid.UUID,
    body: UpdateCommentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a comment. Author only, within 15 minutes."""
    try:
        comment = await service.update_comment(
            db, comment_id, current_user.user_id, body.content
        )
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        await db.commit()

        # Build response
        comments, user_map = await service.list_comments(
            db, current_user.org_id, comment.entity_type, comment.entity_id
        )
        user_map_for_resp = {comment.user_id: user_map.get(comment.user_id)}
        return _comment_to_response(comment, user_map_for_resp)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment. Author or admin only."""
    try:
        deleted = await service.delete_comment(
            db, comment_id, current_user.user_id, current_user.role
        )
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        await db.commit()
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/comments/{comment_id}/resolve",
    response_model=CommentResponse,
    dependencies=[Depends(require_permission("edit", "comment"))],
)
async def resolve_comment(
    comment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle resolved status on a comment."""
    comment = await service.resolve_comment(db, comment_id, current_user.org_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    await db.commit()

    # Build response
    from app.models.core import User
    from sqlalchemy import select

    user_result = await db.execute(select(User).where(User.id == comment.user_id))
    user = user_result.scalar_one_or_none()
    user_map = {comment.user_id: user} if user else {}
    return _comment_to_response(comment, user_map)


# ── Activity ─────────────────────────────────────────────────────────────────


@router.get(
    "/activity",
    response_model=ActivityListResponse,
)
async def get_entity_activity(
    entity_type: str = Query(..., min_length=1),
    entity_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity for a specific entity."""
    activities, total, user_map = await service.get_entity_activity(
        db, current_user.org_id, entity_type, entity_id, page, page_size
    )
    return ActivityListResponse(
        items=[_activity_to_response(a, user_map) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get(
    "/activity/feed",
    response_model=ActivityListResponse,
)
async def get_activity_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all activities for the current org (personal feed)."""
    activities, total, user_map = await service.get_activity_feed(
        db, current_user.org_id, page, page_size
    )
    return ActivityListResponse(
        items=[_activity_to_response(a, user_map) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )
