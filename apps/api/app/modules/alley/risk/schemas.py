"""Alley-side Risk schemas — developer mitigation view."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class RiskItemSummary(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    severity: str  # "critical" | "high" | "medium" | "low"
    dimension: str  # "technical" | "financial" | "regulatory" | "esg" | "market"
    mitigation_status: str  # "unaddressed" | "acknowledged" | "in_progress" | "mitigated" | "accepted"
    guidance: str | None = None
    evidence_document_ids: list[uuid.UUID] = []
    notes: str | None = None


class ProjectRiskSummary(BaseModel):
    project_id: uuid.UUID
    project_name: str
    total_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    mitigation_progress_pct: int


class RiskListResponse(BaseModel):
    items: list[ProjectRiskSummary]
    total: int


class ProjectRiskDetailResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    risk_items: list[RiskItemSummary]
    total_risks: int
    addressed_risks: int
    mitigation_progress_pct: int


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
