"""Admin module — platform-level service functions (cross-org queries)."""

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIConversation, AITaskLog
from app.models.core import AuditLog, Organization, User
from app.models.enums import OrgType, SubscriptionStatus, SubscriptionTier
from app.modules.admin.schemas import (
    AICostEntry,
    AICostReport,
    AuditLogEntry,
    AuditLogPage,
    OrgBreakdown,
    OrgDetail,
    OrgSummary,
    PlatformAnalytics,
    ServiceHealth,
    SystemHealthResponse,
    UserBreakdown,
    UserSummary,
)

logger = structlog.get_logger()

# ── Organizations ──────────────────────────────────────────────────────────────


async def list_organizations(
    db: AsyncSession,
    search: str | None = None,
    org_type: OrgType | None = None,
    status: SubscriptionStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[OrgSummary], int]:
    """List all organizations with user counts (no org_id scoping — platform admin)."""
    # Count users per org via subquery
    user_count_sq = (
        select(User.org_id, func.count(User.id).label("user_count"))
        .where(User.is_deleted.is_(False))
        .group_by(User.org_id)
        .subquery()
    )

    base = select(Organization, func.coalesce(user_count_sq.c.user_count, 0).label("user_count")).outerjoin(
        user_count_sq, Organization.id == user_count_sq.c.org_id
    ).where(Organization.is_deleted.is_(False))

    if search:
        base = base.where(
            Organization.name.ilike(f"%{search}%") | Organization.slug.ilike(f"%{search}%")
        )
    if org_type:
        base = base.where(Organization.type == org_type)
    if status:
        base = base.where(Organization.subscription_status == status)

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginated rows
    rows = (await db.execute(base.order_by(Organization.created_at.desc()).offset(offset).limit(limit))).all()

    items = [
        OrgSummary(
            id=org.id,
            name=org.name,
            slug=org.slug,
            type=org.type,
            subscription_tier=org.subscription_tier,
            subscription_status=org.subscription_status,
            user_count=int(count),
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
        for org, count in rows
    ]
    return items, total


async def get_organization(db: AsyncSession, org_id: uuid.UUID) -> OrgDetail | None:
    user_count_sq = (
        select(User.org_id, func.count(User.id).label("user_count"))
        .where(User.is_deleted.is_(False))
        .group_by(User.org_id)
        .subquery()
    )
    stmt = (
        select(Organization, func.coalesce(user_count_sq.c.user_count, 0).label("user_count"))
        .outerjoin(user_count_sq, Organization.id == user_count_sq.c.org_id)
        .where(Organization.id == org_id, Organization.is_deleted.is_(False))
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return None
    org, count = row
    return OrgDetail(
        id=org.id,
        name=org.name,
        slug=org.slug,
        type=org.type,
        subscription_tier=org.subscription_tier,
        subscription_status=org.subscription_status,
        user_count=int(count),
        logo_url=org.logo_url,
        settings=org.settings or {},
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


async def update_org_status(
    db: AsyncSession, org_id: uuid.UUID, status: SubscriptionStatus
) -> bool:
    stmt = (
        update(Organization)
        .where(Organization.id == org_id, Organization.is_deleted.is_(False))
        .values(subscription_status=status)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0


async def update_org_tier(
    db: AsyncSession, org_id: uuid.UUID, tier: SubscriptionTier
) -> bool:
    stmt = (
        update(Organization)
        .where(Organization.id == org_id, Organization.is_deleted.is_(False))
        .values(subscription_tier=tier)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0


# ── Users ──────────────────────────────────────────────────────────────────────


async def list_users(
    db: AsyncSession,
    search: str | None = None,
    org_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserSummary], int]:
    base = (
        select(User, Organization.name.label("org_name"), Organization.type.label("org_type"))
        .join(Organization, User.org_id == Organization.id)
        .where(User.is_deleted.is_(False))
    )
    if search:
        base = base.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    if org_id:
        base = base.where(User.org_id == org_id)
    if is_active is not None:
        base = base.where(User.is_active.is_(is_active))

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    rows = (await db.execute(base.order_by(User.created_at.desc()).offset(offset).limit(limit))).all()

    items = [
        UserSummary(
            id=user.id,
            org_id=user.org_id,
            org_name=org_name,
            org_type=org_type,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            mfa_enabled=user.mfa_enabled,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
        for user, org_name, org_type in rows
    ]
    return items, total


async def update_user_status(
    db: AsyncSession, user_id: uuid.UUID, is_active: bool
) -> bool:
    stmt = (
        update(User)
        .where(User.id == user_id, User.is_deleted.is_(False))
        .values(is_active=is_active)
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0


# ── Platform Analytics ─────────────────────────────────────────────────────────


async def get_platform_analytics(db: AsyncSession) -> PlatformAnalytics:
    # Organization breakdown
    org_rows = (
        await db.execute(
            select(
                Organization.type,
                Organization.subscription_status,
                func.count(Organization.id).label("cnt"),
            )
            .where(Organization.is_deleted.is_(False))
            .group_by(Organization.type, Organization.subscription_status)
        )
    ).all()

    org_totals: dict[str, Any] = {
        "total": 0, "ally": 0, "investor": 0, "admin": 0,
        "trial": 0, "active": 0, "suspended": 0, "cancelled": 0,
    }
    for otype, ostatus, cnt in org_rows:
        org_totals["total"] += cnt
        org_totals[otype.value] = org_totals.get(otype.value, 0) + cnt
        org_totals[ostatus.value] = org_totals.get(ostatus.value, 0) + cnt

    # User breakdown
    user_rows = (
        await db.execute(
            select(User.role, User.is_active, func.count(User.id).label("cnt"))
            .where(User.is_deleted.is_(False))
            .group_by(User.role, User.is_active)
        )
    ).all()

    user_totals: dict[str, Any] = {
        "total": 0, "active": 0, "inactive": 0,
        "admins": 0, "managers": 0, "analysts": 0, "viewers": 0,
    }
    for role, is_active, cnt in user_rows:
        user_totals["total"] += cnt
        if is_active:
            user_totals["active"] += cnt
        else:
            user_totals["inactive"] += cnt
        role_key = f"{role.value}s"
        user_totals[role_key] = user_totals.get(role_key, 0) + cnt

    # Project / portfolio / conversation / document counts
    from app.models.projects import Project  # type: ignore[attr-defined]
    from app.models.portfolio import Portfolio  # type: ignore[attr-defined]

    total_projects = (await db.execute(select(func.count()).select_from(Project).where(Project.is_deleted.is_(False)))).scalar_one()  # type: ignore[attr-defined]
    total_portfolios = (await db.execute(select(func.count()).select_from(Portfolio).where(Portfolio.is_deleted.is_(False)))).scalar_one()  # type: ignore[attr-defined]
    total_conversations = (await db.execute(select(func.count()).select_from(AIConversation).where(AIConversation.is_deleted.is_(False)))).scalar_one()

    # Documents (try, may not have module imported yet)
    try:
        from app.models.dataroom import Document  # type: ignore[attr-defined]
        total_documents = (await db.execute(select(func.count()).select_from(Document).where(Document.is_deleted.is_(False)))).scalar_one()  # type: ignore[attr-defined]
    except Exception:
        total_documents = 0

    return PlatformAnalytics(
        orgs=OrgBreakdown(**org_totals),
        users=UserBreakdown(**user_totals),
        total_projects=total_projects,
        total_portfolios=total_portfolios,
        total_ai_conversations=total_conversations,
        total_documents=total_documents,
        generated_at=datetime.now(timezone.utc),
    )


# ── AI Cost Report ─────────────────────────────────────────────────────────────


async def get_ai_cost_report(db: AsyncSession, days: int = 30) -> AICostReport:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        await db.execute(
            select(
                AITaskLog.agent_type,
                AITaskLog.model_used,
                AITaskLog.org_id,
                AITaskLog.status,
                func.count(AITaskLog.id).label("task_count"),
                func.coalesce(func.sum(AITaskLog.tokens_used), 0).label("total_tokens"),
                func.avg(AITaskLog.processing_time_ms).label("avg_ms"),
            )
            .where(AITaskLog.created_at >= since)
            .group_by(AITaskLog.agent_type, AITaskLog.model_used, AITaskLog.org_id, AITaskLog.status)
        )
    ).all()

    total_tasks = 0
    total_tokens = 0
    total_failed = 0
    by_agent: dict[str, dict] = {}
    by_model: dict[str, dict] = {}
    by_org: dict[str, dict] = {}

    for agent_type, model_used, org_id, status, count, tokens, avg_ms in rows:
        total_tasks += count
        total_tokens += tokens
        is_failed = status.value == "failed"
        if is_failed:
            total_failed += count

        # by agent
        key = agent_type.value
        if key not in by_agent:
            by_agent[key] = {"task_count": 0, "total_tokens": 0, "avg_ms_sum": 0.0, "avg_ms_count": 0, "failed_count": 0}
        by_agent[key]["task_count"] += count
        by_agent[key]["total_tokens"] += tokens
        if avg_ms:
            by_agent[key]["avg_ms_sum"] += float(avg_ms) * count
            by_agent[key]["avg_ms_count"] += count
        if is_failed:
            by_agent[key]["failed_count"] += count

        # by model
        mkey = model_used or "unknown"
        if mkey not in by_model:
            by_model[mkey] = {"task_count": 0, "total_tokens": 0, "avg_ms_sum": 0.0, "avg_ms_count": 0, "failed_count": 0}
        by_model[mkey]["task_count"] += count
        by_model[mkey]["total_tokens"] += tokens
        if avg_ms:
            by_model[mkey]["avg_ms_sum"] += float(avg_ms) * count
            by_model[mkey]["avg_ms_count"] += count
        if is_failed:
            by_model[mkey]["failed_count"] += count

        # by org
        okey = str(org_id)
        if okey not in by_org:
            by_org[okey] = {"task_count": 0, "total_tokens": 0, "avg_ms_sum": 0.0, "avg_ms_count": 0, "failed_count": 0}
        by_org[okey]["task_count"] += count
        by_org[okey]["total_tokens"] += tokens
        if avg_ms:
            by_org[okey]["avg_ms_sum"] += float(avg_ms) * count
            by_org[okey]["avg_ms_count"] += count
        if is_failed:
            by_org[okey]["failed_count"] += count

    def _to_entry(label: str, d: dict) -> AICostEntry:
        avg = d["avg_ms_sum"] / d["avg_ms_count"] if d["avg_ms_count"] else None
        return AICostEntry(
            label=label,
            task_count=d["task_count"],
            total_tokens=d["total_tokens"],
            avg_processing_ms=avg,
            failed_count=d["failed_count"],
        )

    return AICostReport(
        period_days=days,
        total_tasks=total_tasks,
        total_tokens=total_tokens,
        total_failed=total_failed,
        by_agent=sorted([_to_entry(k, v) for k, v in by_agent.items()], key=lambda x: -x.total_tokens),
        by_model=sorted([_to_entry(k, v) for k, v in by_model.items()], key=lambda x: -x.total_tokens),
        by_org=sorted([_to_entry(k, v) for k, v in by_org.items()], key=lambda x: -x.total_tokens)[:10],
    )


# ── Audit Logs ─────────────────────────────────────────────────────────────────


async def list_audit_logs(
    db: AsyncSession,
    search: str | None = None,
    org_id: uuid.UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditLogPage:
    base = (
        select(
            AuditLog,
            Organization.name.label("org_name"),
            User.email.label("user_email"),
        )
        .outerjoin(Organization, AuditLog.org_id == Organization.id)
        .outerjoin(User, AuditLog.user_id == User.id)
    )
    if search:
        base = base.where(
            AuditLog.action.ilike(f"%{search}%")
            | AuditLog.entity_type.ilike(f"%{search}%")
        )
    if org_id:
        base = base.where(AuditLog.org_id == org_id)
    if action:
        base = base.where(AuditLog.action == action)
    if entity_type:
        base = base.where(AuditLog.entity_type == entity_type)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    rows = (await db.execute(base.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit))).all()

    items = [
        AuditLogEntry(
            id=log.id,
            org_id=log.org_id,
            org_name=org_name,
            user_id=log.user_id,
            user_email=user_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            ip_address=log.ip_address,
            timestamp=log.timestamp,
        )
        for log, org_name, user_email in rows
    ]
    return AuditLogPage(items=items, total=total, limit=limit, offset=offset)


# ── System Health ──────────────────────────────────────────────────────────────


async def get_system_health(db: AsyncSession) -> SystemHealthResponse:
    services: list[ServiceHealth] = []

    # Database
    t0 = time.monotonic()
    try:
        await db.execute(select(func.now()))
        latency = (time.monotonic() - t0) * 1000
        services.append(ServiceHealth(name="database", status="ok", latency_ms=round(latency, 2), detail=None))
    except Exception as exc:
        services.append(ServiceHealth(name="database", status="down", latency_ms=None, detail=str(exc)))

    # Redis (try to import and ping)
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        t0 = time.monotonic()
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        await r.ping()
        await r.aclose()
        latency = (time.monotonic() - t0) * 1000
        services.append(ServiceHealth(name="redis", status="ok", latency_ms=round(latency, 2), detail=None))
    except Exception as exc:
        services.append(ServiceHealth(name="redis", status="degraded", latency_ms=None, detail=str(exc)[:100]))

    # AI Gateway (try HTTP ping)
    try:
        import httpx
        from app.core.config import settings
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.AI_GATEWAY_URL}/health")
        latency = (time.monotonic() - t0) * 1000
        status = "ok" if resp.status_code == 200 else "degraded"
        services.append(ServiceHealth(name="ai-gateway", status=status, latency_ms=round(latency, 2), detail=None))
    except Exception as exc:
        services.append(ServiceHealth(name="ai-gateway", status="degraded", latency_ms=None, detail=str(exc)[:100]))

    overall = "ok"
    if any(s.status == "down" for s in services):
        overall = "down"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"

    return SystemHealthResponse(
        overall=overall,
        services=services,
        checked_at=datetime.now(timezone.utc),
    )
