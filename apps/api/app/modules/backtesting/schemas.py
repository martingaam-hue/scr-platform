"""Pydantic v2 schemas for the Score Backtesting module."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Request models ────────────────────────────────────────────────────────────


class RecordOutcomeRequest(BaseModel):
    project_id: uuid.UUID | None = None
    outcome_type: str = Field(
        ...,
        description="One of: funded, passed, closed_lost, in_progress",
    )
    actual_irr: Decimal | None = None
    actual_moic: Decimal | None = None
    actual_revenue_eur: Decimal | None = None
    signal_score_at_evaluation: Decimal | None = None
    signal_score_at_decision: Decimal | None = None
    signal_dimensions_at_decision: dict | None = None
    decision_date: date | None = None
    outcome_date: date | None = None
    notes: str | None = None


class BacktestRunRequest(BaseModel):
    methodology: str = Field(
        default="threshold",
        description="One of: threshold, cohort, time_series",
    )
    date_from: date | None = None
    date_to: date | None = None
    min_score_threshold: Decimal | None = Field(default=None, ge=0, le=100)


# ── Response models ───────────────────────────────────────────────────────────


class DealOutcomeResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    deal_flow_stage_id: uuid.UUID | None
    outcome_type: str
    actual_irr: Decimal | None
    actual_moic: Decimal | None
    actual_revenue_eur: Decimal | None
    signal_score_at_evaluation: Decimal | None
    signal_score_at_decision: Decimal | None
    signal_dimensions_at_decision: dict | None
    decision_date: date | None
    outcome_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BacktestRunResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    run_by: uuid.UUID | None
    methodology: str
    date_from: date | None
    date_to: date | None
    min_score_threshold: Decimal | None
    accuracy: Decimal | None
    precision: Decimal | None
    recall: Decimal | None
    auc_roc: Decimal | None
    f1_score: Decimal | None
    sample_size: int | None
    results: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BacktestSummaryResponse(BaseModel):
    total_outcomes: int
    funded_count: int
    pass_count: int
    closed_lost_count: int
    in_progress_count: int
    funded_rate: float | None
    avg_score_of_funded: float | None
    latest_run: BacktestRunResponse | None
