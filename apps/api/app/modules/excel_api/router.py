"""Excel Add-in API router.

All endpoints are authenticated via the ``X-SCR-API-Key`` header (see
``auth.py``) instead of the standard Clerk-based ``get_current_user``
dependency.  Responses are intentionally flat:
``{"value": X, "label": "...", "as_of": "..."}``
so that Excel custom functions can consume them with minimal parsing.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.excel_api.auth import verify_api_key

router = APIRouter(prefix="/excel", tags=["Excel API"])

# ── Helpers ───────────────────────────────────────────────────────────────────

_NOT_FOUND: dict[str, Any] = {
    "value": None,
    "label": "",
    "as_of": None,
    "error": "Not found",
}


def _not_found(label: str = "") -> dict[str, Any]:
    return {"value": None, "label": label, "as_of": None, "error": "Not found"}


# ── Signal Score ──────────────────────────────────────────────────────────────

_DIMENSION_MAP: dict[str, str] = {
    "project_viability": "project_viability_score",
    "financial_planning": "financial_planning_score",
    "team_strength": "team_strength_score",
    "risk_assessment": "risk_assessment_score",
    "esg": "esg_score",
    "market_opportunity": "market_opportunity_score",
}


@router.get("/signal-score/{project_id}")
async def excel_signal_score(
    project_id: uuid.UUID,
    dimension: str | None = None,
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the latest signal score (or a single dimension) for a project.

    Optional query param ``dimension``: ``project_viability``,
    ``financial_planning``, ``team_strength``, ``risk_assessment``, ``esg``,
    ``market_opportunity``.
    """
    from app.models.projects import Project, SignalScore  # noqa: PLC0415

    # Verify project belongs to org
    proj_stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    proj_result = await db.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail=_not_found("Signal Score")["error"])

    # Load latest score (highest version / most recent created_at)
    score_stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc(), SignalScore.created_at.desc())
        .limit(1)
    )
    score_result = await db.execute(score_stmt)
    score = score_result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="No signal score found for this project")

    as_of = score.calculated_at.isoformat() if score.calculated_at else None

    if dimension:
        field = _DIMENSION_MAP.get(dimension.lower())
        if not field:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown dimension '{dimension}'. Valid: {', '.join(_DIMENSION_MAP)}",
            )
        value = getattr(score, field, None)
        return {"value": value, "label": f"Signal Score – {dimension}", "as_of": as_of}

    return {"value": score.overall_score, "label": "Signal Score", "as_of": as_of}


# ── Valuation ─────────────────────────────────────────────────────────────────

_VALUATION_DIRECT: set[str] = {
    "enterprise_value",
    "equity_value",
}

_VALUATION_ASSUMPTIONS: set[str] = {
    "irr",
    "moic",
    "npv",
}


@router.get("/valuation/{project_id}/{metric}")
async def excel_valuation(
    project_id: uuid.UUID,
    metric: str,
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a valuation metric for a project.

    Supported metrics: ``enterprise_value``, ``equity_value``, ``irr``,
    ``moic``, ``npv``, ``ev_per_mw``.
    """
    from app.models.financial import Valuation  # noqa: PLC0415
    from app.models.projects import Project  # noqa: PLC0415

    # Verify project belongs to org
    proj_stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    proj_result = await db.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load latest valuation
    val_stmt = (
        select(Valuation)
        .where(
            Valuation.project_id == project_id,
            Valuation.org_id == org_id,
            Valuation.is_deleted.is_(False),
        )
        .order_by(Valuation.version.desc(), Valuation.created_at.desc())
        .limit(1)
    )
    val_result = await db.execute(val_stmt)
    valuation = val_result.scalar_one_or_none()
    if not valuation:
        raise HTTPException(status_code=404, detail="No valuation found for this project")

    as_of = valuation.valued_at.isoformat() if isinstance(valuation.valued_at, date) else None
    label = f"Valuation – {metric}"

    if metric in _VALUATION_DIRECT:
        raw = getattr(valuation, metric)
        value = float(raw) if raw is not None else None
        return {"value": value, "label": label, "as_of": as_of}

    if metric in _VALUATION_ASSUMPTIONS:
        assumptions = valuation.assumptions or {}
        raw = assumptions.get(metric)
        value = float(raw) if raw is not None else None
        if value is None:
            raise HTTPException(
                status_code=404,
                detail=f"Metric '{metric}' not present in valuation assumptions",
            )
        return {"value": value, "label": label, "as_of": as_of}

    if metric == "ev_per_mw":
        if project.capacity_mw and float(project.capacity_mw) > 0:
            value = float(valuation.enterprise_value) / float(project.capacity_mw)
        else:
            raise HTTPException(
                status_code=422,
                detail="Project capacity_mw is not set — cannot compute EV/MW",
            )
        return {"value": value, "label": label, "as_of": as_of}

    raise HTTPException(
        status_code=422,
        detail=(
            f"Unknown metric '{metric}'. "
            "Valid: enterprise_value, equity_value, irr, moic, npv, ev_per_mw"
        ),
    )


# ── Benchmark ─────────────────────────────────────────────────────────────────

_PERCENTILE_FIELDS: dict[str, str] = {
    "p10": "p10",
    "p25": "p25",
    "p50": "median",
    "p75": "p75",
    "p90": "p90",
}


@router.get("/benchmark/{asset_class}/{metric}")
async def excel_benchmark(
    asset_class: str,
    metric: str,
    geography: str | None = None,
    percentile: str = "p50",
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a benchmark percentile value for the given asset class and metric.

    ``percentile``: ``p10``, ``p25``, ``p50`` (default), ``p75``, ``p90``.
    """
    from app.models.metrics import BenchmarkAggregate  # noqa: PLC0415

    pct_field = _PERCENTILE_FIELDS.get(percentile.lower())
    if not pct_field:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown percentile '{percentile}'. Valid: p10, p25, p50, p75, p90",
        )

    stmt = select(BenchmarkAggregate).where(
        BenchmarkAggregate.asset_class == asset_class,
        BenchmarkAggregate.metric_name == metric,
    )
    if geography:
        stmt = stmt.where(BenchmarkAggregate.geography == geography)

    # Return the most-recently computed row
    stmt = stmt.order_by(BenchmarkAggregate.computed_at.desc()).limit(1)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No benchmark data for asset_class='{asset_class}' metric='{metric}'",
        )

    value = getattr(row, pct_field, None)
    label = f"Benchmark {asset_class} {metric} {percentile}"
    as_of = row.computed_at.isoformat() if row.computed_at else None

    return {"value": value, "label": label, "as_of": as_of}


# ── FX Rate ───────────────────────────────────────────────────────────────────


@router.get("/fx/{base}/{quote}")
async def excel_fx(
    base: str,
    quote: str,
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the most recent FX rate for the given currency pair."""
    from app.models.fx import FXRate  # noqa: PLC0415

    stmt = (
        select(FXRate)
        .where(
            FXRate.base_currency == base.upper(),
            FXRate.quote_currency == quote.upper(),
        )
        .order_by(FXRate.rate_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No FX rate found for {base.upper()}/{quote.upper()}",
        )

    return {
        "value": row.rate,
        "label": f"{base.upper()}/{quote.upper()}",
        "as_of": row.rate_date.isoformat() if row.rate_date else None,
    }


# ── Project KPI ───────────────────────────────────────────────────────────────


@router.get("/project-kpi/{project_id}/{kpi_name}")
async def excel_kpi(
    project_id: uuid.UUID,
    kpi_name: str,
    period: str | None = None,
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a KPI actual value for a project.

    Optional ``period`` filter: e.g. ``2026-Q1``, ``2026-01``.
    """
    from app.models.monitoring import KPIActual  # noqa: PLC0415
    from app.models.projects import Project  # noqa: PLC0415

    # Verify project belongs to org
    proj_stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    proj_result = await db.execute(proj_stmt)
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(KPIActual).where(
        KPIActual.project_id == project_id,
        KPIActual.org_id == org_id,
        KPIActual.kpi_name == kpi_name,
        KPIActual.is_deleted.is_(False),
    )
    if period:
        stmt = stmt.where(KPIActual.period == period)

    # Return the most recent entry
    stmt = stmt.order_by(KPIActual.period.desc(), KPIActual.updated_at.desc()).limit(1)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        detail = (
            f"No KPI '{kpi_name}' found for project"
            + (f" in period '{period}'" if period else "")
        )
        raise HTTPException(status_code=404, detail=detail)

    return {
        "value": row.value,
        "label": f"{kpi_name} ({row.period})",
        "as_of": row.updated_at.isoformat() if row.updated_at else None,
    }


# ── Portfolio Metrics ─────────────────────────────────────────────────────────

_PORTFOLIO_METRIC_MAP: dict[str, str] = {
    "nav": "total_value",
    "irr": "irr_net",      # prefer net IRR; fall back to gross if absent
    "irr_gross": "irr_gross",
    "moic": "moic",
    "tvpi": "tvpi",
    "dpi": "dpi",
}


@router.get("/portfolio/{portfolio_id}/{metric}")
async def excel_portfolio(
    portfolio_id: uuid.UUID,
    metric: str,
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a portfolio-level metric from the latest ``PortfolioMetrics`` snapshot.

    Supported metrics: ``nav``, ``irr``, ``moic``, ``tvpi``, ``dpi``.
    """
    from app.models.investors import Portfolio, PortfolioMetrics  # noqa: PLC0415

    # Verify portfolio belongs to org
    port_stmt = select(Portfolio).where(
        Portfolio.id == portfolio_id,
        Portfolio.org_id == org_id,
        Portfolio.is_deleted.is_(False),
    )
    port_result = await db.execute(port_stmt)
    portfolio = port_result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    field = _PORTFOLIO_METRIC_MAP.get(metric.lower())
    if not field:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown metric '{metric}'. "
                "Valid: nav, irr, irr_gross, moic, tvpi, dpi"
            ),
        )

    metrics_stmt = (
        select(PortfolioMetrics)
        .where(PortfolioMetrics.portfolio_id == portfolio_id)
        .order_by(PortfolioMetrics.as_of_date.desc(), PortfolioMetrics.created_at.desc())
        .limit(1)
    )
    metrics_result = await db.execute(metrics_stmt)
    pm = metrics_result.scalar_one_or_none()
    if not pm:
        raise HTTPException(status_code=404, detail="No portfolio metrics found")

    raw = getattr(pm, field, None)
    # For IRR net, fall back to gross if net is not populated
    if raw is None and metric.lower() == "irr":
        raw = pm.irr_gross

    value = float(raw) if raw is not None else None
    as_of = pm.as_of_date.isoformat() if isinstance(pm.as_of_date, date) else None

    return {"value": value, "label": f"Portfolio {metric.upper()}", "as_of": as_of}


# ── Comparable Transactions ───────────────────────────────────────────────────

_COMP_FIELD_MAP: dict[str, str] = {
    "irr": "equity_irr",
    "project_irr": "project_irr",
    "moic": "ebitda_multiple",   # closest available field
    "ev_per_mw": "ev_per_mw",
    "deal_size": "deal_size_eur",
    "equity_value": "equity_value_eur",
}


@router.get("/comp/{asset_class}/{metric}")
async def excel_comp(
    asset_class: str,
    metric: str,
    geography: str | None = None,
    org_id: uuid.UUID = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the median comparable-transaction value for an asset class and metric.

    Includes both public (``org_id IS NULL``) and org-private comps.
    Optional ``geography`` filter narrows the comparable set.
    """
    from app.models.comps import ComparableTransaction  # noqa: PLC0415

    field = _COMP_FIELD_MAP.get(metric.lower())
    if not field:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown metric '{metric}'. "
                "Valid: irr, project_irr, moic, ev_per_mw, deal_size, equity_value"
            ),
        )

    from sqlalchemy import or_  # noqa: PLC0415

    stmt = select(ComparableTransaction).where(
        ComparableTransaction.asset_type == asset_class,
        ComparableTransaction.is_deleted.is_(False),
        or_(
            ComparableTransaction.org_id.is_(None),
            ComparableTransaction.org_id == org_id,
        ),
    )
    if geography:
        stmt = stmt.where(ComparableTransaction.geography == geography)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    values = [
        float(getattr(r, field))
        for r in rows
        if getattr(r, field) is not None
    ]

    if not values:
        raise HTTPException(
            status_code=404,
            detail=f"No comp data for asset_class='{asset_class}' metric='{metric}'",
        )

    median_val = statistics.median(values)
    label = f"Comp {asset_class} {metric}"

    return {"value": median_val, "label": label, "as_of": None}
