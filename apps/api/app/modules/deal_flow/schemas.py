"""Deal Flow Analytics — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TransitionCreate(BaseModel):
    project_id: uuid.UUID
    to_stage: str = Field(..., max_length=50)
    from_stage: str | None = Field(None, max_length=50)
    reason: str | None = Field(None, max_length=100)
    investor_id: uuid.UUID | None = None
    metadata: dict = {}


class TransitionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    investor_id: uuid.UUID | None
    from_stage: str | None
    to_stage: str
    reason: str | None
    transitioned_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StageCount(BaseModel):
    stage: str
    count: int
    deal_value: float | None


class ConversionStep(BaseModel):
    from_stage: str
    to_stage: str
    from_count: int
    to_count: int
    conversion_rate: float


class AvgTimeInStage(BaseModel):
    stage: str
    avg_days: float | None


class FunnelResponse(BaseModel):
    period_days: int
    stage_counts: list[StageCount]
    conversions: list[ConversionStep]
    avg_time_in_stage: list[AvgTimeInStage]
    drop_off_reasons: dict[str, int]
    total_entered: int
    total_closed: int
    overall_conversion_rate: float
    generated_at: datetime


class PipelineValueResponse(BaseModel):
    by_stage: dict[str, float]
    total: float


class VelocityResponse(BaseModel):
    avg_days_to_close: float | None
    by_stage: list[AvgTimeInStage]
    trend: list[dict]  # [{month: "2026-01", avg_days: 45.2}, ...]
