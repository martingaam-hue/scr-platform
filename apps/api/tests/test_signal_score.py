"""Tests for the Signal Score module."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.ai import AITaskLog
from app.models.core import Organization, User
from app.models.dataroom import Document, DocumentExtraction
from app.models.enums import (
    AIAgentType,
    AITaskStatus,
    DocumentStatus,
    ExtractionType,
    OrgType,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.projects import Project, SignalScore
from app.modules.signal_score import service
from app.modules.signal_score.criteria import ALL_CRITERIA, DIMENSIONS
from app.modules.signal_score.engine import SignalScoreEngine
from app.modules.signal_score.schemas import (
    CalculateAcceptedResponse,
    GapsResponse,
    ScoreHistoryResponse,
    SignalScoreDetailResponse,
    TaskStatusResponse,
)
from app.schemas.auth import CurrentUser

# ── Test Data ────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
VIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")

ADMIN_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="admin@example.com",
    external_auth_id="user_test_admin",
)

VIEWER_USER = CurrentUser(
    user_id=VIEWER_USER_ID,
    org_id=ORG_ID,
    role=UserRole.VIEWER,
    email="viewer@example.com",
    external_auth_id="user_test_viewer",
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user
    return _override


@pytest.fixture
async def seed_data(db: AsyncSession):
    """Seed org, users, and project."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.ALLY)
    db.add(org)
    user = User(
        id=USER_ID, org_id=ORG_ID, email="admin@example.com",
        full_name="Admin User", role=UserRole.ADMIN,
        external_auth_id="user_test_admin", is_active=True,
    )
    db.add(user)
    viewer = User(
        id=VIEWER_USER_ID, org_id=ORG_ID, email="viewer@example.com",
        full_name="Viewer User", role=UserRole.VIEWER,
        external_auth_id="user_test_viewer", is_active=True,
    )
    db.add(viewer)
    project = Project(
        id=PROJECT_ID,
        org_id=ORG_ID,
        name="Solar Farm Alpha",
        slug="solar-farm-alpha",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="Kenya",
        total_investment_required=Decimal("5000000"),
    )
    db.add(project)
    await db.flush()


@pytest.fixture
async def seed_signal_score(db: AsyncSession, seed_data):
    """Seed a signal score for the project."""
    score = SignalScore(
        project_id=PROJECT_ID,
        overall_score=65,
        project_viability_score=70,
        financial_planning_score=75,
        esg_score=55,
        risk_assessment_score=60,
        team_strength_score=50,
        market_opportunity_score=58,
        scoring_details={
            "dimensions": {
                "technical": {
                    "score": 70,
                    "completeness_score": 65,
                    "quality_score": 73,
                    "criteria": [
                        {
                            "id": "tech_site_assessment",
                            "name": "Site Assessment / Feasibility Study",
                            "max_points": 15,
                            "score": 12,
                            "has_document": True,
                            "ai_assessment": {
                                "score": 82,
                                "reasoning": "Strong assessment",
                                "strengths": ["Detailed analysis"],
                                "weaknesses": ["Missing wind data"],
                                "recommendation": "Add wind analysis",
                            },
                        },
                    ],
                },
                "financial": {"score": 75, "completeness_score": 70, "quality_score": 78, "criteria": []},
                "esg": {"score": 55, "completeness_score": 50, "quality_score": 58, "criteria": []},
                "regulatory": {"score": 60, "completeness_score": 55, "quality_score": 63, "criteria": []},
                "team": {"score": 50, "completeness_score": 45, "quality_score": 53, "criteria": []},
            }
        },
        gaps={
            "items": [
                {
                    "dimension_id": "team",
                    "dimension_name": "Team & Execution",
                    "criterion_id": "team_advisory",
                    "criterion_name": "Advisory Board",
                    "current_score": 0,
                    "max_points": 15,
                    "priority": "high",
                    "recommendation": "Add advisory board documentation",
                    "relevant_doc_types": ["presentation"],
                },
            ]
        },
        strengths={
            "items": [
                {
                    "dimension_id": "financial",
                    "dimension_name": "Financial Viability",
                    "criterion_id": "fin_revenue_model",
                    "criterion_name": "Revenue Model / PPA",
                    "score": 14,
                    "summary": "Strong PPA documentation",
                },
            ]
        },
        model_used="claude-sonnet-4",
        version=1,
        calculated_at=datetime.utcnow(),
    )
    db.add(score)
    await db.flush()
    return score


@pytest.fixture
async def seed_multiple_scores(db: AsyncSession, seed_data):
    """Seed multiple score versions."""
    for i in range(1, 4):
        score = SignalScore(
            project_id=PROJECT_ID,
            overall_score=50 + i * 10,
            project_viability_score=55 + i * 5,
            financial_planning_score=60 + i * 5,
            esg_score=45 + i * 5,
            risk_assessment_score=50 + i * 5,
            team_strength_score=40 + i * 5,
            market_opportunity_score=45 + i * 5,
            scoring_details={"dimensions": {}},
            gaps={"items": []},
            strengths={"items": []},
            model_used="deterministic",
            version=i,
            calculated_at=datetime.utcnow(),
        )
        db.add(score)
    await db.flush()


# ── Criteria Definition Tests ────────────────────────────────────────────────


class TestCriteriaDefinitions:
    def test_six_dimensions(self):
        assert len(DIMENSIONS) == 6

    def test_dimension_weights_sum_to_one(self):
        total = sum(d.weight for d in DIMENSIONS)
        assert abs(total - 1.0) < 0.001

    def test_each_dimension_has_100_points(self):
        for dim in DIMENSIONS:
            total_points = sum(c.max_points for c in dim.criteria)
            assert total_points == 100, f"{dim.name} has {total_points} points, expected 100"

    def test_all_criteria_have_classifications(self):
        for dim in DIMENSIONS:
            for crit in dim.criteria:
                assert len(crit.relevant_classifications) > 0, (
                    f"Criterion {crit.id} has no classifications"
                )

    def test_all_criteria_indexed(self):
        assert len(ALL_CRITERIA) == sum(len(d.criteria) for d in DIMENSIONS)
        for dim in DIMENSIONS:
            for crit in dim.criteria:
                assert crit.id in ALL_CRITERIA

    def test_dimension_ids_unique(self):
        ids = [d.id for d in DIMENSIONS]
        assert len(ids) == len(set(ids))

    def test_criterion_ids_unique(self):
        ids = list(ALL_CRITERIA.keys())
        assert len(ids) == len(set(ids))


# ── Engine Tests (mocked AI) ────────────────────────────────────────────────


class TestSignalScoreEngine:
    @pytest.mark.anyio
    async def test_score_no_documents(self, db: AsyncSession, seed_data):
        """With no documents, all scores should be zero."""
        # Use a sync session mock since engine is sync
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock()

        # Mock project load
        project = MagicMock()
        project.project_type.value = "solar"
        project.stage.value = "development"
        project.geography_country = "Kenya"

        # execute() returns different things for different queries
        call_count = [0]
        def mock_execute(stmt):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # Project query
                result.scalar_one.return_value = project
            elif call_count[0] == 2:
                # Documents query
                result.scalars.return_value.all.return_value = []
            elif call_count[0] == 3:
                # Version query
                result.scalar.return_value = None
            return result

        mock_session.execute.side_effect = mock_execute
        mock_session.add = MagicMock()
        mock_session.flush = MagicMock()

        engine = SignalScoreEngine(mock_session)
        signal_score = engine.calculate_score(PROJECT_ID, ORG_ID, USER_ID)

        assert signal_score.overall_score == 0
        assert signal_score.version == 1

    @pytest.mark.anyio
    async def test_gap_identification(self, db: AsyncSession, seed_data):
        """Criteria with score < 50% should appear in gaps."""
        engine = SignalScoreEngine.__new__(SignalScoreEngine)
        dimension_results = {}
        for dim in DIMENSIONS:
            criteria = [
                {
                    "id": crit.id,
                    "name": crit.name,
                    "max_points": crit.max_points,
                    "score": 0,  # all zero = all gaps
                    "has_document": False,
                    "ai_assessment": None,
                }
                for crit in dim.criteria
            ]
            dimension_results[dim.id] = {
                "score": 0,
                "completeness_score": 0,
                "quality_score": 0,
                "criteria": criteria,
            }

        gaps = engine._identify_gaps(dimension_results)
        # All criteria should be gaps since score is 0
        total_criteria = sum(len(d.criteria) for d in DIMENSIONS)
        assert len(gaps) == total_criteria
        # All should be high priority since score is 0
        assert all(g["priority"] == "high" for g in gaps)

    @pytest.mark.anyio
    async def test_strength_identification(self, db: AsyncSession, seed_data):
        """Criteria with score >= 80% should appear in strengths."""
        engine = SignalScoreEngine.__new__(SignalScoreEngine)
        dimension_results = {}
        for dim in DIMENSIONS:
            criteria = [
                {
                    "id": crit.id,
                    "name": crit.name,
                    "max_points": crit.max_points,
                    "score": crit.max_points,  # perfect score
                    "has_document": True,
                    "ai_assessment": {
                        "score": 100,
                        "strengths": ["Excellent"],
                        "weaknesses": [],
                    },
                }
                for crit in dim.criteria
            ]
            dimension_results[dim.id] = {
                "score": 100,
                "completeness_score": 100,
                "quality_score": 100,
                "criteria": criteria,
            }

        strengths = engine._identify_strengths(dimension_results)
        total_criteria = sum(len(d.criteria) for d in DIMENSIONS)
        assert len(strengths) == total_criteria

    def test_gaps_sorted_by_priority(self):
        """Gaps should be sorted: high priority first, then by max_points desc."""
        engine = SignalScoreEngine.__new__(SignalScoreEngine)
        dimension_results = {}
        for dim in DIMENSIONS:
            criteria = []
            for i, crit in enumerate(dim.criteria):
                # Alternate between 0 and 30% score
                score = round(crit.max_points * 0.3) if i % 2 else 0
                criteria.append({
                    "id": crit.id,
                    "name": crit.name,
                    "max_points": crit.max_points,
                    "score": score,
                    "has_document": score > 0,
                    "ai_assessment": None,
                })
            dimension_results[dim.id] = {
                "score": 30,
                "completeness_score": 30,
                "quality_score": 30,
                "criteria": criteria,
            }

        gaps = engine._identify_gaps(dimension_results)
        # Check ordering: all "high" before "medium"
        priorities = [g["priority"] for g in gaps]
        high_indices = [i for i, p in enumerate(priorities) if p == "high"]
        medium_indices = [i for i, p in enumerate(priorities) if p == "medium"]
        if high_indices and medium_indices:
            assert max(high_indices) < min(medium_indices)


# ── Service Tests ────────────────────────────────────────────────────────────


class TestSignalScoreService:
    @pytest.mark.anyio
    async def test_get_latest_score(self, db: AsyncSession, seed_signal_score):
        score = await service.get_latest_score(db, PROJECT_ID, ORG_ID)
        assert score is not None
        assert score.overall_score == 65
        assert score.version == 1

    @pytest.mark.anyio
    async def test_get_latest_score_returns_highest_version(
        self, db: AsyncSession, seed_multiple_scores
    ):
        score = await service.get_latest_score(db, PROJECT_ID, ORG_ID)
        assert score is not None
        assert score.version == 3
        assert score.overall_score == 80  # 50 + 3*10

    @pytest.mark.anyio
    async def test_get_latest_score_no_scores(self, db: AsyncSession, seed_data):
        score = await service.get_latest_score(db, PROJECT_ID, ORG_ID)
        assert score is None

    @pytest.mark.anyio
    async def test_get_score_history(self, db: AsyncSession, seed_multiple_scores):
        scores = await service.get_score_history(db, PROJECT_ID, ORG_ID)
        assert len(scores) == 3
        # Should be ordered by version desc
        versions = [s.version for s in scores]
        assert versions == [3, 2, 1]

    @pytest.mark.anyio
    async def test_get_score_history_empty(self, db: AsyncSession, seed_data):
        scores = await service.get_score_history(db, PROJECT_ID, ORG_ID)
        assert len(scores) == 0

    @pytest.mark.anyio
    async def test_trigger_calculation(self, db: AsyncSession, seed_data):
        """trigger_calculation creates AITaskLog and dispatches Celery."""
        with patch(
            "app.modules.signal_score.tasks.calculate_signal_score_task.delay"
        ) as mock_delay:
            task_log = await service.trigger_calculation(
                db, PROJECT_ID, ORG_ID, USER_ID
            )
            assert task_log.agent_type == AIAgentType.SCORING
            assert task_log.status == AITaskStatus.PENDING
            assert task_log.entity_id == PROJECT_ID
            mock_delay.assert_called_once()

    @pytest.mark.anyio
    async def test_trigger_calculation_project_not_found(self, db: AsyncSession, seed_data):
        fake_id = uuid.UUID("00000000-0000-0000-0000-999999999999")
        with pytest.raises(LookupError):
            await service.trigger_calculation(db, fake_id, ORG_ID, USER_ID)

    @pytest.mark.anyio
    async def test_get_task_status(self, db: AsyncSession, seed_data):
        task_log = AITaskLog(
            org_id=ORG_ID,
            agent_type=AIAgentType.SCORING,
            entity_type="project",
            entity_id=PROJECT_ID,
            status=AITaskStatus.COMPLETED,
            triggered_by=USER_ID,
        )
        db.add(task_log)
        await db.flush()

        result = await service.get_task_status(db, task_log.id, ORG_ID)
        assert result is not None
        assert result.status == AITaskStatus.COMPLETED


# ── API Router Tests ─────────────────────────────────────────────────────────


class TestSignalScoreAPI:
    @pytest.mark.anyio
    async def test_get_latest_score_200(
        self, client: AsyncClient, db: AsyncSession, seed_signal_score
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/{PROJECT_ID}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["overall_score"] == 65
            assert len(data["dimensions"]) == 6
            assert data["version"] == 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_latest_score_404_no_score(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/{PROJECT_ID}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_details_200(
        self, client: AsyncClient, db: AsyncSession, seed_signal_score
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/{PROJECT_ID}/details")
            assert resp.status_code == 200
            data = resp.json()
            assert "dimensions" in data
            tech_dim = next(d for d in data["dimensions"] if d["id"] == "technical")
            assert tech_dim["score"] == 70
            assert len(tech_dim["criteria"]) >= 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_gaps_200(
        self, client: AsyncClient, db: AsyncSession, seed_signal_score
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/{PROJECT_ID}/gaps")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["criterion_id"] == "team_advisory"
            assert data["items"][0]["priority"] == "high"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_history_200(
        self, client: AsyncClient, db: AsyncSession, seed_multiple_scores
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/{PROJECT_ID}/history")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 3
            # Ordered desc by version
            assert data["items"][0]["version"] == 3
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_calculate_202(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with patch(
                "app.modules.signal_score.tasks.calculate_signal_score_task.delay"
            ):
                resp = await client.post(f"/v1/signal-score/calculate/{PROJECT_ID}")
                assert resp.status_code == 202
                data = resp.json()
                assert data["status"] == "pending"
                assert "task_log_id" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_recalculate_202(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with patch(
                "app.modules.signal_score.tasks.calculate_signal_score_task.delay"
            ):
                resp = await client.post(f"/v1/signal-score/{PROJECT_ID}/recalculate")
                assert resp.status_code == 202
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_calculate_404_project_not_found(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        fake_id = uuid.UUID("00000000-0000-0000-0000-999999999999")
        try:
            resp = await client.post(f"/v1/signal-score/calculate/{fake_id}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_viewer_cannot_calculate(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        """Viewer role should not have run_analysis permission."""
        app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.post(f"/v1/signal-score/calculate/{PROJECT_ID}")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_task_status_200(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        task_log = AITaskLog(
            org_id=ORG_ID,
            agent_type=AIAgentType.SCORING,
            entity_type="project",
            entity_id=PROJECT_ID,
            status=AITaskStatus.PROCESSING,
            triggered_by=USER_ID,
        )
        db.add(task_log)
        await db.flush()

        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/task/{task_log.id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "processing"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_task_status_404(
        self, client: AsyncClient, db: AsyncSession, seed_data
    ):
        fake_id = uuid.UUID("00000000-0000-0000-0000-999999999999")
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/signal-score/task/{fake_id}")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()
