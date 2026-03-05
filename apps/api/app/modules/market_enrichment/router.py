"""Market Data Enrichment — API router."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.models.core import User
from app.modules.market_enrichment import service
from app.modules.market_enrichment.schemas import (
    EnrichmentRunResponse,
    FetchLogRead,
    ManualEntryCreate,
    MarketDataProcessedRead,
    MarketDataSourceCreate,
    MarketDataSourceRead,
    MarketDataSourceUpdate,
    MarketEnrichmentDashboard,
    ReviewDecision,
    ReviewQueueItemRead,
)

router = APIRouter(prefix="/market-enrichment", tags=["Market Enrichment"])


# ── Dashboard ─────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=MarketEnrichmentDashboard)
async def get_dashboard(
    current_user: User = Depends(require_permission("read", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> MarketEnrichmentDashboard:
    return await service.get_dashboard_stats(db, current_user.org_id)


# ── Sources ───────────────────────────────────────────────────────────────────


@router.get("/sources", response_model=list[MarketDataSourceRead])
async def list_sources(
    tier: int | None = Query(None, ge=1, le=4),
    is_active: bool | None = Query(None),
    current_user: User = Depends(require_permission("read", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> list[MarketDataSourceRead]:
    sources = await service.list_sources(db, current_user.org_id, tier=tier, is_active=is_active)
    return [MarketDataSourceRead.model_validate(s) for s in sources]


@router.post("/sources", response_model=MarketDataSourceRead, status_code=201)
async def create_source(
    body: MarketDataSourceCreate,
    current_user: User = Depends(require_permission("write", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> MarketDataSourceRead:
    source = await service.create_source(db, current_user.org_id, current_user.id, body)
    return MarketDataSourceRead.model_validate(source)


@router.patch("/sources/{source_id}", response_model=MarketDataSourceRead)
async def update_source(
    source_id: uuid.UUID,
    body: MarketDataSourceUpdate,
    current_user: User = Depends(require_permission("write", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> MarketDataSourceRead:
    source = await service.update_source(db, current_user.org_id, source_id, body)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return MarketDataSourceRead.model_validate(source)


@router.post("/sources/{source_id}/fetch", response_model=EnrichmentRunResponse)
async def trigger_fetch(
    source_id: uuid.UUID,
    current_user: User = Depends(require_permission("write", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> EnrichmentRunResponse:
    source = await service.get_source(db, current_user.org_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.is_active:
        raise HTTPException(status_code=400, detail="Source is inactive")

    fetch_log = await service.create_fetch_log(db, current_user.org_id, source_id)

    # Dispatch Celery task based on tier
    from app.core.celery_app import celery_app

    task_name = (
        "market_enrichment.fetch_tier1_source"
        if source.tier == 1
        else "market_enrichment.fetch_tier2_rss"
        if source.tier == 2
        else "market_enrichment.fetch_tier1_source"
    )
    celery_app.send_task(
        task_name,
        kwargs={
            "source_id": str(source_id),
            "org_id": str(current_user.org_id),
            "fetch_log_id": str(fetch_log.id),
        },
    )

    return EnrichmentRunResponse(
        fetch_log_id=fetch_log.id,
        status="pending",
        records_fetched=0,
    )


@router.get("/sources/{source_id}/logs", response_model=list[FetchLogRead])
async def get_fetch_logs(
    source_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("read", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> list[FetchLogRead]:
    logs = await service.get_fetch_logs(db, current_user.org_id, source_id=source_id, limit=limit)
    return [FetchLogRead.model_validate(lg) for lg in logs]


# ── Data ──────────────────────────────────────────────────────────────────────


@router.get("/data", response_model=list[MarketDataProcessedRead])
async def list_data(
    data_type: str | None = Query(None),
    category: str | None = Query(None),
    region: str | None = Query(None),
    technology: str | None = Query(None),
    effective_date_from: date | None = Query(None),
    effective_date_to: date | None = Query(None),
    review_status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_permission("read", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> list[MarketDataProcessedRead]:
    rows = await service.list_processed(
        db,
        current_user.org_id,
        data_type=data_type,
        category=category,
        region=region,
        technology=technology,
        effective_date_from=effective_date_from,
        effective_date_to=effective_date_to,
        review_status=review_status,
        skip=skip,
        limit=limit,
    )
    return [MarketDataProcessedRead.model_validate(r) for r in rows]


@router.post("/data/manual", response_model=MarketDataProcessedRead, status_code=201)
async def create_manual_entry(
    body: ManualEntryCreate,
    current_user: User = Depends(require_permission("write", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> MarketDataProcessedRead:
    entry = await service.create_manual_entry(db, current_user.org_id, current_user.id, body)
    return MarketDataProcessedRead.model_validate(entry)


@router.get("/data/{processed_id}", response_model=MarketDataProcessedRead)
async def get_data_record(
    processed_id: uuid.UUID,
    current_user: User = Depends(require_permission("read", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> MarketDataProcessedRead:
    record = await service.get_processed(db, current_user.org_id, processed_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return MarketDataProcessedRead.model_validate(record)


@router.post("/data/{processed_id}/review", response_model=MarketDataProcessedRead)
async def review_entry(
    processed_id: uuid.UUID,
    body: ReviewDecision,
    current_user: User = Depends(require_permission("write", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> MarketDataProcessedRead:
    entry = await service.review_entry(db, current_user.org_id, current_user.id, processed_id, body)
    if entry is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return MarketDataProcessedRead.model_validate(entry)


# ── Review Queue ──────────────────────────────────────────────────────────────


@router.get("/review-queue", response_model=list[ReviewQueueItemRead])
async def get_review_queue(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("read", "market_enrichment")),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewQueueItemRead]:
    items = await service.get_review_queue(db, current_user.org_id, limit=limit)
    return [ReviewQueueItemRead.model_validate(i) for i in items]
