"""Market Data Enrichment — service layer."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_enrichment import (
    DataReviewQueue,
    MarketDataProcessed,
    MarketDataSource,
    MarketEnrichmentFetchLog,
)
from app.modules.market_enrichment.schemas import (
    ManualEntryCreate,
    MarketDataSourceCreate,
    MarketDataSourceUpdate,
    MarketEnrichmentDashboard,
    ReviewDecision,
)


async def list_sources(
    db: AsyncSession,
    org_id: uuid.UUID,
    tier: int | None = None,
    is_active: bool | None = None,
) -> list[MarketDataSource]:
    stmt = select(MarketDataSource).where(MarketDataSource.org_id == org_id)
    if tier is not None:
        stmt = stmt.where(MarketDataSource.tier == tier)
    if is_active is not None:
        stmt = stmt.where(MarketDataSource.is_active == is_active)
    stmt = stmt.order_by(MarketDataSource.tier, MarketDataSource.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_source(
    db: AsyncSession, org_id: uuid.UUID, source_id: uuid.UUID
) -> MarketDataSource | None:
    result = await db.execute(
        select(MarketDataSource).where(
            MarketDataSource.id == source_id,
            MarketDataSource.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def create_source(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MarketDataSourceCreate,
) -> MarketDataSource:
    source = MarketDataSource(
        org_id=org_id,
        created_by=user_id,
        **data.model_dump(),
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def update_source(
    db: AsyncSession,
    org_id: uuid.UUID,
    source_id: uuid.UUID,
    data: MarketDataSourceUpdate,
) -> MarketDataSource | None:
    source = await get_source(db, org_id, source_id)
    if source is None:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


async def get_dashboard_stats(db: AsyncSession, org_id: uuid.UUID) -> MarketEnrichmentDashboard:
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    sources_count_result = await db.execute(
        select(func.count()).where(MarketDataSource.org_id == org_id)
    )
    sources_count = sources_count_result.scalar_one()

    active_count_result = await db.execute(
        select(func.count()).where(
            MarketDataSource.org_id == org_id,
            MarketDataSource.is_active.is_(True),
        )
    )
    active_sources_count = active_count_result.scalar_one()

    records_today_result = await db.execute(
        select(func.count()).where(
            MarketDataProcessed.org_id == org_id,
            MarketDataProcessed.created_at >= today_start,
        )
    )
    records_today = records_today_result.scalar_one()

    pending_review_result = await db.execute(
        select(func.count()).where(
            DataReviewQueue.org_id == org_id,
            DataReviewQueue.resolved_at.is_(None),
        )
    )
    pending_review_count = pending_review_result.scalar_one()

    recent_fetches_result = await db.execute(
        select(MarketEnrichmentFetchLog)
        .where(MarketEnrichmentFetchLog.org_id == org_id)
        .order_by(MarketEnrichmentFetchLog.created_at.desc())
        .limit(10)
    )
    recent_fetches = list(recent_fetches_result.scalars().all())

    return MarketEnrichmentDashboard(
        sources_count=sources_count,
        active_sources_count=active_sources_count,
        records_today=records_today,
        pending_review_count=pending_review_count,
        recent_fetches=recent_fetches,  # type: ignore[arg-type]
    )


async def list_processed(
    db: AsyncSession,
    org_id: uuid.UUID,
    data_type: str | None = None,
    category: str | None = None,
    region: str | None = None,
    technology: str | None = None,
    effective_date_from: date | None = None,
    effective_date_to: date | None = None,
    review_status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[MarketDataProcessed]:
    conditions = [MarketDataProcessed.org_id == org_id]
    if data_type:
        conditions.append(MarketDataProcessed.data_type == data_type)
    if category:
        conditions.append(MarketDataProcessed.category.ilike(f"%{category}%"))
    if region:
        conditions.append(MarketDataProcessed.region.ilike(f"%{region}%"))
    if technology:
        conditions.append(MarketDataProcessed.technology.ilike(f"%{technology}%"))
    if effective_date_from:
        conditions.append(MarketDataProcessed.effective_date >= effective_date_from)
    if effective_date_to:
        conditions.append(MarketDataProcessed.effective_date <= effective_date_to)
    if review_status:
        conditions.append(MarketDataProcessed.review_status == review_status)

    stmt = (
        select(MarketDataProcessed)
        .where(and_(*conditions))
        .order_by(MarketDataProcessed.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_processed(
    db: AsyncSession, org_id: uuid.UUID, processed_id: uuid.UUID
) -> MarketDataProcessed | None:
    result = await db.execute(
        select(MarketDataProcessed).where(
            MarketDataProcessed.id == processed_id,
            MarketDataProcessed.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def create_manual_entry(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ManualEntryCreate,
) -> MarketDataProcessed:
    entry = MarketDataProcessed(
        org_id=org_id,
        raw_id=None,
        confidence=1.0,
        review_status="auto_accepted",
        reviewed_by=user_id,
        reviewed_at=datetime.now(tz=UTC),
        **data.model_dump(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def review_entry(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    processed_id: uuid.UUID,
    decision: ReviewDecision,
) -> MarketDataProcessed | None:
    entry = await get_processed(db, org_id, processed_id)
    if entry is None:
        return None

    entry.review_status = "approved" if decision.action == "approve" else "rejected"
    entry.reviewed_by = user_id
    entry.reviewed_at = datetime.now(tz=UTC)

    # Mark review queue item as resolved
    queue_result = await db.execute(
        select(DataReviewQueue).where(
            DataReviewQueue.processed_id == processed_id,
            DataReviewQueue.resolved_at.is_(None),
        )
    )
    queue_items = list(queue_result.scalars().all())
    for item in queue_items:
        item.resolved_at = datetime.now(tz=UTC)

    await db.commit()
    await db.refresh(entry)
    return entry


async def get_fetch_logs(
    db: AsyncSession,
    org_id: uuid.UUID,
    source_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[MarketEnrichmentFetchLog]:
    stmt = select(MarketEnrichmentFetchLog).where(MarketEnrichmentFetchLog.org_id == org_id)
    if source_id:
        stmt = stmt.where(MarketEnrichmentFetchLog.source_id == source_id)
    stmt = stmt.order_by(MarketEnrichmentFetchLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_review_queue(
    db: AsyncSession, org_id: uuid.UUID, limit: int = 50
) -> list[DataReviewQueue]:
    stmt = (
        select(DataReviewQueue)
        .where(
            DataReviewQueue.org_id == org_id,
            DataReviewQueue.resolved_at.is_(None),
        )
        .order_by(DataReviewQueue.priority.desc(), DataReviewQueue.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_fetch_log(
    db: AsyncSession, org_id: uuid.UUID, source_id: uuid.UUID
) -> MarketEnrichmentFetchLog:
    log = MarketEnrichmentFetchLog(
        org_id=org_id,
        source_id=source_id,
        status="pending",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def search_for_ralph(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    data_type: str | None = None,
    region: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search processed market data for Ralph AI tool use."""
    conditions = [MarketDataProcessed.org_id == org_id]
    if data_type:
        conditions.append(MarketDataProcessed.data_type == data_type)
    if region:
        conditions.append(MarketDataProcessed.region.ilike(f"%{region}%"))
    # Keyword match on category
    if query:
        conditions.append(MarketDataProcessed.category.ilike(f"%{query}%"))

    stmt = (
        select(MarketDataProcessed)
        .where(and_(*conditions))
        .order_by(MarketDataProcessed.effective_date.desc().nullslast())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return [
        {
            "id": str(r.id),
            "data_type": r.data_type,
            "category": r.category,
            "region": r.region,
            "technology": r.technology,
            "effective_date": str(r.effective_date) if r.effective_date else None,
            "value_numeric": float(r.value_numeric) if r.value_numeric is not None else None,
            "value_text": r.value_text,
            "unit": r.unit,
            "confidence": float(r.confidence),
        }
        for r in rows
    ]
