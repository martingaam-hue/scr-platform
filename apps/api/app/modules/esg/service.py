"""ESG Impact Dashboard service."""

from __future__ import annotations

import io
import json
import time
import uuid
from collections import defaultdict
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.esg import ESGMetrics
from app.modules.esg.schemas import (
    CarbonTrendPoint,
    ESGMetricsResponse,
    ESGPortfolioSummaryResponse,
    ESGPortfolioTotals,
    SFDRDistribution,
    TopSDG,
)

logger = structlog.get_logger()

# SDG display names (1-17)
SDG_NAMES: dict[int, str] = {
    1: "No Poverty",
    2: "Zero Hunger",
    3: "Good Health",
    4: "Quality Education",
    5: "Gender Equality",
    6: "Clean Water",
    7: "Affordable Energy",
    8: "Decent Work",
    9: "Industry & Innovation",
    10: "Reduced Inequalities",
    11: "Sustainable Cities",
    12: "Responsible Consumption",
    13: "Climate Action",
    14: "Life Below Water",
    15: "Life on Land",
    16: "Peace & Justice",
    17: "Partnerships",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_response(m: ESGMetrics) -> ESGMetricsResponse:
    return ESGMetricsResponse(
        id=m.id,
        project_id=m.project_id,
        org_id=m.org_id,
        period=m.period,
        carbon_footprint_tco2e=m.carbon_footprint_tco2e,
        carbon_avoided_tco2e=m.carbon_avoided_tco2e,
        renewable_energy_mwh=m.renewable_energy_mwh,
        water_usage_cubic_m=m.water_usage_cubic_m,
        waste_diverted_tonnes=m.waste_diverted_tonnes,
        biodiversity_score=m.biodiversity_score,
        jobs_created=m.jobs_created,
        jobs_supported=m.jobs_supported,
        local_procurement_pct=m.local_procurement_pct,
        community_investment_eur=m.community_investment_eur,
        gender_diversity_pct=m.gender_diversity_pct,
        health_safety_incidents=m.health_safety_incidents,
        board_independence_pct=m.board_independence_pct,
        audit_completed=m.audit_completed,
        esg_reporting_standard=m.esg_reporting_standard,
        taxonomy_eligible=m.taxonomy_eligible,
        taxonomy_aligned=m.taxonomy_aligned,
        taxonomy_activity=m.taxonomy_activity,
        sfdr_article=m.sfdr_article,
        sdg_contributions=m.sdg_contributions,
        esg_narrative=m.esg_narrative,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── Portfolio summary ─────────────────────────────────────────────────────────


async def get_portfolio_esg_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
    period: str | None = None,
) -> ESGPortfolioSummaryResponse:
    """Aggregate ESG metrics across all projects in the org (optionally filtered)."""
    stmt = select(ESGMetrics).where(
        ESGMetrics.org_id == org_id,
        ESGMetrics.is_deleted.is_(False),
    )
    if period:
        stmt = stmt.where(ESGMetrics.period == period)

    # portfolio_id filter: join to PortfolioHolding if provided
    # For now we simply filter by org — portfolio filtering can be layered in later
    # when the join to portfolio holdings is desired.

    stmt = stmt.order_by(ESGMetrics.period.asc())
    result = await db.execute(stmt)
    all_metrics: list[ESGMetrics] = list(result.scalars().all())

    # ── Totals ────────────────────────────────────────────────────────────────
    # For each project, take the latest record when computing totals
    latest_by_project: dict[uuid.UUID, ESGMetrics] = {}
    for m in all_metrics:
        existing = latest_by_project.get(m.project_id)
        if existing is None or m.period > existing.period:
            latest_by_project[m.project_id] = m

    latest = list(latest_by_project.values())
    total_projects = len(latest)

    total_carbon_avoided = sum(
        (m.carbon_avoided_tco2e or 0.0) for m in latest
    )
    total_renewable_energy = sum(
        (m.renewable_energy_mwh or 0.0) for m in latest
    )
    total_jobs = sum((m.jobs_created or 0) for m in latest)
    taxonomy_aligned_count = sum(1 for m in latest if m.taxonomy_aligned)
    taxonomy_aligned_pct = (
        (taxonomy_aligned_count / total_projects * 100.0) if total_projects else 0.0
    )

    totals = ESGPortfolioTotals(
        total_projects=total_projects,
        total_carbon_avoided_tco2e=round(total_carbon_avoided, 2),
        total_renewable_energy_mwh=round(total_renewable_energy, 2),
        total_jobs_created=total_jobs,
        taxonomy_aligned_count=taxonomy_aligned_count,
        taxonomy_aligned_pct=round(taxonomy_aligned_pct, 1),
    )

    # ── SFDR distribution ─────────────────────────────────────────────────────
    sfdr_counts: dict[int | None, int] = defaultdict(int)
    for m in latest:
        sfdr_counts[m.sfdr_article] += 1

    sfdr_distribution = SFDRDistribution(
        article_6=sfdr_counts.get(6, 0),
        article_8=sfdr_counts.get(8, 0),
        article_9=sfdr_counts.get(9, 0),
        unclassified=sfdr_counts.get(None, 0),
    )

    # ── SDG contributions ─────────────────────────────────────────────────────
    sdg_project_counts: dict[int, int] = defaultdict(int)
    for m in latest:
        if m.sdg_contributions:
            for sdg_key in m.sdg_contributions:
                try:
                    sdg_id = int(sdg_key)
                    sdg_project_counts[sdg_id] += 1
                except (ValueError, TypeError):
                    pass

    top_sdgs: list[TopSDG] = sorted(
        [
            TopSDG(
                sdg_id=sdg_id,
                name=SDG_NAMES.get(sdg_id, f"SDG {sdg_id}"),
                project_count=count,
            )
            for sdg_id, count in sdg_project_counts.items()
        ],
        key=lambda x: x.project_count,
        reverse=True,
    )[:10]

    # ── Carbon trend (all periods, sum per period) ─────────────────────────────
    period_carbon: dict[str, dict[str, float]] = defaultdict(
        lambda: {"avoided": 0.0, "footprint": 0.0}
    )
    for m in all_metrics:
        period_carbon[m.period]["avoided"] += m.carbon_avoided_tco2e or 0.0
        period_carbon[m.period]["footprint"] += m.carbon_footprint_tco2e or 0.0

    carbon_trend: list[CarbonTrendPoint] = [
        CarbonTrendPoint(
            period=p,
            total_carbon_avoided_tco2e=round(vals["avoided"], 2),
            total_carbon_footprint_tco2e=round(vals["footprint"], 2),
        )
        for p, vals in sorted(period_carbon.items())
    ]

    # ── Project rows (latest per project) ─────────────────────────────────────
    project_rows = [_to_response(m) for m in sorted(latest, key=lambda m: m.period, reverse=True)]

    return ESGPortfolioSummaryResponse(
        totals=totals,
        sfdr_distribution=sfdr_distribution,
        taxonomy_alignment_pct=round(taxonomy_aligned_pct, 1),
        top_sdgs=top_sdgs,
        carbon_trend=carbon_trend,
        project_rows=project_rows,
    )


# ── Project metrics history ───────────────────────────────────────────────────


async def get_project_esg_metrics(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> list[ESGMetricsResponse]:
    """Return all ESG metric records for a project, newest first."""
    stmt = (
        select(ESGMetrics)
        .where(
            ESGMetrics.project_id == project_id,
            ESGMetrics.org_id == org_id,
            ESGMetrics.is_deleted.is_(False),
        )
        .order_by(ESGMetrics.period.desc())
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())
    return [_to_response(m) for m in records]


# ── Upsert ────────────────────────────────────────────────────────────────────


async def upsert_esg_metrics(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    data: Any,  # ESGMetricsUpsertRequest
) -> ESGMetrics:
    """Create or update ESG metrics for a project+period."""
    stmt = select(ESGMetrics).where(
        ESGMetrics.project_id == project_id,
        ESGMetrics.org_id == org_id,
        ESGMetrics.period == data.period,
        ESGMetrics.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    metrics = result.scalar_one_or_none()

    if metrics is None:
        metrics = ESGMetrics(
            project_id=project_id,
            org_id=org_id,
            period=data.period,
        )
        db.add(metrics)

    # Update all provided fields
    update_fields = data.model_dump(exclude={"period", "regenerate_narrative"}, exclude_unset=True)
    for field, value in update_fields.items():
        if field != "esg_narrative" or not data.regenerate_narrative:
            setattr(metrics, field, value)

    # Generate AI narrative if requested or if none exists
    if data.regenerate_narrative or (metrics.esg_narrative is None and not data.esg_narrative):
        try:
            metrics_dict = data.model_dump(exclude={"regenerate_narrative"})
            metrics_dict["project_id"] = str(project_id)
            narrative = await generate_esg_narrative(metrics_dict)
            metrics.esg_narrative = narrative
        except Exception as exc:
            logger.warning("esg_narrative_generation_failed", error=str(exc))

    # Record ESG metric snapshot (best-effort, uses savepoint to not abort outer tx)
    try:
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        async with db.begin_nested():
            svc = MetricSnapshotService(db)
            fields = data.model_dump(exclude={"period", "regenerate_narrative", "esg_narrative"}, exclude_unset=True)
            esg_value = fields.get("carbon_reduction_tons") or fields.get("renewable_energy_kwh") or 0.0
            await svc.record_snapshot(
                org_id=org_id,
                entity_type="project",
                entity_id=project_id,
                metric_name="esg_score",
                value=float(esg_value),
                metadata={"period": data.period, "fields": list(fields.keys())},
                trigger_event="esg_metrics_updated",
            )
    except Exception:
        pass

    return metrics


# ── AI narrative ──────────────────────────────────────────────────────────────


async def generate_esg_narrative(metrics: dict) -> str:
    """Call AI gateway to generate an ESG performance narrative."""
    if not settings.AI_GATEWAY_API_KEY:
        logger.warning("ai_gateway_key_not_set_for_esg_narrative")
        return ""

    prompt = _build_narrative_prompt(metrics)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "task_type": "generate_esg_narrative",
                    "temperature": 0.5,
                    "max_tokens": 1024,
                    "org_id": str(metrics.get("org_id", "system")),
                    "user_id": "system",
                },
                headers={
                    "Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content", "")

            # Try validated_data first, then parse raw content
            validated = data.get("validated_data")
            if validated and isinstance(validated, dict) and validated.get("narrative"):
                return str(validated["narrative"])

            # Fallback: parse JSON from content
            try:
                parsed = json.loads(content)
                return str(parsed.get("narrative", content))
            except (json.JSONDecodeError, AttributeError):
                return content

    except Exception as exc:
        logger.warning("esg_narrative_ai_call_failed", error=str(exc))
        return ""


def _build_narrative_prompt(metrics: dict) -> str:
    period = metrics.get("period", "N/A")
    carbon_avoided = metrics.get("carbon_avoided_tco2e")
    renewable = metrics.get("renewable_energy_mwh")
    jobs = metrics.get("jobs_created")
    taxonomy_aligned = metrics.get("taxonomy_aligned", False)
    sfdr = metrics.get("sfdr_article")
    sdgs = metrics.get("sdg_contributions") or {}

    sdg_list = ", ".join(
        f"SDG {k} ({v.get('contribution_level', 'contributing')})"
        for k, v in sdgs.items()
    ) if sdgs else "None specified"

    return f"""You are an ESG analyst generating a performance summary for an impact investment project.

Period: {period}
Environmental:
  - Carbon avoided: {carbon_avoided} tCO2e
  - Renewable energy generated: {renewable} MWh
  - Carbon footprint: {metrics.get('carbon_footprint_tco2e')} tCO2e
  - Water usage: {metrics.get('water_usage_cubic_m')} m³
  - Waste diverted: {metrics.get('waste_diverted_tonnes')} tonnes
  - Biodiversity score: {metrics.get('biodiversity_score')}/100

Social:
  - Jobs created: {jobs}
  - Jobs supported: {metrics.get('jobs_supported')}
  - Local procurement: {metrics.get('local_procurement_pct')}%
  - Community investment: EUR {metrics.get('community_investment_eur')}
  - Gender diversity: {metrics.get('gender_diversity_pct')}%
  - Health & safety incidents: {metrics.get('health_safety_incidents')}

Governance:
  - Board independence: {metrics.get('board_independence_pct')}%
  - Audit completed: {metrics.get('audit_completed')}
  - Reporting standard: {metrics.get('esg_reporting_standard')}

Regulatory:
  - EU Taxonomy aligned: {taxonomy_aligned}
  - SFDR Article: {sfdr}
  - SDG contributions: {sdg_list}

Write a concise, professional ESG performance narrative (3-4 paragraphs) for this project.
Highlight key achievements, note areas for improvement, and comment on regulatory alignment.

Respond ONLY with valid JSON (no markdown, no extra text):
{{
    "narrative": "<full narrative text>",
    "key_achievements": ["<achievement1>", "<achievement2>"],
    "areas_for_improvement": ["<area1>", "<area2>"]
}}"""


# ── CSV export ────────────────────────────────────────────────────────────────


async def export_portfolio_csv(
    db: AsyncSession,
    org_id: uuid.UUID,
    period: str | None = None,
) -> str:
    """Return ESG data as CSV string."""
    stmt = select(ESGMetrics).where(
        ESGMetrics.org_id == org_id,
        ESGMetrics.is_deleted.is_(False),
    )
    if period:
        stmt = stmt.where(ESGMetrics.period == period)
    stmt = stmt.order_by(ESGMetrics.period.desc())
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    headers = [
        "project_id", "period",
        "carbon_footprint_tco2e", "carbon_avoided_tco2e", "renewable_energy_mwh",
        "water_usage_cubic_m", "waste_diverted_tonnes", "biodiversity_score",
        "jobs_created", "jobs_supported", "local_procurement_pct",
        "community_investment_eur", "gender_diversity_pct", "health_safety_incidents",
        "board_independence_pct", "audit_completed", "esg_reporting_standard",
        "taxonomy_eligible", "taxonomy_aligned", "taxonomy_activity",
        "sfdr_article",
    ]

    output = io.StringIO()
    output.write(",".join(headers) + "\n")
    for m in records:
        row = [
            str(m.project_id), m.period,
            str(m.carbon_footprint_tco2e or ""), str(m.carbon_avoided_tco2e or ""),
            str(m.renewable_energy_mwh or ""), str(m.water_usage_cubic_m or ""),
            str(m.waste_diverted_tonnes or ""), str(m.biodiversity_score or ""),
            str(m.jobs_created or ""), str(m.jobs_supported or ""),
            str(m.local_procurement_pct or ""), str(m.community_investment_eur or ""),
            str(m.gender_diversity_pct or ""), str(m.health_safety_incidents or ""),
            str(m.board_independence_pct or ""), str(m.audit_completed),
            m.esg_reporting_standard or "",
            str(m.taxonomy_eligible), str(m.taxonomy_aligned),
            m.taxonomy_activity or "", str(m.sfdr_article or ""),
        ]
        output.write(",".join(row) + "\n")

    return output.getvalue()
