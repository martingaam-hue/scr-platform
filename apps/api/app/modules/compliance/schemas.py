"""Compliance deadline Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeadlineCreate(BaseModel):
    category: str  # regulatory_filing, tax, environmental, permit, license, insurance, reporting, sfdr
    title: str
    description: str | None = None
    jurisdiction: str | None = None
    regulatory_body: str | None = None
    due_date: date
    recurrence: str | None = None  # monthly, quarterly, annually, one_time
    priority: str = "high"
    project_id: uuid.UUID | None = None
    portfolio_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None


class DeadlineUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    jurisdiction: str | None = None
    regulatory_body: str | None = None
    due_date: date | None = None
    recurrence: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: uuid.UUID | None = None


class DeadlineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    portfolio_id: uuid.UUID | None
    category: str
    title: str
    description: str | None
    jurisdiction: str | None
    regulatory_body: str | None
    due_date: date
    recurrence: str | None
    status: str
    priority: str
    assigned_to: uuid.UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Computed
    days_until_due: int | None = None
    is_overdue: bool = False


class DeadlineListResponse(BaseModel):
    items: list[DeadlineResponse]
    total: int
    overdue_count: int
    due_this_week: int
    due_this_month: int


class AutoGenerateRequest(BaseModel):
    project_id: uuid.UUID
    jurisdiction: str = "EU"  # EU, UK, US
    project_type: str = "solar"  # solar, wind, real_estate, general


class CompleteDeadlineRequest(BaseModel):
    notes: str | None = None
