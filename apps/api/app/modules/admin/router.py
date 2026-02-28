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
