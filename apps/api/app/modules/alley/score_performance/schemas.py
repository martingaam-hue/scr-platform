"""Alley Score Performance (Score Journey) schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScoreJourneyPoint(BaseModel):
    version: int
    overall_score: int
    calculated_at: datetime
    score_change: int
    event_label: str | None = None  # e.g. "Documents uploaded"


class DimensionTrendPoint(BaseModel):
    version: int
    calculated_at: datetime
    project_viability: int
    financial_planning: int
    team_strength: int
    risk_assessment: int
    esg: int
    market_opportunity: int


class ScoreInsightItem(BaseModel):
    dimension: str
    insight: str
    recommendation: str
    estimated_impact: int


class ProjectScorePerformanceSummary(BaseModel):
    project_id: uuid.UUID
    project_name: str
    current_score: int
    start_score: int
    total_improvement: int
    versions: int
    trend: str  # "improving" | "declining" | "stable" | "new"


class ScorePerformanceListResponse(BaseModel):
    items: list[ProjectScorePerformanceSummary]
    total: int


class ScoreJourneyResponse(BaseModel):
    project_id: uuid.UUID
    journey: list[ScoreJourneyPoint]
    total_improvement: int


class DimensionTrendsResponse(BaseModel):
    project_id: uuid.UUID
    trends: list[DimensionTrendPoint]


class ScoreInsightsResponse(BaseModel):
    project_id: uuid.UUID
    insights: list[ScoreInsightItem]
    generated_at: datetime
