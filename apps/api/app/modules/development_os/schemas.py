"""Development OS schemas — construction lifecycle management."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class MilestoneResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    due_date: date | None
    completed_date: date | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MilestoneCreate(BaseModel):
    title: str
    description: str | None = None
    due_date: date | None = None
    status: str = "not_started"  # not_started, in_progress, completed, delayed, blocked


class MilestoneUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    completed_date: date | None = None
    status: str | None = None


class ConstructionPhase(BaseModel):
    phase_name: str
    start_date: date | None
    end_date: date | None
    completion_pct: float   # 0–100
    milestones: list[MilestoneResponse]
    status: str             # not_started, in_progress, completed


class ProcurementItem(BaseModel):
    id: str
    name: str
    vendor: str | None
    category: str
    estimated_cost_usd: float | None
    status: str             # pending, rfq_sent, negotiating, contracted, delivered
    delivery_date: date | None
    notes: str | None


class DevelopmentOSResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    project_stage: str
    overall_completion_pct: float
    phases: list[ConstructionPhase]
    procurement: list[ProcurementItem]
    next_milestone: MilestoneResponse | None
    days_to_next_milestone: int | None
    last_updated: datetime
