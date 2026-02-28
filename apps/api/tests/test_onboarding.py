"""Tests for the onboarding module."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization, User
from app.models.dataroom import DocumentFolder
from app.models.enums import OrgType, PortfolioStrategy, RiskTolerance, UserRole
from app.models.investors import InvestorMandate, Portfolio
from app.models.projects import Project
from app.modules.onboarding.service import complete_onboarding
from app.schemas.auth import CurrentUser
from tests.conftest import SAMPLE_CLERK_ID, SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.anyio


# ── Service tests ────────────────────────────────────────────────────────


class TestOnboardingServiceInvestor:
    """Investor onboarding flow."""

    async def test_updates_org_type_to_investor(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital",
            org_industry="energy",
            org_geography="Europe",
            org_aum="50000000",
            preferences={
                "sectors": ["solar", "wind"],
                "geographies": ["Europe", "North America"],
                "stages": ["development", "construction"],
                "ticket_size_min": "1000000",
                "ticket_size_max": "10000000",
                "risk_tolerance": "moderate",
            },
        )
        result = await complete_onboarding(db, sample_current_user, data)

        assert result["success"] is True
        assert result["org_type"] == "investor"
        assert result["redirect_to"] == "/dashboard/portfolio"

        # Org updated
        org = await db.get(Organization, SAMPLE_ORG_ID)
        assert org.type == OrgType.INVESTOR
        assert org.name == "Acme Capital"
        assert org.settings["industry"] == "energy"
        assert org.settings["aum"] == "50000000"

    async def test_creates_default_portfolio(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital",
            org_aum="50000000",
            preferences={"risk_tolerance": "moderate"},
        )
        result = await complete_onboarding(db, sample_current_user, data)

        assert "portfolio_id" in result["created_entities"]
        portfolio = await db.get(Portfolio, uuid.UUID(result["created_entities"]["portfolio_id"]))
        assert portfolio is not None
        assert portfolio.name == "Acme Capital Portfolio"
        assert portfolio.strategy == PortfolioStrategy.BALANCED

    async def test_creates_investor_mandate(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital",
            preferences={
                "sectors": ["solar"],
                "geographies": ["Europe"],
                "risk_tolerance": "conservative",
            },
        )
        result = await complete_onboarding(db, sample_current_user, data)

        assert "mandate_id" in result["created_entities"]
        mandate = await db.get(InvestorMandate, uuid.UUID(result["created_entities"]["mandate_id"]))
        assert mandate is not None
        assert mandate.sectors == ["solar"]
        assert mandate.risk_tolerance == RiskTolerance.CONSERVATIVE

    async def test_creates_investor_folders(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital",
            preferences={"risk_tolerance": "moderate"},
        )
        result = await complete_onboarding(db, sample_current_user, data)

        folder_ids = result["created_entities"]["folder_ids"]
        assert len(folder_ids) == 3

        folders = []
        for fid in folder_ids:
            f = await db.get(DocumentFolder, uuid.UUID(fid))
            folders.append(f)

        folder_names = {f.name for f in folders}
        assert folder_names == {"Due Diligence", "Legal Documents", "Financial Reports"}
        assert all(f.project_id is None for f in folders)

    async def test_sets_onboarding_completed_preference(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital",
            preferences={"risk_tolerance": "aggressive"},
        )
        await complete_onboarding(db, sample_current_user, data)

        user = await db.get(User, SAMPLE_USER_ID)
        assert user.preferences["onboarding_completed"] is True
        assert user.preferences["risk_tolerance"] == "aggressive"


class TestOnboardingServiceAlly:
    """Ally onboarding flow."""

    async def test_updates_org_type_to_ally(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="ally",
            org_name="GreenTech Corp",
            org_industry="energy",
            org_size="11-50",
            preferences={"primary_technology": "solar"},
        )
        result = await complete_onboarding(db, sample_current_user, data)

        assert result["success"] is True
        assert result["org_type"] == "ally"
        assert result["redirect_to"] == "/dashboard/projects"

        org = await db.get(Organization, SAMPLE_ORG_ID)
        assert org.type == OrgType.ALLY
        assert org.name == "GreenTech Corp"
        assert org.settings["size"] == "11-50"

    async def test_creates_first_project_when_provided(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="ally",
            org_name="GreenTech Corp",
            preferences={},
            first_action={
                "name": "Solar Farm Alpha",
                "project_type": "solar",
                "geography_country": "Germany",
                "total_investment_required": "5000000",
            },
        )
        result = await complete_onboarding(db, sample_current_user, data)

        assert "project_id" in result["created_entities"]
        project = await db.get(Project, uuid.UUID(result["created_entities"]["project_id"]))
        assert project is not None
        assert project.name == "Solar Farm Alpha"

    async def test_creates_project_folders_when_project_provided(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="ally",
            org_name="GreenTech Corp",
            preferences={},
            first_action={
                "name": "Solar Farm Alpha",
                "project_type": "solar",
                "geography_country": "Germany",
                "total_investment_required": "5000000",
            },
        )
        result = await complete_onboarding(db, sample_current_user, data)

        folder_ids = result["created_entities"]["folder_ids"]
        assert len(folder_ids) == 3

        folders = []
        for fid in folder_ids:
            f = await db.get(DocumentFolder, uuid.UUID(fid))
            folders.append(f)

        folder_names = {f.name for f in folders}
        assert folder_names == {"Technical Documents", "Financial Models", "Legal & Permits"}
        # Folders linked to the project
        project_id = uuid.UUID(result["created_entities"]["project_id"])
        assert all(f.project_id == project_id for f in folders)

    async def test_creates_org_folders_when_no_first_action(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="ally",
            org_name="GreenTech Corp",
            preferences={},
        )
        result = await complete_onboarding(db, sample_current_user, data)

        assert "project_id" not in result["created_entities"]
        folder_ids = result["created_entities"]["folder_ids"]
        assert len(folder_ids) == 3

        folders = []
        for fid in folder_ids:
            f = await db.get(DocumentFolder, uuid.UUID(fid))
            folders.append(f)

        folder_names = {f.name for f in folders}
        assert folder_names == {"Project Templates", "Compliance", "Reports"}
        assert all(f.project_id is None for f in folders)


class TestOnboardingIdempotent:
    """Second onboarding call should succeed without errors."""

    async def test_second_call_succeeds(
        self, db: AsyncSession, sample_user: User, sample_current_user: CurrentUser
    ):
        from app.modules.onboarding.schemas import OnboardingCompleteRequest

        data = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital",
            preferences={"risk_tolerance": "moderate"},
        )
        r1 = await complete_onboarding(db, sample_current_user, data)
        assert r1["success"] is True

        # Second call — different name, still succeeds
        data2 = OnboardingCompleteRequest(
            org_type="investor",
            org_name="Acme Capital Updated",
            preferences={"risk_tolerance": "aggressive"},
        )
        r2 = await complete_onboarding(db, sample_current_user, data2)
        assert r2["success"] is True

        org = await db.get(Organization, SAMPLE_ORG_ID)
        assert org.name == "Acme Capital Updated"

        user = await db.get(User, SAMPLE_USER_ID)
        assert user.preferences["risk_tolerance"] == "aggressive"


# ── API endpoint tests ───────────────────────────────────────────────────


class TestOnboardingEndpoint:
    """Test PUT /onboarding/complete via the HTTP client."""

    async def test_complete_investor(
        self, authenticated_client, sample_user
    ):
        response = await authenticated_client.put(
            "/onboarding/complete",
            json={
                "org_type": "investor",
                "org_name": "API Test Capital",
                "org_aum": "100000000",
                "preferences": {"risk_tolerance": "moderate"},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["org_type"] == "investor"
        assert body["redirect_to"] == "/dashboard/portfolio"
        assert "portfolio_id" in body["created_entities"]
        assert "mandate_id" in body["created_entities"]
        assert len(body["created_entities"]["folder_ids"]) == 3

    async def test_complete_ally_with_project(
        self, authenticated_client, sample_user
    ):
        response = await authenticated_client.put(
            "/onboarding/complete",
            json={
                "org_type": "ally",
                "org_name": "API Test GreenTech",
                "preferences": {},
                "first_action": {
                    "name": "Wind Farm Beta",
                    "project_type": "wind",
                    "geography_country": "Netherlands",
                    "total_investment_required": "20000000",
                },
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["org_type"] == "ally"
        assert body["redirect_to"] == "/dashboard/projects"
        assert "project_id" in body["created_entities"]

    async def test_complete_ally_without_project(
        self, authenticated_client, sample_user
    ):
        response = await authenticated_client.put(
            "/onboarding/complete",
            json={
                "org_type": "ally",
                "org_name": "API Test GreenTech",
                "preferences": {},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "project_id" not in body["created_entities"]
        assert len(body["created_entities"]["folder_ids"]) == 3

    async def test_missing_org_name_returns_422(
        self, authenticated_client, sample_user
    ):
        response = await authenticated_client.put(
            "/onboarding/complete",
            json={
                "org_type": "investor",
                "preferences": {},
            },
        )
        assert response.status_code == 422

    async def test_invalid_org_type_returns_422(
        self, authenticated_client, sample_user
    ):
        response = await authenticated_client.put(
            "/onboarding/complete",
            json={
                "org_type": "unknown",
                "org_name": "Bad Type Corp",
                "preferences": {},
            },
        )
        assert response.status_code == 422

    async def test_unauthenticated_returns_403(self, client):
        response = await client.put(
            "/onboarding/complete",
            json={
                "org_type": "investor",
                "org_name": "Unauth Corp",
                "preferences": {},
            },
        )
        assert response.status_code == 403

    async def test_empty_org_name_returns_422(
        self, authenticated_client, sample_user
    ):
        response = await authenticated_client.put(
            "/onboarding/complete",
            json={
                "org_type": "investor",
                "org_name": "",
                "preferences": {},
            },
        )
        assert response.status_code == 422
