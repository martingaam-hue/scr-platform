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
    improvement_guidance: dict[str, Any] | None = None
    model_used: str
    version: int
    is_live: bool = False
    calculated_at: datetime
    task_log_id: uuid.UUID | None = None


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


# ── Strengths ─────────────────────────────────────────────────────────────────


class StrengthItem(BaseModel):
    dimension_id: str
    dimension_name: str
    criterion_id: str
    criterion_name: str
    score: int
    summary: str


class StrengthsResponse(BaseModel):
    items: list[StrengthItem]
    total: int


# ── History ──────────────────────────────────────────────────────────────────


class ScoreHistoryItem(BaseModel):
    version: int
    overall_score: int
    project_viability_score: int
    financial_planning_score: int
    esg_score: int
    risk_assessment_score: int
    team_strength_score: int
    market_opportunity_score: int
    is_live: bool
    calculated_at: datetime


class ScoreHistoryResponse(BaseModel):
    items: list[ScoreHistoryItem]


# ── Live Score ────────────────────────────────────────────────────────────────


class LiveScoreFactor(BaseModel):
    name: str
    met: bool
    impact: int


class LiveScoreResponse(BaseModel):
    overall_score: int
    factors: list[LiveScoreFactor]
    guidance: str
    note: str = "Quick score based on project metadata completeness. Run full signal score for AI-powered analysis."


# ── Improvement Guidance ──────────────────────────────────────────────────────


class ImprovementAction(BaseModel):
    dimension_id: str
    dimension_name: str
    action: str
    expected_gain: int
    effort: str
    doc_types_needed: list[str]


class ImprovementGuidanceResponse(BaseModel):
    quick_wins: list[str]
    focus_area: str | None
    high_priority_count: int
    medium_priority_count: int
    estimated_max_gain: int
    top_actions: list[ImprovementAction]
    based_on_version: int


# ── Calculate ────────────────────────────────────────────────────────────────


class CalculateAcceptedResponse(BaseModel):
    task_log_id: uuid.UUID
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_message: str | None = None
