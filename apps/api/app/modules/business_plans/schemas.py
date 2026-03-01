"""Business Plans — Pydantic v2 request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import BusinessPlanStatus


class BusinessPlanCreate(BaseModel):
    project_id: uuid.UUID
    title: str
    executive_summary: str = ""
    financial_projections: dict[str, Any] | None = None
    market_analysis: dict[str, Any] | None = None
    risk_analysis: dict[str, Any] | None = None
    use_of_funds: str | None = None
    team_section: str | None = None
    risk_section: str | None = None
    status: BusinessPlanStatus = BusinessPlanStatus.DRAFT


class BusinessPlanUpdate(BaseModel):
    title: str | None = None
    executive_summary: str | None = None
    financial_projections: dict[str, Any] | None = None
    market_analysis: dict[str, Any] | None = None
    risk_analysis: dict[str, Any] | None = None
    use_of_funds: str | None = None
    team_section: str | None = None
    risk_section: str | None = None
    status: BusinessPlanStatus | None = None


class BusinessPlanResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID | None
    title: str
    executive_summary: str
    financial_projections: dict[str, Any] | None
    market_analysis: dict[str, Any] | None
    risk_analysis: dict[str, Any] | None
    use_of_funds: str | None
    team_section: str | None
    risk_section: str | None
    status: BusinessPlanStatus
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
