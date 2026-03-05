"""Alley-side Signal Score schemas — developer-focused framing."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

# ── Portfolio Overview ─────────────────────────────────────────────────────────


class PortfolioStats(BaseModel):
    avg_score: float  # 0.0–10.0
    total_projects: int
    investment_ready_count: int


class ProjectScoreListItem(BaseModel):
    project_id: uuid.UUID
    project_name: str
    sector: str | None
    stage: str | None
    score: float  # 0.0–10.0 (stored value ÷ 10)
    score_label: str  # Excellent | Strong | Good | Needs Review
    score_label_color: str  # green | yellow | amber | red
    status: str  # Ready | Needs Review
    calculated_at: datetime
    trend: str  # up | down | stable | new


class ImprovementFactor(BaseModel):
    dimension: str
    avg_score: float  # 0.0–10.0


class ImprovementAction(BaseModel):
    action: str
    dimension: str
    priority: str  # critical | high | medium | low
    estimated_impact: float  # 0.0–10.0 scale


class PortfolioScoreResponse(BaseModel):
    stats: PortfolioStats
    projects: list[ProjectScoreListItem]
    improvement_factors: list[ImprovementFactor]
    improvement_actions: list[ImprovementAction]


# ── Project Detail ─────────────────────────────────────────────────────────────


class DimensionDetail(BaseModel):
    id: str
    label: str
    score: int  # 0–100 (raw, used as % width for bar)
    description: str | None = None


class ReadinessIndicator(BaseModel):
    label: str
    met: bool


class CriterionDetail(BaseModel):
    id: str
    name: str
    status: str  # met | partial | not_met
    points_earned: int
    points_max: int
    evidence_note: str | None = None


class DimensionBreakdown(BaseModel):
    dimension_id: str
    dimension_name: str
    score: int
    criteria: list[CriterionDetail]


class GapAction(BaseModel):
    dimension: str
    action: str
    effort: str  # low | medium | high
    timeline: str
    estimated_impact: float  # 0.0–10.0 scale


class ScoreHistoryPoint(BaseModel):
    date: str  # ISO date "YYYY-MM-DD"
    score: float  # 0.0–10.0


class ProjectScoreDetailResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    score: float  # 0.0–10.0
    score_label: str
    score_label_color: str
    dimensions: list[DimensionDetail]
    readiness_indicators: list[ReadinessIndicator]
    criteria_breakdown: list[DimensionBreakdown]
    gap_analysis: list[GapAction]
    score_history: list[ScoreHistoryPoint]


# ── Generate / Task Status ─────────────────────────────────────────────────────


class GenerateScoreResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending | running | completed | failed
    progress_message: str | None = None
    result: dict | None = None


# ── Legacy schemas (kept for backward-compat endpoints) ────────────────────────


class AlleyProjectScoreSummary(BaseModel):
    project_id: uuid.UUID
    project_name: str
    overall_score: int
    project_viability_score: int
    financial_planning_score: int
    team_strength_score: int
    risk_assessment_score: int
    esg_score: int
    market_opportunity_score: int
    version: int
    calculated_at: datetime
    trend: str
    score_change: int


class AlleyScoreListResponse(BaseModel):
    items: list[AlleyProjectScoreSummary]
    total: int


class GapActionItem(BaseModel):
    dimension: str
    criterion: str
    current_score: int
    max_score: int
    action: str
    estimated_impact: int
    priority: str
    effort: str
    document_types: list[str]


class GapAnalysisResponse(BaseModel):
    project_id: uuid.UUID
    overall_score: int
    target_score: int
    gap_items: list[GapActionItem]
    generated_at: datetime | None = None


class SimulateRequest(BaseModel):
    criteria_overrides: dict[str, str]


class SimulateResponse(BaseModel):
    current_score: int
    projected_score: int
    score_change: int
    dimension_changes: dict[str, int]


class ScoreHistoryResponse(BaseModel):
    project_id: uuid.UUID
    history: list[ScoreHistoryPoint]


class BenchmarkResponse(BaseModel):
    project_id: uuid.UUID
    your_score: int
    platform_median: int
    top_quartile: int
    percentile: int
    peer_asset_type: str
    peer_count: int
