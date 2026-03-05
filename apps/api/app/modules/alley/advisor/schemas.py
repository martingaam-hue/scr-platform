"""Alley Development Advisor schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AdvisorQueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AdvisorQueryResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: list[str] = []
    model_used: str = "claude-sonnet-4"


class FinancingReadinessResponse(BaseModel):
    project_id: uuid.UUID
    readiness_score: int  # 0-100
    summary: str
    checklist: list[dict]  # [{item, status, action}]
    recommended_structure: str
    generated_at: datetime


class MarketPositioningResponse(BaseModel):
    project_id: uuid.UUID
    strengths: list[str]
    weaknesses: list[str]
    timing_assessment: str
    score_percentile: int
    generated_at: datetime


class MilestonePlanResponse(BaseModel):
    project_id: uuid.UUID
    current_stage: str
    next_milestones: list[dict]  # [{title, description, estimated_weeks, priority}]
    critical_path_item: str
    generated_at: datetime


class RegulatoryGuidanceResponse(BaseModel):
    project_id: uuid.UUID
    jurisdiction: str
    asset_type: str
    permit_requirements: list[dict]  # [{permit, timeline, authority, notes}]
    common_pitfalls: list[str]
    generated_at: datetime
