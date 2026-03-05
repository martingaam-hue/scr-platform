"""Alley Pipeline Analytics service — aggregate view of org's project portfolio."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.dataroom import Document
from app.models.projects import Project, SignalScore
from app.modules.alley.analytics.schemas import (
    DocumentCompletenessItem,
    PipelineOverview,
    ProjectCompareItem,
    RiskHeatmapCell,
    ScoreDistributionItem,
    StageDistributionItem,
)

logger = structlog.get_logger()

# Expected document types per asset type (simplified)
_EXPECTED_DOCS: dict[str, list[str]] = {
    "solar": [
        "financial_model",
        "land_agreement",
        "grid_connection",
        "epc_contract",
        "environmental_impact",
    ],
    "wind": [
        "financial_model",
        "land_agreement",
        "grid_connection",
        "epc_contract",
        "environmental_impact",
        "wind_resource_assessment",
    ],
    "hydro": [
        "financial_model",
        "water_rights",
        "grid_connection",
        "environmental_impact",
        "feasibility_study",
    ],
    "default": ["financial_model", "land_agreement", "environmental_impact", "feasibility_study"],
}


async def _get_all_projects(db: AsyncSession, org_id: uuid.UUID) -> list[Project]:
    stmt = select(Project).where(Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_score(db: AsyncSession, project_id: uuid.UUID) -> SignalScore | None:
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_overview(db: AsyncSession, org_id: uuid.UUID) -> PipelineOverview:
    projects = await _get_all_projects(db, org_id)
    stage_counts: dict[str, int] = {}
    total_mw = 0.0
    total_value = 0.0
    currency = "EUR"
    scored = 0
    total_score = 0

    for p in projects:
        stage = p.stage.value if p.stage else "unknown"
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        total_mw += float(p.capacity_mw or 0)
        total_value += float(p.total_investment_required or 0)
        if p.currency:
            currency = p.currency
        score = await _get_score(db, p.id)
        if score:
            scored += 1
            total_score += score.overall_score

    return PipelineOverview(
        total_projects=len(projects),
        total_mw=round(total_mw, 1),
        total_value=round(total_value, 0),
        currency=currency,
        scored_projects=scored,
        avg_score=round(total_score / scored, 1) if scored > 0 else 0.0,
        stage_counts=stage_counts,
    )


async def get_stage_distribution(
    db: AsyncSession, org_id: uuid.UUID
) -> list[StageDistributionItem]:
    projects = await _get_all_projects(db, org_id)
    buckets: dict[str, dict] = {}
    for p in projects:
        stage = p.stage.value if p.stage else "unknown"
        if stage not in buckets:
            buckets[stage] = {"count": 0, "total_mw": 0.0, "total_value": 0.0}
        buckets[stage]["count"] += 1
        buckets[stage]["total_mw"] += float(p.capacity_mw or 0)
        buckets[stage]["total_value"] += float(p.total_investment_required or 0)
    return [StageDistributionItem(stage=stage, **data) for stage, data in buckets.items()]


async def get_score_distribution(
    db: AsyncSession, org_id: uuid.UUID
) -> list[ScoreDistributionItem]:
    projects = await _get_all_projects(db, org_id)
    counts = {f"{i}-{i+20}": 0 for i in range(0, 100, 20)}
    for p in projects:
        score = await _get_score(db, p.id)
        if score:
            bucket_start = (score.overall_score // 20) * 20
            key = f"{bucket_start}-{min(bucket_start + 20, 100)}"
            counts[key] = counts.get(key, 0) + 1
    return [ScoreDistributionItem(bucket=k, count=v) for k, v in counts.items()]


async def get_risk_heatmap(db: AsyncSession, org_id: uuid.UUID) -> list[RiskHeatmapCell]:
    projects = await _get_all_projects(db, org_id)
    cells = []
    for p in projects:
        score = await _get_score(db, p.id)
        if not score:
            continue
        # Invert dimension scores to get risk levels (lower score = higher risk)
        tech = 100 - score.project_viability_score
        fin = 100 - score.financial_planning_score
        reg = 100 - score.risk_assessment_score
        esg = 100 - score.esg_score
        mkt = 100 - score.market_opportunity_score
        avg_risk = (tech + fin + reg + esg + mkt) // 5
        overall_level = (
            "critical"
            if avg_risk > 75
            else "high"
            if avg_risk > 55
            else "medium"
            if avg_risk > 35
            else "low"
        )
        cells.append(
            RiskHeatmapCell(
                project_id=p.id,
                project_name=p.name,
                technical=tech,
                financial=fin,
                regulatory=reg,
                esg=esg,
                market=mkt,
                overall_risk_level=overall_level,
            )
        )
    return cells


async def get_document_completeness(
    db: AsyncSession, org_id: uuid.UUID
) -> list[DocumentCompletenessItem]:
    projects = await _get_all_projects(db, org_id)
    items = []
    for p in projects:
        asset_type = p.project_type.value if p.project_type else "default"
        expected = _EXPECTED_DOCS.get(asset_type, _EXPECTED_DOCS["default"])

        doc_result = await db.execute(
            select(Document).where(
                Document.project_id == p.id,
                Document.is_deleted.is_(False),
            )
        )
        docs = doc_result.scalars().all()
        doc_types_uploaded = {d.document_type.value if d.document_type else "" for d in docs}

        uploaded_count = len(docs)
        expected_count = len(expected)
        missing = [t for t in expected if t not in doc_types_uploaded]
        pct = (
            max(0, min(100, int(((expected_count - len(missing)) / expected_count) * 100)))
            if expected_count > 0
            else 0
        )

        items.append(
            DocumentCompletenessItem(
                project_id=p.id,
                project_name=p.name,
                uploaded_count=uploaded_count,
                expected_count=expected_count,
                completeness_pct=pct,
                missing_types=missing,
            )
        )
    return items


async def compare_projects(
    db: AsyncSession, org_id: uuid.UUID, project_ids: list[uuid.UUID]
) -> list[ProjectCompareItem]:
    items = []
    for pid in project_ids[:5]:  # max 5
        stmt = select(Project).where(Project.id == pid, Project.is_deleted.is_(False))
        stmt = tenant_filter(stmt, org_id, Project)
        result = await db.execute(stmt)
        p = result.scalar_one_or_none()
        if not p:
            continue
        score = await _get_score(db, p.id)
        risk_level = "unknown"
        if score:
            avg_risk = 100 - score.overall_score
            risk_level = (
                "critical"
                if avg_risk > 75
                else "high"
                if avg_risk > 55
                else "medium"
                if avg_risk > 35
                else "low"
            )
        items.append(
            ProjectCompareItem(
                project_id=p.id,
                project_name=p.name,
                stage=p.stage.value if p.stage else "unknown",
                asset_type=p.project_type.value if p.project_type else "unknown",
                geography=p.geography_country or "",
                overall_score=score.overall_score if score else 0,
                total_investment=float(p.total_investment_required or 0),
                currency=p.currency or "EUR",
                capacity_mw=float(p.capacity_mw or 0),
                risk_level=risk_level,
            )
        )
    return items
