"""Launch Preparation API router (E04)."""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.modules.launch.schemas import (
    FeatureFlagResponse,
    FlagOverrideRequest,
    HealthStatus,
    UsageEventRequest,
    WaitlistEntryRequest,
    WaitlistEntryResponse,
)
from app.modules.launch.service import LaunchService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/launch", tags=["Launch"])


# ── Feature Flags ──────────────────────────────────────────────────────────────


@router.get("/flags", response_model=list[FeatureFlagResponse])
async def list_flags(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[FeatureFlagResponse]:
    """List all feature flags with the current org's overrides applied."""
    svc = LaunchService(db)
    return await svc.list_flags(current_user.org_id)


@router.put("/flags/{flag_name}/override", response_model=FeatureFlagResponse)
async def set_flag_override(
    flag_name: str,
    body: FlagOverrideRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> FeatureFlagResponse:
    """Set a per-org override for a feature flag (admin only)."""
    svc = LaunchService(db)
    await svc.set_org_override(flag_name, current_user.org_id, body.enabled)
    flags = await svc.list_flags(current_user.org_id)
    match = next((f for f in flags if f.name == flag_name), None)
    if not match:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    return match


# ── Usage Events ───────────────────────────────────────────────────────────────


@router.post("/usage", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def record_usage(
    body: UsageEventRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Record a usage event for the current user/org."""
    svc = LaunchService(db)
    await svc.record_usage(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        event_type=body.event_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        metadata=body.metadata,
    )


@router.get("/usage/summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregated usage stats for the current org over the last N days."""
    svc = LaunchService(db)
    return await svc.get_usage_summary(current_user.org_id, days=days)


# ── Waitlist ───────────────────────────────────────────────────────────────────


@router.post(
    "/waitlist",
    response_model=WaitlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_waitlist_entry(
    body: WaitlistEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_current_user),  # noqa: UP007
) -> WaitlistEntryResponse:
    """Add an email to the waitlist. Auth optional — public endpoint."""
    svc = LaunchService(db)
    entry = await svc.create_waitlist_entry(
        email=body.email,
        name=body.name,
        company=body.company,
        use_case=body.use_case,
    )
    return WaitlistEntryResponse.model_validate(entry)


@router.get("/waitlist", response_model=list[WaitlistEntryResponse])
async def list_waitlist(
    status_filter: str | None = Query(None, alias="status"),
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[WaitlistEntryResponse]:
    """List all waitlist entries (admin only)."""
    svc = LaunchService(db)
    entries = await svc.list_waitlist(status_filter=status_filter)
    return [WaitlistEntryResponse.model_validate(e) for e in entries]


@router.post("/waitlist/{entry_id}/approve", response_model=WaitlistEntryResponse)
async def approve_waitlist_entry(
    entry_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
) -> WaitlistEntryResponse:
    """Approve a waitlist entry (admin only)."""
    svc = LaunchService(db)
    entry = await svc.approve_waitlist_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return WaitlistEntryResponse.model_validate(entry)


# ── Health ─────────────────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthStatus)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthStatus:
    """Enhanced health check — tests DB and Redis connectivity. No auth required."""
    checks: dict[str, bool] = {}

    # Check database
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
        checks["database"] = True
    except Exception as exc:
        logger.warning("health_db_check_failed", error=str(exc))
        checks["database"] = False

    # Check Redis
    redis_ok = False
    try:
        from app.services.response_cache import get_redis

        r = await get_redis()
        await r.ping()
        redis_ok = True
        checks["redis"] = True
    except Exception as exc:
        logger.warning("health_redis_check_failed", error=str(exc))
        checks["redis"] = False

    all_ok = db_ok and redis_ok
    overall = "healthy" if all_ok else ("degraded" if db_ok or redis_ok else "unhealthy")

    return HealthStatus(
        status=overall,
        version="0.1.0",
        db_ok=db_ok,
        redis_ok=redis_ok,
        checks=checks,
    )
