"""Digest API router — manual trigger and preview for activity digest emails."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.digest import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/digest", tags=["digest"])


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
