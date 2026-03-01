"""MetricSnapshotService — records and queries point-in-time metric values."""

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import MetricSnapshot

logger = structlog.get_logger()


class MetricSnapshotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_snapshot(
        self,
        org_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        metric_name: str,
        value: float,
        metadata: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        trigger_entity_id: uuid.UUID | None = None,
    ) -> MetricSnapshot:
        """Record a point-in-time metric value."""
        # Get previous value for delta
        prev_result = await self.db.execute(
            select(MetricSnapshot.value)
            .where(
                MetricSnapshot.entity_type == entity_type,
                MetricSnapshot.entity_id == entity_id,
                MetricSnapshot.metric_name == metric_name,
            )
            .order_by(MetricSnapshot.recorded_at.desc())
            .limit(1)
        )
        previous_value = prev_result.scalar_one_or_none()

        snapshot = MetricSnapshot(
            org_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metric_name=metric_name,
            value=value,
            previous_value=previous_value,
            metadata_=metadata or {},
            trigger_event=trigger_event,
            trigger_entity_id=trigger_entity_id,
        )
        self.db.add(snapshot)
        await self.db.flush()
        logger.info(
            "metric_snapshot_recorded",
            entity_type=entity_type,
            entity_id=str(entity_id),
            metric_name=metric_name,
            value=value,
            delta=round(value - previous_value, 2) if previous_value is not None else None,
        )
        return snapshot

    async def get_trend(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        metric_name: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[MetricSnapshot]:
        """Return time series of metric values for trend charts."""
        query = (
            select(MetricSnapshot)
            .where(
                MetricSnapshot.entity_type == entity_type,
                MetricSnapshot.entity_id == entity_id,
                MetricSnapshot.metric_name == metric_name,
            )
            .order_by(MetricSnapshot.recorded_at.asc())
        )
        if from_date:
            query = query.where(MetricSnapshot.recorded_at >= from_date)
        if to_date:
            query = query.where(MetricSnapshot.recorded_at <= to_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_change_explanation(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        metric_name: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[dict]:
        """Return snapshots with trigger events explaining what changed and why."""
        snapshots = await self.get_trend(entity_type, entity_id, metric_name, from_date, to_date)
        changes = []
        for s in snapshots:
            if s.previous_value is not None and s.previous_value != s.value:
                changes.append({
                    "date": s.recorded_at.isoformat(),
                    "from": s.previous_value,
                    "to": s.value,
                    "delta": round(s.value - s.previous_value, 2),
                    "trigger": s.trigger_event,
                    "trigger_entity": str(s.trigger_entity_id) if s.trigger_entity_id else None,
                    "metadata": s.metadata_,
                })
        return changes

    async def _get_latest(
        self, entity_type: str, entity_id: uuid.UUID, metric_name: str
    ) -> MetricSnapshot | None:
        result = await self.db.execute(
            select(MetricSnapshot)
            .where(
                MetricSnapshot.entity_type == entity_type,
                MetricSnapshot.entity_id == entity_id,
                MetricSnapshot.metric_name == metric_name,
            )
            .order_by(MetricSnapshot.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_percentile_rank(
        self, entity_type: str, entity_id: uuid.UUID, metric_name: str
    ) -> float | None:
        """Where does this entity rank vs all others of same type for this metric?"""
        current = await self._get_latest(entity_type, entity_id, metric_name)
        if not current:
            return None

        # Count distinct entities with this metric
        total_result = await self.db.execute(
            select(func.count(func.distinct(MetricSnapshot.entity_id)))
            .where(
                MetricSnapshot.metric_name == metric_name,
                MetricSnapshot.entity_type == entity_type,
            )
        )
        total_count = total_result.scalar() or 0
        if total_count == 0:
            return None

        # Subquery: latest value per entity
        subq = (
            select(
                MetricSnapshot.entity_id,
                func.max(MetricSnapshot.value).label("latest_val"),
            )
            .where(
                MetricSnapshot.metric_name == metric_name,
                MetricSnapshot.entity_type == entity_type,
            )
            .group_by(MetricSnapshot.entity_id)
            .subquery()
        )
        below_result = await self.db.execute(
            select(func.count())
            .select_from(subq)
            .where(subq.c.latest_val < current.value)
        )
        below_count = below_result.scalar() or 0
        return round((below_count / total_count) * 100, 1)
