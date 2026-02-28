"""Watchlists API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.watchlists import service
from app.modules.watchlists.schemas import (
    AlertListResponse,
    AlertResponse,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistUpdate,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.post("/parse-criteria")
async def parse_watchlist_criteria(
    body: dict,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
):
    """Use the Smart Screener NL parser to generate watchlist criteria from plain text.

    Body: {"query": "solar projects in East Africa with signal score above 70"}
    Returns: {"criteria": {...parsed filters...}, "watch_type": "new_projects"}
    """
    query: str = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    from app.modules.smart_screener import service as screener_service

    parsed = await screener_service.parse_query(query)
    # Convert ParsedFilters → watchlist criteria format
    criteria: dict = {}
    if parsed.project_types:
        criteria["project_types"] = parsed.project_types
    if parsed.geographies:
        criteria["geographies"] = parsed.geographies
    if parsed.stages:
        criteria["stages"] = parsed.stages
    if parsed.min_signal_score is not None:
        criteria["min_signal_score"] = parsed.min_signal_score
    if parsed.max_signal_score is not None:
        criteria["max_signal_score"] = parsed.max_signal_score
    if parsed.min_ticket_size is not None:
        criteria["min_ticket_size"] = parsed.min_ticket_size
    if parsed.max_ticket_size is not None:
        criteria["max_ticket_size"] = parsed.max_ticket_size
    if parsed.sector_keywords:
        criteria["sector_keywords"] = parsed.sector_keywords

    return {
        "criteria": criteria,
        "watch_type": "new_projects",
        "parsed_query": query,
    }


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    body: WatchlistCreate,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    # Auto-populate criteria from natural language query when criteria is empty
    if body.nl_query and not body.criteria:
        from app.modules.smart_screener import service as screener_service
        try:
            parsed = await screener_service.parse_query(body.nl_query)
            criteria: dict = {}
            if parsed.project_types:
                criteria["project_types"] = parsed.project_types
            if parsed.geographies:
                criteria["geographies"] = parsed.geographies
            if parsed.stages:
                criteria["stages"] = parsed.stages
            if parsed.min_signal_score is not None:
                criteria["min_signal_score"] = parsed.min_signal_score
            if parsed.max_signal_score is not None:
                criteria["max_signal_score"] = parsed.max_signal_score
            if parsed.min_ticket_size is not None:
                criteria["min_ticket_size"] = parsed.min_ticket_size
            if parsed.max_ticket_size is not None:
                criteria["max_ticket_size"] = parsed.max_ticket_size
            if parsed.sector_keywords:
                criteria["sector_keywords"] = parsed.sector_keywords
            body = body.model_copy(update={"criteria": criteria})
        except Exception:
            pass  # proceed with empty criteria if NL parsing fails

    wl = await service.create_watchlist(db, current_user.user_id, current_user.org_id, body)
    return WatchlistResponse.model_validate(wl)


@router.get("/", response_model=list[WatchlistResponse])
async def list_watchlists(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    watchlists = await service.list_watchlists(db, current_user.user_id)
    return [WatchlistResponse.model_validate(w) for w in watchlists]


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: uuid.UUID,
    body: WatchlistUpdate,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    wl = await service.get_watchlist(db, watchlist_id, current_user.user_id)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    wl = await service.update_watchlist(db, wl, body)
    return WatchlistResponse.model_validate(wl)


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    wl = await service.get_watchlist(db, watchlist_id, current_user.user_id)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    await service.delete_watchlist(db, wl)


@router.put("/{watchlist_id}/toggle", response_model=WatchlistResponse)
async def toggle_watchlist(
    watchlist_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    wl = await service.get_watchlist(db, watchlist_id, current_user.user_id)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    wl = await service.toggle_watchlist(db, wl)
    return WatchlistResponse.model_validate(wl)


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    unread_only: bool = Query(False),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    alerts = await service.list_alerts(db, current_user.user_id, unread_only=unread_only)
    unread = sum(1 for a in alerts if not a.is_read)
    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=len(alerts),
        unread_count=unread,
    )


@router.put("/alerts/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_alert_read(
    alert_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    await service.mark_alert_read(db, alert_id, current_user.user_id)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_alert(db, alert_id, current_user.user_id)
