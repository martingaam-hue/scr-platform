"""Tests for the expert insights module: CRUD, org scoping, AI enrichment trigger."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStage, ProjectStatus, ProjectType
from app.models.expert_notes import ExpertNote
from app.models.projects import Project
from app.modules.expert_insights.schemas import (
    CreateExpertNoteRequest,
    UpdateExpertNoteRequest,
)
from app.modules.expert_insights.service import ExpertInsightsService
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000088")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_project(db: AsyncSession, org_id: uuid.UUID) -> Project:
    from decimal import Decimal

    proj = Project(
        org_id=org_id,
        name="Expert Notes Test Project",
        slug="expert-notes-project-" + str(uuid.uuid4())[:8],
        description="",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="Germany",
        geography_region="Europe",
        total_investment_required=Decimal("1000000"),
    )
    db.add(proj)
    await db.flush()
    await db.refresh(proj)
    return proj


async def _make_note(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    title: str = "Site Visit Notes",
    note_type: str = "site_visit",
    is_private: bool = False,
) -> ExpertNote:
    note = ExpertNote(
        org_id=org_id,
        project_id=project_id,
        created_by=SAMPLE_USER_ID,
        note_type=note_type,
        title=title,
        content="Detailed observations from the site visit.",
        enrichment_status="pending",
        is_private=is_private,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_create_note_stores_and_returns_note(db: AsyncSession, sample_org, sample_user):
    """Service.create_note persists a new ExpertNote and returns it."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    svc = ExpertInsightsService(db)

    data = CreateExpertNoteRequest(
        project_id=proj.id,
        note_type="management_call",
        title="Q3 Management Call",
        content="CEO confirmed pipeline milestones on track.",
        participants=[{"name": "CEO", "role": "executive"}],
        meeting_date=date(2026, 3, 10),
    )
    note = await svc.create_note(SAMPLE_ORG_ID, SAMPLE_USER_ID, data)

    assert note.id is not None
    assert note.title == "Q3 Management Call"
    assert note.org_id == SAMPLE_ORG_ID
    assert note.project_id == proj.id
    assert note.enrichment_status == "pending"
    assert note.is_deleted is False


async def test_list_notes_returns_only_org_notes(db: AsyncSession, sample_org, sample_user):
    """list_notes is org-scoped — notes from another org are not visible."""
    from app.models.core import Organization
    from app.models.enums import OrgType

    proj = await _make_project(db, SAMPLE_ORG_ID)
    await _make_note(db, SAMPLE_ORG_ID, proj.id, title="Own Note")

    # Create the other org so FK constraint is satisfied
    other_org = Organization(
        id=OTHER_ORG_ID,
        name="Other Org",
        slug="other-org-expert",
        type=OrgType.INVESTOR,
    )
    db.add(other_org)
    await db.flush()

    other_note = ExpertNote(
        org_id=OTHER_ORG_ID,
        project_id=proj.id,
        created_by=SAMPLE_USER_ID,
        note_type="call",
        title="Other Org Note",
        content="Should not be visible",
        enrichment_status="pending",
    )
    db.add(other_note)
    await db.flush()

    svc = ExpertInsightsService(db)
    notes = await svc.list_notes(SAMPLE_ORG_ID)

    titles = [n.title for n in notes]
    assert "Own Note" in titles
    assert "Other Org Note" not in titles


async def test_list_notes_filtered_by_project(db: AsyncSession, sample_org, sample_user):
    """list_notes filters by project_id when provided."""
    proj_a = await _make_project(db, SAMPLE_ORG_ID)
    proj_b = await _make_project(db, SAMPLE_ORG_ID)
    await _make_note(db, SAMPLE_ORG_ID, proj_a.id, title="Note for A")
    await _make_note(db, SAMPLE_ORG_ID, proj_b.id, title="Note for B")

    svc = ExpertInsightsService(db)
    notes = await svc.list_notes(SAMPLE_ORG_ID, project_id=proj_a.id)

    assert all(n.project_id == proj_a.id for n in notes)
    titles = [n.title for n in notes]
    assert "Note for A" in titles
    assert "Note for B" not in titles


async def test_update_note_patches_fields(db: AsyncSession, sample_org, sample_user):
    """update_note only changes provided fields; others are untouched."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    note = await _make_note(db, SAMPLE_ORG_ID, proj.id, title="Original Title")
    svc = ExpertInsightsService(db)

    updated = await svc.update_note(
        SAMPLE_ORG_ID,
        note.id,
        UpdateExpertNoteRequest(title="Updated Title", is_private=True),
    )

    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.is_private is True
    # Untouched fields remain
    assert updated.note_type == note.note_type
    assert updated.content == note.content


async def test_delete_note_soft_deletes(db: AsyncSession, sample_org, sample_user):
    """delete_note sets is_deleted=True and hides the note from list_notes."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    note = await _make_note(db, SAMPLE_ORG_ID, proj.id, title="To Be Deleted")
    svc = ExpertInsightsService(db)

    deleted = await svc.delete_note(SAMPLE_ORG_ID, note.id)
    assert deleted is True

    remaining = await svc.list_notes(SAMPLE_ORG_ID)
    assert all(n.id != note.id for n in remaining)


async def test_get_note_returns_none_for_wrong_org(db: AsyncSession, sample_org, sample_user):
    """get_note returns None when the org_id doesn't match."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    note = await _make_note(db, SAMPLE_ORG_ID, proj.id)
    svc = ExpertInsightsService(db)

    result = await svc.get_note(OTHER_ORG_ID, note.id)
    assert result is None


async def test_get_project_insights_timeline_ordering(db: AsyncSession, sample_org, sample_user):
    """Timeline returns notes ordered by meeting_date descending."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    svc = ExpertInsightsService(db)

    for title, meeting_date in [
        ("Earliest Call", date(2026, 1, 1)),
        ("Middle Call", date(2026, 2, 15)),
        ("Latest Call", date(2026, 3, 10)),
    ]:
        note = ExpertNote(
            org_id=SAMPLE_ORG_ID,
            project_id=proj.id,
            created_by=SAMPLE_USER_ID,
            note_type="call",
            title=title,
            content="Content",
            meeting_date=meeting_date,
            enrichment_status="pending",
        )
        db.add(note)
    await db.flush()

    timeline_data = await svc.get_project_insights_timeline(SAMPLE_ORG_ID, proj.id)
    timeline = timeline_data["timeline"]

    assert timeline_data["total"] == 3
    # Most recent first
    assert timeline[0]["title"] == "Latest Call"
    assert timeline[-1]["title"] == "Earliest Call"


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_create_note_returns_201(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/expert-insights returns 201 with persisted note data."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    # Suppress Celery + background task enrichment
    with patch(
        "app.core.celery_app.celery_app"
    ), patch("app.modules.expert_insights.tasks.enrich_expert_note_task", new_callable=AsyncMock):
        resp = await authenticated_client.post(
            "/v1/expert-insights",
            json={
                "project_id": str(proj.id),
                "note_type": "expert_interview",
                "title": "Renewable Energy Expert Q&A",
                "content": "Expert confirmed technology readiness level 7.",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Renewable Energy Expert Q&A"
    assert data["note_type"] == "expert_interview"
    assert data["enrichment_status"] == "pending"
    assert "id" in data


async def test_http_list_notes_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/expert-insights returns paginated list."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    await _make_note(db, SAMPLE_ORG_ID, proj.id, title="Listed Note")

    resp = await authenticated_client.get("/v1/expert-insights")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


async def test_http_get_note_404_for_unknown(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/expert-insights/{unknown_id} returns 404."""
    resp = await authenticated_client.get(f"/v1/expert-insights/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_http_delete_note_returns_204(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """DELETE /v1/expert-insights/{id} returns 204 and hides the note."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    note = await _make_note(db, SAMPLE_ORG_ID, proj.id, title="About to be Deleted")

    delete_resp = await authenticated_client.delete(f"/v1/expert-insights/{note.id}")
    assert delete_resp.status_code == 204

    get_resp = await authenticated_client.get(f"/v1/expert-insights/{note.id}")
    assert get_resp.status_code == 404
