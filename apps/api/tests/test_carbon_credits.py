"""Tests for the Carbon Credits module."""

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
    CarbonVerificationStatus,
    OrgType,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.financial import CarbonCredit
from app.models.projects import Project
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs for this module ──────────────────────────────────────────────

CC_ORG_ID = uuid.UUID("00000000-0000-0002-0000-000000000001")
CC_USER_ID = uuid.UUID("00000000-0000-0002-0000-000000000002")
CC_PROJECT_ID = uuid.UUID("00000000-0000-0002-0000-000000000003")
CC_PROJECT2_ID = uuid.UUID("00000000-0000-0002-0000-000000000004")

CC_CURRENT_USER = CurrentUser(
    user_id=CC_USER_ID,
    org_id=CC_ORG_ID,
    role=UserRole.ADMIN,
    email="cc_test@example.com",
    external_auth_id="clerk_cc_test",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def cc_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=CC_ORG_ID,
        name="CC Test Org",
        slug="cc-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cc_user(db: AsyncSession, cc_org: Organization) -> User:
    user = User(
        id=CC_USER_ID,
        org_id=CC_ORG_ID,
        email="cc_test@example.com",
        full_name="CC Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_cc_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def cc_project(db: AsyncSession, cc_org: Organization) -> Project:
    """A solar project owned by CC org, with capacity so estimate works."""
    proj = Project(
        id=CC_PROJECT_ID,
        org_id=CC_ORG_ID,
        name="CC Solar Project",
        slug="cc-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Germany",
        total_investment_required=Decimal("5000000"),
        currency="EUR",
        capacity_mw=Decimal("50"),
        is_published=True,
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def cc_project_with_credit(
    db: AsyncSession, cc_project: Project
) -> tuple[Project, CarbonCredit]:
    """A project that already has a CarbonCredit record."""
    cc = CarbonCredit(
        project_id=CC_PROJECT_ID,
        org_id=CC_ORG_ID,
        registry="Verra (estimated)",
        methodology="VM0015",
        vintage_year=2025,
        quantity_tons=Decimal("1500"),
        currency="USD",
        verification_status=CarbonVerificationStatus.ESTIMATED,
    )
    db.add(cc)
    await db.flush()
    return cc_project, cc


@pytest.fixture
async def cc_client(db: AsyncSession, cc_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: CC_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestCarbonStaticEndpoints:
    """Tests for static data endpoints that require no project data."""

    async def test_get_pricing_trends_200(
        self, cc_client: AsyncClient, cc_user: User
    ) -> None:
        """GET /v1/carbon/pricing-trends returns a list of trend points."""
        resp = await cc_client.get("/v1/carbon/pricing-trends")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "date" in first
        assert "vcs_price" in first
        assert "gold_standard_price" in first
        assert "eu_ets_price" in first

    async def test_get_methodologies_200(
        self, cc_client: AsyncClient, cc_user: User
    ) -> None:
        """GET /v1/carbon/methodologies returns a non-empty list."""
        resp = await cc_client.get("/v1/carbon/methodologies")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "registry" in first

    async def test_pricing_trends_values_are_numeric(
        self, cc_client: AsyncClient, cc_user: User
    ) -> None:
        """Pricing trend numeric fields are floats, not strings."""
        resp = await cc_client.get("/v1/carbon/pricing-trends")
        assert resp.status_code == 200
        for point in resp.json():
            assert isinstance(point["vcs_price"], (int, float))
            assert isinstance(point["eu_ets_price"], (int, float))


class TestCarbonEstimate:
    """Tests for POST /v1/carbon/estimate/{project_id}."""

    async def test_estimate_unknown_project_returns_404(
        self, cc_client: AsyncClient, cc_user: User
    ) -> None:
        """Estimating credits for an unknown project returns 404."""
        resp = await cc_client.post(f"/v1/carbon/estimate/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_estimate_known_project_returns_200(
        self, cc_client: AsyncClient, cc_project: Project
    ) -> None:
        """Estimating credits for a known project returns 200 with estimate and record."""
        resp = await cc_client.post(f"/v1/carbon/estimate/{CC_PROJECT_ID}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "estimate" in data
        assert "credit_record" in data
        estimate = data["estimate"]
        assert "annual_tons_co2e" in estimate
        assert "methodology" in estimate
        assert "confidence" in estimate

    async def test_estimate_creates_credit_record(
        self, cc_client: AsyncClient, cc_project: Project
    ) -> None:
        """Estimate response includes a credit_record with project_id."""
        resp = await cc_client.post(f"/v1/carbon/estimate/{CC_PROJECT_ID}")
        assert resp.status_code == 200
        record = resp.json()["credit_record"]
        assert "project_id" in record
        assert str(record["project_id"]) == str(CC_PROJECT_ID)


class TestCarbonCreditCRUD:
    """Tests for GET/PUT on /v1/carbon/{project_id} (requires credit record)."""

    async def test_get_credit_no_record_returns_404(
        self, cc_client: AsyncClient, cc_project: Project
    ) -> None:
        """GET carbon credit for project without a record returns 404."""
        resp = await cc_client.get(f"/v1/carbon/{CC_PROJECT_ID}")
        assert resp.status_code == 404

    async def test_get_credit_with_record_returns_200(
        self, cc_client: AsyncClient, cc_project_with_credit: tuple
    ) -> None:
        """GET carbon credit for project with record returns 200."""
        resp = await cc_client.get(f"/v1/carbon/{CC_PROJECT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "verification_status" in data
        assert str(data["project_id"]) == str(CC_PROJECT_ID)

    async def test_update_credit_fields_returns_200(
        self, cc_client: AsyncClient, cc_project_with_credit: tuple
    ) -> None:
        """PUT carbon credit updates specified fields and returns 200."""
        resp = await cc_client.put(
            f"/v1/carbon/{CC_PROJECT_ID}",
            json={
                "price_per_ton": 12.50,
                "currency": "EUR",
                "serial_number": "VCS-2025-00001",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["price_per_ton"] == 12.50
        assert data["currency"] == "EUR"
        assert data["serial_number"] == "VCS-2025-00001"

    async def test_update_verification_status_returns_200(
        self, cc_client: AsyncClient, cc_project_with_credit: tuple
    ) -> None:
        """PUT verification-status advances status and returns 200."""
        resp = await cc_client.put(
            f"/v1/carbon/{CC_PROJECT_ID}/verification-status",
            json={
                "verification_status": "submitted",
                "verification_body": "Gold Standard Foundation",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["verification_status"] == "submitted"

    async def test_update_unknown_project_returns_404(
        self, cc_client: AsyncClient, cc_user: User
    ) -> None:
        """PUT on unknown project returns 404."""
        resp = await cc_client.put(
            f"/v1/carbon/{uuid.uuid4()}",
            json={"price_per_ton": 10.0},
        )
        assert resp.status_code == 404
