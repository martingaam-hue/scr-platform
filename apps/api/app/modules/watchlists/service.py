"""Watchlist service — CRUD, alert creation, monitoring engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watchlists import Watchlist, WatchlistAlert

logger = structlog.get_logger()


async def create_watchlist(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID, body: Any) -> Watchlist:
    criteria = body.criteria or {}

    # If the user supplied a natural language query but no structured filters, parse it
    nl_query: str | None = getattr(body, "nl_query", None)
    if nl_query and not criteria:
        try:
            from app.modules.smart_screener.service import parse_query
            parsed = await parse_query(nl_query)
            criteria = parsed.model_dump(exclude_none=True)
        except Exception as exc:
            logger.warning("watchlist_nl_parse_failed", error=str(exc))

    wl = Watchlist(
        user_id=user_id,
        org_id=org_id,
        name=body.name,
        watch_type=body.watch_type,
        criteria=criteria,
        alert_channels=body.alert_channels,
        alert_frequency=body.alert_frequency,
    )
    db.add(wl)
    await db.commit()
    await db.refresh(wl)
    return wl


async def list_watchlists(db: AsyncSession, user_id: uuid.UUID) -> list[Watchlist]:
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.is_deleted == False)
        .order_by(Watchlist.created_at.desc())
    )
    return list(result.scalars().all())


async def get_watchlist(db: AsyncSession, wl_id: uuid.UUID, user_id: uuid.UUID) -> Watchlist | None:
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.id == wl_id, Watchlist.user_id == user_id, Watchlist.is_deleted == False
        )
    )
    return result.scalar_one_or_none()


async def update_watchlist(db: AsyncSession, wl: Watchlist, body: Any) -> Watchlist:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(wl, field, value)
    await db.commit()
    await db.refresh(wl)
    return wl


async def delete_watchlist(db: AsyncSession, wl: Watchlist) -> None:
    wl.is_deleted = True
    await db.commit()


async def toggle_watchlist(db: AsyncSession, wl: Watchlist) -> Watchlist:
    wl.is_active = not wl.is_active
    await db.commit()
    await db.refresh(wl)
    return wl


async def create_alert(
    db: AsyncSession,
    watchlist: Watchlist,
    alert_type: str,
    title: str,
    description: str | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    data: dict | None = None,
) -> WatchlistAlert:
    alert = WatchlistAlert(
        watchlist_id=watchlist.id,
        user_id=watchlist.user_id,
        alert_type=alert_type,
        title=title,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data or {},
    )
    db.add(alert)
    watchlist.total_alerts_sent = (watchlist.total_alerts_sent or 0) + 1

    # In-app notification
    if "in_app" in (watchlist.alert_channels or []):
        try:
            from app.models.core import Notification
            notif = Notification(
                user_id=watchlist.user_id,
                notification_type="info",
                title=title,
                message=description or "",
            )
            db.add(notif)
        except Exception:
            pass

    await db.commit()
    await db.refresh(alert)
    return alert


async def list_alerts(
    db: AsyncSession, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
) -> list[WatchlistAlert]:
    stmt = select(WatchlistAlert).where(WatchlistAlert.user_id == user_id)
    if unread_only:
        stmt = stmt.where(WatchlistAlert.is_read == False)
    stmt = stmt.order_by(WatchlistAlert.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_alert_read(db: AsyncSession, alert_id: uuid.UUID, user_id: uuid.UUID) -> None:
    await db.execute(
        update(WatchlistAlert)
        .where(WatchlistAlert.id == alert_id, WatchlistAlert.user_id == user_id)
        .values(is_read=True)
    )
    await db.commit()


async def delete_alert(db: AsyncSession, alert_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(WatchlistAlert).where(WatchlistAlert.id == alert_id, WatchlistAlert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if alert:
        await db.delete(alert)
        await db.commit()


async def get_active_watchlists(db: AsyncSession) -> list[Watchlist]:
    result = await db.execute(
        select(Watchlist).where(Watchlist.is_active == True, Watchlist.is_deleted == False)
    )
    return list(result.scalars().all())


async def check_watchlist(db: AsyncSession, wl: Watchlist) -> int:
    """Check a single watchlist and create alerts. Returns number of alerts created."""
    since_str = wl.last_checked_at  # stored as ISO string
    since = datetime.fromisoformat(since_str) if isinstance(since_str, str) else (datetime.utcnow() - timedelta(hours=1))
    alert_count = 0

    try:
        if wl.watch_type == "new_projects":
            from app.models.projects import Project
            criteria = wl.criteria or {}
            stmt = select(Project).where(
                Project.org_id != wl.org_id,  # other orgs' projects
                Project.is_deleted == False,
                Project.created_at >= since,
            )
            if criteria.get("project_type"):
                stmt = stmt.where(Project.project_type == criteria["project_type"])
            if criteria.get("min_capacity_mw"):
                stmt = stmt.where(Project.capacity_mw >= criteria["min_capacity_mw"])
            result = await db.execute(stmt.limit(10))
            projects = result.scalars().all()
            for p in projects:
                await create_alert(
                    db, wl, "new_match",
                    title=f"New project matches '{wl.name}'",
                    description=f"{p.name} — {p.project_type}",
                    entity_type="project", entity_id=p.id,
                )
                alert_count += 1

        elif wl.watch_type == "score_changes":
            from app.models.projects import SignalScore
            result = await db.execute(
                select(SignalScore).where(SignalScore.created_at >= since).limit(20)
            )
            for score in result.scalars().all():
                await create_alert(
                    db, wl, "score_improved",
                    title=f"Signal Score update",
                    description=f"Score: {score.overall_score}",
                    entity_type="project", entity_id=score.project_id,
                )
                alert_count += 1

    except Exception as exc:
        logger.error("watchlist.check_failed", watchlist_id=str(wl.id), error=str(exc))

    # Update last_checked_at
    wl.last_checked_at = datetime.utcnow().isoformat()
    await db.commit()
    return alert_count
