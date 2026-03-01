"""Tests for the Legal Document Manager module."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    LegalDocumentStatus,
    LegalDocumentType,
    OrgType,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.legal import LegalDocument
from app.models.projects import Project
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs for this module ──────────────────────────────────────────────

LG_ORG_ID = uuid.UUID("00000000-0000-0003-0000-000000000001")
LG_USER_ID = uuid.UUID("00000000-0000-0003-0000-000000000002")
LG_PROJECT_ID = uuid.UUID("00000000-0000-0003-0000-000000000003")

LG_CURRENT_USER = CurrentUser(
    user_id=LG_USER_ID,
    org_id=LG_ORG_ID,
    role=UserRole.ADMIN,
    email="legal_test@example.com",
    external_auth_id="clerk_legal_test",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def lg_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=LG_ORG_ID,
        name="Legal Test Org",
        slug="legal-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def lg_user(db: AsyncSession, lg_org: Organization) -> User:
    user = User(
        id=LG_USER_ID,
        org_id=LG_ORG_ID,
        email="legal_test@example.com",
        full_name="Legal Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_legal_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def lg_project(db: AsyncSession, lg_org: Organization) -> Project:
    proj = Project(
        id=LG_PROJECT_ID,
        org_id=LG_ORG_ID,
        name="Legal Test Project",
        slug="legal-test-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="England",
        total_investment_required=Decimal("3000000"),
        currency="GBP",
        is_published=True,
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def lg_client(db: AsyncSession, lg_user: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: LG_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestLegalTemplates:
    """Tests for /v1/legal/templates and /v1/legal/jurisdictions."""

    async def test_list_templates_returns_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/templates returns a non-empty list of templates."""
        resp = await lg_client.get("/v1/legal/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "doc_type" in first
        assert "description" in first
        assert "estimated_pages" in first

    async def test_list_templates_includes_nda(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """Template list includes the standard NDA template."""
        resp = await lg_client.get("/v1/legal/templates")
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert "nda_standard" in ids

    async def test_get_template_detail_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/templates/{id} for a known template returns 200 with questionnaire."""
        resp = await lg_client.get("/v1/legal/templates/nda_standard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "nda_standard"
        assert "questionnaire" in data
        assert "sections" in data["questionnaire"]

    async def test_get_template_not_found_returns_404(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/templates/{id} for an unknown template returns 404."""
        resp = await lg_client.get("/v1/legal/templates/nonexistent_template_xyz")
        assert resp.status_code == 404

    async def test_list_jurisdictions_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/jurisdictions returns a list of jurisdiction strings."""
        resp = await lg_client.get("/v1/legal/jurisdictions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert "England & Wales" in data


class TestLegalDocuments:
    """Tests for /v1/legal/documents CRUD operations."""

    async def test_list_documents_empty_returns_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/documents returns 200 with empty items when no docs exist."""
        resp = await lg_client.get("/v1/legal/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_create_document_201(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """POST /v1/legal/documents with valid template_id and title returns 201."""
        resp = await lg_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "nda_standard",
                "title": "Test NDA Agreement",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "Test NDA Agreement"
        assert data["doc_type"] == "nda"
        assert data["status"] == "draft"
        assert "id" in data

    async def test_create_document_invalid_template_422(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """POST /v1/legal/documents with unknown template_id returns 422."""
        resp = await lg_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "nonexistent_template_xyz",
                "title": "Should Fail",
            },
        )
        assert resp.status_code == 422

    async def test_get_document_after_create_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """Create then GET a document by ID returns 200 with matching data."""
        create_resp = await lg_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "term_sheet_equity",
                "title": "Test Term Sheet",
            },
        )
        assert create_resp.status_code == 201
        doc_id = create_resp.json()["id"]

        get_resp = await lg_client.get(f"/v1/legal/documents/{doc_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == doc_id
        assert data["title"] == "Test Term Sheet"

    async def test_get_document_not_found_404(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/documents/{id} for an unknown ID returns 404."""
        resp = await lg_client.get(
            "/v1/legal/documents/00000000-0000-0000-0000-000000000099"
        )
        assert resp.status_code == 404

    async def test_update_document_answers_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """PUT /v1/legal/documents/{id} updates questionnaire answers and returns 200."""
        create_resp = await lg_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "nda_standard",
                "title": "NDA Update Test",
            },
        )
        assert create_resp.status_code == 201
        doc_id = create_resp.json()["id"]

        put_resp = await lg_client.put(
            f"/v1/legal/documents/{doc_id}",
            json={
                "questionnaire_answers": {
                    "disclosing_party": "Acme Corp",
                    "receiving_party": "Beta Ventures",
                    "governing_law": "England & Wales",
                    "duration_years": "2 years",
                    "nda_type": "Mutual (both parties)",
                    "purpose": "Evaluation of renewable energy investment",
                }
            },
        )
        assert put_resp.status_code == 200, put_resp.text
        data = put_resp.json()
        assert data["id"] == doc_id

    async def test_create_document_appears_in_list(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """A created document appears in the list response."""
        create_resp = await lg_client.post(
            "/v1/legal/documents",
            json={
                "template_id": "side_letter",
                "title": "Side Letter List Test",
            },
        )
        assert create_resp.status_code == 201
        doc_id = create_resp.json()["id"]

        list_resp = await lg_client.get("/v1/legal/documents")
        assert list_resp.status_code == 200
        ids = [d["id"] for d in list_resp.json()["items"]]
        assert doc_id in ids


class TestLegalReview:
    """Tests for POST /v1/legal/review and GET /v1/legal/review/{review_id}."""

    async def test_review_with_text_returns_202(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """POST /v1/legal/review with document_text returns 202 with review_id."""
        resp = await lg_client.post(
            "/v1/legal/review",
            json={
                "document_text": (
                    "This agreement is entered into between Party A and Party B "
                    "for the purpose of evaluating a potential investment. "
                    "Confidentiality obligations last for 2 years."
                ),
                "mode": "risk_focused",
                "jurisdiction": "England & Wales",
            },
        )
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert "review_id" in data
        assert data["status"] == "accepted"

    async def test_review_missing_both_fields_returns_422(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """POST /v1/legal/review with neither document_id nor document_text returns 422."""
        resp = await lg_client.post(
            "/v1/legal/review",
            json={
                "mode": "risk_focused",
            },
        )
        assert resp.status_code == 422

    async def test_review_invalid_mode_returns_422(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """POST /v1/legal/review with invalid mode returns 422."""
        resp = await lg_client.post(
            "/v1/legal/review",
            json={
                "document_text": "Some contract text here.",
                "mode": "invalid_mode_xyz",
            },
        )
        assert resp.status_code == 422

    async def test_get_review_result_after_submit_200(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """Submit a review then GET the result by review_id returns 200."""
        submit_resp = await lg_client.post(
            "/v1/legal/review",
            json={
                "document_text": "This NDA between Discloser and Recipient is valid for one year.",
                "mode": "comprehensive",
                "jurisdiction": "Delaware",
            },
        )
        assert submit_resp.status_code == 202
        review_id = submit_resp.json()["review_id"]

        get_resp = await lg_client.get(f"/v1/legal/review/{review_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert str(data["review_id"]) == review_id
        assert "status" in data
        assert "clause_analyses" in data

    async def test_get_review_not_found_404(
        self, lg_client: AsyncClient, lg_user: User
    ) -> None:
        """GET /v1/legal/review/{id} for unknown review returns 404."""
        resp = await lg_client.get(
            f"/v1/legal/review/{uuid.uuid4()}"
        )
        assert resp.status_code == 404
