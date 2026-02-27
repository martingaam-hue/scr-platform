"""Pydantic schemas for Projects endpoints."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    BudgetItemStatus,
    MilestoneStatus,
    ProjectStage,
    ProjectStatus,
    ProjectType,
)


# ── Projects ────────────────────────────────────────────────────────────────


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    project_type: ProjectType
    description: str = ""
    geography_country: str = Field(..., min_length=1, max_length=100)
    geography_region: str = ""
    geography_coordinates: dict[str, Any] | None = None
    technology_details: dict[str, Any] | None = None
    capacity_mw: Decimal | None = None
    total_investment_required: Decimal = Field(..., gt=0)
    currency: str = Field("USD", max_length=3)
    target_close_date: date | None = None
    stage: ProjectStage = ProjectStage.CONCEPT
    status: ProjectStatus = ProjectStatus.DRAFT


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    project_type: ProjectType | None = None
    status: ProjectStatus | None = None
    stage: ProjectStage | None = None
    geography_country: str | None = Field(None, max_length=100)
    geography_region: str | None = None
    geography_coordinates: dict[str, Any] | None = None
    technology_details: dict[str, Any] | None = None
    capacity_mw: Decimal | None = None
    total_investment_required: Decimal | None = Field(None, gt=0)
    currency: str | None = Field(None, max_length=3)
    target_close_date: date | None = None
    cover_image_url: str | None = None


class SignalScoreResponse(BaseModel):
    overall_score: int
    technical_score: int
    financial_score: int
    esg_score: int
    regulatory_score: int
    team_score: int
    gaps: dict[str, Any] | None = None
    strengths: dict[str, Any] | None = None
    model_used: str
    version: int
    calculated_at: datetime


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str
    project_type: ProjectType
    status: ProjectStatus
    stage: ProjectStage
    geography_country: str
    geography_region: str
    geography_coordinates: dict[str, Any] | None = None
    technology_details: dict[str, Any] | None = None
    capacity_mw: Decimal | None = None
    total_investment_required: Decimal
    currency: str
    target_close_date: date | None = None
    cover_image_url: str | None = None
    is_published: bool
    published_at: datetime | None = None
    latest_signal_score: int | None = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    milestone_count: int = 0
    budget_item_count: int = 0
    document_count: int = 0
    latest_signal: SignalScoreResponse | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProjectStatsResponse(BaseModel):
    total_projects: int
    active_fundraising: int
    total_funding_needed: Decimal
    avg_signal_score: float | None = None


# ── Milestones ──────────────────────────────────────────────────────────────


class MilestoneCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    target_date: date
    order_index: int = 0


class MilestoneUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    target_date: date | None = None
    completed_date: date | None = None
    status: MilestoneStatus | None = None
    completion_pct: int | None = Field(None, ge=0, le=100)
    order_index: int | None = None


class MilestoneResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str
    target_date: date
    completed_date: date | None = None
    status: MilestoneStatus
    completion_pct: int
    order_index: int
    created_at: datetime
    updated_at: datetime


# ── Budget Items ────────────────────────────────────────────────────────────


class BudgetItemCreateRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    estimated_amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", max_length=3)


class BudgetItemUpdateRequest(BaseModel):
    category: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    estimated_amount: Decimal | None = Field(None, gt=0)
    actual_amount: Decimal | None = None
    currency: str | None = Field(None, max_length=3)
    status: BudgetItemStatus | None = None


class BudgetItemResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    category: str
    description: str
    estimated_amount: Decimal
    actual_amount: Decimal | None = None
    currency: str
    status: BudgetItemStatus
    created_at: datetime
    updated_at: datetime
