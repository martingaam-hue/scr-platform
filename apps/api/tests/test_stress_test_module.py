"""Tests for the Portfolio Stress Test module."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    AssetType,
    FundType,
    HoldingStatus,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStatus,
    ProjectType,
    SFDRClassification,
    UserRole,
)
from app.models.investors import Portfolio, PortfolioHolding
from app.models.projects import Project
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs for this module ──────────────────────────────────────────────

ST_ORG_ID = uuid.UUID("00000000-0000-0006-0000-000000000001")
ST_USER_ID = uuid.UUID("00000000-0000-0006-0000-000000000002")
ST_PROJECT_ID = uuid.UUID("00000000-0000-0006-0000-000000000003")
ST_PORTFOLIO_ID = uuid.UUID("00000000-0000-0006-0000-000000000004")
ST_HOLDING_ID = uuid.UUID("00000000-0000-0006-0000-000000000005")

ST_CURRENT_USER = CurrentUser(
    user_id=ST_USER_ID,
    org_id=ST_ORG_ID,
    role=UserRole.ADMIN,
    email="st_test@example.com",
    external_auth_id="clerk_st_test",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def st_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=ST_ORG_ID,
        name="ST Test Org",
        slug="st-test-org",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def st_user(db: AsyncSession, st_org: Organization) -> User:
    user = User(
        id=ST_USER_ID,
        org_id=ST_ORG_ID,
        email="st_test@example.com",
        full_name="ST Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_st_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def st_project(db: AsyncSession, st_org: Organization) -> Project:
    proj = Project(
        id=ST_PROJECT_ID,
        org_id=ST_ORG_ID,
        name="ST Wind Project",
        slug="st-wind-project",
        project_type=ProjectType.WIND,
        status=ProjectStatus.OPERATIONAL,
        geography_country="United Kingdom",
        total_investment_required=Decimal("20000000"),
        currency="GBP",
        capacity_mw=Decimal("100"),
        is_published=True,
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def st_portfolio(db: AsyncSession, st_org: Organization) -> Portfolio:
    portfolio = Portfolio(
        id=ST_PORTFOLIO_ID,
        org_id=ST_ORG_ID,
        name="ST Test Portfolio",
        description="Stress test portfolio",
        strategy=PortfolioStrategy.INCOME,
        fund_type=FundType.CLOSED_END,
        vintage_year=2023,
        target_aum=Decimal("200000000"),
        current_aum=Decimal("80000000"),
        currency="GBP",
        sfdr_classification=SFDRClassification.ARTICLE_8,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


@pytest.fixture
async def st_holding(
    db: AsyncSession, st_portfolio: Portfolio, st_project: Project
) -> PortfolioHolding:
    """Portfolio holding linking portfolio to project — required for stress test runs."""
    holding = PortfolioHolding(
        id=ST_HOLDING_ID,
        portfolio_id=ST_PORTFOLIO_ID,
        project_id=ST_PROJECT_ID,
        asset_name="ST Wind Asset",
        asset_type=AssetType.EQUITY,
        investment_date=date(2023, 6, 1),
        investment_amount=Decimal("10000000"),
        current_value=Decimal("11500000"),
        currency="GBP",
        status=HoldingStatus.ACTIVE,
        is_deleted=False,
    )
    db.add(holding)
    await db.flush()
    return holding


@pytest.fixture
async def st_client(db: AsyncSession, st_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: ST_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestStressTestScenarios:
    """Tests for GET /v1/stress-test/scenarios."""

    async def test_list_scenarios_returns_200(
        self, st_client: AsyncClient, st_user: User
    ) -> None:
        """GET /v1/stress-test/scenarios returns a non-empty list of scenario objects."""
        resp = await st_client.get("/v1/stress-test/scenarios")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) > 0

    async def test_scenarios_have_required_fields(
        self, st_client: AsyncClient, st_user: User
    ) -> None:
        """Each scenario has key, name, description, and params fields."""
        resp = await st_client.get("/v1/stress-test/scenarios")
        assert resp.status_code == 200
        for scenario in resp.json():
            assert "key" in scenario
            assert "name" in scenario
            assert "description" in scenario
            assert "params" in scenario

    async def test_scenarios_include_known_keys(
        self, st_client: AsyncClient, st_user: User
    ) -> None:
        """Predefined scenario set includes the expected named scenarios."""
        resp = await st_client.get("/v1/stress-test/scenarios")
        assert resp.status_code == 200
        keys = {s["key"] for s in resp.json()}
        assert "combined_downturn" in keys
        assert "rate_shock_200" in keys
        assert "energy_crash_30" in keys


class TestStressTestRun:
    """Tests for POST /v1/stress-test/run."""

    async def test_run_stress_test_no_holdings_400(
        self, st_client: AsyncClient, st_portfolio: Portfolio
    ) -> None:
        """Running a stress test for a portfolio with no holdings returns 400."""
        resp = await st_client.post(
            "/v1/stress-test/run",
            json={
                "portfolio_id": str(ST_PORTFOLIO_ID),
                "scenario_key": "combined_downturn",
                "simulations": 1000,
            },
        )
        assert resp.status_code == 400

    async def test_run_stress_test_with_holdings_201(
        self, st_client: AsyncClient, st_holding: PortfolioHolding
    ) -> None:
        """Running a stress test for a portfolio with holdings returns 201 with results."""
        resp = await st_client.post(
            "/v1/stress-test/run",
            json={
                "portfolio_id": str(ST_PORTFOLIO_ID),
                "scenario_key": "rate_shock_100",
                "simulations": 1000,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "id" in data
        assert str(data["portfolio_id"]) == str(ST_PORTFOLIO_ID)
        assert data["scenario_key"] == "rate_shock_100"
        assert "base_nav" in data
        assert "mean_nav" in data
        assert "var_95" in data
        assert isinstance(data["histogram"], list)

    async def test_run_stress_test_missing_portfolio_id_422(
        self, st_client: AsyncClient, st_user: User
    ) -> None:
        """POST /v1/stress-test/run without portfolio_id returns 422."""
        resp = await st_client.post(
            "/v1/stress-test/run",
            json={"scenario_key": "combined_downturn"},
        )
        assert resp.status_code == 422


class TestStressTestGetAndList:
    """Tests for GET /v1/stress-test/{run_id} and GET /v1/stress-test/portfolio/{portfolio_id}."""

    async def test_get_stress_test_not_found_404(
        self, st_client: AsyncClient, st_user: User
    ) -> None:
        """GET /v1/stress-test/{id} for unknown run returns 404."""
        resp = await st_client.get(f"/v1/stress-test/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_list_stress_tests_for_portfolio_200(
        self, st_client: AsyncClient, st_portfolio: Portfolio
    ) -> None:
        """GET /v1/stress-test/portfolio/{portfolio_id} returns paginated structure."""
        resp = await st_client.get(f"/v1/stress-test/portfolio/{ST_PORTFOLIO_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_stress_test_by_id_after_run_200(
        self, st_client: AsyncClient, st_holding: PortfolioHolding
    ) -> None:
        """Create a stress test run then GET it by ID returns 200."""
        run_resp = await st_client.post(
            "/v1/stress-test/run",
            json={
                "portfolio_id": str(ST_PORTFOLIO_ID),
                "scenario_key": "energy_crash_30",
                "simulations": 1000,
            },
        )
        assert run_resp.status_code == 201
        run_id = run_resp.json()["id"]

        get_resp = await st_client.get(f"/v1/stress-test/{run_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == run_id
        assert data["scenario_key"] == "energy_crash_30"
        assert str(data["portfolio_id"]) == str(ST_PORTFOLIO_ID)

    async def test_list_stress_tests_after_run_contains_run(
        self, st_client: AsyncClient, st_holding: PortfolioHolding
    ) -> None:
        """After running a test, it appears in the portfolio list."""
        run_resp = await st_client.post(
            "/v1/stress-test/run",
            json={
                "portfolio_id": str(ST_PORTFOLIO_ID),
                "scenario_key": "rate_shock_200",
                "simulations": 1000,
            },
        )
        assert run_resp.status_code == 201
        run_id = run_resp.json()["id"]

        list_resp = await st_client.get(f"/v1/stress-test/portfolio/{ST_PORTFOLIO_ID}")
        assert list_resp.status_code == 200
        ids = [r["id"] for r in list_resp.json()["items"]]
        assert run_id in ids
