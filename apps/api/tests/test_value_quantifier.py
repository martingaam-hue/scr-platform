"""Tests for the value_quantifier module: calculator functions, service logic, HTTP endpoints."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStage, ProjectStatus, ProjectType
from app.models.projects import Project
from app.modules.value_quantifier import calculator as calc
from app.modules.value_quantifier.schemas import ValueQuantifierRequest
from app.modules.value_quantifier.service import calculate_value
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_project(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    project_type: ProjectType = ProjectType.SOLAR,
    capacity_mw: float = 50.0,
    country: str = "DE",
    total_investment: float = 60_000_000,
) -> Project:
    proj = Project(
        org_id=org_id,
        name="Value Quantifier Test Project",
        slug="vq-test-" + str(uuid.uuid4())[:8],
        description="",
        project_type=project_type,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country=country,
        geography_region="Europe",
        capacity_mw=Decimal(str(capacity_mw)),
        total_investment_required=Decimal(str(total_investment)),
    )
    db.add(proj)
    await db.flush()
    await db.refresh(proj)
    return proj


# ── Pure calculator unit tests ────────────────────────────────────────────────


def test_calculate_npv_discounts_future_cashflows():
    """calculate_npv correctly discounts cash flows at the given rate."""
    # Simple 2-year project: invest $100 today, get $60 each year
    cfs = [-100.0, 60.0, 60.0]
    npv = calc.calculate_npv(cfs, discount_rate=0.10)
    # Manual: -100 + 60/1.1 + 60/1.21 = -100 + 54.545 + 49.587 = 4.132
    assert abs(npv - 4.132) < 0.01


def test_calculate_npv_negative_for_bad_investment():
    """calculate_npv returns a negative value when outflows exceed discounted inflows."""
    cfs = [-200.0, 10.0, 10.0]  # Clearly NPV-negative
    npv = calc.calculate_npv(cfs, discount_rate=0.10)
    assert npv < 0


def test_calculate_irr_converges_for_standard_cash_flows():
    """calculate_irr returns a reasonable IRR for a standard investment."""
    # Invest $100, earn $30/yr for 5 years → IRR ≈ 15.24%
    cfs = [-100.0] + [30.0] * 5
    irr = calc.calculate_irr(cfs)
    assert irr is not None
    assert 14.0 < irr < 16.0


def test_calculate_payback_divides_capex_by_annual_net():
    """calculate_payback returns capex / annual_net correctly."""
    result = calc.calculate_payback(capex=1_000_000, annual_net_cash_flow=100_000)
    assert result == 10.0


def test_calculate_payback_returns_none_for_zero_or_negative_cashflow():
    """calculate_payback returns None when annual cash flow is zero or negative."""
    assert calc.calculate_payback(capex=1_000_000, annual_net_cash_flow=0) is None
    assert calc.calculate_payback(capex=1_000_000, annual_net_cash_flow=-50_000) is None


def test_calculate_dscr_ratio():
    """calculate_dscr returns EBITDA / debt_service."""
    result = calc.calculate_dscr(ebitda=1_500_000, annual_debt_service=1_000_000)
    assert result == 1.50


def test_calculate_dscr_returns_none_for_zero_debt_service():
    """calculate_dscr returns None when annual_debt_service is zero (no debt)."""
    assert calc.calculate_dscr(ebitda=1_500_000, annual_debt_service=0) is None


def test_calculate_lcoe_produces_reasonable_value_for_solar():
    """calculate_lcoe returns a cost in the realistic solar range ($30-$80/MWh)."""
    lcoe = calc.calculate_lcoe(
        capex=40_000_000,   # $40M CAPEX for 50MW
        opex_annual=600_000,  # $600K/yr opex
        energy_output_mwh_annual=87_600,  # 50MW * 0.20 CF * 8760h
        discount_rate=0.07,
        project_lifetime=25,
    )
    assert lcoe is not None
    lcoe_per_mwh = lcoe  # already in $/MWh
    assert 20 < lcoe_per_mwh < 100


def test_capacity_factors_for_known_project_types():
    """CAPACITY_FACTORS dict contains expected values for common project types."""
    assert calc.CAPACITY_FACTORS["solar"] == pytest.approx(0.22)
    assert calc.CAPACITY_FACTORS["wind"] == pytest.approx(0.35)
    assert calc.CAPACITY_FACTORS["geothermal"] == pytest.approx(0.85)
    assert "default" in calc.CAPACITY_FACTORS


def test_estimate_jobs_created_scales_with_capacity():
    """estimate_jobs_created returns more jobs for larger capacity."""
    jobs_10mw = calc.estimate_jobs_created(10.0, "solar")
    jobs_100mw = calc.estimate_jobs_created(100.0, "solar")
    assert jobs_100mw > jobs_10mw


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_calculate_value_returns_all_kpis(db: AsyncSession, sample_org, sample_user):
    """calculate_value returns a response with all 6 KPI entries."""
    proj = await _make_project(db, SAMPLE_ORG_ID, capacity_mw=50.0)
    req = ValueQuantifierRequest(
        project_id=proj.id,
        capex_usd=40_000_000,
        revenue_annual_usd=5_000_000,
        project_lifetime_years=25,
        discount_rate=0.10,
        debt_ratio=0.70,
        interest_rate=0.05,
        loan_term_years=20,
    )

    result = await calculate_value(db, SAMPLE_ORG_ID, req)

    assert result.project_id == proj.id
    assert result.project_name == "Value Quantifier Test Project"
    assert result.total_investment == pytest.approx(40_000_000, rel=0.01)

    kpi_labels = [k.label for k in result.kpis]
    assert "IRR" in kpi_labels
    assert "NPV" in kpi_labels
    assert "Payback Period" in kpi_labels
    assert "DSCR" in kpi_labels
    assert "LCOE" in kpi_labels
    assert "Carbon Savings" in kpi_labels


async def test_calculate_value_raises_lookup_error_for_missing_project(
    db: AsyncSession, sample_org, sample_user
):
    """calculate_value raises LookupError when project_id doesn't exist."""
    req = ValueQuantifierRequest(project_id=uuid.uuid4())

    with pytest.raises(LookupError, match="Project not found"):
        await calculate_value(db, SAMPLE_ORG_ID, req)


async def test_calculate_value_irr_quality_good_for_high_return_project(
    db: AsyncSession, sample_org, sample_user
):
    """IRR KPI quality is 'good' when IRR > 12%."""
    # Generous revenue to generate high IRR
    proj = await _make_project(db, SAMPLE_ORG_ID, capacity_mw=100.0)
    req = ValueQuantifierRequest(
        project_id=proj.id,
        capex_usd=50_000_000,
        revenue_annual_usd=10_000_000,  # 20% revenue/capex ratio → high IRR
        opex_annual_usd=500_000,
        project_lifetime_years=25,
        discount_rate=0.08,
    )

    result = await calculate_value(db, SAMPLE_ORG_ID, req)

    irr_kpi = next(k for k in result.kpis if k.label == "IRR")
    assert irr_kpi.quality == "good"


async def test_calculate_value_uses_carbon_savings_from_grid_factor(
    db: AsyncSession, sample_org, sample_user
):
    """calculate_value estimates carbon savings from grid emission factor when no CarbonCredit exists."""
    proj = await _make_project(
        db, SAMPLE_ORG_ID, capacity_mw=50.0, country="US"
    )
    req = ValueQuantifierRequest(
        project_id=proj.id,
        capex_usd=40_000_000,
        revenue_annual_usd=4_000_000,
    )

    result = await calculate_value(db, SAMPLE_ORG_ID, req)

    assert result.carbon_savings_tons is not None
    assert result.carbon_savings_tons > 0


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_calculate_value_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/value-quantifier/calculate returns 200 with KPI data."""
    proj = await _make_project(db, SAMPLE_ORG_ID, capacity_mw=30.0)

    resp = await authenticated_client.post(
        "/v1/value-quantifier/calculate",
        json={
            "project_id": str(proj.id),
            "capex_usd": 24_000_000,
            "revenue_annual_usd": 3_000_000,
            "project_lifetime_years": 20,
            "discount_rate": 0.09,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == str(proj.id)
    assert "kpis" in data
    assert len(data["kpis"]) >= 5
    assert "assumptions" in data


async def test_http_get_value_quantifier_returns_404_for_unknown_project(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/value-quantifier/{unknown_id} returns 404."""
    resp = await authenticated_client.get(f"/v1/value-quantifier/{uuid.uuid4()}")
    assert resp.status_code == 404
