"""Alley Pipeline Analytics schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class PipelineOverview(BaseModel):
    total_projects: int
    total_mw: float
    total_value: float
    currency: str
    scored_projects: int
    avg_score: float
    stage_counts: dict[str, int]


class StageDistributionItem(BaseModel):
    stage: str
    count: int
    total_mw: float
    total_value: float


class ScoreDistributionItem(BaseModel):
    bucket: str  # e.g. "0-20", "20-40"
    count: int


class RiskHeatmapCell(BaseModel):
    project_id: uuid.UUID
    project_name: str
    technical: int
    financial: int
    regulatory: int
    esg: int
    market: int
    overall_risk_level: str  # "low" | "medium" | "high" | "critical"


class DocumentCompletenessItem(BaseModel):
    project_id: uuid.UUID
    project_name: str
    uploaded_count: int
    expected_count: int
    completeness_pct: int
    missing_types: list[str]


class ProjectCompareItem(BaseModel):
    project_id: uuid.UUID
    project_name: str
    stage: str
    asset_type: str
    geography: str
    overall_score: int
    total_investment: float
    currency: str
    capacity_mw: float
    risk_level: str
