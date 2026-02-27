"""Investor Signal Score schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DimensionScore(BaseModel):
    score: float
    weight: float
    details: dict[str, Any] | None
    gaps: list[str]
    recommendations: list[str]


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
