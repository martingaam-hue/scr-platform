"""Admin module — platform-level administration endpoints.

All endpoints require UserRole.ADMIN and OrgType.ADMIN.
These are cross-org queries with no multi-tenant scoping.
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.core.database import get_db
from app.models.core import Organization
from app.models.enums import OrgType, SubscriptionStatus, SubscriptionTier, UserRole
from app.schemas.auth import CurrentUser
from sqlalchemy import select

from app.modules.admin import service
from app.modules.admin.schemas import (
    AICostReport,
    AuditLogPage,
    OrgDetail,
    OrgSummary,
    SystemHealthResponse,
    UpdateOrgStatusRequest,
    UpdateOrgTierRequest,
    UpdateUserStatusRequest,
    UserSummary,
    PlatformAnalytics,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_role = require_role([UserRole.ADMIN])


async def _require_platform_admin(
    current_user: CurrentUser = Depends(_admin_role),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Ensure user belongs to an ADMIN-type org."""
    stmt = select(Organization).where(
        Organization.id == current_user.org_id,
        Organization.is_deleted.is_(False),
    )
    org = (await db.execute(stmt)).scalar_one_or_none()
    if org is None or org.type != OrgType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required",
        )
    return current_user


# ── Organizations ──────────────────────────────────────────────────────────────


@router.get("/organizations", response_model=dict)
async def list_organizations(
    search: str | None = Query(None),
    type: OrgType | None = Query(None),
    status: SubscriptionStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await service.list_organizations(
        db, search=search, org_type=type, status=status, limit=limit, offset=offset
    )
    return {
        "items": [i.model_dump() for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/organizations/{org_id}", response_model=OrgDetail)
async def get_organization(
    org_id: uuid.UUID,
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> OrgDetail:
    org = await service.get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/organizations/{org_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_org_status(
    org_id: uuid.UUID,
    body: UpdateOrgStatusRequest,
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await service.update_org_status(db, org_id, body.status)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")
    await db.commit()
    logger.info("admin.org_status_updated", org_id=str(org_id), new_status=body.status.value)


@router.put("/organizations/{org_id}/tier", status_code=status.HTTP_204_NO_CONTENT)
async def update_org_tier(
    org_id: uuid.UUID,
    body: UpdateOrgTierRequest,
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await service.update_org_tier(db, org_id, body.tier)
    if not ok:
        raise HTTPException(status_code=404, detail="Organization not found")
    await db.commit()
    logger.info("admin.org_tier_updated", org_id=str(org_id), new_tier=body.tier.value)


# ── Users ──────────────────────────────────────────────────────────────────────


@router.get("/users", response_model=dict)
async def list_users(
    search: str | None = Query(None),
    org_id: uuid.UUID | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await service.list_users(
        db, search=search, org_id=org_id, is_active=is_active, limit=limit, offset=offset
    )
    return {
        "items": [i.model_dump() for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.put("/users/{user_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_status(
    user_id: uuid.UUID,
    body: UpdateUserStatusRequest,
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    ok = await service.update_user_status(db, user_id, body.is_active)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    logger.info("admin.user_status_updated", user_id=str(user_id), is_active=body.is_active)


# ── Analytics ─────────────────────────────────────────────────────────────────


@router.get("/analytics", response_model=PlatformAnalytics)
async def get_analytics(
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> PlatformAnalytics:
    return await service.get_platform_analytics(db)


# ── AI Costs ──────────────────────────────────────────────────────────────────


@router.get("/ai-costs", response_model=AICostReport)
async def get_ai_costs(
    days: int = Query(30, ge=1, le=365),
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AICostReport:
    return await service.get_ai_cost_report(db, days=days)


# ── AI Budget Overview ────────────────────────────────────────────────────────


@router.get("/ai-budget-overview")
async def get_ai_budget_overview(
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return per-org AI spend vs. budget for the current calendar month."""
    from datetime import datetime, timezone
    from sqlalchemy import func, text

    from app.models.ai import AITaskLog
    from app.models.enums import SubscriptionTier
    from app.services.ai_budget import _TIER_BUDGETS

    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Aggregate spend per org for current month
    stmt = (
        select(
            AITaskLog.org_id,
            func.coalesce(func.sum(AITaskLog.cost_usd), 0).label("spend_usd"),
            func.count(AITaskLog.id).label("call_count"),
        )
        .where(AITaskLog.created_at >= first_of_month, AITaskLog.cost_usd.isnot(None))
        .group_by(AITaskLog.org_id)
    )
    rows = (await db.execute(stmt)).all()

    # Fetch org budgets + tiers in one query
    from app.models.core import Organization as Org
    org_ids = [r.org_id for r in rows]
    if org_ids:
        org_stmt = select(Org.id, Org.name, Org.subscription_tier, Org.ai_monthly_budget).where(
            Org.id.in_(org_ids)
        )
        org_rows = {r.id: r for r in (await db.execute(org_stmt)).all()}
    else:
        org_rows = {}

    items = []
    for r in rows:
        org = org_rows.get(r.org_id)
        tier = org.subscription_tier if org else SubscriptionTier.FOUNDATION
        budget = float(org.ai_monthly_budget) if org and org.ai_monthly_budget is not None else _TIER_BUDGETS.get(tier, 50.0)
        items.append({
            "org_id": str(r.org_id),
            "org_name": org.name if org else "unknown",
            "tier": tier.value if org else "foundation",
            "spend_usd": float(r.spend_usd),
            "budget_usd": budget,
            "utilisation_pct": round(float(r.spend_usd) / budget * 100, 1) if budget else 0,
            "call_count": r.call_count,
        })

    # Sort by utilisation desc
    items.sort(key=lambda x: x["utilisation_pct"], reverse=True)

    return {
        "month": first_of_month.strftime("%Y-%m"),
        "total_spend_usd": round(sum(i["spend_usd"] for i in items), 4),
        "org_count": len(items),
        "items": items,
    }


# ── Audit Logs ────────────────────────────────────────────────────────────────


@router.get("/audit-logs", response_model=AuditLogPage)
async def list_audit_logs(
    search: str | None = Query(None),
    org_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AuditLogPage:
    return await service.list_audit_logs(
        db,
        search=search,
        org_id=org_id,
        action=action,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )


# ── System Health ─────────────────────────────────────────────────────────────


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health(
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> SystemHealthResponse:
    return await service.get_system_health(db)


# ── Digest ─────────────────────────────────────────────────────────────────────


@router.post("/cache/clear")
async def clear_cache(
    prefix: str = "signal_score",
    _: CurrentUser = Depends(_require_platform_admin),
) -> dict:
    """Clear all cached responses for the given prefix across all orgs.

    Uses the pattern ``{prefix}:*`` to wipe every org's entries for that
    prefix.  Silently succeeds even if Redis is unavailable.
    """
    from app.services.response_cache import get_redis

    cleared = 0
    try:
        r = await get_redis()
        pattern = f"{prefix}:*"
        keys = await r.keys(pattern)
        if keys:
            cleared = await r.delete(*keys)
    except Exception as exc:
        logger.warning("admin.cache_clear_error", prefix=prefix, error=str(exc))

    logger.info("admin.cache_cleared", prefix=prefix, keys_deleted=cleared)
    return {"cleared": True, "prefix": prefix, "keys_deleted": cleared}


@router.post("/digest/send-test")
async def send_digest_test(
    user_id: uuid.UUID = Query(..., description="User ID to send test digest to"),
    _: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a test digest email for a specific user (platform admin only)."""
    from datetime import datetime, timedelta
    from app.models.core import Organization, User
    from app.modules.digest import service as digest_service
    from sqlalchemy import select

    stmt = (
        select(User, Organization.name.label("org_name"))
        .join(Organization, User.org_id == Organization.id)
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    user = row[0]
    org_name = row[1]
    since = datetime.utcnow() - timedelta(days=7)

    activity = await digest_service.gather_digest_data(db, user.org_id, user.id, since)
    summary = await digest_service.generate_digest_summary(activity, org_name)

    from app.tasks.weekly_digest import _send_digest_email
    await _send_digest_email(user.email, user.full_name, org_name, activity, summary)

    return {"status": "sent", "email": user.email, "activity": activity}
