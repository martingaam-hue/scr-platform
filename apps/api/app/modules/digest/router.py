"""Digest API router — manual trigger and preview for activity digest emails."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.digest import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/digest", tags=["digest"])


class DigestPreferences(BaseModel):
    is_subscribed: bool = True
    frequency: Literal["daily", "weekly", "monthly"] = "weekly"


# ── History response schemas ────────────────────────────────────────────────


class DigestLogResponse(BaseModel):
    id: uuid.UUID
    digest_type: str
    period_start: date
    period_end: date
    subject: str
    narrative: str
    sent_at: datetime

    model_config = {"from_attributes": True}


class DigestHistoryResponse(BaseModel):
    items: list[DigestLogResponse]
    total: int
    page: int
    page_size: int


@router.get("/preview")
async def preview_digest(
    days: int = Query(7, ge=1, le=90, description="Look-back window in days"),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Preview the digest data that would be included in the next email.

    Returns a structured summary without sending any email.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    data = await service.gather_digest_data(db, current_user.org_id, current_user.user_id, since)
    return {"days": days, "summary": data}


@router.post("/trigger")
async def trigger_digest(
    days: int = Query(7, ge=1, le=90, description="Look-back window in days"),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an AI-generated digest summary.

    Aggregates platform activity for the specified window, calls AI to generate
    a narrative, and returns the result. Does not send email — call the email
    dispatch service separately if needed.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Gather org name for narrative context
    try:
        from app.models.core import Organization
        org = await db.get(Organization, current_user.org_id)
        org_name = org.name if org else "Your organisation"
    except Exception:
        org_name = "Your organisation"

    data = await service.gather_digest_data(db, current_user.org_id, current_user.user_id, since)
    narrative = await service.generate_digest_summary(data, org_name)

    logger.info(
        "digest_triggered",
        org_id=str(current_user.org_id),
        user_id=str(current_user.user_id),
        days=days,
    )
    return {
        "status": "generated",
        "days": days,
        "narrative": narrative,
        "data": data,
    }


# ── Digest history ─────────────────────────────────────────────────────────────


@router.get("/history", response_model=DigestHistoryResponse)
async def get_digest_history(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List previously sent digests for the current user (newest first)."""
    items, total = await service.list_digest_history(
        db,
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        page=page,
        page_size=page_size,
    )
    return DigestHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Digest preferences ─────────────────────────────────────────────────────────


@router.get("/preferences", response_model=DigestPreferences)
async def get_digest_preferences(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's digest subscription preferences."""
    prefs = await service.get_preferences(db, current_user.user_id)
    return DigestPreferences(**prefs)


@router.put("/preferences", response_model=DigestPreferences)
async def update_digest_preferences(
    body: DigestPreferences,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update digest subscription preferences (opt-in/out, frequency)."""
    try:
        updated = await service.update_preferences(
            db, current_user.user_id, body.is_subscribed, body.frequency
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return DigestPreferences(**updated)
