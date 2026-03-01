"""Risk Analysis & Compliance API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Risk Assessment ───────────────────────────────────────────────────────────


class RiskAssessmentCreate(BaseModel):
    entity_type: str  # RiskEntityType value
    entity_id: uuid.UUID
    risk_type: str    # RiskType value
    severity: str     # RiskSeverity value
    probability: str  # RiskProbability value
    description: str
    mitigation: str | None = None
    status: str = "identified"


class RiskAssessmentResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    risk_type: str
    severity: str
    probability: str
    description: str
    mitigation: str | None
    status: str
    assessed_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Heatmap ───────────────────────────────────────────────────────────────────


class HeatmapCell(BaseModel):
    severity: str       # low|medium|high|critical
    probability: str    # unlikely|possible|likely|very_likely
    count: int
    risk_ids: list[uuid.UUID]


class RiskHeatmapResponse(BaseModel):
    cells: list[HeatmapCell]
    total_risks: int


# ── Concentration ─────────────────────────────────────────────────────────────


class ConcentrationItem(BaseModel):
    label: str
    value: float        # invested amount
    pct: float          # % of total
    is_concentrated: bool


class ConcentrationAnalysisResponse(BaseModel):
    portfolio_id: uuid.UUID
    total_invested: float
    by_sector: list[ConcentrationItem]
    by_geography: list[ConcentrationItem]
    by_counterparty: list[ConcentrationItem]
    by_currency: list[ConcentrationItem]
    concentration_flags: list[str]  # human-readable warnings


# ── Dashboard ─────────────────────────────────────────────────────────────────


class AutoRiskItem(BaseModel):
    risk_type: str
    severity: str
    probability: str
    description: str


class RiskTrendPoint(BaseModel):
    date: str
    risk_score: float


class RiskDashboardResponse(BaseModel):
    portfolio_id: uuid.UUID
    overall_risk_score: float       # 0-100, weighted
    heatmap: RiskHeatmapResponse
    top_risks: list[RiskAssessmentResponse]
    auto_identified: list[AutoRiskItem]
    concentration: ConcentrationAnalysisResponse
    risk_trend: list[RiskTrendPoint]


# ── Scenario Analysis ─────────────────────────────────────────────────────────


class ScenarioRequest(BaseModel):
    scenario_type: str  # interest_rate_shock|carbon_price_change|technology_disruption|regulatory_change|climate_event|custom
    parameters: dict[str, Any] = Field(default_factory=dict)
    # e.g. {"basis_points": 200}, {"pct_change": -30}, {"sectors": ["solar"], "haircut_pct": 15}


class HoldingImpact(BaseModel):
    holding_id: uuid.UUID
    asset_name: str
    current_value: float
    stressed_value: float
    delta_value: float
    delta_pct: float


class ScenarioResult(BaseModel):
    scenario_type: str
    parameters: dict[str, Any]
    # Before
    nav_before: float
    irr_before: float | None
    # After
    nav_after: float
    irr_after: float | None
    # Deltas
    nav_delta: float
    nav_delta_pct: float
    # Per holding
    holding_impacts: list[HoldingImpact]
    # Waterfall: ordered list of (label, value) contribution
    waterfall: list[dict[str, Any]]
    narrative: str


# ── ESG Scoring ───────────────────────────────────────────────────────────────


class ESGDimensionScore(BaseModel):
    label: str
    weight: float
    score: float
    sub_scores: dict[str, float]


class ESGScoreResponse(BaseModel):
    project_id: uuid.UUID
    overall_score: float
    environment: ESGDimensionScore
    social: ESGDimensionScore
    governance: ESGDimensionScore
    methodology: str


# ── SFDR / Taxonomy Compliance ────────────────────────────────────────────────


class PAIIndicator(BaseModel):
    id: int
    name: str
    category: str
    value: str | None
    unit: str
    status: str   # met|not_met|not_applicable|needs_data


class DNSHCheck(BaseModel):
    objective: str
    status: str   # compliant|non_compliant|needs_assessment
    notes: str


class TaxonomyResult(BaseModel):
    holding_id: uuid.UUID
    asset_name: str
    eligible: bool
    aligned: bool
    eligible_pct: float
    aligned_pct: float
    economic_activity: str
    dnsh_checks: list[DNSHCheck]


class ComplianceStatusResponse(BaseModel):
    portfolio_id: uuid.UUID
    sfdr_classification: str            # article_6|article_8|article_9|not_applicable
    sustainable_investment_pct: float
    taxonomy_eligible_pct: float
    taxonomy_aligned_pct: float
    pai_indicators: list[PAIIndicator]
    taxonomy_results: list[TaxonomyResult]
    overall_status: str                 # compliant|needs_attention|non_compliant
    last_assessed: datetime


# ── 5-Domain Risk Framework ───────────────────────────────────────────────────


class RiskDomainScore(BaseModel):
    domain: str  # market|climate|regulatory|technology|liquidity
    score: float | None       # 0–100 (higher = more risk)
    label: str                # Low | Medium | High | Critical
    details: dict[str, Any] | None = None
    mitigation: dict[str, Any] | None = None


class FiveDomainRiskResponse(BaseModel):
    portfolio_id: uuid.UUID
    overall_risk_score: float | None
    domains: list[RiskDomainScore]
    monitoring_enabled: bool
    last_monitoring_check: datetime | None
    active_alerts_count: int
    source: str  # "stored" | "computed"


# ── Monitoring Alerts ─────────────────────────────────────────────────────────


class MonitoringAlertResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    portfolio_id: uuid.UUID | None
    project_id: uuid.UUID | None
    alert_type: str
    severity: str
    domain: str
    title: str
    description: str
    source_name: str | None
    is_read: bool
    is_actioned: bool
    action_taken: str | None
    created_at: datetime


class MonitoringAlertListResponse(BaseModel):
    items: list[MonitoringAlertResponse]
    total: int


class AlertResolveRequest(BaseModel):
    action_taken: str


class MitigationRequest(BaseModel):
    domain: str  # market|climate|regulatory|technology|liquidity


class MitigationResponse(BaseModel):
    domain: str
    mitigation_text: str
    key_actions: list[str]
    model_used: str


# ── Audit Trail ───────────────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    changes: dict[str, Any] | None
    ip_address: str | None


class AuditTrailResponse(BaseModel):
    items: list[AuditEntry]
    total: int


# ── Batch Risk Assessment ─────────────────────────────────────────────────────


class BatchRiskRequest(BaseModel):
    project_ids: list[uuid.UUID]
    risk_type: str = "operational"
    severity: str = "medium"
    probability: str = "possible"
    description: str = "Batch risk assessment"


class BatchRiskItem(BaseModel):
    project_id: uuid.UUID
    assessment_id: uuid.UUID | None
    status: str


class BatchRiskResponse(BaseModel):
    queued: int
    failed: int
    items: list[BatchRiskItem]
    errors: list[dict]
