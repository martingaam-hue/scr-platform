"""Alley-side Risk schemas — developer mitigation view."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class RiskItemSummary(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    severity: str  # "critical" | "high" | "medium" | "low"
    dimension: str  # "technical" | "financial" | "regulatory" | "esg" | "market"
    mitigation_status: (
        str  # "unaddressed" | "acknowledged" | "in_progress" | "mitigated" | "accepted"
    )
    guidance: str | None = None
    evidence_document_ids: list[uuid.UUID] = []
    notes: str | None = None
    source: str = "auto"  # "auto" | "logged"


class ProjectRiskSummary(BaseModel):
    project_id: uuid.UUID
    project_name: str
    total_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    mitigated_count: int = 0  # risks with status "mitigated" or "accepted"
    mitigation_progress_pct: int  # = mitigated_count / total_risks * 100
    overall_risk_score: float = 0.0  # 0–100, severity-weighted, adjusted for mitigation
    auto_identified_count: int = 0
    logged_count: int = 0


class RiskListResponse(BaseModel):
    items: list[ProjectRiskSummary]
    total: int
    portfolio_risk_score: float = 0.0  # portfolio-level weighted average
    total_auto_identified: int = 0
    total_logged: int = 0


class ProjectRiskDetailResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    risk_items: list[RiskItemSummary]
    total_risks: int
    addressed_risks: int
    mitigation_progress_pct: int
    overall_risk_score: float = 0.0


class DomainRiskItem(BaseModel):
    domain: str
    risk_score: float  # 0–100
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total: int


class DomainRiskResponse(BaseModel):
    domains: list[DomainRiskItem]
    portfolio_risk_score: float


class RunCheckResponse(BaseModel):
    task_id: str
    message: str


class MitigationUpdateRequest(BaseModel):
    status: str  # "acknowledged" | "in_progress" | "mitigated" | "accepted"
    notes: str | None = None


class EvidenceLinkRequest(BaseModel):
    document_id: uuid.UUID


class MitigationProgressResponse(BaseModel):
    project_id: uuid.UUID
    total_risks: int
    addressed: int
    in_progress: int
    mitigated: int
    accepted: int
    unaddressed: int
    progress_pct: int
