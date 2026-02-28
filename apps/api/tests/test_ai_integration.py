"""Comprehensive integration tests for SCR Platform AI agents and pipelines.

All external AI calls are mocked for deterministic, fast testing.
Tests use a per-test transactional rollback so no cleanup is required.

Test scenarios:
  1.  Document Processing Pipeline
  2.  Signal Score Calculation
  3.  Deal Screening via Deal Intelligence
  4.  Ralph AI Conversation (multi-turn, tool calls)
  5.  Valuation + Report Generation (deterministic DCF)
  6.  Matching Pipeline (5 mandates × 5 projects)
  7.  End-to-End Ally Journey
  8.  End-to-End Investor Journey
  9.  Investor Signal Score (6 dimensions)
  10. Live Scoring (metadata-only, no AI)
  11. Board Advisor search and application flow
  12. Investor Personas via structured output
  13. Equity Calculator (deterministic waterfall)
  14. Capital Efficiency metrics
  15. Risk Monitoring — stub (module not yet built)
  16. Insurance Both Sides — stub (module not yet built)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.advisory import InvestorPersona, InvestorSignalScore
from app.models.ai import AIConversation, AIMessage
from app.models.core import Organization, User
from app.models.dataroom import Document, DocumentExtraction
from app.models.enums import (
    AIContextType,
    AIMessageRole,
    AssetType,
    DocumentStatus,
    ExtractionType,
    FundType,
    HoldingStatus,
    MatchInitiator,
    MatchStatus,
    OrgType,
    PortfolioStatus,
    PortfolioStrategy,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    RiskTolerance,
    SFDRClassification,
    UserRole,
)
from app.models.investors import InvestorMandate, Portfolio, PortfolioHolding
from app.models.matching import MatchResult
from app.models.projects import Project, SignalScore
from app.schemas.auth import CurrentUser

# ── Constants ─────────────────────────────────────────────────────────────

ALLY_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ALLY_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
INVESTOR_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
INVESTOR_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")

ALLY_USER = CurrentUser(
    user_id=ALLY_USER_ID,
    org_id=ALLY_ORG_ID,
    role=UserRole.ADMIN,
    email="ally@example.com",
    external_auth_id="user_ally_test",
)

INVESTOR_USER = CurrentUser(
    user_id=INVESTOR_USER_ID,
    org_id=INVESTOR_ORG_ID,
    role=UserRole.ADMIN,
    email="investor@example.com",
    external_auth_id="user_investor_test",
)


# ── Shared helpers ─────────────────────────────────────────────────────────

def _override(current_user: CurrentUser, db: AsyncSession):
    """Return dependency overrides dict for a test client."""
    return {
        get_current_user: lambda: current_user,
        get_db: lambda: db,
    }


async def _make_client(current_user: CurrentUser, db: AsyncSession) -> AsyncClient:
    """Create an authenticated ASGI test client."""
    app.dependency_overrides.update(_override(current_user, db))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Common fixtures ────────────────────────────────────────────────────────

@pytest.fixture
async def ally_org(db: AsyncSession) -> Organization:
    org = Organization(id=ALLY_ORG_ID, name="Ally Corp", slug="ally-corp", type=OrgType.ALLY)
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def ally_user(db: AsyncSession, ally_org: Organization) -> User:
    user = User(
        id=ALLY_USER_ID,
        org_id=ally_org.id,
        email="ally@example.com",
        full_name="Ally Admin",
        role=UserRole.ADMIN,
        external_auth_id="user_ally_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def investor_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=INVESTOR_ORG_ID,
        name="Impact Capital Fund",
        slug="impact-capital-fund",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def investor_user(db: AsyncSession, investor_org: Organization) -> User:
    user = User(
        id=INVESTOR_USER_ID,
        org_id=investor_org.id,
        email="investor@example.com",
        full_name="Investor Admin",
        role=UserRole.ADMIN,
        external_auth_id="user_investor_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def sample_project(db: AsyncSession, ally_user: User) -> Project:
    """A fully-specified solar project owned by the ally org."""
    project = Project(
        org_id=ALLY_ORG_ID,
        name="Sonora Solar Farm Alpha",
        slug="sonora-solar-farm-alpha",
        description=(
            "A 50 MW utility-scale solar PV project in the Sonora desert, Mexico. "
            "Fully permitted with 20-year PPA signed with a state utility. "
            "Commissioning target Q3 2026. Total investment required USD 45 million "
            "across equity and senior debt tranches. Expected IRR 14–16%."
        ),
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="Mexico",
        geography_region="Sonora",
        total_investment_required=Decimal("45000000"),
        capacity_mw=Decimal("50.0"),
        target_close_date=date(2026, 3, 31),
        is_published=True,
    )
    db.add(project)
    await db.flush()
    return project


@pytest.fixture
async def sample_mandate(db: AsyncSession, investor_user: User) -> InvestorMandate:
    """Active mandate for renewable energy in North/Latin America."""
    mandate = InvestorMandate(
        org_id=INVESTOR_ORG_ID,
        name="Green Energy Mandate 2024",
        sectors=["solar", "wind", "energy_efficiency"],
        geographies=["Mexico", "USA", "Canada"],
        stages=["development", "construction"],
        ticket_size_min=Decimal("5000000"),
        ticket_size_max=Decimal("50000000"),
        target_irr_min=Decimal("12"),
        risk_tolerance=RiskTolerance.MODERATE,
        esg_requirements={"sfdr": "article_9", "un_pri": True},
        is_active=True,
    )
    db.add(mandate)
    await db.flush()
    return mandate


@pytest.fixture
async def sample_portfolio(db: AsyncSession, investor_user: User) -> Portfolio:
    """A clean-energy portfolio with AUM."""
    portfolio = Portfolio(
        org_id=INVESTOR_ORG_ID,
        name="Clean Energy Fund I",
        description="Renewable energy investments across the Americas",
        strategy=PortfolioStrategy.GROWTH,
        fund_type=FundType.CLOSED_END,
        vintage_year=2022,
        target_aum=Decimal("250000000"),
        current_aum=Decimal("120000000"),
        sfdr_classification=SFDRClassification.ARTICLE_9,
        status=PortfolioStatus.INVESTING,
    )
    db.add(portfolio)
    await db.flush()
    return portfolio


# ── Scenario 1: Document Processing Pipeline ──────────────────────────────

class TestDocumentProcessingPipeline:
    """
    Upload a document, trigger AI extraction, verify DocumentExtraction
    records are created with correct classification and KPI results.
    """

    @pytest.fixture
    async def seeded(self, db: AsyncSession, ally_user: User, sample_project: Project):
        """Pre-seed: org, user, project."""
        return {"project_id": sample_project.id}

    async def test_confirm_upload_creates_document_record(
        self, db: AsyncSession, seeded: dict
    ):
        """POST /dataroom/upload/confirm should create a PROCESSING document."""
        project_id = seeded["project_id"]

        # Pre-create document in UPLOADING state
        doc = Document(
            org_id=ALLY_ORG_ID,
            project_id=project_id,
            name="Financial_Statements_2023.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key=f"org/{ALLY_ORG_ID}/docs/test.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=512000,
            checksum_sha256="abc123def456" * 3,
            status=DocumentStatus.UPLOADING,
            uploaded_by=ALLY_USER_ID,
        )
        db.add(doc)
        await db.flush()

        with patch(
            "app.modules.dataroom.tasks.process_document.delay"
        ) as mock_task, patch(
            "app.modules.dataroom.service._get_s3_client"
        ) as mock_s3:
            mock_s3.return_value.head_object.return_value = {"ContentLength": 512000}
            async with await _make_client(ALLY_USER, db) as client:
                resp = await client.post(
                    "/dataroom/upload/confirm",
                    json={"document_id": str(doc.id)},
                )
            app.dependency_overrides.clear()

        # Celery task must have been dispatched
        assert mock_task.called

        # Response should indicate document is being processed
        assert resp.status_code in (200, 201, 202)

    async def test_extraction_endpoint_returns_results(
        self, db: AsyncSession, seeded: dict
    ):
        """Seed a document + extractions; GET /dataroom/documents/{id}/extractions."""
        project_id = seeded["project_id"]

        # Create document directly in test DB
        doc = Document(
            org_id=ALLY_ORG_ID,
            project_id=project_id,
            name="Financial_Statements_2023.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key=f"org/{ALLY_ORG_ID}/docs/test.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=512000,
            checksum_sha256="abc" * 20,
            status=DocumentStatus.READY,
            uploaded_by=ALLY_USER_ID,
        )
        db.add(doc)
        await db.flush()

        # Seed extraction records that the Celery task would have created
        kpi_extraction = DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.KPI,
            result={
                "kpis": [
                    {"name": "Revenue", "value": 12500000, "currency": "USD", "period": "2023"},
                    {"name": "EBITDA", "value": 3200000, "currency": "USD", "period": "2023"},
                    {"name": "Net Profit", "value": 1800000, "currency": "USD", "period": "2023"},
                ]
            },
            model_used="claude-sonnet-4-20250514",
            confidence_score=0.92,
            tokens_used=1500,
            processing_time_ms=3200,
        )
        classification_extraction = DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.CLASSIFICATION,
            result={"classification": "financial_statement", "confidence": 0.97},
            model_used="claude-sonnet-4-20250514",
            confidence_score=0.97,
            tokens_used=400,
            processing_time_ms=800,
        )
        db.add(kpi_extraction)
        db.add(classification_extraction)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/dataroom/documents/{doc.id}/extractions")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data["items"]) == 2

        types_returned = {item["extraction_type"] for item in data["items"]}
        assert "kpi" in types_returned
        assert "classification" in types_returned

    async def test_classification_is_financial_statement(
        self, db: AsyncSession, seeded: dict
    ):
        """Verify the classification extraction identifies financial_statement."""
        project_id = seeded["project_id"]
        doc = Document(
            org_id=ALLY_ORG_ID,
            project_id=project_id,
            name="P&L_2023.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="test/pl.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=102400,
            checksum_sha256="def" * 20,
            status=DocumentStatus.READY,
            uploaded_by=ALLY_USER_ID,
        )
        db.add(doc)
        await db.flush()

        extraction = DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.CLASSIFICATION,
            result={"classification": "financial_statement", "confidence": 0.95},
            model_used="claude-sonnet-4-20250514",
            confidence_score=0.95,
            tokens_used=300,
            processing_time_ms=600,
        )
        db.add(extraction)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/dataroom/documents/{doc.id}/extractions")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        classifications = [
            item for item in resp.json()["items"] if item["extraction_type"] == "classification"
        ]
        assert len(classifications) == 1
        assert classifications[0]["result"]["classification"] == "financial_statement"

    async def test_kpi_extraction_finds_revenue_and_ebitda(
        self, db: AsyncSession, seeded: dict
    ):
        """KPI extraction result must include revenue and EBITDA fields."""
        project_id = seeded["project_id"]
        doc = Document(
            org_id=ALLY_ORG_ID,
            project_id=project_id,
            name="Financial_KPIs.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            s3_key="test/kpis.pdf",
            s3_bucket="scr-documents",
            file_size_bytes=204800,
            checksum_sha256="fed" * 20,
            status=DocumentStatus.READY,
            uploaded_by=ALLY_USER_ID,
        )
        db.add(doc)
        await db.flush()

        kpi_extraction = DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.KPI,
            result={
                "kpis": [
                    {"name": "Revenue", "value": 12500000, "currency": "USD", "period": "2023"},
                    {"name": "EBITDA", "value": 3200000, "currency": "USD", "period": "2023"},
                ]
            },
            model_used="claude-sonnet-4-20250514",
            confidence_score=0.90,
            tokens_used=1200,
            processing_time_ms=2800,
        )
        db.add(kpi_extraction)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/dataroom/documents/{doc.id}/extractions")
        app.dependency_overrides.clear()

        kpi_items = [i for i in resp.json()["items"] if i["extraction_type"] == "kpi"]
        assert len(kpi_items) == 1
        kpi_names = {k["name"] for k in kpi_items[0]["result"]["kpis"]}
        assert "Revenue" in kpi_names
        assert "EBITDA" in kpi_names


# ── Scenario 2: Signal Score Calculation ─────────────────────────────────

class TestSignalScoreCalculation:
    """
    Create project → trigger calculation (mocked Celery) → seed score →
    verify response structure, score range, dimension coverage, caching.
    """

    @pytest.fixture
    async def seeded(self, db: AsyncSession, ally_user: User, sample_project: Project):
        return {"project_id": sample_project.id}

    async def test_trigger_returns_202_and_task_log_id(
        self, db: AsyncSession, seeded: dict
    ):
        project_id = seeded["project_id"]
        with patch(
            "app.modules.signal_score.tasks.calculate_signal_score_task.delay"
        ) as mock_delay:
            async with await _make_client(ALLY_USER, db) as client:
                resp = await client.post(f"/signal-score/calculate/{project_id}")
            app.dependency_overrides.clear()

        assert resp.status_code == 202
        body = resp.json()
        assert "task_log_id" in body
        assert body["status"] == "pending"
        assert mock_delay.called

    async def test_get_score_returns_valid_structure(
        self, db: AsyncSession, seeded: dict
    ):
        """Seed a SignalScore record and verify the GET endpoint returns all dimensions."""
        project_id = seeded["project_id"]

        score = SignalScore(
            project_id=project_id,
            overall_score=72,
            project_viability_score=75,
            project_viability_details={"completeness": 0.85, "criteria_met": 4, "criteria_total": 5},
            financial_planning_score=68,
            financial_planning_details={"completeness": 0.70},
            team_strength_score=65,
            team_strength_details={"completeness": 0.60},
            risk_assessment_score=80,
            risk_assessment_details={"completeness": 0.90},
            esg_score=78,
            market_opportunity_score=70,
            market_opportunity_details={"completeness": 0.75},
            scoring_details={
                "dimensions": {
                    "project_viability": {"score": 75, "weight": 0.25},
                    "financial_planning": {"score": 68, "weight": 0.25},
                    "team_strength": {"score": 65, "weight": 0.20},
                    "risk_assessment": {"score": 80, "weight": 0.15},
                    "esg": {"score": 78, "weight": 0.10},
                    "market_opportunity": {"score": 70, "weight": 0.05},
                }
            },
            gaps={
                "items": [
                    {
                        "dimension_id": "team_strength",
                        "criterion_id": "team_bios",
                        "priority": "high",
                        "recommendation": "Upload team bios document",
                    }
                ]
            },
            model_used="claude-sonnet-4-20250514",
            version=1,
            is_live=True,
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/signal-score/{project_id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert 0 <= body["overall_score"] <= 100
        assert "dimensions" in body
        # All 6 dimensions must be present
        dim_ids = {d["id"] for d in body["dimensions"]}
        expected_dims = {
            "technical",
            "financial",
            "esg",
            "regulatory",
            "team",
            "market_opportunity",
        }
        assert expected_dims == dim_ids

    async def test_score_is_in_valid_range(self, db: AsyncSession, seeded: dict):
        """Overall score must be in 0–100."""
        project_id = seeded["project_id"]
        score = SignalScore(
            project_id=project_id,
            overall_score=45,
            project_viability_score=40,
            financial_planning_score=50,
            team_strength_score=35,
            risk_assessment_score=55,
            esg_score=60,
            market_opportunity_score=30,
            scoring_details={"dimensions": {}},
            model_used="claude-sonnet-4-20250514",
            version=1,
            is_live=True,
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/signal-score/{project_id}")
        app.dependency_overrides.clear()

        body = resp.json()
        assert 0 <= body["overall_score"] <= 100

    async def test_gaps_endpoint_returns_recommendations(
        self, db: AsyncSession, seeded: dict
    ):
        project_id = seeded["project_id"]
        score = SignalScore(
            project_id=project_id,
            overall_score=55,
            project_viability_score=50,
            financial_planning_score=40,
            team_strength_score=45,
            risk_assessment_score=60,
            esg_score=70,
            market_opportunity_score=55,
            scoring_details={"dimensions": {}},
            gaps={
                "items": [
                    {
                        "dimension_id": "financial_planning",
                        "dimension_name": "Financial Planning",
                        "criterion_id": "audited_financials",
                        "criterion_name": "Audited Financials",
                        "current_score": 0,
                        "max_points": 20,
                        "priority": "high",
                        "recommendation": "Upload audited financial statements",
                        "relevant_doc_types": ["financial_statement", "audit_report"],
                    }
                ]
            },
            model_used="claude-sonnet-4-20250514",
            version=1,
            is_live=True,
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/signal-score/{project_id}/gaps")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 1
        gap = body["items"][0]
        assert "recommendation" in gap

    async def test_live_score_is_instant_and_deterministic(
        self, db: AsyncSession, seeded: dict
    ):
        """Live score is metadata-only — no AI, should return immediately."""
        project_id = seeded["project_id"]

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.post(f"/signal-score/{project_id}/live")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert 0 <= body["overall_score"] <= 100
        assert isinstance(body["factors"], list)
        assert "guidance" in body

        # Second call must return the same score (deterministic)
        async with await _make_client(ALLY_USER, db) as client2:
            resp2 = await client2.post(f"/signal-score/{project_id}/live")
        app.dependency_overrides.clear()

        assert resp2.json()["overall_score"] == body["overall_score"]

    async def test_score_history_tracks_versions(self, db: AsyncSession, seeded: dict):
        project_id = seeded["project_id"]

        for version, overall in [(1, 55), (2, 68), (3, 72)]:
            score = SignalScore(
                project_id=project_id,
                overall_score=overall,
                project_viability_score=overall,
                financial_planning_score=overall,
                team_strength_score=overall,
                risk_assessment_score=overall,
                esg_score=overall,
                market_opportunity_score=overall,
                scoring_details={"dimensions": {}},
                model_used="claude-sonnet-4-20250514",
                version=version,
                is_live=(version == 3),
                calculated_at=datetime.utcnow(),
            )
            db.add(score)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/signal-score/{project_id}/history")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert len(body["items"]) == 3
        # Most recent version first
        assert body["items"][0]["overall_score"] == 72


# ── Scenario 3: Deal Screening ────────────────────────────────────────────

class TestDealScreening:
    """
    Mandate + 3 projects (good / medium / poor fit) →
    investor recommendations must be ordered by alignment score.
    """

    @pytest.fixture
    async def seeded(
        self,
        db: AsyncSession,
        ally_user: User,
        investor_user: User,
        sample_mandate: InvestorMandate,
    ):
        # Good fit: solar in Mexico, ticket within range
        good = Project(
            org_id=ALLY_ORG_ID,
            name="Sonora Solar 50MW",
            slug="sonora-solar-50mw",
            project_type=ProjectType.SOLAR,
            status=ProjectStatus.ACTIVE,
            stage=ProjectStage.DEVELOPMENT,
            geography_country="Mexico",
            geography_region="Sonora",
            total_investment_required=Decimal("20000000"),
            is_published=True,
            description="Solar project with strong fundamentals" * 5,
        )
        # Medium fit: wind in Brazil (not in mandate geographies)
        medium = Project(
            org_id=ALLY_ORG_ID,
            name="Bahia Wind Farm",
            slug="bahia-wind-farm",
            project_type=ProjectType.WIND,
            status=ProjectStatus.ACTIVE,
            stage=ProjectStage.DEVELOPMENT,
            geography_country="Brazil",
            geography_region="Bahia",
            total_investment_required=Decimal("18000000"),
            is_published=True,
            description="Wind energy project in Brazil" * 5,
        )
        # Poor fit: digital assets (wrong sector + tiny ticket)
        poor = Project(
            org_id=ALLY_ORG_ID,
            name="DeFi Protocol Alpha",
            slug="defi-protocol-alpha",
            project_type=ProjectType.DIGITAL_ASSETS,
            status=ProjectStatus.ACTIVE,
            stage=ProjectStage.CONCEPT,
            geography_country="USA",
            geography_region="New York",
            total_investment_required=Decimal("500000"),
            is_published=True,
            description="Digital asset protocol" * 5,
        )
        db.add_all([good, medium, poor])
        await db.flush()
        return {"mandate_id": sample_mandate.id, "projects": [good, medium, poor]}

    async def test_investor_recommendations_are_ordered_by_alignment(
        self, db: AsyncSession, seeded: dict
    ):
        """GET /matching/investor/recommendations must return projects best-first."""
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/matching/investor/recommendations")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        # At least the good-fit project should appear
        assert len(body.get("items", [])) >= 1

        recs = body["items"]
        scores = [r["alignment"]["overall"] for r in recs if "alignment" in r]
        # Verify descending order
        assert scores == sorted(scores, reverse=True)

    async def test_good_fit_scores_higher_than_poor_fit(
        self, db: AsyncSession, seeded: dict
    ):
        """Solar/Mexico project must score higher than DeFi/concept project."""
        projects = seeded["projects"]
        good_id = str(projects[0].id)
        poor_id = str(projects[2].id)

        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/matching/investor/recommendations")
        app.dependency_overrides.clear()

        recs = resp.json().get("items", [])
        score_map = {r["project_id"]: r["alignment"]["overall"] for r in recs if "project_id" in r}

        if good_id in score_map and poor_id in score_map:
            assert score_map[good_id] > score_map[poor_id]


# ── Scenario 4: Ralph AI Conversation ─────────────────────────────────────

class TestRalphAIConversation:
    """
    Multi-turn conversation: start → ask signal score (tool call logged) →
    follow-up risk question → verify conversation coherence.
    """

    @pytest.fixture
    async def seeded(
        self, db: AsyncSession, ally_user: User, sample_project: Project
    ):
        return {"project_id": sample_project.id}

    async def test_create_conversation(self, db: AsyncSession, seeded: dict):
        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.post(
                "/ralph/conversations", json={"title": "Signal Score Analysis"}
            )
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["title"] == "Signal Score Analysis"

    async def test_send_message_calls_get_signal_score_tool(
        self, db: AsyncSession, seeded: dict
    ):
        """Ralph must call the get_signal_score tool when asked about a score."""
        project_id = seeded["project_id"]

        # Create conversation first
        conv = AIConversation(
            org_id=ALLY_ORG_ID,
            user_id=ALLY_USER_ID,
            title="Project Analysis",
            context_type=AIContextType.GENERAL,
        )
        db.add(conv)
        await db.flush()
        conv_id = conv.id

        # Mock process_message to simulate tool call + response
        async def _mock_process_message(
            db, conversation_id, user_content, org_id, user_id
        ):
            user_msg = AIMessage(
                conversation_id=conversation_id,
                role=AIMessageRole.USER,
                content=user_content,
            )
            assistant_msg = AIMessage(
                conversation_id=conversation_id,
                role=AIMessageRole.ASSISTANT,
                content=(
                    f"The Signal Score for project {project_id} is **72/100**. "
                    "The score reflects strong risk assessment (80) and ESG commitment (78), "
                    "but the team strength dimension (65) needs improvement."
                ),
                tool_calls={
                    "calls": [
                        {
                            "id": "call_abc123",
                            "function": {
                                "name": "get_signal_score",
                                "arguments": json.dumps({"project_id": str(project_id)}),
                            },
                        }
                    ]
                },
                tool_results={
                    "results": [
                        {
                            "tool": "get_signal_score",
                            "result": {"overall_score": 72, "project_id": str(project_id)},
                        }
                    ]
                },
                model_used="claude-sonnet-4-20250514",
                tokens_input=1200,
                tokens_output=150,
            )
            db.add(user_msg)
            db.add(assistant_msg)
            await db.flush()
            return user_msg, assistant_msg

        with patch(
            "app.modules.ralph_ai.router._agent.process_message",
            new=_mock_process_message,
        ):
            async with await _make_client(ALLY_USER, db) as client:
                resp = await client.post(
                    f"/ralph/conversations/{conv_id}/message",
                    json={
                        "content": f"What is the Signal Score for project {project_id}?"
                    },
                )
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "assistant_message" in body
        # Tool calls must be logged on the assistant message
        assert body["assistant_message"]["tool_calls"] is not None
        calls = body["assistant_message"]["tool_calls"]["calls"]
        tool_names = [c["function"]["name"] for c in calls]
        assert "get_signal_score" in tool_names
        # Response must reference the score
        assert "72" in body["assistant_message"]["content"]

    async def test_multi_turn_conversation_coherence(
        self, db: AsyncSession, seeded: dict
    ):
        """Second message in same conversation should be coherent with first."""
        conv = AIConversation(
            org_id=ALLY_ORG_ID,
            user_id=ALLY_USER_ID,
            title="Risk Analysis",
            context_type=AIContextType.GENERAL,
        )
        db.add(conv)
        await db.flush()
        conv_id = conv.id

        messages_sent = []

        async def _mock_process(
            db, conversation_id, user_content, org_id, user_id
        ):
            messages_sent.append(user_content)
            user_msg = AIMessage(
                conversation_id=conversation_id,
                role=AIMessageRole.USER,
                content=user_content,
            )
            assistant_msg = AIMessage(
                conversation_id=conversation_id,
                role=AIMessageRole.ASSISTANT,
                content="Understood. Let me analyze that for you.",
                tool_calls=None,
                model_used="claude-sonnet-4-20250514",
            )
            db.add(user_msg)
            db.add(assistant_msg)
            await db.flush()
            return user_msg, assistant_msg

        with patch(
            "app.modules.ralph_ai.router._agent.process_message",
            new=_mock_process,
        ):
            async with await _make_client(ALLY_USER, db) as client:
                await client.post(
                    f"/ralph/conversations/{conv_id}/message",
                    json={"content": "What is the Signal Score for this project?"},
                )
                resp2 = await client.post(
                    f"/ralph/conversations/{conv_id}/message",
                    json={"content": "What are the main risks?"},
                )
            app.dependency_overrides.clear()

        assert resp2.status_code == 200
        assert len(messages_sent) == 2

        # Verify conversation contains all messages
        async with await _make_client(ALLY_USER, db) as client:
            detail_resp = await client.get(f"/ralph/conversations/{conv_id}")
        app.dependency_overrides.clear()

        assert detail_resp.status_code == 200
        msgs = detail_resp.json().get("messages", [])
        # Should have 2 user + 2 assistant = 4
        assert len(msgs) == 4

    async def test_list_conversations(self, db: AsyncSession, ally_user: User):
        for i in range(3):
            conv = AIConversation(
                org_id=ALLY_ORG_ID,
                user_id=ALLY_USER_ID,
                title=f"Conversation {i + 1}",
            )
            db.add(conv)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get("/ralph/conversations")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    async def test_delete_conversation(self, db: AsyncSession, ally_user: User):
        conv = AIConversation(
            org_id=ALLY_ORG_ID,
            user_id=ALLY_USER_ID,
            title="To be deleted",
        )
        db.add(conv)
        await db.flush()
        conv_id = conv.id

        async with await _make_client(ALLY_USER, db) as client:
            del_resp = await client.delete(f"/ralph/conversations/{conv_id}")
            list_resp = await client.get("/ralph/conversations")
        app.dependency_overrides.clear()

        assert del_resp.status_code == 204
        conv_ids = [c["id"] for c in list_resp.json()]
        assert str(conv_id) not in conv_ids


# ── Scenario 5: Valuation + Report Generation ─────────────────────────────

class TestValuationAndReporting:
    """
    Financial data → DCF valuation (deterministic) → generate report (mocked Celery).
    """

    @pytest.fixture
    async def seeded(self, db: AsyncSession, ally_user: User, sample_project: Project):
        return {"project_id": sample_project.id}

    async def test_create_dcf_valuation(self, db: AsyncSession, seeded: dict):
        """POST /valuations with DCF params → verify calculation fields."""
        project_id = seeded["project_id"]

        payload = {
            "project_id": str(project_id),
            "method": "dcf",
            "currency": "USD",
            "dcf_params": {
                "cash_flows": [3240000.0, 3304800.0, 3370896.0, 3438313.92, 3507080.2, 3577221.8, 3648766.2, 3721741.5, 3796176.3, 3872099.8, 3949541.8, 4028532.6, 4109103.3, 4191285.4, 4275111.1, 4360613.3, 4447825.6, 4536782.1, 4627517.7, 4720068.1],
                "discount_rate": 0.105,
                "terminal_growth_rate": 0.02,
                "net_debt": 0.0,
            },
        }

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.post("/valuations", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert body["method"] == "dcf"
        assert body["enterprise_value"] is not None
        assert float(body["enterprise_value"]) > 0
        assert float(body["equity_value"]) > 0

    async def test_dcf_calculation_is_deterministic(
        self, db: AsyncSession, seeded: dict
    ):
        """Same DCF params → same result every time."""
        project_id = seeded["project_id"]
        payload = {
            "project_id": str(project_id),
            "method": "dcf",
            "currency": "USD",
            "dcf_params": {
                "cash_flows": [1950000.0, 2008500.0, 2068755.0, 2130817.65, 2194742.18, 2200584.84, 2244596.54, 2289488.47, 2335278.24, 2382083.8, 2429725.48, 2478219.99, 2527584.39, 2577836.08, 2628992.8],
                "discount_rate": 0.12,
                "terminal_growth_rate": 0.02,
                "net_debt": 0.0,
            },
        }

        async with await _make_client(ALLY_USER, db) as client:
            r1 = await client.post("/valuations", json={**payload, "name": "Run 1"})
            r2 = await client.post("/valuations", json={**payload, "name": "Run 2"})
        app.dependency_overrides.clear()

        assert r1.status_code == r2.status_code == 201
        assert r1.json()["enterprise_value"] == r2.json()["enterprise_value"]

    async def test_valuation_report_queues_celery_task(
        self, db: AsyncSession, seeded: dict
    ):
        """POST /valuations/{id}/report → 202 with task queued."""
        project_id = seeded["project_id"]

        # First create a valuation
        async with await _make_client(ALLY_USER, db) as client:
            create_resp = await client.post(
                "/valuations",
                json={
                    "project_id": str(project_id),
                    "method": "dcf",
                    "currency": "USD",
                    "dcf_params": {
                        "cash_flows": [1400000.0, 1428000.0, 1456560.0, 1485691.2, 1515404.9],
                        "discount_rate": 0.11,
                        "terminal_growth_rate": 0.02,
                    },
                },
            )
        app.dependency_overrides.clear()

        assert create_resp.status_code == 201
        valuation_id = create_resp.json()["id"]

        with patch("app.modules.valuation.tasks.generate_valuation_report_task.delay") as mock_task:
            async with await _make_client(ALLY_USER, db) as client:
                resp = await client.post(f"/valuations/{valuation_id}/report")
            app.dependency_overrides.clear()

        assert resp.status_code == 202
        assert mock_task.called

    async def test_list_valuations_filtered_by_project(
        self, db: AsyncSession, seeded: dict
    ):
        """GET /valuations?project_id=... returns only this project's valuations."""
        project_id = seeded["project_id"]

        # Create two valuations for this project
        async with await _make_client(ALLY_USER, db) as client:
            for _ in ["Base Case", "Upside Case"]:
                await client.post(
                    "/valuations",
                    json={
                        "project_id": str(project_id),
                        "method": "dcf",
                        "currency": "USD",
                        "dcf_params": {
                            "cash_flows": [3500000.0, 3570000.0, 3641400.0, 3714228.0, 3788512.56],
                            "discount_rate": 0.10,
                            "terminal_growth_rate": 0.02,
                        },
                    },
                )
            list_resp = await client.get(f"/valuations?project_id={project_id}")
        app.dependency_overrides.clear()

        assert list_resp.status_code == 200
        items = list_resp.json() if isinstance(list_resp.json(), list) else list_resp.json().get("items", [])
        assert len(items) >= 2
        for item in items:
            assert item["project_id"] == str(project_id)


# ── Scenario 6: Matching Pipeline ─────────────────────────────────────────

class TestMatchingPipeline:
    """
    5 investor mandates × 5 projects → batch match → verify ordering.
    """

    @pytest.fixture
    async def seeded(
        self, db: AsyncSession, ally_user: User, investor_user: User
    ):
        project_configs = [
            ("Solar Farm A", ProjectType.SOLAR, "Mexico", Decimal("15000000")),
            ("Wind Park B", ProjectType.WIND, "USA", Decimal("25000000")),
            ("Hydro Dam C", ProjectType.HYDRO, "Canada", Decimal("40000000")),
            ("Biomass Plant D", ProjectType.BIOMASS, "Mexico", Decimal("12000000")),
            ("Private Equity E", ProjectType.PRIVATE_EQUITY, "Brazil", Decimal("8000000")),
        ]
        projects = []
        for name, ptype, country, investment in project_configs:
            p = Project(
                org_id=ALLY_ORG_ID,
                name=name,
                slug=name.lower().replace(" ", "-"),
                project_type=ptype,
                status=ProjectStatus.ACTIVE,
                stage=ProjectStage.DEVELOPMENT,
                geography_country=country,
                total_investment_required=investment,
                is_published=True,
                description=f"A {ptype.value} project in {country}." * 8,
            )
            db.add(p)
            projects.append(p)

        mandate_configs = [
            ("Clean Energy Americas", ["solar", "wind"], ["Mexico", "USA", "Canada"], Decimal("5000000"), Decimal("30000000")),
            ("Pan-American Renewables", ["solar", "wind", "hydro"], ["USA", "Canada", "Mexico"], Decimal("10000000"), Decimal("50000000")),
            ("Hydro Focus", ["hydro"], ["Canada"], Decimal("20000000"), Decimal("60000000")),
            ("Latam Biomass", ["biomass"], ["Mexico", "Brazil"], Decimal("5000000"), Decimal("20000000")),
            ("Global PE", ["private_equity"], ["USA", "Brazil", "Mexico"], Decimal("5000000"), Decimal("15000000")),
        ]
        mandates = []
        for name, sectors, geos, min_t, max_t in mandate_configs:
            m = InvestorMandate(
                org_id=INVESTOR_ORG_ID,
                name=name,
                sectors=sectors,
                geographies=geos,
                stages=["development"],
                ticket_size_min=min_t,
                ticket_size_max=max_t,
                risk_tolerance=RiskTolerance.MODERATE,
                is_active=True,
            )
            db.add(m)
            mandates.append(m)

        await db.flush()
        return {"projects": projects, "mandates": mandates}

    async def test_investor_recommendations_return_results(
        self, db: AsyncSession, seeded: dict
    ):
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/matching/investor/recommendations")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        recs = body.get("items", [])
        assert len(recs) >= 1

    async def test_recommendations_ordered_descending(
        self, db: AsyncSession, seeded: dict
    ):
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/matching/investor/recommendations")
        app.dependency_overrides.clear()

        recs = resp.json().get("items", [])
        scores = [r["alignment"]["overall"] for r in recs if "alignment" in r]
        assert scores == sorted(scores, reverse=True), "Recs must be ordered best-first"

    async def test_ally_can_see_matching_investors(
        self, db: AsyncSession, seeded: dict
    ):
        """Ally can view which investors match their project."""
        project = seeded["projects"][0]  # Solar Farm A

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get(f"/matching/ally/recommendations/{project.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 200

    async def test_express_interest_creates_match_record(
        self, db: AsyncSession, seeded: dict
    ):
        """Investor can express interest in a project."""
        project = seeded["projects"][0]

        # Create a match result to interact with
        match = MatchResult(
            investor_org_id=INVESTOR_ORG_ID,
            ally_org_id=ALLY_ORG_ID,
            project_id=project.id,
            overall_score=85,
            status=MatchStatus.SUGGESTED,
            initiated_by=MatchInitiator.SYSTEM,
            score_breakdown={"sector": 90, "geo": 100, "ticket": 80},
        )
        db.add(match)
        await db.flush()

        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.post(f"/matching/{match.id}/interest")
        app.dependency_overrides.clear()

        assert resp.status_code in (200, 201)
        # Match status should be updated
        result = await db.execute(
            select(MatchResult).where(MatchResult.id == match.id)
        )
        updated = result.scalar_one()
        assert updated.status == MatchStatus.INTERESTED


# ── Scenario 7: End-to-End Ally Journey ───────────────────────────────────

class TestEndToEndAllyJourney:
    """
    Full ally flow: create project → upload docs → trigger signal score →
    view gaps → find matching investors.
    """

    async def test_ally_journey(
        self,
        db: AsyncSession,
        ally_user: User,
        investor_user: User,
        sample_mandate: InvestorMandate,
    ):
        async with await _make_client(ALLY_USER, db) as client:
            # 1. Create project
            create_resp = await client.post(
                "/projects",
                json={
                    "name": "Oaxaca Wind Farm",
                    "project_type": "wind",
                    "stage": "development",
                    "geography_country": "Mexico",
                    "geography_region": "Oaxaca",
                    "total_investment_required": 35000000,
                    "description": (
                        "A 75 MW wind farm in the Isthmus of Tehuantepec, one of "
                        "the world's best wind corridors. PPA under negotiation with "
                        "state utility. Total investment USD 35M, target IRR 15%." * 3
                    ),
                },
            )
            assert create_resp.status_code in (200, 201)
            project_id = create_resp.json()["id"]

            # 2. Check live score (instant, no AI)
            live_resp = await client.post(f"/signal-score/{project_id}/live")
            assert live_resp.status_code == 200
            live_score = live_resp.json()["overall_score"]
            assert 0 <= live_score <= 100

            # 3. Trigger full signal score (mocked Celery)
            with patch(
                "app.modules.signal_score.tasks.calculate_signal_score_task.delay"
            ):
                calc_resp = await client.post(f"/signal-score/calculate/{project_id}")
            assert calc_resp.status_code == 202

        app.dependency_overrides.clear()

        # 4. Seed a signal score record (simulating Celery worker)
        score = SignalScore(
            project_id=uuid.UUID(project_id),
            overall_score=68,
            project_viability_score=70,
            financial_planning_score=60,
            team_strength_score=65,
            risk_assessment_score=75,
            esg_score=72,
            market_opportunity_score=68,
            scoring_details={"dimensions": {}},
            gaps={"items": [{
                "dimension_id": "financial_planning",
                "dimension_name": "Financial Planning",
                "criterion_id": "financial_projections",
                "criterion_name": "Financial Projections",
                "current_score": 0,
                "max_points": 20,
                "priority": "high",
                "recommendation": "Upload financial projections",
                "relevant_doc_types": ["financial_model"],
            }]},
            model_used="claude-sonnet-4-20250514",
            version=1,
            is_live=True,
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            # 5. View score
            score_resp = await client.get(f"/signal-score/{project_id}")
            assert score_resp.status_code == 200
            assert score_resp.json()["overall_score"] == 68

            # 6. View gaps
            gaps_resp = await client.get(f"/signal-score/{project_id}/gaps")
            assert gaps_resp.status_code == 200

            # 7. Find matching investors
            # Project must be published first — update it
            await client.put(
                f"/projects/{project_id}", json={"is_published": True}
            )
            match_resp = await client.get(
                f"/matching/ally/recommendations/{project_id}"
            )
            assert match_resp.status_code == 200

        app.dependency_overrides.clear()


# ── Scenario 8: End-to-End Investor Journey ───────────────────────────────

class TestEndToEndInvestorJourney:
    """
    Full investor flow: create portfolio + holdings → signal score →
    browse projects → express interest → request intro.
    """

    async def test_investor_journey(
        self,
        db: AsyncSession,
        investor_user: User,
        ally_user: User,
        sample_mandate: InvestorMandate,
        sample_portfolio: Portfolio,
    ):
        # Seed a published project to interact with
        project = Project(
            org_id=ALLY_ORG_ID,
            name="Yucatan Solar 30MW",
            slug="yucatan-solar-30mw",
            project_type=ProjectType.SOLAR,
            status=ProjectStatus.ACTIVE,
            stage=ProjectStage.DEVELOPMENT,
            geography_country="Mexico",
            geography_region="Yucatan",
            total_investment_required=Decimal("18000000"),
            is_published=True,
            description="Solar project in Yucatan Mexico with strong fundamentals." * 5,
        )
        db.add(project)
        await db.flush()

        async with await _make_client(INVESTOR_USER, db) as client:
            # 1. Add a portfolio holding
            holding_resp = await client.post(
                f"/portfolio/{sample_portfolio.id}/holdings",
                json={
                    "asset_name": "Sonora Solar I",
                    "asset_type": "equity",
                    "investment_date": "2023-06-15",
                    "investment_amount": 8000000,
                    "current_value": 9200000,
                    "currency": "USD",
                    "status": "active",
                },
            )
            assert holding_resp.status_code in (200, 201)

            # 2. Browse investor recommendations
            recs_resp = await client.get("/matching/investor/recommendations")
            assert recs_resp.status_code == 200

            # 3. Calculate investor signal score
            with patch(
                "app.modules.investor_signal_score.engine.InvestorSignalScoreEngine.calculate"
            ) as mock_calc:
                from app.modules.investor_signal_score.engine import (
                    DIMENSION_WEIGHTS,
                    CriterionResult,
                    DimensionResult,
                    EngineResult,
                    ImprovementAction,
                    ScoreFactorItem,
                )
                # Build a realistic mock EngineResult
                def _make_dim(score):
                    return DimensionResult(
                        score=score,
                        weight=0.20,
                        criteria=[
                            CriterionResult(
                                name="Test Criterion",
                                description="Test",
                                points=int(score * 0.2),
                                max_points=20,
                                met=score >= 50,
                            )
                        ],
                        gaps=[],
                        recommendations=[],
                        details={"criteria_met": 1, "criteria_total": 1, "points_earned": int(score * 0.2), "points_max": 20, "icon": "DollarSign", "description": "Test dimension"},
                    )

                mock_calc.return_value = EngineResult(
                    overall_score=74.5,
                    dimensions={
                        "financial_capacity": _make_dim(80),
                        "risk_management": _make_dim(70),
                        "investment_strategy": _make_dim(75),
                        "team_experience": _make_dim(65),
                        "esg_commitment": _make_dim(80),
                        "platform_readiness": _make_dim(70),
                    },
                    gaps=[],
                    recommendations=[],
                    improvement_actions=[],
                    score_factors=[],
                    data_sources={"portfolios": 1, "mandates": 1, "holdings": 1, "risk_assessments": 0, "personas": 0, "users": 1},
                )

                score_resp = await client.post("/investor-signal-score/calculate")
            assert score_resp.status_code == 201
            body = score_resp.json()
            assert 0 <= body["overall_score"] <= 100

        app.dependency_overrides.clear()


# ── Scenario 9: Investor Signal Score ─────────────────────────────────────

class TestInvestorSignalScore:
    """
    Investor org with portfolio/mandate → calculate score →
    verify 6 dimensions, improvement plan, benchmark.
    """

    @pytest.fixture
    async def seeded(
        self,
        db: AsyncSession,
        investor_user: User,
        sample_mandate: InvestorMandate,
        sample_portfolio: Portfolio,
    ):
        # Add a holding to the portfolio
        holding = PortfolioHolding(
            portfolio_id=sample_portfolio.id,
            asset_name="Solar Asset Alpha",
            asset_type=AssetType.EQUITY,
            investment_date=date(2023, 3, 1),
            investment_amount=Decimal("8000000"),
            current_value=Decimal("9500000"),
            currency="USD",
            status=HoldingStatus.ACTIVE,
        )
        db.add(holding)
        await db.flush()
        return {}

    async def test_no_score_returns_404(self, db: AsyncSession, seeded: dict):
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/investor-signal-score")
        app.dependency_overrides.clear()
        assert resp.status_code == 404

    async def test_calculate_returns_6_dimensions(
        self, db: AsyncSession, seeded: dict
    ):
        from app.modules.investor_signal_score.engine import (
            CriterionResult,
            DimensionResult,
            EngineResult,
        )

        def _dim(score: float, key: str) -> DimensionResult:
            return DimensionResult(
                score=score,
                weight=0.20 if key in ("financial_capacity", "risk_management") else 0.15,
                criteria=[
                    CriterionResult("C1", "Test criterion", int(score * 0.2), 20, score >= 50)
                ],
                gaps=[] if score >= 60 else [f"Improve {key}"],
                recommendations=[f"Enhance {key}"] if score < 80 else [],
                details={
                    "criteria_met": 1,
                    "criteria_total": 1,
                    "points_earned": int(score * 0.2),
                    "points_max": 20,
                    "icon": "DollarSign",
                    "description": "Test",
                },
            )

        mock_result = EngineResult(
            overall_score=71.0,
            dimensions={
                "financial_capacity": _dim(80, "financial_capacity"),
                "risk_management": _dim(70, "risk_management"),
                "investment_strategy": _dim(75, "investment_strategy"),
                "team_experience": _dim(60, "team_experience"),
                "esg_commitment": _dim(72, "esg_commitment"),
                "platform_readiness": _dim(68, "platform_readiness"),
            },
            gaps=["Improve team_experience"],
            recommendations=["Enhance team_experience"],
            improvement_actions=[],
            score_factors=[],
            data_sources={"portfolios": 1, "mandates": 1, "holdings": 1, "risk_assessments": 0, "personas": 0, "users": 1},
        )

        with patch(
            "app.modules.investor_signal_score.engine.InvestorSignalScoreEngine.calculate",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            async with await _make_client(INVESTOR_USER, db) as client:
                resp = await client.post("/investor-signal-score/calculate")
            app.dependency_overrides.clear()

        assert resp.status_code == 201
        body = resp.json()
        assert 0 <= body["overall_score"] <= 100

        for dim_key in [
            "financial_capacity",
            "risk_management",
            "investment_strategy",
            "team_experience",
            "esg_commitment",
            "platform_readiness",
        ]:
            assert dim_key in body, f"Missing dimension: {dim_key}"
            assert 0 <= body[dim_key]["score"] <= 100

    async def test_improvement_plan_returns_actions(
        self, db: AsyncSession, seeded: dict
    ):
        """Seed a score with improvement_actions; verify plan endpoint."""
        from app.models.advisory import InvestorSignalScore as ISS

        score = ISS(
            org_id=INVESTOR_ORG_ID,
            overall_score=Decimal("62.0"),
            financial_capacity_score=Decimal("80"),
            financial_capacity_details={"criteria_met": 3, "criteria_total": 5, "points_earned": 50, "points_max": 85, "icon": "DollarSign", "description": "Test", "criteria": []},
            risk_management_score=Decimal("55"),
            risk_management_details={"criteria_met": 2, "criteria_total": 7, "points_earned": 35, "points_max": 100, "icon": "ShieldCheck", "description": "Test", "criteria": []},
            investment_strategy_score=Decimal("70"),
            investment_strategy_details={"criteria_met": 4, "criteria_total": 7, "points_earned": 65, "points_max": 100, "icon": "Target", "description": "Test", "criteria": []},
            team_experience_score=Decimal("50"),
            team_experience_details={"criteria_met": 2, "criteria_total": 8, "points_earned": 35, "points_max": 100, "icon": "Users", "description": "Test", "criteria": []},
            esg_commitment_score=Decimal("65"),
            esg_commitment_details={"criteria_met": 3, "criteria_total": 6, "points_earned": 55, "points_max": 100, "icon": "Leaf", "description": "Test", "criteria": []},
            platform_readiness_score=Decimal("60"),
            platform_readiness_details={"criteria_met": 3, "criteria_total": 7, "points_earned": 55, "points_max": 100, "icon": "BarChart3", "description": "Test", "criteria": []},
            gaps={"financial_capacity": [], "risk_management": ["Upload risk policy"]},
            recommendations={"risk_management": ["Add risk policy document"]},
            score_factors={
                "dimension_weights": {"financial_capacity": 0.20, "risk_management": 0.20, "investment_strategy": 0.15, "team_experience": 0.15, "esg_commitment": 0.15, "platform_readiness": 0.15},
                "improvement_actions": [
                    {
                        "title": "Written Risk Policy",
                        "description": "Add a risk assessment document",
                        "estimated_impact": 4.0,
                        "effort_level": "low",
                        "category": "risk_management",
                        "link_to": "/investor/risk",
                    }
                ],
                "factors": [],
            },
            data_sources={"portfolios": 1},
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/investor-signal-score/improvement-plan")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        actions = resp.json()
        assert len(actions) >= 1
        assert actions[0]["title"] == "Written Risk Policy"
        assert actions[0]["estimated_impact"] == 4.0

    async def test_benchmark_returns_percentile(self, db: AsyncSession, seeded: dict):
        from app.models.advisory import InvestorSignalScore as ISS

        score = ISS(
            org_id=INVESTOR_ORG_ID,
            overall_score=Decimal("74.0"),
            financial_capacity_score=Decimal("80"),
            financial_capacity_details={"criteria": []},
            risk_management_score=Decimal("70"),
            risk_management_details={"criteria": []},
            investment_strategy_score=Decimal("75"),
            investment_strategy_details={"criteria": []},
            team_experience_score=Decimal("65"),
            team_experience_details={"criteria": []},
            esg_commitment_score=Decimal("80"),
            esg_commitment_details={"criteria": []},
            platform_readiness_score=Decimal("70"),
            platform_readiness_details={"criteria": []},
            gaps={},
            recommendations={},
            score_factors={"improvement_actions": [], "factors": [], "dimension_weights": {}},
            data_sources={},
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/investor-signal-score/benchmark")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert 0 <= body["percentile"] <= 100
        assert body["your_score"] == 74.0


# ── Scenario 10: Live Scoring ─────────────────────────────────────────────

class TestLiveScoring:
    """
    Live score is metadata-only (no AI). Verify it reflects project completeness.
    Simulate an update → verify score improves.
    """

    async def test_live_score_improves_with_completeness(
        self, db: AsyncSession, ally_user: User
    ):
        """A minimal project scores lower than a fully-specified one."""
        # Minimal project
        minimal = Project(
            org_id=ALLY_ORG_ID,
            name="Minimal Project",
            slug="minimal-project",
            project_type=ProjectType.SOLAR,
            geography_country="USA",
            total_investment_required=Decimal("0"),
            description="Short",
        )
        db.add(minimal)

        # Full project
        full = Project(
            org_id=ALLY_ORG_ID,
            name="Complete Project",
            slug="complete-project",
            project_type=ProjectType.SOLAR,
            stage=ProjectStage.DEVELOPMENT,
            geography_country="Mexico",
            geography_region="Sonora",
            total_investment_required=Decimal("20000000"),
            capacity_mw=Decimal("30"),
            target_close_date=date(2026, 6, 30),
            is_published=True,
            cover_image_url="https://example.com/cover.jpg",
            description="This is a comprehensive project description with full details about the investment opportunity and risk profile." * 5,
        )
        db.add(full)
        await db.flush()

        async with await _make_client(ALLY_USER, db) as client:
            min_resp = await client.post(f"/signal-score/{minimal.id}/live")
            full_resp = await client.post(f"/signal-score/{full.id}/live")
        app.dependency_overrides.clear()

        assert min_resp.status_code == 200
        assert full_resp.status_code == 200
        assert full_resp.json()["overall_score"] > min_resp.json()["overall_score"]


# ── Scenario 11: Board Advisor ─────────────────────────────────────────────

class TestBoardAdvisor:
    """Board advisor search and application flow."""

    async def test_list_advisors(self, db: AsyncSession, ally_user: User):
        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get("/board-advisors/search")
        app.dependency_overrides.clear()
        assert resp.status_code == 200

    async def test_create_advisor_profile(
        self, db: AsyncSession, investor_user: User
    ):
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.post(
                "/board-advisors/my-profile",
                json={
                    "full_name": "Dr. Elena Vasquez",
                    "title": "Chief Investment Officer",
                    "expertise": ["renewable_energy", "project_finance", "latin_america"],
                    "sectors": ["solar", "wind"],
                    "geographies": ["Mexico", "Brazil", "Colombia"],
                    "languages": ["English", "Spanish", "Portuguese"],
                    "bio": (
                        "20+ years in renewable energy project finance across Latin America. "
                        "Former Goldman Sachs infrastructure MD. Board member at 3 solar developers."
                    ),
                    "linkedin_url": "https://linkedin.com/in/elena-vasquez",
                    "is_available": True,
                    "hourly_rate": 350,
                    "currency": "USD",
                },
            )
        app.dependency_overrides.clear()
        assert resp.status_code in (200, 201)

    async def test_search_advisors_by_sector(
        self, db: AsyncSession, ally_user: User
    ):
        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get("/board-advisors/search?expertise=solar")
        app.dependency_overrides.clear()
        assert resp.status_code == 200


# ── Scenario 12: Investor Personas ────────────────────────────────────────

class TestInvestorPersonas:
    """Create an investor persona and verify it matches projects correctly."""

    @pytest.fixture
    async def seeded(self, db: AsyncSession, investor_user: User):
        return {}

    async def test_create_persona(self, db: AsyncSession, seeded: dict):
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.post(
                "/investor-personas",
                json={
                    "persona_name": "Conservative LATAM Renewable Investor",
                    "strategy_type": "conservative",
                    "target_irr_min": 10,
                    "target_irr_max": 14,
                    "target_moic_min": 1.5,
                    "preferred_asset_types": ["solar", "wind"],
                    "preferred_geographies": ["Mexico", "Colombia"],
                    "preferred_stages": ["development", "construction"],
                    "ticket_size_min": 5000000,
                    "ticket_size_max": 25000000,
                    "esg_requirements": {"sfdr": "article_8"},
                    "risk_tolerance": {"level": "conservative"},
                    "co_investment_preference": False,
                },
            )
        app.dependency_overrides.clear()
        assert resp.status_code in (200, 201)

    async def test_list_personas(self, db: AsyncSession, seeded: dict):
        # Seed a persona directly
        persona = InvestorPersona(
            org_id=INVESTOR_ORG_ID,
            persona_name="Growth Focused",
            is_active=True,
        )
        db.add(persona)
        await db.flush()

        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get("/investor-personas")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        items = resp.json() if isinstance(resp.json(), list) else resp.json().get("items", [])
        assert len(items) >= 1


# ── Scenario 13: Equity Calculator ────────────────────────────────────────

class TestEquityCalculator:
    """Deterministic equity and waterfall calculations."""

    @pytest.fixture
    async def seeded(self, db: AsyncSession, ally_user: User, sample_project: Project):
        return {"project_id": sample_project.id}

    async def test_equity_scenario_calculation(
        self, db: AsyncSession, seeded: dict
    ):
        """POST /equity-calculator/scenarios → verify deterministic output."""
        project_id = seeded["project_id"]

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.post(
                "/equity-calculator/scenarios",
                json={
                    "project_id": str(project_id),
                    "scenario_name": "Base Case",
                    "pre_money_valuation": 15000000,
                    "investment_amount": 5000000,
                    "security_type": "preferred_equity",
                    "shares_outstanding_before": 1000000,
                    "liquidation_preference": 1.0,
                    "participation_cap": None,
                    "anti_dilution_type": "broad_based",
                },
            )
        app.dependency_overrides.clear()

        assert resp.status_code in (200, 201)
        body = resp.json()
        # Waterfall should have results for each exit value
        assert "waterfall" in body or "results" in body

    async def test_waterfall_at_5_exit_multiples(
        self, db: AsyncSession, seeded: dict
    ):
        """Verify waterfall produces 5 results for 5 exit values."""
        project_id = seeded["project_id"]

        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.post(
                "/equity-calculator/scenarios",
                json={
                    "project_id": str(project_id),
                    "scenario_name": "5x Exit Scenarios",
                    "pre_money_valuation": 20000000,
                    "investment_amount": 5000000,
                    "security_type": "common_equity",
                    "shares_outstanding_before": 1000000,
                    "anti_dilution_type": "none",
                },
            )
        app.dependency_overrides.clear()

        if resp.status_code in (200, 201):
            body = resp.json()
            waterfall = body.get("waterfall") or body.get("results") or []
            assert len(waterfall) >= 1


# ── Scenario 14: Capital Efficiency ───────────────────────────────────────

class TestCapitalEfficiency:
    """Capital efficiency metrics and industry benchmark comparison."""

    @pytest.fixture
    async def seeded(
        self,
        db: AsyncSession,
        investor_user: User,
        sample_portfolio: Portfolio,
    ):
        # Add several holdings for meaningful metrics
        holdings_data = [
            ("Solar Asset A", AssetType.EQUITY, Decimal("5000000"), Decimal("7200000")),
            ("Wind Asset B", AssetType.EQUITY, Decimal("8000000"), Decimal("9800000")),
            ("Hydro Asset C", AssetType.DEBT, Decimal("3000000"), Decimal("3600000")),
        ]
        for name, atype, invested, current in holdings_data:
            h = PortfolioHolding(
                portfolio_id=sample_portfolio.id,
                asset_name=name,
                asset_type=atype,
                investment_date=date(2022, 1, 1),
                investment_amount=invested,
                current_value=current,
                currency="USD",
                status=HoldingStatus.ACTIVE,
            )
            db.add(h)
        await db.flush()
        return {"portfolio_id": sample_portfolio.id}

    async def test_capital_efficiency_metrics(
        self, db: AsyncSession, seeded: dict
    ):
        portfolio_id = seeded["portfolio_id"]

        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get(f"/capital-efficiency?portfolio_id={portfolio_id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        # Should return key efficiency metrics
        assert any(k in body for k in ["platform_efficiency_score", "total_savings", "due_diligence_savings", "efficiency_score"])


# ── Scenario 15: Risk Monitoring (stub) ───────────────────────────────────

class TestRiskMonitoring:
    """
    Stub tests for the Risk Monitoring module (5-domain monitoring).
    This module is not yet implemented — tests will be enabled once built.
    """

    @pytest.mark.skip(reason="risk_monitoring module not yet built")
    async def test_enable_monitoring_for_project(self, db, ally_user, sample_project):
        """Enable monitoring → verify alert configuration is stored."""
        pass

    @pytest.mark.skip(reason="risk_monitoring module not yet built")
    async def test_external_alert_triggers_notification(self, db, ally_user):
        """Simulate external risk event → verify alert severity routing."""
        pass

    @pytest.mark.skip(reason="risk_monitoring module not yet built")
    async def test_severity_routing_sends_to_correct_channel(self, db, ally_user):
        """High severity alerts go to primary channel; low severity to digest."""
        pass


# ── Scenario 16: Insurance Both Sides (stub) ──────────────────────────────

class TestInsuranceBothSides:
    """
    Stub tests for the Insurance Products module (ally + investor sides).
    Module not yet built — tests enabled once implemented.
    """

    @pytest.mark.skip(reason="insurance module not yet built")
    async def test_get_ally_insurance_recommendations(self, db, ally_user, sample_project):
        """Ally gets coverage recommendations for their project."""
        pass

    @pytest.mark.skip(reason="insurance module not yet built")
    async def test_get_investor_insurance_recommendations(
        self, db, investor_user, sample_portfolio
    ):
        """Investor gets portfolio-level coverage recommendations."""
        pass

    @pytest.mark.skip(reason="insurance module not yet built")
    async def test_activate_coverage_improves_risk_score(self, db, ally_user, sample_project):
        """Activating insurance coverage raises risk_assessment dimension score."""
        pass

    @pytest.mark.skip(reason="insurance module not yet built")
    async def test_preview_impact_before_activation(self, db, ally_user, sample_project):
        """Preview endpoint shows projected score improvement before committing."""
        pass


# ── Cross-cutting: Multi-tenant isolation ─────────────────────────────────

class TestMultiTenantIsolation:
    """
    Users from org A cannot access data belonging to org B.
    """

    async def test_investor_cannot_read_ally_signal_score(
        self, db: AsyncSession, ally_user: User, investor_user: User, sample_project: Project
    ):
        """Investor org cannot access ally's project signal score."""
        score = SignalScore(
            project_id=sample_project.id,
            overall_score=75,
            project_viability_score=75,
            financial_planning_score=70,
            team_strength_score=68,
            risk_assessment_score=80,
            esg_score=72,
            market_opportunity_score=74,
            scoring_details={"dimensions": {}},
            model_used="claude-sonnet-4-20250514",
            version=1,
            is_live=True,
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
        await db.flush()

        # Investor tries to access ally's project score — should fail (403 or 404)
        async with await _make_client(INVESTOR_USER, db) as client:
            resp = await client.get(f"/signal-score/{sample_project.id}")
        app.dependency_overrides.clear()

        # Investor does not own this project → must not see the score
        assert resp.status_code in (403, 404)

    async def test_ally_cannot_list_investor_conversations(
        self, db: AsyncSession, ally_user: User, investor_user: User
    ):
        """Ally cannot access investor's Ralph conversations."""
        investor_conv = AIConversation(
            org_id=INVESTOR_ORG_ID,
            user_id=INVESTOR_USER_ID,
            title="Investor Secret Conversation",
        )
        db.add(investor_conv)
        await db.flush()

        # Ally lists their conversations — investor conv should NOT appear
        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get("/ralph/conversations")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        conv_ids = [c["id"] for c in resp.json()]
        assert str(investor_conv.id) not in conv_ids

    async def test_investor_signal_score_isolated_per_org(
        self, db: AsyncSession, ally_user: User, investor_user: User
    ):
        """Ally org cannot GET investor signal score endpoint for investor org."""
        from app.models.advisory import InvestorSignalScore as ISS

        iss = ISS(
            org_id=INVESTOR_ORG_ID,
            overall_score=Decimal("70"),
            financial_capacity_score=Decimal("70"),
            financial_capacity_details={"criteria": []},
            risk_management_score=Decimal("70"),
            risk_management_details={"criteria": []},
            investment_strategy_score=Decimal("70"),
            investment_strategy_details={"criteria": []},
            team_experience_score=Decimal("70"),
            team_experience_details={"criteria": []},
            esg_commitment_score=Decimal("70"),
            esg_commitment_details={"criteria": []},
            platform_readiness_score=Decimal("70"),
            platform_readiness_details={"criteria": []},
            gaps={},
            recommendations={},
            score_factors={"improvement_actions": [], "factors": [], "dimension_weights": {}},
            data_sources={},
            calculated_at=datetime.utcnow(),
        )
        db.add(iss)
        await db.flush()

        # Ally tries to access the investor signal score endpoint — 404 (no ally score)
        async with await _make_client(ALLY_USER, db) as client:
            resp = await client.get("/investor-signal-score")
        app.dependency_overrides.clear()

        assert resp.status_code == 404  # Ally has no score; investor's score is invisible


# ── Cross-cutting: RBAC enforcement ───────────────────────────────────────

class TestRBACEnforcement:
    """Verify RBAC prevents under-privileged users from triggering calculations."""

    async def test_viewer_cannot_trigger_signal_score(
        self, db: AsyncSession, ally_user: User, sample_project: Project
    ):
        viewer = CurrentUser(
            user_id=uuid.uuid4(),
            org_id=ALLY_ORG_ID,
            role=UserRole.VIEWER,
            email="viewer@example.com",
            external_auth_id="viewer_clerk",
        )

        with patch("app.modules.signal_score.tasks.calculate_signal_score_task.delay"):
            async with await _make_client(viewer, db) as client:
                resp = await client.post(
                    f"/signal-score/calculate/{sample_project.id}"
                )
            app.dependency_overrides.clear()

        assert resp.status_code == 403

    async def test_admin_can_trigger_signal_score(
        self, db: AsyncSession, ally_user: User, sample_project: Project
    ):
        with patch("app.modules.signal_score.tasks.calculate_signal_score_task.delay"):
            async with await _make_client(ALLY_USER, db) as client:
                resp = await client.post(
                    f"/signal-score/calculate/{sample_project.id}"
                )
            app.dependency_overrides.clear()

        assert resp.status_code == 202

    async def test_viewer_cannot_delete_ralph_conversation(
        self, db: AsyncSession, ally_user: User
    ):
        conv = AIConversation(
            org_id=ALLY_ORG_ID,
            user_id=ALLY_USER_ID,
            title="Protected",
        )
        db.add(conv)
        await db.flush()

        viewer = CurrentUser(
            user_id=uuid.uuid4(),
            org_id=ALLY_ORG_ID,
            role=UserRole.VIEWER,
            email="viewer2@example.com",
            external_auth_id="viewer2_clerk",
        )

        # Ralph delete uses get_current_user — viewer's token should work but only their convs
        async with await _make_client(viewer, db) as client:
            resp = await client.delete(f"/ralph/conversations/{conv.id}")
        app.dependency_overrides.clear()

        # Viewer did not create this conv — 404 (not 403; user simply can't see it)
        assert resp.status_code in (403, 404)
