"""Covenant & KPI Monitoring — Pydantic v2 schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Covenant ──────────────────────────────────────────────────────────────────


class CovenantCreate(BaseModel):
    name: str
    description: str | None = None
    covenant_type: str
    metric_name: str
    threshold_value: float | None = None
    comparison: str  # >=, <=, ==, between, not_null
    threshold_upper: float | None = None
    warning_threshold_pct: float = 0.1
    check_frequency: str = "monthly"
    source_document_id: uuid.UUID | None = None
    portfolio_id: uuid.UUID | None = None


class CovenantUpdate(BaseModel):
    name: str | None = None
    threshold_value: float | None = None
    status: str | None = None
    check_frequency: str | None = None


class CovenantWaiveRequest(BaseModel):
    reason: str


class CovenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    portfolio_id: uuid.UUID | None
    name: str
    description: str | None
    covenant_type: str
    metric_name: str
    threshold_value: float | None
    comparison: str
    threshold_upper: float | None
    current_value: float | None
    last_checked_at: datetime | None
    status: str
    warning_threshold_pct: float
    breach_date: datetime | None
    waived_by: uuid.UUID | None
    waived_reason: str | None
    source_document_id: uuid.UUID | None
    check_frequency: str
    created_at: datetime
    updated_at: datetime


# ── KPI Actual ────────────────────────────────────────────────────────────────


class KPIActualCreate(BaseModel):
    kpi_name: str
    value: float
    unit: str | None = None
    period: str
    period_type: str = "quarterly"
    source: str = "manual"
    source_document_id: uuid.UUID | None = None


class KPIActualResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    kpi_name: str
    value: float
    unit: str | None
    period: str
    period_type: str
    source: str
    source_document_id: uuid.UUID | None
    entered_by: uuid.UUID | None
    created_at: datetime


# ── KPI Target ────────────────────────────────────────────────────────────────


class KPITargetCreate(BaseModel):
    kpi_name: str
    target_value: float
    period: str
    tolerance_pct: float = 0.1
    source: str = "business_plan"


class KPITargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    kpi_name: str
    target_value: float
    period: str
    tolerance_pct: float
    source: str
    created_at: datetime


# ── Variance & Dashboard ──────────────────────────────────────────────────────


class KPIVarianceItem(BaseModel):
    kpi: str
    actual: float
    target: float
    variance_pct: float
    status: Literal["on_track", "above", "below"]
    unit: str | None = None


class CovenantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    metric_name: str
    current_value: float | None
    threshold_value: float | None
    comparison: str


class MonitoringDashboardItem(BaseModel):
    project_id: uuid.UUID
    project_name: str
    covenants: list[CovenantSummary]
    overall_status: Literal["compliant", "warning", "breach"]
