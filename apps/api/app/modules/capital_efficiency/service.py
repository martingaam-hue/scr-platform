"""Capital Efficiency service — computes platform ROI metrics."""

import hashlib
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import CapitalEfficiencyMetrics
from app.modules.capital_efficiency.schemas import (
    BenchmarkResponse,
    EfficiencyBreakdownResponse,
    EfficiencyMetricsResponse,
)

# ── Industry benchmarks ───────────────────────────────────────────────────────

INDUSTRY_BENCHMARKS = {
    "avg_dd_cost_usd": 85_000,
    "avg_time_to_close_days": 127,
    "avg_legal_cost_usd": 45_000,
    "avg_risk_assessment_cost_usd": 25_000,
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_total_savings(metrics: EfficiencyMetricsResponse) -> float:
    return (
        metrics.due_diligence_savings
        + metrics.legal_automation_savings
        + metrics.risk_analytics_savings
        + metrics.tax_credit_value_captured
    )


def _orm_to_response(m: CapitalEfficiencyMetrics) -> EfficiencyMetricsResponse:
    dd = float(m.due_diligence_savings)
    legal = float(m.legal_automation_savings)
    risk = float(m.risk_analytics_savings)
    tax = float(m.tax_credit_value_captured)
    total = dd + legal + risk + tax

    return EfficiencyMetricsResponse(
        id=m.id,
        org_id=m.org_id,
        portfolio_id=m.portfolio_id,
        period_start=m.period_start,
        period_end=m.period_end,
        due_diligence_savings=dd,
        legal_automation_savings=legal,
        risk_analytics_savings=risk,
        tax_credit_value_captured=tax,
        time_saved_hours=float(m.time_saved_hours),
        deals_screened=m.deals_screened,
        deals_closed=m.deals_closed,
        avg_time_to_close_days=float(m.avg_time_to_close_days),
        portfolio_irr_improvement=(
            float(m.portfolio_irr_improvement) if m.portfolio_irr_improvement is not None else None
        ),
        industry_avg_dd_cost=float(m.industry_avg_dd_cost),
        industry_avg_time_to_close=float(m.industry_avg_time_to_close),
        platform_efficiency_score=float(m.platform_efficiency_score),
        total_savings=total,
        breakdown=m.breakdown,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _synthetic_metrics(org_id: uuid.UUID) -> EfficiencyMetricsResponse:
    """Return deterministic synthetic data seeded by org_id hash."""
    # Use first 8 hex chars of org_id hash as a small integer seed for variation
    seed = int(hashlib.md5(str(org_id).encode()).hexdigest()[:8], 16) % 100

    dd_savings = 65_000.0 + seed * 150.0
    legal_savings = 38_000.0 + seed * 80.0
    risk_savings = 22_000.0 + seed * 60.0
    tax_captured = 18_000.0 + seed * 120.0
    total = dd_savings + legal_savings + risk_savings + tax_captured

    time_saved = 240.0 + seed * 2.0
    deals_screened = 42 + (seed % 20)
    deals_closed = 8 + (seed % 5)
    avg_close_days = 72.0 - (seed % 15)
    efficiency_score = min(95.0, 68.0 + seed * 0.3)

    now = datetime.now(timezone.utc)
    period_end = date(now.year, now.month, 1)
    period_start = date(now.year - 1, now.month, 1)

    synthetic_id = uuid.UUID(int=int.from_bytes(str(org_id).encode()[:16], "big") % (2**128))

    return EfficiencyMetricsResponse(
        id=synthetic_id,
        org_id=org_id,
        portfolio_id=None,
        period_start=period_start,
        period_end=period_end,
        due_diligence_savings=round(dd_savings, 2),
        legal_automation_savings=round(legal_savings, 2),
        risk_analytics_savings=round(risk_savings, 2),
        tax_credit_value_captured=round(tax_captured, 2),
        time_saved_hours=round(time_saved, 1),
        deals_screened=deals_screened,
        deals_closed=deals_closed,
        avg_time_to_close_days=round(avg_close_days, 1),
        portfolio_irr_improvement=round(1.8 + seed * 0.02, 2),
        industry_avg_dd_cost=float(INDUSTRY_BENCHMARKS["avg_dd_cost_usd"]),
        industry_avg_time_to_close=float(INDUSTRY_BENCHMARKS["avg_time_to_close_days"]),
        platform_efficiency_score=round(efficiency_score, 1),
        total_savings=round(total, 2),
        breakdown=None,
        created_at=now,
        updated_at=now,
    )


async def _compute_live_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> EfficiencyMetricsResponse | None:
    """Compute efficiency metrics from actual platform activity. Returns None if no data yet."""
    from decimal import Decimal
    from app.models.ai import AITaskLog
    from app.models.deal_flow import DealStageTransition
    from app.models.legal import LegalDocument
    from app.models.financial import TaxCredit
    from app.models.enums import AITaskStatus, TaxCreditQualification
    from sqlalchemy import func

    now = datetime.now(timezone.utc)
    period_end = date(now.year, now.month, 1)
    period_start = date(now.year - 1, now.month, 1)

    # --- Deal metrics from DealStageTransition ---
    trans_result = await db.execute(
        select(func.count(DealStageTransition.id.distinct()))
        .where(DealStageTransition.org_id == org_id)
    )
    deals_screened = trans_result.scalar() or 0

    closed_result = await db.execute(
        select(func.count(DealStageTransition.project_id.distinct()))
        .where(
            DealStageTransition.org_id == org_id,
            DealStageTransition.to_stage == "closed",
        )
    )
    deals_closed = closed_result.scalar() or 0

    if deals_screened == 0:
        return None  # No activity yet — caller will use synthetic

    # --- AI task time savings (2h per completed task) ---
    ai_result = await db.execute(
        select(func.count(AITaskLog.id))
        .where(
            AITaskLog.org_id == org_id,
            AITaskLog.status == AITaskStatus.COMPLETED,
        )
    )
    ai_tasks_done = ai_result.scalar() or 0
    time_saved_hours = round(ai_tasks_done * 2.0, 1)

    # --- Legal automation savings ---
    legal_result = await db.execute(
        select(func.count(LegalDocument.id))
        .where(LegalDocument.org_id == org_id)
    )
    legal_docs = legal_result.scalar() or 0
    legal_savings = round(legal_docs * 3_000.0, 2)  # ~$3k avg legal doc cost saved

    # --- Tax credit value captured ---
    tax_result = await db.execute(
        select(func.coalesce(func.sum(TaxCredit.claimed_value), 0))
        .where(
            TaxCredit.org_id == org_id,
            TaxCredit.qualification == TaxCreditQualification.CLAIMED,
        )
    )
    tax_captured = float(tax_result.scalar() or 0)

    # --- DD savings: deals_screened * industry_avg reduced by platform efficiency ---
    dd_savings = round(deals_screened * INDUSTRY_BENCHMARKS["avg_dd_cost_usd"] * 0.45, 2)
    risk_savings = round(deals_screened * INDUSTRY_BENCHMARKS["avg_risk_assessment_cost_usd"] * 0.4, 2)

    # --- Avg days to close ---
    if deals_closed > 0:
        avg_close_result = await db.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        func.max(DealStageTransition.created_at) - func.min(DealStageTransition.created_at)
                    ) / 86400
                )
            )
            .where(DealStageTransition.org_id == org_id)
            .group_by(DealStageTransition.project_id)
            .having(func.bool_or(DealStageTransition.to_stage == "closed"))
        )
        avg_close_days = float(avg_close_result.scalar() or INDUSTRY_BENCHMARKS["avg_time_to_close_days"])
    else:
        avg_close_days = float(INDUSTRY_BENCHMARKS["avg_time_to_close_days"])

    total = dd_savings + legal_savings + risk_savings + tax_captured
    efficiency_score = min(95.0, 50.0 + (deals_closed / max(deals_screened, 1)) * 30.0 + (ai_tasks_done / max(deals_screened, 1)) * 15.0)

    synthetic_id = uuid.UUID(int=int.from_bytes(str(org_id).encode()[:16], "big") % (2**128))

    return EfficiencyMetricsResponse(
        id=synthetic_id,
        org_id=org_id,
        portfolio_id=None,
        period_start=period_start,
        period_end=period_end,
        due_diligence_savings=dd_savings,
        legal_automation_savings=legal_savings,
        risk_analytics_savings=risk_savings,
        tax_credit_value_captured=tax_captured,
        time_saved_hours=time_saved_hours,
        deals_screened=deals_screened,
        deals_closed=deals_closed,
        avg_time_to_close_days=round(avg_close_days, 1),
        portfolio_irr_improvement=None,
        industry_avg_dd_cost=float(INDUSTRY_BENCHMARKS["avg_dd_cost_usd"]),
        industry_avg_time_to_close=float(INDUSTRY_BENCHMARKS["avg_time_to_close_days"]),
        platform_efficiency_score=round(efficiency_score, 1),
        total_savings=round(total, 2),
        breakdown=None,
        created_at=now,
        updated_at=now,
    )


# ── Service functions ─────────────────────────────────────────────────────────


async def get_current_metrics(
    db: AsyncSession,
    org_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
) -> EfficiencyMetricsResponse:
    """Get the most recent capital efficiency metrics for an org."""
    stmt = (
        select(CapitalEfficiencyMetrics)
        .where(CapitalEfficiencyMetrics.org_id == org_id)
        .order_by(CapitalEfficiencyMetrics.period_end.desc())
        .limit(1)
    )
    if portfolio_id is not None:
        stmt = stmt.where(CapitalEfficiencyMetrics.portfolio_id == portfolio_id)

    result = await db.execute(stmt)
    metrics = result.scalar_one_or_none()

    if metrics is None:
        live = await _compute_live_metrics(db, org_id)
        return live if live is not None else _synthetic_metrics(org_id)

    return _orm_to_response(metrics)


async def get_breakdown(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> EfficiencyBreakdownResponse:
    """Build a savings breakdown with vs-industry context for each category."""
    metrics = await get_current_metrics(db, org_id)

    total = metrics.total_savings or 1.0  # avoid division by zero

    def vs_industry_label(platform_val: float, industry_val: float) -> str:
        if industry_val <= 0:
            return "N/A"
        saved_pct = round((1.0 - platform_val / industry_val) * 100, 1)
        if saved_pct > 0:
            return f"saved {saved_pct}% vs industry"
        else:
            return f"{abs(saved_pct)}% above industry avg"

    categories = [
        {
            "name": "Due Diligence",
            "value": metrics.due_diligence_savings,
            "percentage": round(metrics.due_diligence_savings / total * 100, 1),
            "vs_industry": vs_industry_label(
                metrics.due_diligence_savings,
                INDUSTRY_BENCHMARKS["avg_dd_cost_usd"],
            ),
        },
        {
            "name": "Legal Automation",
            "value": metrics.legal_automation_savings,
            "percentage": round(metrics.legal_automation_savings / total * 100, 1),
            "vs_industry": vs_industry_label(
                metrics.legal_automation_savings,
                INDUSTRY_BENCHMARKS["avg_legal_cost_usd"],
            ),
        },
        {
            "name": "Risk Analytics",
            "value": metrics.risk_analytics_savings,
            "percentage": round(metrics.risk_analytics_savings / total * 100, 1),
            "vs_industry": vs_industry_label(
                metrics.risk_analytics_savings,
                INDUSTRY_BENCHMARKS["avg_risk_assessment_cost_usd"],
            ),
        },
        {
            "name": "Tax Credits",
            "value": metrics.tax_credit_value_captured,
            "percentage": round(metrics.tax_credit_value_captured / total * 100, 1),
            "vs_industry": "platform advantage",
        },
    ]

    totals = {
        "total_savings": metrics.total_savings,
        "time_saved_hours": metrics.time_saved_hours,
        "deals_closed": float(metrics.deals_closed),
        "platform_efficiency_score": metrics.platform_efficiency_score,
    }

    return EfficiencyBreakdownResponse(categories=categories, totals=totals)


async def get_benchmark(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> BenchmarkResponse:
    """Compare platform metrics vs industry averages and compute percentile."""
    metrics = await get_current_metrics(db, org_id)

    platform = {
        "dd_cost": metrics.due_diligence_savings,
        "time_to_close_days": metrics.avg_time_to_close_days,
        "legal_cost": metrics.legal_automation_savings,
        "risk_assessment_cost": metrics.risk_analytics_savings,
        "efficiency_score": metrics.platform_efficiency_score,
    }

    industry_avg = {
        "dd_cost": float(INDUSTRY_BENCHMARKS["avg_dd_cost_usd"]),
        "time_to_close_days": float(INDUSTRY_BENCHMARKS["avg_time_to_close_days"]),
        "legal_cost": float(INDUSTRY_BENCHMARKS["avg_legal_cost_usd"]),
        "risk_assessment_cost": float(INDUSTRY_BENCHMARKS["avg_risk_assessment_cost_usd"]),
        "efficiency_score": 50.0,  # industry midpoint
    }

    # Determine percentile based on efficiency score
    eff = metrics.platform_efficiency_score
    if eff >= 80:
        percentile = 90
    elif eff >= 70:
        percentile = 75
    elif eff >= 55:
        percentile = 60
    elif eff >= 40:
        percentile = 50
    else:
        percentile = 30

    # Dimensions where platform is better (lower is better for cost/time; higher for score)
    outperforming: list[str] = []
    if platform["dd_cost"] < industry_avg["dd_cost"]:
        outperforming.append("Due Diligence Cost")
    if platform["time_to_close_days"] < industry_avg["time_to_close_days"]:
        outperforming.append("Time to Close")
    if platform["legal_cost"] < industry_avg["legal_cost"]:
        outperforming.append("Legal Cost")
    if platform["risk_assessment_cost"] < industry_avg["risk_assessment_cost"]:
        outperforming.append("Risk Assessment Cost")
    if platform["efficiency_score"] > industry_avg["efficiency_score"]:
        outperforming.append("Platform Efficiency Score")

    return BenchmarkResponse(
        platform=platform,
        industry_avg=industry_avg,
        percentile=percentile,
        outperforming=outperforming,
    )
