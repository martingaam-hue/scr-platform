"""Comprehensive tests for the Projects module."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    BudgetItemStatus,
    MilestoneStatus,
    OrgType,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone, SignalScore
from app.modules.projects import service
from app.schemas.auth import CurrentUser

# ── Test Data ────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
VIEWER_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

CURRENT_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="test@example.com",
    external_auth_id="user_test_123",
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
async def seed_data(db: AsyncSession) -> None:
    """Seed Organization and Users for FK constraints."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.ALLY)
    db.add(org)
    other_org = Organization(
        id=OTHER_ORG_ID, name="Other Org", slug="other-org", type=OrgType.INVESTOR
    )
    db.add(other_org)
    user = User(
        id=USER_ID, org_id=ORG_ID, email="test@example.com",
        full_name="Test User", role=UserRole.ADMIN,
        external_auth_id="user_test_123", is_active=True,
    )
    db.add(user)
    viewer = User(
        id=VIEWER_USER_ID, org_id=ORG_ID, email="viewer@example.com",
        full_name="Viewer User", role=UserRole.VIEWER,
        external_auth_id="user_test_viewer", is_active=True,
    )
    db.add(viewer)
    await db.flush()


@pytest.fixture
async def test_client(db: AsyncSession, seed_data) -> AsyncClient:
    """Client with admin auth and DB override."""
    app.dependency_overrides[get_current_user] = _override_auth(CURRENT_USER)
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def viewer_client(db: AsyncSession, seed_data) -> AsyncClient:
    """Client with viewer auth (read-only)."""
    app.dependency_overrides[get_current_user] = _override_auth(VIEWER_USER)
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_project(db: AsyncSession, seed_data) -> Project:
    """Create a sample project directly in DB."""
    project = Project(
        org_id=ORG_ID,
        name="Solar Farm Alpha",
        slug="solar-farm-alpha",
        description="A 50MW solar farm in Spain",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="Spain",
        geography_region="Andalusia",
        total_investment_required=Decimal("10000000"),
        currency="EUR",
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


# ── Service: Slugify ─────────────────────────────────────────────────────────


def test_slugify_basic():
    assert service._slugify("Solar Farm Alpha") == "solar-farm-alpha"


def test_slugify_special_chars():
    assert service._slugify("Wind Farm (Offshore) #1!") == "wind-farm-offshore-1"


def test_slugify_multiple_spaces():
    assert service._slugify("  Too   Many   Spaces  ") == "too-many-spaces"


# ── Service: Project CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project(db: AsyncSession, seed_data):
    project = await service.create_project(
        db, CURRENT_USER,
        name="Wind Farm Beta",
        project_type=ProjectType.WIND,
        description="Offshore wind project",
        geography_country="Denmark",
        total_investment_required=Decimal("50000000"),
    )
    assert project.id is not None
    assert project.name == "Wind Farm Beta"
    assert project.slug == "wind-farm-beta"
    assert project.project_type == ProjectType.WIND
    assert project.status == ProjectStatus.DRAFT
    assert project.stage == ProjectStage.CONCEPT
    assert project.org_id == ORG_ID


@pytest.mark.asyncio
async def test_create_project_duplicate_slug(db: AsyncSession, seed_data, sample_project):
    """Second project with same name gets a unique slug."""
    project = await service.create_project(
        db, CURRENT_USER,
        name="Solar Farm Alpha",
        project_type=ProjectType.SOLAR,
        geography_country="Spain",
        total_investment_required=Decimal("5000000"),
    )
    assert project.slug != "solar-farm-alpha"
    assert project.slug.startswith("solar-farm-alpha")


@pytest.mark.asyncio
async def test_list_projects(db: AsyncSession, seed_data, sample_project):
    items, total = await service.list_projects(db, ORG_ID)
    assert total >= 1
    assert any(p.id == sample_project.id for p in items)


@pytest.mark.asyncio
async def test_list_projects_filter_status(db: AsyncSession, seed_data, sample_project):
    items, total = await service.list_projects(db, ORG_ID, status=ProjectStatus.ACTIVE)
    assert total >= 1
    assert all(p.status == ProjectStatus.ACTIVE for p in items)


@pytest.mark.asyncio
async def test_list_projects_filter_type(db: AsyncSession, seed_data, sample_project):
    items, total = await service.list_projects(db, ORG_ID, project_type=ProjectType.SOLAR)
    assert total >= 1
    assert all(p.project_type == ProjectType.SOLAR for p in items)


@pytest.mark.asyncio
async def test_list_projects_search(db: AsyncSession, seed_data, sample_project):
    items, total = await service.list_projects(db, ORG_ID, search="solar")
    assert total >= 1


@pytest.mark.asyncio
async def test_list_projects_pagination(db: AsyncSession, seed_data, sample_project):
    items, total = await service.list_projects(db, ORG_ID, page=1, page_size=1)
    assert len(items) <= 1


@pytest.mark.asyncio
async def test_list_projects_tenant_isolation(db: AsyncSession, seed_data, sample_project):
    """Other org should not see our projects."""
    items, total = await service.list_projects(db, OTHER_ORG_ID)
    assert total == 0


@pytest.mark.asyncio
async def test_get_project(db: AsyncSession, seed_data, sample_project):
    project = await service.get_project(db, sample_project.id, ORG_ID)
    assert project.id == sample_project.id
    assert project.name == "Solar Farm Alpha"


@pytest.mark.asyncio
async def test_get_project_not_found(db: AsyncSession, seed_data):
    with pytest.raises(LookupError):
        await service.get_project(db, uuid.uuid4(), ORG_ID)


@pytest.mark.asyncio
async def test_get_project_wrong_org(db: AsyncSession, seed_data, sample_project):
    """Cannot access project from another org."""
    with pytest.raises(LookupError):
        await service.get_project(db, sample_project.id, OTHER_ORG_ID)


@pytest.mark.asyncio
async def test_update_project(db: AsyncSession, seed_data, sample_project):
    updated = await service.update_project(
        db, sample_project.id, ORG_ID, name="Solar Farm Alpha V2"
    )
    assert updated.name == "Solar Farm Alpha V2"


@pytest.mark.asyncio
async def test_delete_project(db: AsyncSession, seed_data, sample_project):
    await service.delete_project(db, sample_project.id, ORG_ID)
    # Should not be found after soft delete
    with pytest.raises(LookupError):
        await service.get_project(db, sample_project.id, ORG_ID)


# ── Service: Publish ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_project_success(db: AsyncSession, seed_data, sample_project):
    published = await service.publish_project(db, sample_project.id, ORG_ID)
    assert published.is_published is True
    assert published.published_at is not None
    assert published.status == ProjectStatus.ACTIVE


@pytest.mark.asyncio
async def test_publish_project_missing_fields(db: AsyncSession, seed_data):
    """Project missing description should fail publish."""
    project = Project(
        org_id=ORG_ID,
        name="Incomplete Project",
        slug="incomplete-project",
        description="",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.DRAFT,
        stage=ProjectStage.CONCEPT,
        geography_country="Spain",
        total_investment_required=Decimal("1000000"),
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    with pytest.raises(ValueError, match="Cannot publish"):
        await service.publish_project(db, project.id, ORG_ID)


# ── Service: Stats ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_project_stats(db: AsyncSession, seed_data, sample_project):
    stats = await service.get_project_stats(db, ORG_ID)
    assert stats["total_projects"] >= 1
    assert isinstance(stats["total_funding_needed"], (int, float, Decimal))


# ── Service: Milestones ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_milestone(db: AsyncSession, seed_data, sample_project):
    milestone = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="Phase 1 Complete",
        target_date=date(2025, 6, 30),
        description="Initial development phase",
    )
    assert milestone.name == "Phase 1 Complete"
    assert milestone.status == MilestoneStatus.NOT_STARTED
    assert milestone.project_id == sample_project.id


@pytest.mark.asyncio
async def test_list_milestones(db: AsyncSession, seed_data, sample_project):
    await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="Milestone 1", target_date=date(2025, 3, 1),
    )
    await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="Milestone 2", target_date=date(2025, 6, 1),
    )
    milestones = await service.list_milestones(db, sample_project.id, ORG_ID)
    assert len(milestones) >= 2


@pytest.mark.asyncio
async def test_update_milestone(db: AsyncSession, seed_data, sample_project):
    milestone = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="Milestone X", target_date=date(2025, 3, 1),
    )
    updated = await service.update_milestone(
        db, milestone.id, sample_project.id, ORG_ID,
        name="Milestone X Updated", completion_pct=50,
    )
    assert updated.name == "Milestone X Updated"
    assert updated.completion_pct == 50


@pytest.mark.asyncio
async def test_update_milestone_auto_complete(db: AsyncSession, seed_data, sample_project):
    """Setting status to COMPLETED should auto-set completed_date and 100%."""
    milestone = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="Auto Complete", target_date=date(2025, 3, 1),
    )
    updated = await service.update_milestone(
        db, milestone.id, sample_project.id, ORG_ID,
        status=MilestoneStatus.COMPLETED,
    )
    assert updated.status == MilestoneStatus.COMPLETED
    assert updated.completed_date is not None
    assert updated.completion_pct == 100


@pytest.mark.asyncio
async def test_delete_milestone(db: AsyncSession, seed_data, sample_project):
    milestone = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="To Delete", target_date=date(2025, 3, 1),
    )
    await service.delete_milestone(db, milestone.id, sample_project.id, ORG_ID)
    milestones = await service.list_milestones(db, sample_project.id, ORG_ID)
    assert all(m.id != milestone.id for m in milestones)


@pytest.mark.asyncio
async def test_milestone_wrong_project(db: AsyncSession, seed_data, sample_project):
    """Milestone on another project should not be accessible."""
    milestone = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="Test", target_date=date(2025, 3, 1),
    )
    fake_project_id = uuid.uuid4()
    with pytest.raises(LookupError):
        await service.update_milestone(
            db, milestone.id, fake_project_id, ORG_ID, name="Fail"
        )


# ── Service: Budget Items ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_budget_item(db: AsyncSession, seed_data, sample_project):
    item = await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="Equipment",
        description="Solar panels",
        estimated_amount=Decimal("500000"),
    )
    assert item.category == "Equipment"
    assert item.estimated_amount == Decimal("500000")
    assert item.status == BudgetItemStatus.PLANNED


@pytest.mark.asyncio
async def test_list_budget_items(db: AsyncSession, seed_data, sample_project):
    await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="Equipment", estimated_amount=Decimal("500000"),
    )
    await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="Labor", estimated_amount=Decimal("200000"),
    )
    items = await service.list_budget_items(db, sample_project.id, ORG_ID)
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_update_budget_item(db: AsyncSession, seed_data, sample_project):
    item = await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="Equipment", estimated_amount=Decimal("500000"),
    )
    updated = await service.update_budget_item(
        db, item.id, sample_project.id, ORG_ID,
        actual_amount=Decimal("480000"),
        status=BudgetItemStatus.COMMITTED,
    )
    assert updated.actual_amount == Decimal("480000")
    assert updated.status == BudgetItemStatus.COMMITTED


@pytest.mark.asyncio
async def test_delete_budget_item(db: AsyncSession, seed_data, sample_project):
    item = await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="To Delete", estimated_amount=Decimal("1000"),
    )
    await service.delete_budget_item(db, item.id, sample_project.id, ORG_ID)
    items = await service.list_budget_items(db, sample_project.id, ORG_ID)
    assert all(b.id != item.id for b in items)


# ── API Endpoint Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_create_project(test_client: AsyncClient):
    resp = await test_client.post("/projects", json={
        "name": "API Test Project",
        "project_type": "solar",
        "geography_country": "Germany",
        "total_investment_required": "25000000",
        "description": "Created via API test",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API Test Project"
    assert data["project_type"] == "solar"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_api_list_projects(test_client: AsyncClient, sample_project):
    resp = await test_client.get("/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_api_list_projects_with_filters(test_client: AsyncClient, sample_project):
    resp = await test_client.get("/projects", params={
        "status": "active",
        "type": "solar",
        "geography": "Spain",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_api_get_project_detail(test_client: AsyncClient, sample_project):
    resp = await test_client.get(f"/projects/{sample_project.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(sample_project.id)
    assert data["name"] == "Solar Farm Alpha"
    assert "milestone_count" in data
    assert "budget_item_count" in data
    assert "document_count" in data


@pytest.mark.asyncio
async def test_api_get_project_not_found(test_client: AsyncClient):
    resp = await test_client.get(f"/projects/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_update_project(test_client: AsyncClient, sample_project):
    resp = await test_client.put(f"/projects/{sample_project.id}", json={
        "name": "Updated Solar Farm",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Solar Farm"


@pytest.mark.asyncio
async def test_api_delete_project(test_client: AsyncClient, sample_project):
    resp = await test_client.delete(f"/projects/{sample_project.id}")
    assert resp.status_code == 204
    # Verify it's gone
    resp2 = await test_client.get(f"/projects/{sample_project.id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_api_publish_project(test_client: AsyncClient, sample_project):
    resp = await test_client.put(f"/projects/{sample_project.id}/publish")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_published"] is True


@pytest.mark.asyncio
async def test_api_stats(test_client: AsyncClient, sample_project):
    resp = await test_client.get("/projects/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_projects" in data
    assert "active_fundraising" in data
    assert "total_funding_needed" in data


# ── API Milestone Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_create_milestone(test_client: AsyncClient, sample_project):
    resp = await test_client.post(f"/projects/{sample_project.id}/milestones", json={
        "name": "API Milestone",
        "target_date": "2025-06-30",
        "description": "Test milestone",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API Milestone"
    assert data["status"] == "not_started"


@pytest.mark.asyncio
async def test_api_list_milestones(test_client: AsyncClient, sample_project, db: AsyncSession):
    await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="M1", target_date=date(2025, 3, 1),
    )
    resp = await test_client.get(f"/projects/{sample_project.id}/milestones")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_update_milestone(test_client: AsyncClient, sample_project, db: AsyncSession):
    m = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="To Update", target_date=date(2025, 3, 1),
    )
    resp = await test_client.put(
        f"/projects/{sample_project.id}/milestones/{m.id}",
        json={"name": "Updated Milestone", "completion_pct": 75},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Milestone"
    assert resp.json()["completion_pct"] == 75


@pytest.mark.asyncio
async def test_api_delete_milestone(test_client: AsyncClient, sample_project, db: AsyncSession):
    m = await service.create_milestone(
        db, sample_project.id, ORG_ID,
        name="To Delete", target_date=date(2025, 3, 1),
    )
    resp = await test_client.delete(f"/projects/{sample_project.id}/milestones/{m.id}")
    assert resp.status_code == 204


# ── API Budget Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_create_budget_item(test_client: AsyncClient, sample_project):
    resp = await test_client.post(f"/projects/{sample_project.id}/budget", json={
        "category": "Equipment",
        "description": "Solar panels",
        "estimated_amount": "500000",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "Equipment"
    assert data["status"] == "planned"


@pytest.mark.asyncio
async def test_api_list_budget_items(test_client: AsyncClient, sample_project, db: AsyncSession):
    await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="Labor", estimated_amount=Decimal("200000"),
    )
    resp = await test_client.get(f"/projects/{sample_project.id}/budget")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_update_budget_item(test_client: AsyncClient, sample_project, db: AsyncSession):
    b = await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="Equipment", estimated_amount=Decimal("500000"),
    )
    resp = await test_client.put(
        f"/projects/{sample_project.id}/budget/{b.id}",
        json={"actual_amount": "480000", "status": "committed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "committed"


@pytest.mark.asyncio
async def test_api_delete_budget_item(test_client: AsyncClient, sample_project, db: AsyncSession):
    b = await service.create_budget_item(
        db, sample_project.id, ORG_ID,
        category="To Delete", estimated_amount=Decimal("1000"),
    )
    resp = await test_client.delete(f"/projects/{sample_project.id}/budget/{b.id}")
    assert resp.status_code == 204


# ── RBAC Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(viewer_client: AsyncClient):
    resp = await viewer_client.post("/projects", json={
        "name": "Viewer Project",
        "project_type": "solar",
        "geography_country": "Spain",
        "total_investment_required": "1000000",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_project(viewer_client: AsyncClient, sample_project):
    resp = await viewer_client.delete(f"/projects/{sample_project.id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_list_projects(viewer_client: AsyncClient, sample_project):
    resp = await viewer_client.get("/projects")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_view_project(viewer_client: AsyncClient, sample_project):
    resp = await viewer_client.get(f"/projects/{sample_project.id}")
    assert resp.status_code == 200


# ── Signal Score Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_latest_signal_score(db: AsyncSession, seed_data, sample_project):
    score_v1 = SignalScore(
        project_id=sample_project.id,
        overall_score=72,
        project_viability_score=80,
        financial_planning_score=65,
        esg_score=75,
        risk_assessment_score=70,
        team_strength_score=68,
        market_opportunity_score=60,
        model_used="claude-sonnet-4",
        version=1,
        calculated_at=datetime.utcnow(),
    )
    db.add(score_v1)
    score_v2 = SignalScore(
        project_id=sample_project.id,
        overall_score=78,
        project_viability_score=85,
        financial_planning_score=70,
        esg_score=80,
        risk_assessment_score=75,
        team_strength_score=72,
        market_opportunity_score=65,
        model_used="claude-sonnet-4",
        version=2,
        calculated_at=datetime.utcnow(),
    )
    db.add(score_v2)
    await db.flush()

    latest = await service.get_latest_signal_score(db, sample_project.id)
    assert latest is not None
    assert latest.version == 2
    assert latest.overall_score == 78


@pytest.mark.asyncio
async def test_project_detail_includes_signal_score(
    test_client: AsyncClient, sample_project, db: AsyncSession
):
    score = SignalScore(
        project_id=sample_project.id,
        overall_score=85,
        project_viability_score=90,
        financial_planning_score=80,
        esg_score=85,
        risk_assessment_score=82,
        team_strength_score=88,
        market_opportunity_score=75,
        model_used="claude-sonnet-4",
        version=1,
        calculated_at=datetime.utcnow(),
    )
    db.add(score)
    await db.flush()

    resp = await test_client.get(f"/projects/{sample_project.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["latest_signal_score"] == 85
    assert data["latest_signal"] is not None
    assert data["latest_signal"]["overall_score"] == 85
