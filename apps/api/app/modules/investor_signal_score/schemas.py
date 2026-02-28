"""Investor Signal Score schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CriterionResult(BaseModel):
    name: str
    description: str
    points: int
    max_points: int
    met: bool
    details: str = ""


class DimensionScore(BaseModel):
    score: float
    weight: float
    details: dict[str, Any] | None
    gaps: list[str]
    recommendations: list[str]


class DimensionDetailResponse(BaseModel):
    score: float
    weight: float
    gaps: list[str]
    recommendations: list[str]
    details: dict[str, Any] | None
    criteria: list[CriterionResult]


class ImprovementAction(BaseModel):
    title: str
    description: str
    estimated_impact: float
    effort_level: str  # low | medium | high
    category: str
    link_to: str | None = None


class ScoreFactorItem(BaseModel):
    label: str
    impact: str  # positive | negative
    value: str
    dimension: str


class ScoreHistoryItem(BaseModel):
    id: uuid.UUID
    overall_score: float
    score_change: float | None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class BenchmarkResponse(BaseModel):
    your_score: float
    platform_average: float
    top_quartile: float
    percentile: int  # 0-100


class TopMatchItem(BaseModel):
    project_id: uuid.UUID
    project_name: str
    alignment_score: int
    recommendation: str
    project_type: str | None = None
    geography_country: str | None = None


class GapItem(BaseModel):
    dimension: str
    description: str
    impact_points: int


class InvestorSignalScoreResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    overall_score: float
    financial_capacity: DimensionScore
    risk_management: DimensionScore
    investment_strategy: DimensionScore
    team_experience: DimensionScore
    esg_commitment: DimensionScore
    platform_readiness: DimensionScore
    score_change: float | None
    previous_score: float | None
    calculated_at: datetime

    model_config = {"from_attributes": True}


class DealAlignmentRequest(BaseModel):
    project_id: uuid.UUID


class DealAlignmentResponse(BaseModel):
    project_id: uuid.UUID
    investor_score: float
    alignment_score: int  # 0-100
    alignment_factors: list[dict[str, Any]]  # [{dimension, score, impact}]
    recommendation: str  # strong_fit, good_fit, marginal_fit, poor_fit
