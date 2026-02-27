"""Signal Score Pydantic schemas for detailed API responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Detailed score responses ─────────────────────────────────────────────────


class CriterionScoreResponse(BaseModel):
    id: str
    name: str
    max_points: int
    score: int
    has_document: bool
    ai_assessment: dict[str, Any] | None = None


class DimensionScoreResponse(BaseModel):
    id: str
    name: str
    weight: float
    score: int
    completeness_score: int
    quality_score: int
    criteria: list[CriterionScoreResponse]


class SignalScoreDetailResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    overall_score: int
    dimensions: list[DimensionScoreResponse]
    model_used: str
    version: int
    calculated_at: datetime


# ── Gaps ─────────────────────────────────────────────────────────────────────


class GapItem(BaseModel):
    dimension_id: str
    dimension_name: str
    criterion_id: str
    criterion_name: str
    current_score: int
    max_points: int
    priority: str
    recommendation: str
    relevant_doc_types: list[str]


class GapsResponse(BaseModel):
    items: list[GapItem]
    total: int


# ── History ──────────────────────────────────────────────────────────────────


class ScoreHistoryItem(BaseModel):
    version: int
    overall_score: int
    technical_score: int
    financial_score: int
    esg_score: int
    regulatory_score: int
    team_score: int
    calculated_at: datetime


class ScoreHistoryResponse(BaseModel):
    items: list[ScoreHistoryItem]


# ── Calculate ────────────────────────────────────────────────────────────────


class CalculateAcceptedResponse(BaseModel):
    task_log_id: uuid.UUID
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None = None
