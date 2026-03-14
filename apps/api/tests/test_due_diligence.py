"""Tests for the Due Diligence Checklist module — templates, checklists, item status updates."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.core import Organization, User
from app.models.due_diligence import (
    DDChecklistItem,
    DDChecklistTemplate,
    DDItemStatus,
    DDProjectChecklist,
)
from app.models.enums import OrgType, ProjectType, UserRole
from app.models.projects import Project
from app.modules.due_diligence import service
from app.schemas.auth import CurrentUser

# ── Constants ─────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

CURRENT_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="dd@example.com",
    external_auth_id="user_dd_001",
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user

    return _override


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def seed_data(db: AsyncSession) -> None:
    org = Organization(id=ORG_ID, name="DD Org", slug="dd-org", type=OrgType.INVESTOR)
    user = User(
        id=USER_ID,
        org_id=ORG_ID,
        email="dd@example.com",
        full_name="DD User",
        role=UserRole.ADMIN,
        external_auth_id="user_dd_001",
        is_active=True,
    )
    db.add_all([org, user])
    await db.flush()


@pytest.fixture
async def test_client(db: AsyncSession, seed_data: None) -> AsyncClient:
    app.dependency_overrides[get_current_user] = _override_auth(CURRENT_USER)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_template(db: AsyncSession, seed_data: None) -> DDChecklistTemplate:
    """A single active DD template for solar / screening stage."""
    template = DDChecklistTemplate(
        asset_type="solar",
        deal_stage="screening",
        name="Solar Screening Checklist",
        version=1,
        is_active=True,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@pytest.fixture
async def template_with_items(
    db: AsyncSession, sample_template: DDChecklistTemplate
) -> tuple[DDChecklistTemplate, list[DDChecklistItem]]:
    """Template with two checklist items."""
    item1 = DDChecklistItem(
        template_id=sample_template.id,
        category="financial",
        name="Audited Financial Statements",
        requirement_type="mandatory",
        required_document_types=["financial_statement"],
        priority="required",
        sort_order=1,
    )
    item2 = DDChecklistItem(
        template_id=sample_template.id,
        category="legal",
        name="Corporate Structure Chart",
        requirement_type="mandatory",
        required_document_types=["legal_agreement"],
        priority="required",
        sort_order=2,
    )
    db.add_all([item1, item2])
    await db.flush()
    await db.refresh(item1)
    await db.refresh(item2)
    return sample_template, [item1, item2]


@pytest.fixture
async def sample_project(db: AsyncSession, seed_data: None) -> Project:
    from decimal import Decimal

    project = Project(
        org_id=ORG_ID,
        name="Solar Alpha Project",
        slug="solar-alpha-project",
        project_type=ProjectType.SOLAR,
        geography_country="KE",
        total_investment_required=Decimal("5000000"),
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@pytest.fixture
async def sample_checklist(
    db: AsyncSession,
    template_with_items: tuple[DDChecklistTemplate, list[DDChecklistItem]],
    sample_project: Project,
) -> DDProjectChecklist:
    """A DD checklist with two items in pending status."""
    template, items = template_with_items
    checklist = DDProjectChecklist(
        project_id=sample_project.id,
        org_id=ORG_ID,
        template_id=template.id,
        status="in_progress",
        completion_percentage=0.0,
        total_items=len(items),
        completed_items=0,
        custom_items=[],
    )
    db.add(checklist)
    await db.flush()

    for item in items:
        item_status = DDItemStatus(
            checklist_id=checklist.id,
            item_id=item.id,
            status="pending",
        )
        db.add(item_status)

    await db.flush()
    await db.refresh(checklist)
    return checklist


# ── Tests: Templates ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_templates_returns_active_only(
    test_client: AsyncClient,
    sample_template: DDChecklistTemplate,
    db: AsyncSession,
    seed_data: None,
) -> None:
    """GET /due-diligence/templates returns only is_active=True templates."""
    inactive = DDChecklistTemplate(
        asset_type="wind",
        deal_stage="screening",
        name="Inactive Wind Template",
        is_active=False,
    )
    db.add(inactive)
    await db.flush()

    resp = await test_client.get("/v1/due-diligence/templates")
    assert resp.status_code == 200
    data = resp.json()
    names = [t["name"] for t in data]
    assert "Solar Screening Checklist" in names
    assert "Inactive Wind Template" not in names


@pytest.mark.anyio
async def test_list_templates_filter_by_asset_type(
    test_client: AsyncClient,
    sample_template: DDChecklistTemplate,
    db: AsyncSession,
    seed_data: None,
) -> None:
    """Filtering templates by asset_type returns only matching entries."""
    wind_template = DDChecklistTemplate(
        asset_type="wind",
        deal_stage="full_dd",
        name="Wind Full DD Checklist",
        is_active=True,
    )
    db.add(wind_template)
    await db.flush()

    resp = await test_client.get("/v1/due-diligence/templates?asset_type=solar")
    assert resp.status_code == 200
    data = resp.json()
    for t in data:
        assert t["asset_type"] == "solar"


@pytest.mark.anyio
async def test_generate_checklist_creates_project_checklist(
    test_client: AsyncClient,
    template_with_items: tuple[DDChecklistTemplate, list[DDChecklistItem]],
    sample_project: Project,
) -> None:
    """POST /due-diligence/checklists/generate creates a checklist from the best template."""
    resp = await test_client.post(
        "/v1/due-diligence/checklists/generate",
        json={"project_id": str(sample_project.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == str(sample_project.id)
    assert data["org_id"] == str(ORG_ID)
    assert data["total_items"] == 2
    assert data["status"] == "in_progress"


@pytest.mark.anyio
async def test_generate_checklist_missing_project_returns_404(
    test_client: AsyncClient, seed_data: None
) -> None:
    """POST /due-diligence/checklists/generate with unknown project returns 404."""
    resp = await test_client.post(
        "/v1/due-diligence/checklists/generate",
        json={"project_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_list_checklists_org_scoped(
    test_client: AsyncClient,
    sample_checklist: DDProjectChecklist,
) -> None:
    """GET /due-diligence/checklists returns this org's checklists only."""
    resp = await test_client.get("/v1/due-diligence/checklists")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    ids = [c["id"] for c in data]
    assert str(sample_checklist.id) in ids


@pytest.mark.anyio
async def test_list_checklists_filter_by_project(
    test_client: AsyncClient,
    sample_checklist: DDProjectChecklist,
    sample_project: Project,
) -> None:
    """Filtering by project_id narrows the checklist list correctly."""
    resp = await test_client.get(
        f"/v1/due-diligence/checklists?project_id={sample_project.id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    for item in data:
        assert item["project_id"] == str(sample_project.id)


@pytest.mark.anyio
async def test_get_checklist_returns_200_for_own(
    test_client: AsyncClient,
    sample_checklist: DDProjectChecklist,
) -> None:
    """GET /due-diligence/checklists/{id} returns the checklist with items_by_category."""
    resp = await test_client.get(f"/v1/due-diligence/checklists/{sample_checklist.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(sample_checklist.id)
    assert "items_by_category" in data
    assert data["total_items"] == 2


@pytest.mark.anyio
async def test_get_checklist_returns_404_for_missing(test_client: AsyncClient) -> None:
    """GET /due-diligence/checklists/{id} returns 404 for an unknown checklist."""
    resp = await test_client.get(f"/v1/due-diligence/checklists/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_item_status_valid_transition(
    test_client: AsyncClient,
    sample_checklist: DDProjectChecklist,
    template_with_items: tuple[DDChecklistTemplate, list[DDChecklistItem]],
) -> None:
    """PUT on a checklist item with status 'satisfied' succeeds and updates the item."""
    _template, items = template_with_items
    item = items[0]

    resp = await test_client.put(
        f"/v1/due-diligence/checklists/{sample_checklist.id}/items/{item.id}/status",
        json={"status": "satisfied", "notes": "All financial docs reviewed and approved."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "satisfied"
    assert data["reviewer_notes"] == "All financial docs reviewed and approved."


@pytest.mark.anyio
async def test_update_item_status_invalid_value_returns_400(
    test_client: AsyncClient,
    sample_checklist: DDProjectChecklist,
    template_with_items: tuple[DDChecklistTemplate, list[DDChecklistItem]],
) -> None:
    """PUT with an unrecognised status value returns 400."""
    _template, items = template_with_items
    item = items[0]

    resp = await test_client.put(
        f"/v1/due-diligence/checklists/{sample_checklist.id}/items/{item.id}/status",
        json={"status": "approved_by_magic"},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_completion_percentage_recalculated_after_status_update(
    db: AsyncSession,
    sample_checklist: DDProjectChecklist,
    template_with_items: tuple[DDChecklistTemplate, list[DDChecklistItem]],
) -> None:
    """After marking one of two items satisfied, completion_percentage becomes 50%."""
    _template, items = template_with_items
    item = items[0]

    await service.update_item_status(
        db,
        checklist_id=sample_checklist.id,
        item_id=item.id,
        org_id=ORG_ID,
        status="satisfied",
    )
    await db.refresh(sample_checklist)

    assert sample_checklist.completion_percentage == pytest.approx(50.0, abs=0.1)
    assert sample_checklist.completed_items == 1


@pytest.mark.anyio
async def test_all_items_satisfied_marks_checklist_completed(
    db: AsyncSession,
    sample_checklist: DDProjectChecklist,
    template_with_items: tuple[DDChecklistTemplate, list[DDChecklistItem]],
) -> None:
    """When all items are satisfied, checklist status transitions to 'completed'."""
    _template, items = template_with_items

    for item in items:
        await service.update_item_status(
            db,
            checklist_id=sample_checklist.id,
            item_id=item.id,
            org_id=ORG_ID,
            status="satisfied",
        )

    await db.refresh(sample_checklist)
    assert sample_checklist.status == "completed"
    assert sample_checklist.completion_percentage == pytest.approx(100.0, abs=0.1)
