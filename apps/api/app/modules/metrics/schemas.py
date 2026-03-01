"""Metrics module Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MetricSnapshotResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    metric_name: str
    value: float
    previous_value: float | None
    metadata: dict[str, Any] | None
    trigger_event: str | None
    trigger_entity_id: uuid.UUID | None
    recorded_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            org_id=obj.org_id,
            entity_type=obj.entity_type,
            entity_id=obj.entity_id,
            metric_name=obj.metric_name,
            value=obj.value,
            previous_value=obj.previous_value,
            metadata=obj.metadata_,
            trigger_event=obj.trigger_event,
            trigger_entity_id=obj.trigger_entity_id,
            recorded_at=obj.recorded_at,
        )


class TrendPoint(BaseModel):
    date: str  # ISO format
    value: float
    previous_value: float | None = None
    delta: float | None = None
    trigger_event: str | None = None


class ChangeEvent(BaseModel):
    date: str
    from_value: float
    to_value: float
    delta: float
    trigger: str | None
    trigger_entity: str | None
    metadata: dict[str, Any] | None


class BenchmarkComparison(BaseModel):
    metric_name: str
    value: float
    peer_group: str
    peer_count: int
    percentile: float | None
    quartile: int | None  # 1-4
    vs_median: float | None
    benchmark: dict[str, float | None]


class BenchmarkAggregateResponse(BaseModel):
    id: uuid.UUID
    asset_class: str
    geography: str | None
    stage: str | None
    vintage_year: int | None
    metric_name: str
    count: int
    mean: float | None
    median: float | None
    p25: float | None
    p75: float | None
    p10: float | None
    p90: float | None
    std_dev: float | None
    min_val: float | None
    max_val: float | None
    period: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class PacingProjection(BaseModel):
    month: int
    contributions: float
    distributions: float
    nav: float
    net_cashflow: float


class QuartileChartData(BaseModel):
    metric_name: str
    value: float
    p10: float | None
    p25: float | None
    p50: float | None
    p75: float | None
    p90: float | None
    percentile: float | None
    quartile: int | None
