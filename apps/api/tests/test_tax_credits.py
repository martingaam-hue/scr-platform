"""Tests for the Tax Credits module."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    FundType,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStatus,
    ProjectType,
    SFDRClassification,
    UserRole,
)
from app.models.investors import Portfolio
from app.models.projects import Project

pytestmark = pytest.mark.anyio

# ── Unique IDs for this module ──────────────────────────────────────────────

TC_ORG_ID = uuid.UUID("00000000-0000-0001-0000-000000000001")
TC_USER_ID = uuid.UUID("00000000-0000-0001-0000-000000000002")
TC_PROJECT_ID = uuid.UUID("00000000-0000-0001-0000-000000000003")
TC_PORTFOLIO_ID = uuid.UUID("00000000-0000-0001-0000-000000000004")

from app.schemas.auth import CurrentUser
from app.main import app
from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.core import Organization, User
from httpx import ASGITransport

TC_CURRENT_USER = CurrentUser(
    user_id=TC_USER_ID,
    org_id=TC_ORG_ID,
    role=UserRole.ADMIN,
    email="tc_test@example.com",
    external_auth_id="clerk_tc_test",
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def tc_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=TC_ORG_ID,
        name="TC Test Org",
        slug="tc-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def tc_user(db: AsyncSession, tc_org: Organization) -> User:
    user = User(
        id=TC_USER_ID,
        org_id=TC_ORG_ID,
        email="tc_test@example.com",
        full_name="TC Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_tc_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def tc_project(db: AsyncSession, tc_org: Organization) -> Project:
    proj = Project(
        id=TC_PROJECT_ID,
        org_id=TC_ORG_ID,
        name="TC Solar Project",
        slug="tc-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="United States",
        total_investment_required=Decimal("10000000"),
        currency="USD",
        is_published=True,
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def tc_portfolio(db: AsyncSession, tc_org: Organization) -> Portfolio:
    portfolio = Portfolio(
        id=TC_PORTFOLIO_ID,
        org_id=TC_ORG_ID,
        name="TC Test Portfolio",
        description="Tax credit test portfolio",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        vintage_year=2024,
        target_aum=Decimal("100000000"),
        current_aum=Decimal("50000000"),
        currency="USD",
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


@pytest.fixture
async def tc_client(db: AsyncSession, tc_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: TC_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestTaxCreditsInventory:
    """Tests for GET /v1/tax-credits/inventory/{portfolio_id}."""

    async def test_get_inventory_unknown_portfolio_returns_404(
        self, tc_client: AsyncClient, tc_user: User
    ) -> None:
        """GET inventory for an unknown portfolio returns 404."""
        resp = await tc_client.get(f"/v1/tax-credits/inventory/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_inventory_known_portfolio_returns_200(
        self, tc_client: AsyncClient, tc_portfolio: Portfolio
    ) -> None:
        """GET inventory for a known portfolio returns 200 with correct structure."""
        resp = await tc_client.get(f"/v1/tax-credits/inventory/{TC_PORTFOLIO_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio_id" in data
        assert str(data["portfolio_id"]) == str(TC_PORTFOLIO_ID)
        assert "total_estimated" in data
        assert "credits" in data
        assert isinstance(data["credits"], list)

    async def test_get_inventory_credits_list_structure(
        self, tc_client: AsyncClient, tc_portfolio: Portfolio
    ) -> None:
        """GET inventory response includes valid numeric total_estimated."""
        resp = await tc_client.get(f"/v1/tax-credits/inventory/{TC_PORTFOLIO_ID}")
        assert resp.status_code == 200
        data = resp.json()
        # total_estimated should be a valid number
        assert isinstance(data["total_estimated"], (int, float))


class TestTaxCreditsIdentify:
    """Tests for POST /v1/tax-credits/identify/{project_id}."""

    async def test_identify_credits_unknown_project_returns_404(
        self, tc_client: AsyncClient, tc_user: User
    ) -> None:
        """POST identify for an unknown project returns 404."""
        resp = await tc_client.post(
            f"/v1/tax-credits/identify/{uuid.uuid4()}"
        )
        assert resp.status_code == 404

    async def test_identify_credits_known_project_returns_201(
        self, tc_client: AsyncClient, tc_project: Project
    ) -> None:
        """POST identify for a known project returns 201 with identification result."""
        resp = await tc_client.post(
            f"/v1/tax-credits/identify/{TC_PROJECT_ID}"
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "project_id" in data
        assert str(data["project_id"]) == str(TC_PROJECT_ID)
        assert "identified" in data
        assert isinstance(data["identified"], list)
        assert "total_estimated_value" in data

    async def test_identify_credits_response_has_numeric_total(
        self, tc_client: AsyncClient, tc_project: Project
    ) -> None:
        """POST identify returns a numeric total_estimated_value."""
        resp = await tc_client.post(
            f"/v1/tax-credits/identify/{TC_PROJECT_ID}"
        )
        assert resp.status_code == 201
        data = resp.json()
        assert isinstance(data["total_estimated_value"], (int, float))


class TestTaxCreditsSummary:
    """Tests for GET /v1/tax-credits/summary/{entity_id}."""

    async def test_get_summary_unknown_entity_returns_404(
        self, tc_client: AsyncClient, tc_user: User
    ) -> None:
        """GET summary for an unknown entity ID returns 404."""
        resp = await tc_client.get(
            f"/v1/tax-credits/summary/{uuid.uuid4()}"
        )
        assert resp.status_code == 404

    async def test_get_summary_known_portfolio_returns_200(
        self, tc_client: AsyncClient, tc_portfolio: Portfolio
    ) -> None:
        """GET summary for a known portfolio returns 200 with expected structure."""
        resp = await tc_client.get(
            f"/v1/tax-credits/summary/{TC_PORTFOLIO_ID}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entity_id" in data
        assert "total_estimated" in data
        assert "credits" in data
        assert isinstance(data["credits"], list)

    async def test_get_summary_fake_uuid_returns_404(
        self, tc_client: AsyncClient, tc_user: User
    ) -> None:
        """GET summary with the sentinel fake UUID returns 404."""
        resp = await tc_client.get(
            "/v1/tax-credits/summary/00000000-0000-0000-0000-000000000099"
        )
        assert resp.status_code == 404
