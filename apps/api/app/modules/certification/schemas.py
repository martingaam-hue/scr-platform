"""Pydantic schemas for Investor Readiness Certification."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class CertificationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    tier: str | None
    certification_score: float | None
    dimension_scores: dict | None
    certified_at: datetime | None
    last_verified_at: datetime | None
    certification_count: int
    consecutive_months_certified: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CertificationBadge(BaseModel):
    certified: bool
    tier: str | None = None
    score: float | None = None
    certified_since: str | None = None
    consecutive_months: int = 0


class CertificationRequirementsResponse(BaseModel):
    eligible: bool
    current_score: float | None
    gaps: list[dict]  # [{type, dimension?, current, needed}]


class LeaderboardEntry(BaseModel):
    project_id: uuid.UUID
    project_name: str
    tier: str
    score: float
    certified_since: str
