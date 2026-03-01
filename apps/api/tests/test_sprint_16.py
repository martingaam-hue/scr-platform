"""Sprint 16 tests — S23 Insurance CRUD + S43 Digest preferences.

Tests:
  TestInsuranceQuotes  — POST/GET/DELETE /insurance/quotes
  TestInsurancePolicies — POST/GET/DELETE /insurance/policies
  TestDigestPreferences — GET/PUT /digest/preferences
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization, User
from app.models.enums import OrgType, UserRole
from app.models.projects import Project
from app.models.enums import ProjectType, ProjectStatus

pytestmark = pytest.mark.anyio

# ── Unique IDs for sprint 16 fixtures ─────────────────────────────────────────

S16_ORG_ID = uuid.UUID("00000000-0000-0000-0016-000000000001")
S16_USER_ID = uuid.UUID("00000000-0000-0000-0016-000000000002")
S16_PROJECT_ID = uuid.UUID("00000000-0000-0000-0016-000000000003")


@pytest.fixture
async def s16_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=S16_ORG_ID,
        name="Sprint16 Org",
        slug="sprint16-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def s16_user(db: AsyncSession, s16_org: Organization) -> User:
    user = User(
        id=S16_USER_ID,
        org_id=S16_ORG_ID,
        email="sprint16@example.com",
        full_name="Sprint 16 User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_sprint16",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def s16_project(db: AsyncSession, s16_org: Organization) -> Project:
    proj = Project(
        id=S16_PROJECT_ID,
        org_id=S16_ORG_ID,
        name="Sprint16 Solar Project",
        slug="sprint16-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Kenya",
        total_investment_required=5_000_000,
        currency="USD",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def s16_client(
    db: AsyncSession, s16_user: User
) -> AsyncClient:
    """Authenticated AsyncClient for sprint 16 fixtures."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app as _app
    from app.schemas.auth import CurrentUser
    from httpx import ASGITransport

    current = CurrentUser(
        user_id=S16_USER_ID,
        org_id=S16_ORG_ID,
        role=UserRole.ADMIN,
        email="sprint16@example.com",
        external_auth_id="clerk_sprint16",
    )
    _app.dependency_overrides[get_current_user] = lambda: current
    _app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=_app), base_url="http://test"
    ) as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)


# ── TestInsuranceQuotes ────────────────────────────────────────────────────────


class TestInsuranceQuotes:
    async def test_create_quote_201(self, s16_client: AsyncClient, s16_project: Project):
        resp = await s16_client.post(
            "/v1/insurance/quotes",
            json={
                "project_id": str(S16_PROJECT_ID),
                "provider_name": "Lloyd's of London",
                "coverage_type": "construction_all_risk",
                "coverage_amount": 5000000,
                "quoted_premium": 22500,
                "currency": "USD",
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["provider_name"] == "Lloyd's of London"
        assert data["coverage_type"] == "construction_all_risk"
        assert data["currency"] == "USD"
        assert data["side"] == "investor"

    async def test_list_quotes_empty(self, s16_client: AsyncClient, s16_org: Organization):
        resp = await s16_client.get("/v1/insurance/quotes")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_quotes_after_create(
        self, s16_client: AsyncClient, s16_project: Project
    ):
        # Create a quote
        await s16_client.post(
            "/v1/insurance/quotes",
            json={
                "project_id": str(S16_PROJECT_ID),
                "provider_name": "AIG",
                "coverage_type": "political_risk",
                "coverage_amount": 3000000,
                "quoted_premium": 15000,
                "currency": "USD",
            },
        )
        resp = await s16_client.get(
            "/v1/insurance/quotes", params={"project_id": str(S16_PROJECT_ID)}
        )
        assert resp.status_code == 200
        items = resp.json()
        assert any(q["provider_name"] == "AIG" for q in items)

    async def test_create_quote_without_project(self, s16_client: AsyncClient, s16_org: Organization):
        """Quotes can be created without a project_id."""
        resp = await s16_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Zurich",
                "coverage_type": "cyber_liability",
                "coverage_amount": 1000000,
                "quoted_premium": 8000,
                "currency": "EUR",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["project_id"] is None

    async def test_delete_quote_204(self, s16_client: AsyncClient, s16_org: Organization):
        # Create
        create_resp = await s16_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Swiss Re",
                "coverage_type": "weather_parametric",
                "coverage_amount": 2000000,
                "quoted_premium": 12000,
                "currency": "USD",
            },
        )
        assert create_resp.status_code == 201
        quote_id = create_resp.json()["id"]

        # Delete
        del_resp = await s16_client.delete(f"/v1/insurance/quotes/{quote_id}")
        assert del_resp.status_code == 204

        # Confirm no longer visible
        list_resp = await s16_client.get("/v1/insurance/quotes")
        ids = [q["id"] for q in list_resp.json()]
        assert quote_id not in ids

    async def test_delete_nonexistent_quote_404(
        self, s16_client: AsyncClient, s16_org: Organization
    ):
        fake_id = uuid.uuid4()
        resp = await s16_client.delete(f"/v1/insurance/quotes/{fake_id}")
        assert resp.status_code == 404


# ── TestInsurancePolicies ──────────────────────────────────────────────────────


class TestInsurancePolicies:
    async def _create_quote(self, client: AsyncClient) -> str:
        resp = await client.post(
            "/v1/insurance/quotes",
            json={
                "project_id": str(S16_PROJECT_ID),
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 5000000,
                "quoted_premium": 30000,
                "currency": "USD",
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_create_policy_201(
        self, s16_client: AsyncClient, s16_project: Project
    ):
        quote_id = await self._create_quote(s16_client)
        resp = await s16_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(S16_PROJECT_ID),
                "policy_number": "POL-2026-001",
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 5000000,
                "premium_amount": 30000,
                "premium_frequency": "annual",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["policy_number"] == "POL-2026-001"
        assert data["status"] == "active"
        assert data["premium_frequency"] == "annual"

    async def test_list_policies_empty(self, s16_client: AsyncClient, s16_org: Organization):
        resp = await s16_client.get("/v1/insurance/policies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_policies_after_create(
        self, s16_client: AsyncClient, s16_project: Project
    ):
        quote_id = await self._create_quote(s16_client)
        await s16_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(S16_PROJECT_ID),
                "policy_number": "POL-2026-002",
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 5000000,
                "premium_amount": 30000,
                "premium_frequency": "annual",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
            },
        )
        resp = await s16_client.get(
            "/v1/insurance/policies", params={"project_id": str(S16_PROJECT_ID)}
        )
        assert resp.status_code == 200
        items = resp.json()
        assert any(p["policy_number"] == "POL-2026-002" for p in items)

    async def test_delete_policy_204(
        self, s16_client: AsyncClient, s16_project: Project
    ):
        quote_id = await self._create_quote(s16_client)
        create_resp = await s16_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(S16_PROJECT_ID),
                "policy_number": "POL-2026-DEL",
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 5000000,
                "premium_amount": 30000,
                "premium_frequency": "annual",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
            },
        )
        assert create_resp.status_code == 201
        policy_id = create_resp.json()["id"]

        del_resp = await s16_client.delete(f"/v1/insurance/policies/{policy_id}")
        assert del_resp.status_code == 204

        list_resp = await s16_client.get("/v1/insurance/policies")
        ids = [p["id"] for p in list_resp.json()]
        assert policy_id not in ids

    async def test_delete_nonexistent_policy_404(
        self, s16_client: AsyncClient, s16_org: Organization
    ):
        fake_id = uuid.uuid4()
        resp = await s16_client.delete(f"/v1/insurance/policies/{fake_id}")
        assert resp.status_code == 404


# ── TestDigestPreferences ──────────────────────────────────────────────────────


class TestDigestPreferences:
    async def test_get_preferences_returns_defaults(
        self, s16_client: AsyncClient, s16_user: User
    ):
        resp = await s16_client.get("/v1/digest/preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert "is_subscribed" in data
        assert "frequency" in data
        assert data["frequency"] in ("daily", "weekly", "monthly")

    async def test_update_preferences_200(
        self, s16_client: AsyncClient, s16_user: User
    ):
        resp = await s16_client.put(
            "/v1/digest/preferences",
            json={"is_subscribed": True, "frequency": "weekly"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_subscribed"] is True
        assert data["frequency"] == "weekly"

    async def test_opt_out_200(self, s16_client: AsyncClient, s16_user: User):
        resp = await s16_client.put(
            "/v1/digest/preferences",
            json={"is_subscribed": False, "frequency": "weekly"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_subscribed"] is False

    async def test_get_preferences_after_update(
        self, s16_client: AsyncClient, s16_user: User
    ):
        # Set daily
        await s16_client.put(
            "/v1/digest/preferences",
            json={"is_subscribed": True, "frequency": "daily"},
        )
        # Retrieve and verify
        get_resp = await s16_client.get("/v1/digest/preferences")
        assert get_resp.status_code == 200
        assert get_resp.json()["frequency"] == "daily"

    async def test_invalid_frequency_422(
        self, s16_client: AsyncClient, s16_user: User
    ):
        resp = await s16_client.put(
            "/v1/digest/preferences",
            json={"is_subscribed": True, "frequency": "quarterly"},
        )
        assert resp.status_code == 422
