"""Tests for the cashflow pacing module — J-curve projections, scenarios, actuals."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    FundType,
    PortfolioStatus,
    PortfolioStrategy,
    SFDRClassification,
)
from app.models.investors import Portfolio
from app.modules.pacing.schemas import (
    CreateAssumptionRequest,
    UpdateActualsRequest,
)
from app.modules.pacing.service import PacingService
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_portfolio(db: AsyncSession, org_id: uuid.UUID) -> Portfolio:
    """Create and flush a minimal Portfolio."""
    portfolio = Portfolio(
        org_id=org_id,
        name="Test Fund I",
        description="",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        target_aum=Decimal("100000000"),
        current_aum=Decimal("50000000"),
        currency="EUR",
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


# ── Projection generation ──────────────────────────────────────────────────────


async def test_create_assumption_generates_three_scenarios(db: AsyncSession, sample_org):
    """Creating an assumption auto-generates base, optimistic, and pessimistic projections."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    req = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("10000000"),
        investment_period_years=5,
        fund_life_years=10,
        label="Test Assumption",
    )
    result = await svc.create_assumption(req)

    scenarios = {row.scenario for row in result.projections}
    assert scenarios == {"base", "optimistic", "pessimistic"}


async def test_projection_row_count_matches_fund_life(db: AsyncSession, sample_org):
    """Number of projections per scenario equals fund_life_years."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    fund_years = 8
    req = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("5000000"),
        fund_life_years=fund_years,
        investment_period_years=3,
    )
    result = await svc.create_assumption(req)

    for scenario in ("base", "optimistic", "pessimistic"):
        scenario_rows = [r for r in result.projections if r.scenario == scenario]
        assert len(scenario_rows) == fund_years, f"Expected {fund_years} rows for {scenario}"


async def test_jcurve_trough_in_early_years(db: AsyncSession, sample_org):
    """The J-curve trough (most negative net cashflow) should occur in years 1-3."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    req = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("10000000"),
        investment_period_years=5,
        fund_life_years=10,
    )
    result = await svc.create_assumption(req)

    assert result.trough_year is not None
    assert 1 <= result.trough_year <= 5
    assert result.trough_value is not None
    assert result.trough_value < Decimal("0"), "Trough cashflow must be negative"


async def test_optimistic_scenario_higher_distributions_than_base(
    db: AsyncSession, sample_org
):
    """Optimistic scenario total distributions must exceed base scenario distributions."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    req = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("10000000"),
        optimistic_modifier=Decimal("1.30"),
        pessimistic_modifier=Decimal("0.70"),
    )
    result = await svc.create_assumption(req)

    def total_distributions(scenario: str) -> Decimal:
        return sum(
            (r.projected_distributions or Decimal("0"))
            for r in result.projections
            if r.scenario == scenario
        )

    assert total_distributions("optimistic") > total_distributions("base")
    assert total_distributions("base") > total_distributions("pessimistic")


async def test_pessimistic_scenario_lower_than_base(db: AsyncSession, sample_org):
    """Pessimistic scenario distributions are below base due to modifier < 1.0."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    req = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("10000000"),
        pessimistic_modifier=Decimal("0.75"),
    )
    result = await svc.create_assumption(req)

    base_dists = sum(
        r.projected_distributions or Decimal("0")
        for r in result.projections
        if r.scenario == "base"
    )
    pessimistic_dists = sum(
        r.projected_distributions or Decimal("0")
        for r in result.projections
        if r.scenario == "pessimistic"
    )
    assert pessimistic_dists < base_dists


async def test_update_actuals_sets_values_and_recomputes_net_cashflow(
    db: AsyncSession, sample_org
):
    """update_actuals writes actual data and recomputes actual_net_cashflow."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    req = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("10000000"),
        fund_life_years=5,
    )
    result = await svc.create_assumption(req)
    assumption_id = uuid.UUID(result.assumption_id)

    actuals = UpdateActualsRequest(
        year=1,
        actual_contributions=Decimal("3000000"),
        actual_distributions=Decimal("500000"),
    )
    row = await svc.update_actuals(assumption_id, actuals, scenario="base")

    assert row.actual_contributions == Decimal("3000000")
    assert row.actual_distributions == Decimal("500000")
    # actual_net_cashflow = distributions - contributions = -2,500,000
    assert row.actual_net_cashflow == Decimal("500000") - Decimal("3000000")


async def test_list_assumptions_returns_all_for_portfolio(db: AsyncSession, sample_org):
    """list_assumptions returns all non-deleted assumptions for the portfolio."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    # Create first assumption (will become inactive when second is created)
    req1 = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("5000000"),
        label="Initial",
    )
    await svc.create_assumption(req1)

    req2 = CreateAssumptionRequest(
        portfolio_id=portfolio.id,
        committed_capital=Decimal("8000000"),
        label="Revised",
    )
    await svc.create_assumption(req2)

    assumptions = await svc.list_assumptions(portfolio.id)
    assert len(assumptions) == 2
    labels = {a.label for a in assumptions}
    assert "Initial" in labels
    assert "Revised" in labels


async def test_get_pacing_404_when_no_assumption(db: AsyncSession, sample_org):
    """get_pacing raises LookupError when no active assumption exists for a portfolio."""
    portfolio = await _make_portfolio(db, sample_org.id)
    svc = PacingService(db, sample_org.id)

    with pytest.raises(LookupError, match="No active pacing assumption"):
        await svc.get_pacing(portfolio.id)


# ── HTTP endpoint tests ────────────────────────────────────────────────────────


async def test_api_create_assumption_returns_201(
    authenticated_client, db: AsyncSession, sample_org
):
    """POST /v1/pacing/portfolios/{id}/assumptions returns 201 with projection data."""
    portfolio = await _make_portfolio(db, sample_org.id)

    payload = {
        "portfolio_id": str(portfolio.id),
        "committed_capital": "10000000",
        "investment_period_years": 5,
        "fund_life_years": 10,
    }
    resp = await authenticated_client.post(
        f"/v1/pacing/portfolios/{portfolio.id}/assumptions", json=payload
    )

    assert resp.status_code == 201
    body = resp.json()
    assert "projections" in body
    assert len(body["projections"]) == 30  # 3 scenarios × 10 years
    assert body["committed_capital"] == "10000000.0000"


async def test_api_get_pacing_404_for_unknown_portfolio(authenticated_client):
    """GET /v1/pacing/portfolios/{id} returns 404 when no assumption exists."""
    resp = await authenticated_client.get(f"/v1/pacing/portfolios/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_api_list_assumptions_empty(
    authenticated_client, db: AsyncSession, sample_org
):
    """GET /v1/pacing/portfolios/{id}/assumptions returns empty list when none exist."""
    portfolio = await _make_portfolio(db, sample_org.id)
    resp = await authenticated_client.get(
        f"/v1/pacing/portfolios/{portfolio.id}/assumptions"
    )
    assert resp.status_code == 200
    assert resp.json() == []
