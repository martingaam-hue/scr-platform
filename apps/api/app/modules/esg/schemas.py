"""ESG Impact Dashboard — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Request / Upsert ─────────────────────────────────────────────────────────


class ESGMetricsUpsertRequest(BaseModel):
    period: str  # "2024-Q4"

    # Environmental
    carbon_footprint_tco2e: float | None = None
    carbon_avoided_tco2e: float | None = None
    renewable_energy_mwh: float | None = None
    water_usage_cubic_m: float | None = None
    waste_diverted_tonnes: float | None = None
    biodiversity_score: float | None = None

    # Social
    jobs_created: int | None = None
    jobs_supported: int | None = None
    local_procurement_pct: float | None = None
    community_investment_eur: float | None = None
    gender_diversity_pct: float | None = None
    health_safety_incidents: int | None = None

    # Governance
    board_independence_pct: float | None = None
    audit_completed: bool = False
    esg_reporting_standard: str | None = None

    # EU Taxonomy
    taxonomy_eligible: bool = False
    taxonomy_aligned: bool = False
    taxonomy_activity: str | None = None

    # SFDR
    sfdr_article: int | None = None  # 6, 8, or 9

    # SDG contributions
    sdg_contributions: dict | None = None

    # AI narrative (optionally provided by client; otherwise generated)
    esg_narrative: str | None = None

    # Flag: if True, regenerate AI narrative even if one exists
    regenerate_narrative: bool = False


# ── Single project response ───────────────────────────────────────────────────


class ESGMetricsResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    org_id: uuid.UUID
    period: str

    carbon_footprint_tco2e: float | None
    carbon_avoided_tco2e: float | None
    renewable_energy_mwh: float | None
    water_usage_cubic_m: float | None
    waste_diverted_tonnes: float | None
    biodiversity_score: float | None

    jobs_created: int | None
    jobs_supported: int | None
    local_procurement_pct: float | None
    community_investment_eur: float | None
    gender_diversity_pct: float | None
    health_safety_incidents: int | None

    board_independence_pct: float | None
    audit_completed: bool
    esg_reporting_standard: str | None

    taxonomy_eligible: bool
    taxonomy_aligned: bool
    taxonomy_activity: str | None

    sfdr_article: int | None
    sdg_contributions: dict | None
    esg_narrative: str | None

    created_at: datetime
    updated_at: datetime


class ESGMetricsHistoryResponse(BaseModel):
    project_id: uuid.UUID
    records: list[ESGMetricsResponse]


# ── Portfolio summary ─────────────────────────────────────────────────────────


class SFDRDistribution(BaseModel):
    article_6: int
    article_8: int
    article_9: int
    unclassified: int


class TopSDG(BaseModel):
    sdg_id: int
    name: str
    project_count: int


class CarbonTrendPoint(BaseModel):
    period: str
    total_carbon_avoided_tco2e: float
    total_carbon_footprint_tco2e: float


class ESGPortfolioTotals(BaseModel):
    total_projects: int
    total_carbon_avoided_tco2e: float
    total_renewable_energy_mwh: float
    total_jobs_created: int
    taxonomy_aligned_count: int
    taxonomy_aligned_pct: float


class ESGPortfolioSummaryResponse(BaseModel):
    totals: ESGPortfolioTotals
    sfdr_distribution: SFDRDistribution
    taxonomy_alignment_pct: float
    top_sdgs: list[TopSDG]
    carbon_trend: list[CarbonTrendPoint]
    # Per-project rows for the table (latest period per project)
    project_rows: list[ESGMetricsResponse]
