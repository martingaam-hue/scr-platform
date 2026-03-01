"""Tests for C01–C08 modules.

Modules covered:
  C01 — Q&A Workflow       (/qa/...)
  C02 — Document Engagement (/engagement/...)
  C03 — Covenant & KPI Monitoring (/monitoring/...)
  C06 — J-Curve Pacing     (/pacing/...)
  C08 — Financial Templates (/financial-templates/...)
  C08 — Industry Taxonomy  (/taxonomy)
"""

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
from app.models.dataroom import Document
from app.models.enums import (
    DocumentStatus,
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
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs for C01-C08 fixtures ───────────────────────────────────────────

C_ORG_ID = uuid.UUID("00000000-0000-00C0-0000-000000000001")
C_USER_ID = uuid.UUID("00000000-0000-00C0-0000-000000000002")
C_PROJECT_ID = uuid.UUID("00000000-0000-00C0-0000-000000000003")
C_PORTFOLIO_ID = uuid.UUID("00000000-0000-00C0-0000-000000000004")
C_DOCUMENT_ID = uuid.UUID("00000000-0000-00C0-0000-000000000005")

# Second org for isolation tests
C_ORG2_ID = uuid.UUID("00000000-0000-00C0-0000-000000000010")
C_USER2_ID = uuid.UUID("00000000-0000-00C0-0000-000000000011")
C_PROJECT2_ID = uuid.UUID("00000000-0000-00C0-0000-000000000012")

CURRENT_USER = CurrentUser(
    user_id=C_USER_ID,
    org_id=C_ORG_ID,
    role=UserRole.ADMIN,
    email="c_test@example.com",
    external_auth_id="clerk_c_test",
)

CURRENT_USER2 = CurrentUser(
    user_id=C_USER2_ID,
    org_id=C_ORG2_ID,
    role=UserRole.ADMIN,
    email="c_test2@example.com",
    external_auth_id="clerk_c_test2",
)


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
async def c_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=C_ORG_ID,
        name="C Test Org",
        slug="c-test-org",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def c_user(db: AsyncSession, c_org: Organization) -> User:
    user = User(
        id=C_USER_ID,
        org_id=C_ORG_ID,
        email="c_test@example.com",
        full_name="C Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_c_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def c_project(db: AsyncSession, c_org: Organization) -> Project:
    proj = Project(
        id=C_PROJECT_ID,
        org_id=C_ORG_ID,
        name="C Test Solar Project",
        slug="c-test-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Germany",
        total_investment_required=Decimal("10000000"),
        currency="EUR",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def c_portfolio(db: AsyncSession, c_org: Organization) -> Portfolio:
    portfolio = Portfolio(
        id=C_PORTFOLIO_ID,
        org_id=C_ORG_ID,
        name="C Test Portfolio",
        description="Test portfolio for pacing tests",
        strategy=PortfolioStrategy.IMPACT,
        fund_type=FundType.CLOSED_END,
        vintage_year=2024,
        target_aum=Decimal("100000000"),
        current_aum=Decimal("50000000"),
        currency="EUR",
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


@pytest.fixture
async def c_document(db: AsyncSession, c_org: Organization, c_project: Project, c_user: User) -> Document:
    """Create a test document in the data room (needed for engagement FK)."""
    doc = Document(
        id=C_DOCUMENT_ID,
        org_id=C_ORG_ID,
        project_id=C_PROJECT_ID,
        name="Test Investment Memo.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        s3_key="test/documents/investment-memo.pdf",
        s3_bucket="scr-test",
        file_size_bytes=102400,
        status=DocumentStatus.READY,
        uploaded_by=C_USER_ID,
        checksum_sha256="abc123def456",
        is_deleted=False,
    )
    db.add(doc)
    await db.flush()
    return doc


@pytest.fixture
async def c_org2(db: AsyncSession) -> Organization:
    org = Organization(
        id=C_ORG2_ID,
        name="C Test Org 2",
        slug="c-test-org-2",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def c_user2(db: AsyncSession, c_org2: Organization) -> User:
    user = User(
        id=C_USER2_ID,
        org_id=C_ORG2_ID,
        email="c_test2@example.com",
        full_name="C Test User 2",
        role=UserRole.ADMIN,
        external_auth_id="clerk_c_test2",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def c_project2(db: AsyncSession, c_org2: Organization) -> Project:
    proj = Project(
        id=C_PROJECT2_ID,
        org_id=C_ORG2_ID,
        name="C Test Solar Project 2",
        slug="c-test-solar-project-2",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="France",
        total_investment_required=Decimal("5000000"),
        currency="EUR",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def c_client(db: AsyncSession, c_user: User) -> AsyncClient:
    """Authenticated AsyncClient for C01-C08 tests (org 1)."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def c_client2(db: AsyncSession, c_user2: User) -> AsyncClient:
    """Authenticated AsyncClient for C01-C08 tests (org 2 — isolation checks)."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER2
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


# ═══════════════════════════════════════════════════════════════════════════════
# C01 — Q&A Workflow
# ═══════════════════════════════════════════════════════════════════════════════


class TestQAWorkflow:
    """Tests for /qa/... endpoints (C01)."""

    async def test_create_question_201(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={
                "question": "What is the expected IRR for this project?",
                "category": "financial",
                "priority": "high",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["question"] == "What is the expected IRR for this project?"
        assert data["category"] == "financial"
        assert data["priority"] == "high"
        assert data["status"] == "open"
        assert data["project_id"] == str(C_PROJECT_ID)
        assert data["org_id"] == str(C_ORG_ID)
        assert "id" in data
        assert "question_number" in data
        assert data["question_number"] >= 1

    async def test_list_questions_empty(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.get(f"/qa/projects/{C_PROJECT_ID}/questions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_questions_after_create(
        self, c_client: AsyncClient, c_project: Project
    ):
        # Create a question first
        create_resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={
                "question": "What permits are needed?",
                "category": "legal",
            },
        )
        assert create_resp.status_code == 201

        # List should include it
        list_resp = await c_client.get(f"/qa/projects/{C_PROJECT_ID}/questions")
        assert list_resp.status_code == 200
        questions = list_resp.json()
        assert any(q["question"] == "What permits are needed?" for q in questions)

    async def test_list_questions_filter_by_status(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.get(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            params={"status": "open"},
        )
        assert resp.status_code == 200
        # All returned questions should be open status
        for q in resp.json():
            assert q["status"] == "open"

    async def test_get_question_by_id(
        self, c_client: AsyncClient, c_project: Project
    ):
        create_resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={
                "question": "What is the grid connection capacity?",
                "category": "technical",
            },
        )
        assert create_resp.status_code == 201
        question_id = create_resp.json()["id"]

        get_resp = await c_client.get(f"/qa/questions/{question_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == question_id
        assert data["question"] == "What is the grid connection capacity?"

    async def test_get_question_not_found(self, c_client: AsyncClient, c_project: Project):
        fake_id = uuid.uuid4()
        resp = await c_client.get(f"/qa/questions/{fake_id}")
        assert resp.status_code == 404

    async def test_answer_question_201(
        self, c_client: AsyncClient, c_project: Project
    ):
        # Create a question
        create_resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={
                "question": "What is the PPA contract duration?",
                "category": "commercial",
            },
        )
        assert create_resp.status_code == 201
        question_id = create_resp.json()["id"]

        # Answer the question
        answer_resp = await c_client.post(
            f"/qa/questions/{question_id}/answers",
            json={
                "content": "The PPA contract is for 20 years with an option to extend.",
                "is_official": True,
            },
        )
        assert answer_resp.status_code == 201, answer_resp.text
        data = answer_resp.json()
        assert data["content"] == "The PPA contract is for 20 years with an option to extend."
        assert data["is_official"] is True
        assert data["question_id"] == question_id
        assert data["answered_by"] == str(C_USER_ID)

    async def test_answer_nonexistent_question_404(
        self, c_client: AsyncClient, c_project: Project
    ):
        fake_id = uuid.uuid4()
        resp = await c_client.post(
            f"/qa/questions/{fake_id}/answers",
            json={"content": "Some answer", "is_official": False},
        )
        assert resp.status_code == 404

    async def test_qa_stats(
        self, c_client: AsyncClient, c_project: Project
    ):
        # Create a couple of questions so stats are non-trivial
        for i in range(2):
            await c_client.post(
                f"/qa/projects/{C_PROJECT_ID}/questions",
                json={
                    "question": f"Stats test question {i}",
                    "category": "esg",
                },
            )

        resp = await c_client.get(f"/qa/projects/{C_PROJECT_ID}/stats")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "total" in data
        assert "open" in data
        assert "answered" in data
        assert "overdue" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["open"], int)

    async def test_close_question_via_status_update(
        self, c_client: AsyncClient, c_project: Project
    ):
        create_resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={
                "question": "Will this question be closed?",
                "category": "operational",
            },
        )
        assert create_resp.status_code == 201
        question_id = create_resp.json()["id"]

        # Close the question
        close_resp = await c_client.put(
            f"/qa/questions/{question_id}/status",
            params={"status": "closed"},
        )
        assert close_resp.status_code == 200, close_resp.text
        assert close_resp.json()["status"] == "closed"

    async def test_question_isolation_across_orgs(
        self,
        c_client: AsyncClient,
        c_client2: AsyncClient,
        c_project: Project,
        c_project2: Project,
    ):
        """Questions created in org1's project should not be visible to org2."""
        # Create question under org1 project
        create_resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={
                "question": "Org1 confidential question",
                "category": "financial",
            },
        )
        assert create_resp.status_code == 201

        # Org2 should see empty list for its own project
        list_resp = await c_client2.get(f"/qa/projects/{C_PROJECT2_ID}/questions")
        assert list_resp.status_code == 200
        questions = list_resp.json()
        assert not any(
            q["question"] == "Org1 confidential question" for q in questions
        )

    async def test_export_qa_log_csv(
        self, c_client: AsyncClient, c_project: Project
    ):
        # Create a question so the export is not empty
        await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={"question": "CSV export test question?", "category": "regulatory"},
        )

        resp = await c_client.get(f"/qa/projects/{C_PROJECT_ID}/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    async def test_invalid_category_422(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.post(
            f"/qa/projects/{C_PROJECT_ID}/questions",
            json={"question": "Bad category question?", "category": "invalid_cat"},
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# C02 — Document Engagement
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentEngagement:
    """Tests for /engagement/... endpoints (C02)."""

    async def test_track_open_201(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Track a document open event — returns 201 with session details."""
        session_id = f"sess-{uuid.uuid4()}"

        resp = await c_client.post(
            "/engagement/track/open",
            json={
                "document_id": str(C_DOCUMENT_ID),
                "session_id": session_id,
                "total_pages": 10,
                "device_type": "desktop",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["document_id"] == str(C_DOCUMENT_ID)
        assert data["session_id"] == session_id
        assert data["user_id"] == str(C_USER_ID)
        assert data["org_id"] == str(C_ORG_ID)
        assert data["total_time_seconds"] == 0
        assert data["downloaded"] is False

    async def test_track_page_view_200(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Track a page view within an existing session."""
        # Open a session first
        open_resp = await c_client.post(
            "/engagement/track/open",
            json={
                "document_id": str(C_DOCUMENT_ID),
                "session_id": f"sess-{uuid.uuid4()}",
            },
        )
        assert open_resp.status_code == 201
        engagement_id = open_resp.json()["id"]

        # Track a page view
        page_resp = await c_client.post(
            "/engagement/track/page",
            json={
                "engagement_id": engagement_id,
                "page_number": 3,
                "time_seconds": 45,
            },
        )
        assert page_resp.status_code == 200, page_resp.text
        data = page_resp.json()
        assert data["id"] == engagement_id
        assert data["total_time_seconds"] >= 45

    async def test_track_close_200(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Track a document close event."""
        open_resp = await c_client.post(
            "/engagement/track/open",
            json={
                "document_id": str(C_DOCUMENT_ID),
                "session_id": f"sess-{uuid.uuid4()}",
            },
        )
        assert open_resp.status_code == 201
        engagement_id = open_resp.json()["id"]

        close_resp = await c_client.post(
            "/engagement/track/close",
            json={"engagement_id": engagement_id},
        )
        assert close_resp.status_code == 200, close_resp.text
        data = close_resp.json()
        assert data["id"] == engagement_id
        assert data["closed_at"] is not None

    async def test_track_download_200(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Track a document download event."""
        open_resp = await c_client.post(
            "/engagement/track/open",
            json={
                "document_id": str(C_DOCUMENT_ID),
                "session_id": f"sess-{uuid.uuid4()}",
            },
        )
        assert open_resp.status_code == 201
        engagement_id = open_resp.json()["id"]

        dl_resp = await c_client.post(
            "/engagement/track/download",
            json={"engagement_id": engagement_id},
        )
        assert dl_resp.status_code == 200, dl_resp.text
        data = dl_resp.json()
        assert data["downloaded"] is True

    async def test_track_page_nonexistent_session_404(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Tracking a page view for a non-existent session returns 404."""
        fake_engagement_id = uuid.uuid4()
        resp = await c_client.post(
            "/engagement/track/page",
            json={
                "engagement_id": str(fake_engagement_id),
                "page_number": 1,
                "time_seconds": 10,
            },
        )
        assert resp.status_code == 404

    async def test_get_document_analytics_200(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Get analytics for a document (including one that has sessions)."""
        # Create a session for this document
        await c_client.post(
            "/engagement/track/open",
            json={
                "document_id": str(C_DOCUMENT_ID),
                "session_id": f"sess-{uuid.uuid4()}",
                "total_pages": 5,
            },
        )

        resp = await c_client.get(f"/engagement/document/{C_DOCUMENT_ID}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["document_id"] == str(C_DOCUMENT_ID)
        assert "total_views" in data
        assert "unique_viewers" in data
        assert "total_time_seconds" in data
        assert "avg_completion_pct" in data
        assert "page_heatmap" in data
        assert "recent_sessions" in data
        assert data["total_views"] >= 1

    async def test_get_project_engagement_200(
        self, c_client: AsyncClient, c_project: Project
    ):
        """Get engagement summaries for all investors in a project."""
        resp = await c_client.get(f"/engagement/project/{C_PROJECT_ID}")
        assert resp.status_code == 200
        # Returns a list (may be empty if no investor sessions)
        assert isinstance(resp.json(), list)

    async def test_get_page_heatmap_200(
        self, c_client: AsyncClient, c_document: Document
    ):
        """Get page heatmap for a document — returns a dict of page→seconds."""
        # Open and view a page
        open_resp = await c_client.post(
            "/engagement/track/open",
            json={
                "document_id": str(C_DOCUMENT_ID),
                "session_id": f"sess-{uuid.uuid4()}",
            },
        )
        assert open_resp.status_code == 201
        engagement_id = open_resp.json()["id"]

        await c_client.post(
            "/engagement/track/page",
            json={"engagement_id": engagement_id, "page_number": 2, "time_seconds": 30},
        )

        resp = await c_client.get(f"/engagement/heatmap/{C_DOCUMENT_ID}")
        assert resp.status_code == 200
        # Heatmap is a dict with string-keyed page numbers
        heatmap = resp.json()
        assert isinstance(heatmap, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# C03 — Covenant & KPI Monitoring
# ═══════════════════════════════════════════════════════════════════════════════


class TestCovenantKPIMonitoring:
    """Tests for /monitoring/... endpoints (C03)."""

    async def test_create_covenant_201(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.post(
            f"/monitoring/covenants/{C_PROJECT_ID}",
            json={
                "name": "Minimum DSCR",
                "covenant_type": "financial",
                "metric_name": "dscr",
                "threshold_value": 1.25,
                "comparison": ">=",
                "check_frequency": "quarterly",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Minimum DSCR"
        assert data["metric_name"] == "dscr"
        assert data["covenant_type"] == "financial"
        assert data["comparison"] == ">="
        assert data["org_id"] == str(C_ORG_ID)
        assert data["project_id"] == str(C_PROJECT_ID)
        assert data["status"] == "compliant"
        assert "id" in data

    async def test_list_covenants_empty(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.get(f"/monitoring/covenants/{C_PROJECT_ID}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_covenants_after_create(
        self, c_client: AsyncClient, c_project: Project
    ):
        # Create a covenant
        create_resp = await c_client.post(
            f"/monitoring/covenants/{C_PROJECT_ID}",
            json={
                "name": "Equity Ratio",
                "covenant_type": "financial",
                "metric_name": "equity_ratio",
                "threshold_value": 0.25,
                "comparison": ">=",
            },
        )
        assert create_resp.status_code == 201

        list_resp = await c_client.get(f"/monitoring/covenants/{C_PROJECT_ID}")
        assert list_resp.status_code == 200
        covenants = list_resp.json()
        assert any(c["name"] == "Equity Ratio" for c in covenants)

    async def test_update_covenant_200(
        self, c_client: AsyncClient, c_project: Project
    ):
        create_resp = await c_client.post(
            f"/monitoring/covenants/{C_PROJECT_ID}",
            json={
                "name": "Leverage Ratio",
                "covenant_type": "financial",
                "metric_name": "leverage",
                "threshold_value": 3.0,
                "comparison": "<=",
            },
        )
        assert create_resp.status_code == 201
        covenant_id = create_resp.json()["id"]

        update_resp = await c_client.put(
            f"/monitoring/covenants/{covenant_id}",
            json={"threshold_value": 3.5, "check_frequency": "monthly"},
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()
        assert float(data["threshold_value"]) == pytest.approx(3.5, rel=1e-3)

    async def test_waive_covenant(
        self, c_client: AsyncClient, c_project: Project
    ):
        create_resp = await c_client.post(
            f"/monitoring/covenants/{C_PROJECT_ID}",
            json={
                "name": "Occupancy Covenant",
                "covenant_type": "operational",
                "metric_name": "occupancy_pct",
                "threshold_value": 90.0,
                "comparison": ">=",
            },
        )
        assert create_resp.status_code == 201
        covenant_id = create_resp.json()["id"]

        waive_resp = await c_client.post(
            f"/monitoring/covenants/{covenant_id}/waive",
            json={"reason": "COVID-19 temporary waiver approved by board"},
        )
        assert waive_resp.status_code == 200, waive_resp.text
        data = waive_resp.json()
        assert data["status"] == "waived"
        assert data["waived_reason"] == "COVID-19 temporary waiver approved by board"

    async def test_record_kpi_actual_201(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.post(
            f"/monitoring/kpis/{C_PROJECT_ID}",
            json={
                "kpi_name": "capacity_factor",
                "value": 0.32,
                "unit": "ratio",
                "period": "2025-Q1",
                "period_type": "quarterly",
                "source": "manual",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["kpi_name"] == "capacity_factor"
        assert float(data["value"]) == pytest.approx(0.32, rel=1e-3)
        assert data["period"] == "2025-Q1"
        assert data["org_id"] == str(C_ORG_ID)
        assert data["project_id"] == str(C_PROJECT_ID)

    async def test_list_kpi_actuals_200(
        self, c_client: AsyncClient, c_project: Project
    ):
        # Record a KPI first
        await c_client.post(
            f"/monitoring/kpis/{C_PROJECT_ID}",
            json={
                "kpi_name": "generation_mwh",
                "value": 1500.0,
                "unit": "MWh",
                "period": "2025-Q2",
                "period_type": "quarterly",
            },
        )

        resp = await c_client.get(f"/monitoring/kpis/{C_PROJECT_ID}")
        assert resp.status_code == 200
        actuals = resp.json()
        assert isinstance(actuals, list)
        assert any(a["kpi_name"] == "generation_mwh" for a in actuals)

    async def test_set_kpi_target_201(
        self, c_client: AsyncClient, c_project: Project
    ):
        resp = await c_client.post(
            f"/monitoring/kpis/{C_PROJECT_ID}/targets",
            json={
                "kpi_name": "capacity_factor",
                "target_value": 0.30,
                "period": "2025-Q1",
                "tolerance_pct": 0.05,
                "source": "business_plan",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["kpi_name"] == "capacity_factor"
        assert float(data["target_value"]) == pytest.approx(0.30, rel=1e-3)

    async def test_get_kpi_variance_200(
        self, c_client: AsyncClient, c_project: Project
    ):
        """Get variance after recording both actual and target for the same KPI+period."""
        period = "2026-Q1"
        kpi_name = "revenue_eur"

        # Target
        await c_client.post(
            f"/monitoring/kpis/{C_PROJECT_ID}/targets",
            json={
                "kpi_name": kpi_name,
                "target_value": 200000.0,
                "period": period,
            },
        )
        # Actual
        await c_client.post(
            f"/monitoring/kpis/{C_PROJECT_ID}",
            json={
                "kpi_name": kpi_name,
                "value": 210000.0,
                "unit": "EUR",
                "period": period,
            },
        )

        resp = await c_client.get(
            f"/monitoring/kpis/{C_PROJECT_ID}/variance",
            params={"period": period},
        )
        assert resp.status_code == 200, resp.text
        variance = resp.json()
        assert isinstance(variance, list)
        if variance:
            item = variance[0]
            assert "kpi" in item
            assert "actual" in item
            assert "target" in item
            assert "variance_pct" in item
            assert "status" in item

    async def test_covenant_isolation_across_orgs(
        self,
        c_client: AsyncClient,
        c_client2: AsyncClient,
        c_project: Project,
        c_project2: Project,
    ):
        """Covenants from org1's project must not appear in org2's project listing."""
        # Create a covenant in org1
        create_resp = await c_client.post(
            f"/monitoring/covenants/{C_PROJECT_ID}",
            json={
                "name": "Org1 Secret Covenant",
                "covenant_type": "financial",
                "metric_name": "secret_metric",
                "threshold_value": 1.0,
                "comparison": ">=",
            },
        )
        assert create_resp.status_code == 201

        # Org2 sees its own project's covenants — should not include org1's
        list_resp = await c_client2.get(f"/monitoring/covenants/{C_PROJECT2_ID}")
        assert list_resp.status_code == 200
        covenants = list_resp.json()
        assert not any(c["name"] == "Org1 Secret Covenant" for c in covenants)


# ═══════════════════════════════════════════════════════════════════════════════
# C06 — J-Curve Pacing
# ═══════════════════════════════════════════════════════════════════════════════


class TestJCurvePacing:
    """Tests for /pacing/... endpoints (C06)."""

    async def test_create_assumption_201(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        resp = await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "50000000",
                "investment_period_years": 5,
                "fund_life_years": 10,
                "optimistic_modifier": "1.20",
                "pessimistic_modifier": "0.80",
                "label": "Base Case 2026",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["portfolio_id"] == str(C_PORTFOLIO_ID)
        assert "assumption_id" in data
        assert "projections" in data
        assert len(data["projections"]) > 0
        assert "trough_year" in data
        assert "fund_life_years" in data
        assert data["fund_life_years"] == 10

    async def test_get_pacing_200(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """Create an assumption then retrieve pacing data."""
        # Create assumption
        create_resp = await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "25000000",
                "investment_period_years": 4,
                "fund_life_years": 8,
            },
        )
        assert create_resp.status_code == 201

        # Get pacing
        get_resp = await c_client.get(f"/pacing/portfolios/{C_PORTFOLIO_ID}")
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert data["portfolio_id"] == str(C_PORTFOLIO_ID)
        assert "trough_year" in data
        assert "projections" in data

    async def test_pacing_trough_year_present(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """J-curve trough year should be populated when projections are generated."""
        resp = await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "100000000",
                "investment_period_years": 5,
                "fund_life_years": 10,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        # Trough year should be set (early deployment phase has negative net cashflow)
        assert data["trough_year"] is not None
        assert 1 <= data["trough_year"] <= 10

    async def test_projections_all_three_scenarios(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """Three scenarios (base, optimistic, pessimistic) should be in projections."""
        resp = await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "50000000",
                "investment_period_years": 5,
                "fund_life_years": 10,
                "optimistic_modifier": "1.20",
                "pessimistic_modifier": "0.80",
            },
        )
        assert resp.status_code == 201
        projections = resp.json()["projections"]
        scenarios = {p["scenario"] for p in projections}
        assert "base" in scenarios
        assert "optimistic" in scenarios
        assert "pessimistic" in scenarios

    async def test_optimistic_differs_from_pessimistic(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """Optimistic and pessimistic projections should have different distribution values."""
        resp = await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "50000000",
                "investment_period_years": 5,
                "fund_life_years": 10,
                "optimistic_modifier": "1.30",
                "pessimistic_modifier": "0.70",
            },
        )
        assert resp.status_code == 201
        projections = resp.json()["projections"]

        optimistic_dist = [
            p["projected_distributions"]
            for p in projections
            if p["scenario"] == "optimistic"
        ]
        pessimistic_dist = [
            p["projected_distributions"]
            for p in projections
            if p["scenario"] == "pessimistic"
        ]

        # Find a year where both have nonzero distributions
        opt_nonzero = [float(v) for v in optimistic_dist if v and float(v) > 0]
        pess_nonzero = [float(v) for v in pessimistic_dist if v and float(v) > 0]

        if opt_nonzero and pess_nonzero:
            assert max(opt_nonzero) > max(pess_nonzero)

    async def test_list_assumptions_200(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """List assumptions for a portfolio."""
        # Create at least one
        await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "30000000",
                "investment_period_years": 5,
                "fund_life_years": 10,
            },
        )

        resp = await c_client.get(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions"
        )
        assert resp.status_code == 200, resp.text
        assumptions = resp.json()
        assert isinstance(assumptions, list)
        assert len(assumptions) >= 1
        # Check structure
        a = assumptions[0]
        assert "assumption_id" in a
        assert "portfolio_id" in a
        assert "committed_capital" in a
        assert "is_active" in a

    async def test_update_actuals_200(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """Update actual cashflow data for a specific year in a projection row."""
        # Create assumption
        create_resp = await c_client.post(
            f"/pacing/portfolios/{C_PORTFOLIO_ID}/assumptions",
            json={
                "portfolio_id": str(C_PORTFOLIO_ID),
                "committed_capital": "50000000",
                "investment_period_years": 5,
                "fund_life_years": 10,
            },
        )
        assert create_resp.status_code == 201
        assumption_id = create_resp.json()["assumption_id"]

        # Update actuals for year 1, base scenario
        update_resp = await c_client.put(
            f"/pacing/assumptions/{assumption_id}/actuals",
            params={"scenario": "base"},
            json={
                "year": 1,
                "actual_contributions": "15000000",
                "actual_distributions": "0",
            },
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()
        assert data["year"] == 1
        assert data["scenario"] == "base"
        assert data["actual_contributions"] is not None

    async def test_get_pacing_404_no_assumption(
        self, c_client: AsyncClient, c_portfolio: Portfolio
    ):
        """Getting pacing for a portfolio with no assumption returns 404."""
        fake_portfolio_id = uuid.uuid4()
        resp = await c_client.get(f"/pacing/portfolios/{fake_portfolio_id}")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# C08 — Financial Templates
# ═══════════════════════════════════════════════════════════════════════════════


class TestFinancialTemplates:
    """Tests for /financial-templates/... endpoints (C08)."""

    async def _seed_taxonomy_and_template(
        self, db: AsyncSession, org_id: uuid.UUID
    ) -> tuple[str, uuid.UUID]:
        """Insert a taxonomy node and a financial template, return (code, template_id)."""
        from app.models.financial_templates import FinancialTemplate
        from app.models.taxonomy import IndustryTaxonomy

        code = f"TEST.SOLAR.{uuid.uuid4().hex[:6].upper()}"

        node = IndustryTaxonomy(
            code=code,
            parent_code=None,
            name="Test Solar Utility",
            level=1,
            is_leaf=True,
        )
        db.add(node)
        await db.flush()

        template = FinancialTemplate(
            taxonomy_code=code,
            org_id=None,  # system template visible to all
            name="Solar Utility DCF",
            description="Standard solar utility DCF template",
            assumptions={
                "capacity_mw": {"default": 50, "min": 10, "max": 500, "unit": "MW"},
                "capex_per_mw": {"default": 900000, "unit": "EUR/MW"},
                "p50_irradiance_kwh_m2": {"default": 1800, "unit": "kWh/m2/yr"},
                "performance_ratio": {"default": 0.82},
                "ppa_price_eur_mwh": {"default": 55, "unit": "EUR/MWh"},
                "opex_eur_mw_yr": {"default": 15000},
                "project_life_years": {"default": 25},
                "discount_rate": {"default": 0.07},
                "debt_pct": {"default": 0.70},
            },
            revenue_formula={},
            cashflow_model={},
            is_system=True,
        )
        db.add(template)
        await db.flush()
        await db.refresh(template)
        return code, template.id

    async def test_list_templates_200(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """List templates — returns 200 with a list (may be empty if no migrations)."""
        resp = await c_client.get("/financial-templates")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_templates_after_seed(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """After seeding a template, it appears in the listing."""
        code, template_id = await self._seed_taxonomy_and_template(db, C_ORG_ID)

        resp = await c_client.get("/financial-templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert any(t["id"] == str(template_id) for t in templates)

    async def test_get_template_200(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Fetch a single template by ID."""
        code, template_id = await self._seed_taxonomy_and_template(db, C_ORG_ID)

        resp = await c_client.get(f"/financial-templates/{template_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == str(template_id)
        assert data["name"] == "Solar Utility DCF"
        assert "assumptions" in data
        assert "is_system" in data

    async def test_get_template_404(
        self, c_client: AsyncClient, c_org: Organization
    ):
        fake_id = uuid.uuid4()
        resp = await c_client.get(f"/financial-templates/{fake_id}")
        assert resp.status_code == 404

    async def test_compute_dcf_200(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Run a DCF computation — should return npv, irr, annual_cashflows."""
        code, template_id = await self._seed_taxonomy_and_template(db, C_ORG_ID)

        resp = await c_client.post(
            f"/financial-templates/{template_id}/compute",
            json={
                "overrides": {
                    "capacity_mw": 100,
                    "ppa_price_eur_mwh": 60,
                }
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "npv" in data
        assert "annual_cashflows" in data
        assert "levered_cashflows" in data
        assert "assumptions_used" in data
        # NPV is a numeric value (can be negative)
        assert isinstance(float(data["npv"]), float)
        # Annual cashflows should span project life
        assert len(data["annual_cashflows"]) > 1

    async def test_compute_dcf_404_bad_template(
        self, c_client: AsyncClient, c_org: Organization
    ):
        fake_id = uuid.uuid4()
        resp = await c_client.post(
            f"/financial-templates/{fake_id}/compute",
            json={"overrides": {}},
        )
        assert resp.status_code == 404

    async def test_list_templates_filter_by_taxonomy(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Filtering templates by taxonomy_code should narrow results."""
        code, template_id = await self._seed_taxonomy_and_template(db, C_ORG_ID)

        resp = await c_client.get(
            "/financial-templates", params={"taxonomy_code": code}
        )
        assert resp.status_code == 200
        templates = resp.json()
        # All returned templates should match the requested taxonomy_code
        for t in templates:
            assert t["taxonomy_code"] == code


# ═══════════════════════════════════════════════════════════════════════════════
# C08 (part 2) — Industry Taxonomy
# ═══════════════════════════════════════════════════════════════════════════════


class TestIndustryTaxonomy:
    """Tests for /taxonomy endpoints (C08 taxonomy part)."""

    async def _seed_nodes(self, db: AsyncSession) -> tuple[str, str]:
        """Seed parent + child taxonomy nodes; return (parent_code, child_code)."""
        from app.models.taxonomy import IndustryTaxonomy

        parent_code = f"RENEW_{uuid.uuid4().hex[:4].upper()}"
        child_code = f"{parent_code}.SOLAR"

        parent = IndustryTaxonomy(
            code=parent_code,
            parent_code=None,
            name="Renewable Energy Test",
            level=1,
            is_leaf=False,
        )
        child = IndustryTaxonomy(
            code=child_code,
            parent_code=parent_code,
            name="Solar Power Test",
            level=2,
            is_leaf=True,
            nace_code="D.35.1",
        )
        db.add(parent)
        db.add(child)
        await db.flush()
        return parent_code, child_code

    async def test_list_taxonomy_200(
        self, c_client: AsyncClient, c_org: Organization
    ):
        """GET /taxonomy returns 200 with a list."""
        resp = await c_client.get("/taxonomy")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_taxonomy_after_seed(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Seeded taxonomy nodes appear in the listing."""
        parent_code, child_code = await self._seed_nodes(db)

        resp = await c_client.get("/taxonomy")
        assert resp.status_code == 200
        nodes = resp.json()
        codes = {n["code"] for n in nodes}
        assert parent_code in codes
        assert child_code in codes

    async def test_taxonomy_response_fields(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Each taxonomy node should have the expected fields."""
        await self._seed_nodes(db)

        resp = await c_client.get("/taxonomy")
        assert resp.status_code == 200
        nodes = resp.json()
        if nodes:
            node = nodes[0]
            assert "code" in node
            assert "name" in node
            assert "level" in node
            assert "is_leaf" in node
            assert "parent_code" in node

    async def test_taxonomy_filter_by_parent_code(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Filtering by parent_code returns only children of that parent."""
        parent_code, child_code = await self._seed_nodes(db)

        resp = await c_client.get(
            "/taxonomy", params={"parent_code": parent_code}
        )
        assert resp.status_code == 200
        nodes = resp.json()
        # All returned nodes must have the given parent_code
        for node in nodes:
            assert node["parent_code"] == parent_code
        # Our seeded child should be included
        codes = {n["code"] for n in nodes}
        assert child_code in codes

    async def test_taxonomy_filter_leaf_only(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """leaf_only=true should return only leaf nodes."""
        parent_code, child_code = await self._seed_nodes(db)

        resp = await c_client.get("/taxonomy", params={"leaf_only": True})
        assert resp.status_code == 200
        nodes = resp.json()
        for node in nodes:
            assert node["is_leaf"] is True

    async def test_taxonomy_filter_by_level(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """Filtering by level=2 should return only level-2 nodes."""
        parent_code, child_code = await self._seed_nodes(db)

        resp = await c_client.get("/taxonomy", params={"level": 2})
        assert resp.status_code == 200
        nodes = resp.json()
        for node in nodes:
            assert node["level"] == 2

    async def test_get_taxonomy_node_200(
        self, c_client: AsyncClient, db: AsyncSession, c_org: Organization
    ):
        """GET /taxonomy/{code} returns a single node."""
        parent_code, child_code = await self._seed_nodes(db)

        resp = await c_client.get(f"/taxonomy/{child_code}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["code"] == child_code
        assert data["parent_code"] == parent_code
        assert data["is_leaf"] is True

    async def test_get_taxonomy_node_404(
        self, c_client: AsyncClient, c_org: Organization
    ):
        """GET /taxonomy/{code} for non-existent code returns 404."""
        resp = await c_client.get("/taxonomy/NONEXISTENT_CODE_XYZ")
        assert resp.status_code == 404
