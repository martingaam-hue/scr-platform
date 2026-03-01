"""Business logic for Portfolio module.

Financial calculations (IRR, MOIC, TVPI, DPI, RVPI) use deterministic Python
via numpy-financial. LLMs are NEVER used for financial calculations.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant import tenant_filter
from app.models.enums import (
    AssetType,
    HoldingStatus,
    PortfolioStatus,
    PortfolioStrategy,
)
from app.models.investors import Portfolio, PortfolioHolding, PortfolioMetrics
from app.models.projects import Project
from app.schemas.auth import CurrentUser


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _get_portfolio_or_raise(
    db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID
) -> Portfolio:
    stmt = select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.is_deleted.is_(False)
    )
    stmt = tenant_filter(stmt, org_id, Portfolio)
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise LookupError(f"Portfolio {portfolio_id} not found")
    return portfolio


async def get_latest_metrics(
    db: AsyncSession, portfolio_id: uuid.UUID
) -> PortfolioMetrics | None:
    stmt = (
        select(PortfolioMetrics)
        .where(PortfolioMetrics.portfolio_id == portfolio_id)
        .order_by(PortfolioMetrics.as_of_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Portfolio CRUD ──────────────────────────────────────────────────────────


async def list_portfolios(
    db: AsyncSession, org_id: uuid.UUID
) -> list[Portfolio]:
    stmt = (
        select(Portfolio)
        .where(Portfolio.is_deleted.is_(False))
        .order_by(Portfolio.created_at.desc())
    )
    stmt = tenant_filter(stmt, org_id, Portfolio)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_portfolio(
    db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID
) -> Portfolio:
    return await _get_portfolio_or_raise(db, portfolio_id, org_id)


async def create_portfolio(
    db: AsyncSession,
    current_user: CurrentUser,
    *,
    name: str,
    description: str = "",
    strategy: PortfolioStrategy,
    fund_type,
    vintage_year: int | None = None,
    target_aum: Decimal,
    current_aum: Decimal = Decimal("0"),
    currency: str = "USD",
    sfdr_classification=None,
) -> Portfolio:
    from app.models.enums import SFDRClassification

    portfolio = Portfolio(
        org_id=current_user.org_id,
        name=name,
        description=description,
        strategy=strategy,
        fund_type=fund_type,
        vintage_year=vintage_year,
        target_aum=target_aum,
        current_aum=current_aum,
        currency=currency,
        sfdr_classification=sfdr_classification or SFDRClassification.NOT_APPLICABLE,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    await db.commit()
    return portfolio


async def update_portfolio(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
    **kwargs,
) -> Portfolio:
    portfolio = await _get_portfolio_or_raise(db, portfolio_id, org_id)
    for key, value in kwargs.items():
        if value is not None and hasattr(portfolio, key):
            setattr(portfolio, key, value)
    await db.flush()
    await db.refresh(portfolio)
    await db.commit()
    return portfolio


# ── Holdings CRUD ───────────────────────────────────────────────────────────


async def list_holdings(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
    *,
    status: HoldingStatus | None = None,
) -> list[PortfolioHolding]:
    await _get_portfolio_or_raise(db, portfolio_id, org_id)
    stmt = (
        select(PortfolioHolding)
        .where(
            PortfolioHolding.portfolio_id == portfolio_id,
            PortfolioHolding.is_deleted.is_(False),
        )
        .order_by(PortfolioHolding.investment_date.desc())
    )
    if status:
        stmt = stmt.where(PortfolioHolding.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def add_holding(
    db: AsyncSession,
    current_user: CurrentUser,
    portfolio_id: uuid.UUID,
    *,
    asset_name: str,
    asset_type: AssetType,
    investment_date: date,
    investment_amount: Decimal,
    current_value: Decimal,
    ownership_pct: Decimal | None = None,
    currency: str = "USD",
    project_id: uuid.UUID | None = None,
    notes: str = "",
) -> PortfolioHolding:
    await _get_portfolio_or_raise(db, portfolio_id, current_user.org_id)
    holding = PortfolioHolding(
        portfolio_id=portfolio_id,
        project_id=project_id,
        asset_name=asset_name,
        asset_type=asset_type,
        investment_date=investment_date,
        investment_amount=investment_amount,
        current_value=current_value,
        ownership_pct=ownership_pct,
        currency=currency,
        notes=notes,
    )
    db.add(holding)
    await db.flush()
    await db.refresh(holding)
    await db.commit()
    return holding


async def update_holding(
    db: AsyncSession,
    holding_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
    **kwargs,
) -> PortfolioHolding:
    await _get_portfolio_or_raise(db, portfolio_id, org_id)
    stmt = select(PortfolioHolding).where(
        PortfolioHolding.id == holding_id,
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    holding = result.scalar_one_or_none()
    if not holding:
        raise LookupError(f"Holding {holding_id} not found")

    for key, value in kwargs.items():
        if value is not None and hasattr(holding, key):
            setattr(holding, key, value)
    await db.flush()
    await db.refresh(holding)
    await db.commit()
    return holding


# ── Financial Metrics (Deterministic Python) ────────────────────────────────


async def compute_metrics(
    db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID
) -> dict:
    """Compute portfolio metrics using deterministic Python calculations.

    IRR uses numpy-financial (Newton's method / Brent's method).
    MOIC, TVPI, DPI, RVPI are simple arithmetic.
    """
    holdings = await list_holdings(db, portfolio_id, org_id)
    if not holdings:
        return {
            "irr_gross": None,
            "irr_net": None,
            "moic": None,
            "tvpi": None,
            "dpi": None,
            "rvpi": None,
            "total_invested": Decimal("0"),
            "total_distributions": Decimal("0"),
            "total_value": Decimal("0"),
            "carbon_reduction_tons": None,
            "as_of_date": date.today(),
        }

    total_invested = sum(h.investment_amount for h in holdings)
    total_current = sum(h.current_value for h in holdings)
    total_distributions = sum(
        h.exit_amount for h in holdings
        if h.status == HoldingStatus.EXITED and h.exit_amount
    )
    total_value = total_current + total_distributions

    # MOIC = total value / total invested
    moic = total_value / total_invested if total_invested else None

    # TVPI = total value / paid-in
    tvpi = total_value / total_invested if total_invested else None

    # DPI = distributions / paid-in
    dpi = total_distributions / total_invested if total_invested else None

    # RVPI = residual value / paid-in
    rvpi = total_current / total_invested if total_invested else None

    # IRR calculation using numpy-financial
    irr_gross = _compute_irr(holdings)

    result = {
        "irr_gross": irr_gross,
        "irr_net": irr_gross,  # Simplified: net = gross for now (fees not modeled)
        "moic": moic,
        "tvpi": tvpi,
        "dpi": dpi,
        "rvpi": rvpi,
        "total_invested": total_invested,
        "total_distributions": total_distributions,
        "total_value": total_value,
        "carbon_reduction_tons": None,
        "as_of_date": date.today(),
    }

    # Record metric snapshots (best-effort, uses savepoint to not abort outer tx)
    try:
        from app.modules.metrics.snapshot_service import MetricSnapshotService
        async with db.begin_nested():
            svc = MetricSnapshotService(db)
            snapshot_pairs = [
                ("moic", float(moic) if moic is not None else None),
                ("tvpi", float(tvpi) if tvpi is not None else None),
                ("dpi", float(dpi) if dpi is not None else None),
                ("irr_gross", float(irr_gross) if irr_gross is not None else None),
                ("nav", float(total_value) if total_value else None),
            ]
            for metric_name, value in snapshot_pairs:
                if value is not None:
                    await svc.record_snapshot(
                        org_id=org_id,
                        entity_type="portfolio",
                        entity_id=portfolio_id,
                        metric_name=metric_name,
                        value=value,
                        trigger_event="metrics_computed",
                    )
    except Exception:
        pass  # Non-critical — never break metrics computation

    return result


def _compute_irr(holdings: list[PortfolioHolding]) -> Decimal | None:
    """Compute IRR from holding cash flows using numpy-financial.

    Cash flows:
    - Investment dates: negative (outflow)
    - Exit dates: positive (inflow)
    - Today: current value of active holdings (terminal value)
    """
    try:
        import numpy_financial as npf
    except ImportError:
        return None

    if not holdings:
        return None

    # Build dated cash flows
    cash_flows: list[tuple[date, float]] = []
    for h in holdings:
        cash_flows.append((h.investment_date, -float(h.investment_amount)))
        if h.status == HoldingStatus.EXITED and h.exit_date and h.exit_amount:
            cash_flows.append((h.exit_date, float(h.exit_amount)))
        elif h.status == HoldingStatus.ACTIVE:
            cash_flows.append((date.today(), float(h.current_value)))

    if len(cash_flows) < 2:
        return None

    # Sort by date
    cash_flows.sort(key=lambda x: x[0])

    # Simple IRR using periodic cash flows (approximate: monthly periods)
    first_date = cash_flows[0][0]
    last_date = cash_flows[-1][0]
    total_months = max(
        1, (last_date.year - first_date.year) * 12 + (last_date.month - first_date.month)
    )

    # Create monthly cash flow array
    monthly = [0.0] * (total_months + 1)
    for cf_date, amount in cash_flows:
        month_idx = (cf_date.year - first_date.year) * 12 + (cf_date.month - first_date.month)
        month_idx = min(month_idx, total_months)
        monthly[month_idx] += amount

    try:
        monthly_irr = npf.irr(monthly)
        if monthly_irr is None or monthly_irr != monthly_irr:  # NaN check
            return None
        # Annualize: (1 + monthly)^12 - 1
        annual_irr = (1 + float(monthly_irr)) ** 12 - 1
        return Decimal(str(round(annual_irr, 6)))
    except Exception:
        return None


# ── Cash Flows ──────────────────────────────────────────────────────────────


async def get_cash_flows(
    db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID
) -> list[dict]:
    """Build cash flow timeline from holdings."""
    holdings = await list_holdings(db, portfolio_id, org_id)
    flows = []
    for h in holdings:
        flows.append({
            "date": h.investment_date,
            "amount": -h.investment_amount,  # Negative = outflow
            "type": "contribution",
            "holding_name": h.asset_name,
        })
        if h.status == HoldingStatus.EXITED and h.exit_date and h.exit_amount:
            flows.append({
                "date": h.exit_date,
                "amount": h.exit_amount,
                "type": "distribution",
                "holding_name": h.asset_name,
            })
    flows.sort(key=lambda x: x["date"])
    return flows


# ── Allocation ──────────────────────────────────────────────────────────────


async def get_allocation(
    db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID
) -> dict:
    """Compute portfolio allocation breakdowns by sector, geography, stage, asset type."""
    await _get_portfolio_or_raise(db, portfolio_id, org_id)

    # Get holdings with linked projects
    stmt = (
        select(PortfolioHolding)
        .where(
            PortfolioHolding.portfolio_id == portfolio_id,
            PortfolioHolding.is_deleted.is_(False),
            PortfolioHolding.status == HoldingStatus.ACTIVE,
        )
    )
    result = await db.execute(stmt)
    holdings = list(result.scalars().all())

    if not holdings:
        return {
            "by_sector": [],
            "by_geography": [],
            "by_stage": [],
            "by_asset_type": [],
        }

    total_value = sum(float(h.current_value) for h in holdings) or 1.0

    # Load linked projects for sector/geography/stage
    project_ids = [h.project_id for h in holdings if h.project_id]
    projects_map = {}
    if project_ids:
        proj_result = await db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        for p in proj_result.scalars().all():
            projects_map[p.id] = p

    # By asset type
    by_asset_type = _aggregate(
        holdings,
        lambda h: h.asset_type.value,
        lambda h: float(h.current_value),
        total_value,
    )

    # By sector (from linked project type)
    by_sector = _aggregate(
        holdings,
        lambda h: projects_map[h.project_id].project_type.value if h.project_id and h.project_id in projects_map else "unlinked",
        lambda h: float(h.current_value),
        total_value,
    )

    # By geography
    by_geography = _aggregate(
        holdings,
        lambda h: projects_map[h.project_id].geography_country if h.project_id and h.project_id in projects_map else "unlinked",
        lambda h: float(h.current_value),
        total_value,
    )

    # By stage
    by_stage = _aggregate(
        holdings,
        lambda h: projects_map[h.project_id].stage.value if h.project_id and h.project_id in projects_map else "unlinked",
        lambda h: float(h.current_value),
        total_value,
    )

    return {
        "by_sector": by_sector,
        "by_geography": by_geography,
        "by_stage": by_stage,
        "by_asset_type": by_asset_type,
    }


def _aggregate(items, key_fn, value_fn, total) -> list[dict]:
    """Group items by key and compute value + percentage."""
    buckets: dict[str, float] = {}
    for item in items:
        k = key_fn(item)
        buckets[k] = buckets.get(k, 0) + value_fn(item)
    result = []
    for name, value in sorted(buckets.items(), key=lambda x: -x[1]):
        result.append({
            "name": name,
            "value": Decimal(str(round(value, 4))),
            "percentage": Decimal(str(round(value / total * 100, 2))),
        })
    return result
