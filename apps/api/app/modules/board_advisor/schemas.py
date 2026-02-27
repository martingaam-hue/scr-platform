"""Board Advisor schemas."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class AdvisorProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID
    expertise_areas: dict[str, Any] | None
    industry_experience: dict[str, Any] | None
    board_positions_held: int
    availability_status: str
    compensation_preference: str
    bio: str
    linkedin_url: str | None
    verified: bool
    match_count: int
    avg_rating: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdvisorProfileCreate(BaseModel):
    expertise_areas: dict[str, Any] | None = None
    industry_experience: dict[str, Any] | None = None
    board_positions_held: int = 0
    availability_status: str = "available"
    compensation_preference: str = "negotiable"
    bio: str = ""
    linkedin_url: str | None = None


class AdvisorProfileUpdate(BaseModel):
    expertise_areas: dict[str, Any] | None = None
    industry_experience: dict[str, Any] | None = None
    board_positions_held: int | None = None
    availability_status: str | None = None
    compensation_preference: str | None = None
    bio: str | None = None
    linkedin_url: str | None = None
    is_active: bool | None = None


class AdvisorSearchResult(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    expertise_areas: dict[str, Any] | None
    availability_status: str
    compensation_preference: str
    bio: str
    verified: bool
    board_positions_held: int
    avg_rating: float | None
    match_score: int  # 0-100 deterministic alignment score

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    project_id: uuid.UUID
    role_offered: str
    message: str | None = None
    equity_offered: float | None = None
    compensation_terms: dict[str, Any] | None = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    advisor_profile_id: uuid.UUID
    ally_org_id: uuid.UUID
    status: str
    message: str | None
    role_offered: str
    equity_offered: float | None
    compensation_terms: dict[str, Any] | None
    signal_score_impact: float | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    status: str  # ACCEPTED, REJECTED, ACTIVE, WITHDRAWN, COMPLETED
    notes: str | None = None
