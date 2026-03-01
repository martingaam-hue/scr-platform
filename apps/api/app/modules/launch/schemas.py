"""Pydantic schemas for E04 Launch Preparation module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class FeatureFlagResponse(BaseModel):
    """Response schema for a feature flag, optionally with the current org's override."""

    name: str
    description: str | None
    enabled_globally: bool
    rollout_pct: int
    org_override: bool | None = None

    model_config = {"from_attributes": True}


class FlagOverrideRequest(BaseModel):
    """Request body to set a per-org feature flag override."""

    enabled: bool


class WaitlistEntryRequest(BaseModel):
    """Request to join the waitlist."""

    email: EmailStr
    name: str | None = None
    company: str | None = None
    use_case: str | None = None


class WaitlistEntryResponse(BaseModel):
    """Public response for a waitlist entry."""

    id: uuid.UUID
    email: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageEventRequest(BaseModel):
    """Request to record a usage event."""

    event_type: str = Field(..., max_length=100)
    entity_type: str | None = Field(None, max_length=100)
    entity_id: uuid.UUID | None = None
    metadata: dict = Field(default_factory=dict)


class HealthStatus(BaseModel):
    """System health status response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    db_ok: bool
    redis_ok: bool
    checks: dict[str, bool]
