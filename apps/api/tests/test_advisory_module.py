"""Integration tests for Insurance and Investor Personas advisory modules.

Covers:
- Insurance Quote CRUD lifecycle (POST, GET, DELETE)
- Insurance Policy CRUD lifecycle (POST, GET, DELETE)
- Insurance side field filtering (investor vs ally)
- Investor Persona CRUD lifecycle (POST, GET, PUT, list)
- Multi-tenancy scoping (org isolation)

Note: test_advisory_enums.py covers enum round-trip tests separately.
This file focuses on business logic, CRUD lifecycles, and org scoping.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization, User
from app.models.enums import OrgType, ProjectStatus, ProjectType, UserRole
from app.models.projects import Project
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# Unique UUIDs for this module — no collisions with conftest or other test files
AM_ORG_ID = uuid.UUID("00000000-0000-0000-00cc-000000000001")
AM_USER_ID = uuid.UUID("00000000-0000-0000-00cc-000000000002")
AM_PROJECT_ID = uuid.UUID("00000000-0000-0000-00cc-000000000003")

AM_OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-00cc-000000000010")
AM_OTHER_USER_ID = uuid.UUID("00000000-0000-0000-00cc-000000000011")

AM_INV_ORG_ID = uuid.UUID("00000000-0000-0000-00cc-000000000020")
AM_INV_USER_ID = uuid.UUID("00000000-0000-0000-00cc-000000000021")


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def am_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=AM_ORG_ID,
        name="Advisory Module Org",
        slug="advisory-module-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def am_user(db: AsyncSession, am_org: Organization) -> User:
    user = User(
        id=AM_USER_ID,
        org_id=AM_ORG_ID,
        email="am-user@advisory-module-test.example",
        full_name="Advisory Module User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_am_user",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def am_project(db: AsyncSession, am_org: Organization) -> Project:
    proj = Project(
        id=AM_PROJECT_ID,
        org_id=AM_ORG_ID,
        name="Advisory Module Solar Project",
        slug="advisory-module-solar",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Germany",
        total_investment_required=10_000_000,
        currency="EUR",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def am_client(db: AsyncSession, am_user: User) -> AsyncClient:
    """Authenticated client scoped to am_org (ally org)."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db, get_readonly_session
    from app.main import app as _app

    cu = CurrentUser(
        user_id=AM_USER_ID,
        org_id=AM_ORG_ID,
        role=UserRole.ADMIN,
        email="am-user@advisory-module-test.example",
        external_auth_id="clerk_am_user",
    )
    _app.dependency_overrides[get_current_user] = lambda: cu
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)
    _app.dependency_overrides.pop(get_readonly_session, None)


@pytest.fixture
async def am_other_org(db: AsyncSession) -> Organization:
    """A second org — used for multi-tenancy isolation tests."""
    org = Organization(
        id=AM_OTHER_ORG_ID,
        name="Other Org (Advisory Module)",
        slug="other-org-advisory-module",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def am_other_user(db: AsyncSession, am_other_org: Organization) -> User:
    user = User(
        id=AM_OTHER_USER_ID,
        org_id=AM_OTHER_ORG_ID,
        email="other@advisory-module-test.example",
        full_name="Other Org User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_am_other",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def am_other_client(db: AsyncSession, am_other_user: User) -> AsyncClient:
    """Client authenticated as the second (other) org."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db, get_readonly_session
    from app.main import app as _app

    cu = CurrentUser(
        user_id=AM_OTHER_USER_ID,
        org_id=AM_OTHER_ORG_ID,
        role=UserRole.ADMIN,
        email="other@advisory-module-test.example",
        external_auth_id="clerk_am_other",
    )
    _app.dependency_overrides[get_current_user] = lambda: cu
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)
    _app.dependency_overrides.pop(get_readonly_session, None)


@pytest.fixture
async def am_inv_org(db: AsyncSession) -> Organization:
    """Investor org for persona tests."""
    org = Organization(
        id=AM_INV_ORG_ID,
        name="Advisory Module Investor Org",
        slug="advisory-module-investor",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def am_inv_user(db: AsyncSession, am_inv_org: Organization) -> User:
    user = User(
        id=AM_INV_USER_ID,
        org_id=AM_INV_ORG_ID,
        email="inv@advisory-module-test.example",
        full_name="Advisory Module Investor",
        role=UserRole.ADMIN,
        external_auth_id="clerk_am_inv",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def am_inv_client(db: AsyncSession, am_inv_user: User) -> AsyncClient:
    """Authenticated client scoped to am_inv_org (investor org)."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db, get_readonly_session
    from app.main import app as _app

    cu = CurrentUser(
        user_id=AM_INV_USER_ID,
        org_id=AM_INV_ORG_ID,
        role=UserRole.ADMIN,
        email="inv@advisory-module-test.example",
        external_auth_id="clerk_am_inv",
    )
    _app.dependency_overrides[get_current_user] = lambda: cu
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)
    _app.dependency_overrides.pop(get_readonly_session, None)


# ── TestInsuranceQuoteCRUD ────────────────────────────────────────────────────


class TestInsuranceQuoteCRUD:
    """CRUD lifecycle tests for insurance quotes."""

    _QUOTE_BODY = {
        "provider_name": "Allianz Global",
        "coverage_type": "construction_all_risk",
        "coverage_amount": 5_000_000,
        "quoted_premium": 22_500,
        "currency": "EUR",
        "side": "investor",
    }

    async def test_create_quote_returns_201(self, am_client: AsyncClient, am_org: Organization):
        """POST /v1/insurance/quotes with valid body returns 201 and quote data."""
        resp = await am_client.post("/v1/insurance/quotes", json=self._QUOTE_BODY)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["provider_name"] == "Allianz Global"
        assert data["coverage_type"] == "construction_all_risk"
        assert data["side"] == "investor"
        assert "id" in data
        assert "org_id" in data

    async def test_create_quote_with_project_id(self, am_client: AsyncClient, am_project: Project):
        """Quote can be linked to a project via project_id."""
        body = {**self._QUOTE_BODY, "project_id": str(AM_PROJECT_ID)}
        resp = await am_client.post("/v1/insurance/quotes", json=body)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["project_id"] == str(AM_PROJECT_ID)

    async def test_list_quotes_returns_created_quote(
        self, am_client: AsyncClient, am_org: Organization
    ):
        """Created quote appears in the list response."""
        create_resp = await am_client.post("/v1/insurance/quotes", json=self._QUOTE_BODY)
        assert create_resp.status_code == 201
        quote_id = create_resp.json()["id"]

        list_resp = await am_client.get("/v1/insurance/quotes")
        assert list_resp.status_code == 200
        ids = [q["id"] for q in list_resp.json()]
        assert quote_id in ids

    async def test_delete_quote_returns_204(self, am_client: AsyncClient, am_org: Organization):
        """DELETE /v1/insurance/quotes/{id} returns 204 No Content."""
        create_resp = await am_client.post("/v1/insurance/quotes", json=self._QUOTE_BODY)
        assert create_resp.status_code == 201
        quote_id = create_resp.json()["id"]

        del_resp = await am_client.delete(f"/v1/insurance/quotes/{quote_id}")
        assert del_resp.status_code == 204

    async def test_deleted_quote_not_in_list(self, am_client: AsyncClient, am_org: Organization):
        """Deleted quote no longer appears in the list."""
        create_resp = await am_client.post("/v1/insurance/quotes", json=self._QUOTE_BODY)
        quote_id = create_resp.json()["id"]

        await am_client.delete(f"/v1/insurance/quotes/{quote_id}")

        list_resp = await am_client.get("/v1/insurance/quotes")
        assert list_resp.status_code == 200
        ids = [q["id"] for q in list_resp.json()]
        assert quote_id not in ids

    async def test_delete_nonexistent_quote_returns_404(
        self, am_client: AsyncClient, am_org: Organization
    ):
        """Deleting a quote that doesn't exist returns 404."""
        fake_id = uuid.uuid4()
        resp = await am_client.delete(f"/v1/insurance/quotes/{fake_id}")
        assert resp.status_code == 404


# ── TestInsurancePolicyCRUD ───────────────────────────────────────────────────


class TestInsurancePolicyCRUD:
    """CRUD lifecycle tests for insurance policies."""

    async def _create_quote(self, client: AsyncClient) -> str:
        resp = await client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 8_000_000,
                "quoted_premium": 36_000,
                "currency": "EUR",
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    async def test_create_policy_returns_201(self, am_client: AsyncClient, am_project: Project):
        """POST /v1/insurance/policies with a valid quote returns 201."""
        quote_id = await self._create_quote(am_client)
        resp = await am_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(AM_PROJECT_ID),
                "policy_number": "POL-AM-001",
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 8_000_000,
                "premium_amount": 36_000,
                "premium_frequency": "annual",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["policy_number"] == "POL-AM-001"
        assert data["status"] == "active"
        assert data["premium_frequency"] == "annual"

    async def test_list_policies_returns_created_policy(
        self, am_client: AsyncClient, am_project: Project
    ):
        """Policy created via POST appears in GET /v1/insurance/policies."""
        quote_id = await self._create_quote(am_client)
        create_resp = await am_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(AM_PROJECT_ID),
                "policy_number": "POL-AM-LIST-001",
                "provider_name": "List Test Insurer",
                "coverage_type": "business_interruption",
                "coverage_amount": 2_000_000,
                "premium_amount": 10_000,
                "premium_frequency": "quarterly",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
            },
        )
        assert create_resp.status_code == 201
        policy_id = create_resp.json()["id"]

        list_resp = await am_client.get("/v1/insurance/policies")
        assert list_resp.status_code == 200
        ids = [p["id"] for p in list_resp.json()]
        assert policy_id in ids

    async def test_delete_policy_returns_204(self, am_client: AsyncClient, am_project: Project):
        """DELETE /v1/insurance/policies/{id} returns 204."""
        quote_id = await self._create_quote(am_client)
        create_resp = await am_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(AM_PROJECT_ID),
                "policy_number": "POL-AM-DEL-001",
                "provider_name": "Delete Test Insurer",
                "coverage_type": "cyber_liability",
                "coverage_amount": 1_000_000,
                "premium_amount": 5_000,
                "premium_frequency": "monthly",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
            },
        )
        assert create_resp.status_code == 201
        policy_id = create_resp.json()["id"]

        del_resp = await am_client.delete(f"/v1/insurance/policies/{policy_id}")
        assert del_resp.status_code == 204

    async def test_deleted_policy_not_in_list(self, am_client: AsyncClient, am_project: Project):
        """Deleted policy does not appear in subsequent list response."""
        quote_id = await self._create_quote(am_client)
        create_resp = await am_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(AM_PROJECT_ID),
                "policy_number": "POL-AM-DEL-VERIFY-001",
                "provider_name": "Delete Verify Insurer",
                "coverage_type": "political_risk",
                "coverage_amount": 3_000_000,
                "premium_amount": 15_000,
                "premium_frequency": "annual",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
            },
        )
        policy_id = create_resp.json()["id"]

        await am_client.delete(f"/v1/insurance/policies/{policy_id}")

        list_resp = await am_client.get("/v1/insurance/policies")
        ids = [p["id"] for p in list_resp.json()]
        assert policy_id not in ids


# ── TestInsuranceSideFilter ───────────────────────────────────────────────────


class TestInsuranceSideFilter:
    """Tests that both 'investor' and 'ally' side quotes are created and listed."""

    async def test_both_sides_visible_in_list(self, am_client: AsyncClient, am_org: Organization):
        """Create one quote per side; both appear in the list."""
        resp_investor = await am_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Investor Side Insurer",
                "coverage_type": "construction_all_risk",
                "coverage_amount": 1_000_000,
                "quoted_premium": 4_500,
                "currency": "EUR",
                "side": "investor",
            },
        )
        assert resp_investor.status_code == 201, resp_investor.text
        investor_id = resp_investor.json()["id"]

        resp_ally = await am_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Ally Side Insurer",
                "coverage_type": "environmental_liability",
                "coverage_amount": 500_000,
                "quoted_premium": 2_000,
                "currency": "EUR",
                "side": "ally",
            },
        )
        assert resp_ally.status_code == 201, resp_ally.text
        ally_id = resp_ally.json()["id"]

        list_resp = await am_client.get("/v1/insurance/quotes")
        assert list_resp.status_code == 200
        ids = [q["id"] for q in list_resp.json()]
        assert investor_id in ids
        assert ally_id in ids

    async def test_side_values_are_lowercase_in_response(
        self, am_client: AsyncClient, am_org: Organization
    ):
        """The side field in the response must be lowercase (enum value, not name)."""
        for side in ("investor", "ally"):
            resp = await am_client.post(
                "/v1/insurance/quotes",
                json={
                    "provider_name": f"Side Test {side}",
                    "coverage_type": "weather_parametric",
                    "coverage_amount": 250_000,
                    "quoted_premium": 1_000,
                    "currency": "USD",
                    "side": side,
                },
            )
            assert resp.status_code == 201, resp.text
            assert resp.json()["side"] == side

    async def test_org_scoping_via_service_list(
        self,
        db: AsyncSession,
        am_org: Organization,
        am_other_org: Organization,
    ):
        """Service-level test: list_quotes() with a different org_id excludes the quote.

        Uses service directly since HTTP clients share the same DB session in
        transactional tests, which would make both clients see each other's data.
        The real isolation happens at the service query level (WHERE org_id = ...).
        """
        from app.modules.insurance import service as insurance_service
        from app.modules.insurance.schemas import QuoteCreate

        # Create a quote for am_org
        quote = await insurance_service.create_quote(
            db,
            AM_ORG_ID,
            QuoteCreate(
                provider_name="Scope Service Test Insurer",
                coverage_type="directors_officers",
                coverage_amount=2_000_000,
                quoted_premium=9_000,
                currency="USD",
                side="investor",
            ),
        )

        # Querying with am_other_org's id should NOT return this quote
        other_org_quotes = await insurance_service.list_quotes(db, AM_OTHER_ORG_ID, None)
        other_ids = [q.id for q in other_org_quotes]
        assert quote.id not in other_ids

        # Querying with am_org's id should return the quote
        own_quotes = await insurance_service.list_quotes(db, AM_ORG_ID, None)
        own_ids = [q.id for q in own_quotes]
        assert quote.id in own_ids


# ── TestInvestorPersonaCRUD ───────────────────────────────────────────────────


class TestInvestorPersonaCRUD:
    """CRUD lifecycle tests for investor personas."""

    _PERSONA_BODY = {
        "persona_name": "European Impact Fund",
        "strategy_type": "impact_first",
        "target_irr_min": 8.0,
        "target_irr_max": 15.0,
        "target_moic_min": 1.5,
        "preferred_asset_types": ["solar", "wind"],
        "preferred_geographies": ["EU", "UK"],
        "preferred_stages": ["development", "construction"],
        "ticket_size_min": 1_000_000,
        "ticket_size_max": 50_000_000,
        "esg_requirements": {"min_score": 70},
        "risk_tolerance": {"max_risk_score": 6},
        "co_investment_preference": True,
    }

    async def test_create_persona_returns_201(self, am_inv_client: AsyncClient, am_inv_user: User):
        """POST /v1/investor-personas returns 201 with persona data."""
        resp = await am_inv_client.post("/v1/investor-personas", json=self._PERSONA_BODY)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["persona_name"] == "European Impact Fund"
        assert data["strategy_type"] == "impact_first"
        assert data["is_active"] is True
        assert "id" in data

    async def test_list_personas_returns_created_persona(
        self, am_inv_client: AsyncClient, am_inv_user: User
    ):
        """Created persona appears in GET /v1/investor-personas list."""
        create_resp = await am_inv_client.post("/v1/investor-personas", json=self._PERSONA_BODY)
        assert create_resp.status_code == 201
        persona_id = create_resp.json()["id"]

        list_resp = await am_inv_client.get("/v1/investor-personas")
        assert list_resp.status_code == 200
        ids = [p["id"] for p in list_resp.json()]
        assert persona_id in ids

    async def test_get_single_persona_by_id(self, am_inv_client: AsyncClient, am_inv_user: User):
        """GET /v1/investor-personas/{id} returns the exact persona."""
        create_resp = await am_inv_client.post("/v1/investor-personas", json=self._PERSONA_BODY)
        assert create_resp.status_code == 201
        persona_id = create_resp.json()["id"]

        get_resp = await am_inv_client.get(f"/v1/investor-personas/{persona_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == persona_id
        assert data["persona_name"] == "European Impact Fund"

    async def test_get_nonexistent_persona_returns_404(
        self, am_inv_client: AsyncClient, am_inv_user: User
    ):
        """Fetching a persona that doesn't exist returns 404."""
        fake_id = uuid.uuid4()
        resp = await am_inv_client.get(f"/v1/investor-personas/{fake_id}")
        assert resp.status_code == 404

    async def test_update_persona_via_put(self, am_inv_client: AsyncClient, am_inv_user: User):
        """PUT /v1/investor-personas/{id} partially updates the persona."""
        create_resp = await am_inv_client.post("/v1/investor-personas", json=self._PERSONA_BODY)
        assert create_resp.status_code == 201
        persona_id = create_resp.json()["id"]

        put_resp = await am_inv_client.put(
            f"/v1/investor-personas/{persona_id}",
            json={"persona_name": "Updated Fund Name", "strategy_type": "growth"},
        )
        assert put_resp.status_code == 200, put_resp.text
        data = put_resp.json()
        assert data["persona_name"] == "Updated Fund Name"
        assert data["strategy_type"] == "growth"

    async def test_all_strategy_types_are_accepted(
        self, am_inv_client: AsyncClient, am_inv_user: User
    ):
        """All valid strategy_type values create personas successfully."""
        valid_strategies = ["conservative", "moderate", "growth", "aggressive", "impact_first"]
        for strategy in valid_strategies:
            resp = await am_inv_client.post(
                "/v1/investor-personas",
                json={"persona_name": f"Fund {strategy}", "strategy_type": strategy},
            )
            assert resp.status_code == 201, f"strategy_type={strategy}: {resp.text}"
            assert resp.json()["strategy_type"] == strategy

    async def test_persona_preferred_geographies_round_trip(
        self, am_inv_client: AsyncClient, am_inv_user: User
    ):
        """JSONB list fields like preferred_geographies survive the round-trip."""
        geos = ["EU", "UK", "US", "APAC"]
        resp = await am_inv_client.post(
            "/v1/investor-personas",
            json={"persona_name": "Global Fund", "preferred_geographies": geos},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["preferred_geographies"] == geos


# ── TestMultiTenancy ──────────────────────────────────────────────────────────


class TestMultiTenancy:
    """Multi-tenancy isolation tests for insurance and persona modules.

    Note on test design: The transactional test fixture shares one DB session
    across all fixtures in a test, so two HTTP clients with different CurrentUser
    credentials but the same DB session would see each other's data (because the
    DB filtering is at org_id and both are using the same connection/transaction).

    These tests instead verify org_id scoping at the service layer directly,
    which is the actual isolation mechanism. This matches the real production
    behaviour where each request has its own DB connection.
    """

    async def test_insurance_service_list_quotes_filters_by_org_id(
        self,
        db: AsyncSession,
        am_org: Organization,
        am_other_org: Organization,
    ):
        """InsuranceService.list_quotes() only returns quotes for the given org_id."""
        from app.modules.insurance import service as insurance_service
        from app.modules.insurance.schemas import QuoteCreate

        # Create a quote for org A
        org_a_quote = await insurance_service.create_quote(
            db,
            AM_ORG_ID,
            QuoteCreate(
                provider_name="Org A Insurer",
                coverage_type="cyber_liability",
                coverage_amount=1_000_000,
                quoted_premium=3_500,
                side="investor",
            ),
        )

        # Create a quote for org B (other org)
        org_b_quote = await insurance_service.create_quote(
            db,
            AM_OTHER_ORG_ID,
            QuoteCreate(
                provider_name="Org B Insurer",
                coverage_type="political_risk",
                coverage_amount=2_000_000,
                quoted_premium=8_000,
                side="ally",
            ),
        )

        # Org A's list should only contain org A's quote
        org_a_quotes = await insurance_service.list_quotes(db, AM_ORG_ID, None)
        org_a_ids = [q.id for q in org_a_quotes]
        assert org_a_quote.id in org_a_ids
        assert org_b_quote.id not in org_a_ids

        # Org B's list should only contain org B's quote
        org_b_quotes = await insurance_service.list_quotes(db, AM_OTHER_ORG_ID, None)
        org_b_ids = [q.id for q in org_b_quotes]
        assert org_b_quote.id in org_b_ids
        assert org_a_quote.id not in org_b_ids

    async def test_persona_service_list_personas_filters_by_org_id(
        self,
        db: AsyncSession,
        am_inv_org: Organization,
        am_other_org: Organization,
    ):
        """PersonaService.list_personas() only returns personas for the given org_id."""
        from app.modules.investor_personas import service as persona_service
        from app.modules.investor_personas.schemas import PersonaCreate

        # Create a persona for the investor org
        inv_persona = await persona_service.create_persona(
            db,
            AM_INV_ORG_ID,
            PersonaCreate(persona_name="Inv Org Private Persona", strategy_type="impact_first"),
        )

        # Create a persona for the other org
        other_persona = await persona_service.create_persona(
            db,
            AM_OTHER_ORG_ID,
            PersonaCreate(persona_name="Other Org Persona", strategy_type="conservative"),
        )

        # Inv org should only see its own persona
        inv_personas = await persona_service.list_personas(db, AM_INV_ORG_ID)
        inv_ids = [p.id for p in inv_personas]
        assert inv_persona.id in inv_ids
        assert other_persona.id not in inv_ids

        # Other org should only see its own persona
        other_personas = await persona_service.list_personas(db, AM_OTHER_ORG_ID)
        other_ids = [p.id for p in other_personas]
        assert other_persona.id in other_ids
        assert inv_persona.id not in other_ids

    async def test_insurance_quote_response_carries_correct_org_id(
        self, am_client: AsyncClient, am_org: Organization
    ):
        """The org_id in the quote response matches the authenticated user's org."""
        resp = await am_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Org ID Check Insurer",
                "coverage_type": "third_party_liability",
                "coverage_amount": 500_000,
                "quoted_premium": 2_000,
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        # The org_id in the response must match the authenticated user's org
        assert data["org_id"] == str(AM_ORG_ID)
