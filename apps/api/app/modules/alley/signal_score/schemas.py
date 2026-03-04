"""Alley-side Signal Score schemas — developer-focused framing."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


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
    trend: str  # "up" | "down" | "stable" | "new"
    score_change: int  # vs previous version


class AlleyScoreListResponse(BaseModel):
    items: list[AlleyProjectScoreSummary]
    total: int


class GapActionItem(BaseModel):
    dimension: str
    criterion: str
    current_score: int
    max_score: int
    action: str
    estimated_impact: int  # estimated score improvement
    priority: str  # "critical" | "high" | "medium" | "low"
    effort: str  # "low" | "medium" | "high"
    document_types: list[str]


class GapAnalysisResponse(BaseModel):
    project_id: uuid.UUID
    overall_score: int
    target_score: int
    gap_items: list[GapActionItem]
    generated_at: datetime | None = None


class SimulateRequest(BaseModel):
    criteria_overrides: dict[str, str]  # {criterion_id: "met" | "partial" | "not_met"}


class SimulateResponse(BaseModel):
    current_score: int
    projected_score: int
    score_change: int
    dimension_changes: dict[str, int]


class ScoreHistoryPoint(BaseModel):
    version: int
    overall_score: int
    calculated_at: datetime
    project_viability_score: int
    financial_planning_score: int
    team_strength_score: int
    risk_assessment_score: int
    esg_score: int
    market_opportunity_score: int


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
