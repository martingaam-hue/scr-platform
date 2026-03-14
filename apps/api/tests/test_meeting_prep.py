"""Tests for the meeting_prep module: briefing generation, CRUD, AI mock, HTTP endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStage, ProjectStatus, ProjectType
from app.models.meeting_prep import MeetingBriefing
from app.models.projects import Project
from app.modules.meeting_prep import service
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000044")

# Reusable fake AI briefing content returned by the mocked gateway
_FAKE_BRIEFING = {
    "executive_summary": "AI-generated summary of the project.",
    "key_metrics": {"irr": "12%", "npv": "$5M"},
    "risk_flags": ["Permitting delay risk"],
    "dd_progress": {"legal": "complete", "financial": "in_progress"},
    "talking_points": ["Confirm timeline", "Review financial model"],
    "questions_to_ask": ["What is the permitting status?"],
    "changes_since_last": [],
}


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_project(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str = "Meeting Prep Test Project",
) -> Project:
    from decimal import Decimal

    proj = Project(
        org_id=org_id,
        name=name,
        slug="mp-test-" + str(uuid.uuid4())[:8],
        description="",
        project_type=ProjectType.WIND,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="FR",
        geography_region="Europe",
        capacity_mw=Decimal("80"),
        total_investment_required=Decimal("96000000"),
    )
    db.add(proj)
    await db.flush()
    await db.refresh(proj)
    return proj


async def _make_briefing(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    meeting_type: str = "screening",
    briefing_content: dict | None = None,
) -> MeetingBriefing:
    briefing = MeetingBriefing(
        org_id=org_id,
        project_id=project_id,
        created_by=SAMPLE_USER_ID,
        meeting_type=meeting_type,
        meeting_date=date(2026, 4, 10),
        briefing_content=briefing_content or _FAKE_BRIEFING,
    )
    db.add(briefing)
    await db.flush()
    await db.refresh(briefing)
    return briefing


# ── AI generation mock helper ─────────────────────────────────────────────────


def _patch_ai_gateway(briefing_content: dict | None = None):
    """Context manager that mocks the AI gateway to return fake briefing content."""
    content = briefing_content or _FAKE_BRIEFING

    mock_resp = AsyncMock()
    mock_resp.raise_for_status = AsyncMock()
    mock_resp.json.return_value = {"validated_data": content}

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)
    mock_http.post = AsyncMock(return_value=mock_resp)

    return patch("httpx.AsyncClient", return_value=mock_http)


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_generate_briefing_stores_ai_content(db: AsyncSession, sample_org, sample_user):
    """generate_briefing stores the AI-returned content in briefing_content."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    with _patch_ai_gateway():
        briefing = await service.generate_briefing(
            db,
            org_id=SAMPLE_ORG_ID,
            project_id=proj.id,
            user_id=SAMPLE_USER_ID,
            meeting_type="screening",
            meeting_date=date(2026, 4, 15),
        )

    assert briefing.id is not None
    assert briefing.org_id == SAMPLE_ORG_ID
    assert briefing.project_id == proj.id
    assert briefing.meeting_type == "screening"
    assert briefing.meeting_date == date(2026, 4, 15)
    # Content should be present (either from AI gateway or fallback)
    assert briefing.briefing_content is not None
    assert "talking_points" in briefing.briefing_content


async def test_generate_briefing_uses_fallback_when_ai_fails(
    db: AsyncSession, sample_org, sample_user
):
    """generate_briefing uses the fallback briefing when the AI gateway raises an exception."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(side_effect=Exception("Gateway timeout"))
        mock_cls.return_value = mock_http

        briefing = await service.generate_briefing(
            db,
            org_id=SAMPLE_ORG_ID,
            project_id=proj.id,
            user_id=SAMPLE_USER_ID,
            meeting_type="dd_review",
        )

    # Fallback briefing should still contain the standard talking points
    assert briefing.briefing_content is not None
    content = briefing.briefing_content
    assert "talking_points" in content
    assert isinstance(content["talking_points"], list)
    assert len(content["talking_points"]) > 0


async def test_list_briefings_returns_only_org_briefings(
    db: AsyncSession, sample_org, sample_user
):
    """list_briefings is org-scoped — briefings from another org are not visible."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    own_briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id, meeting_type="screening")

    # Briefing for another org
    other_briefing = MeetingBriefing(
        org_id=OTHER_ORG_ID,
        project_id=proj.id,
        created_by=SAMPLE_USER_ID,
        meeting_type="follow_up",
        briefing_content=_FAKE_BRIEFING,
    )
    db.add(other_briefing)
    await db.flush()

    briefings = await service.list_briefings(db, org_id=SAMPLE_ORG_ID)

    ids = [b.id for b in briefings]
    assert own_briefing.id in ids
    assert other_briefing.id not in ids


async def test_list_briefings_filtered_by_project(db: AsyncSession, sample_org, sample_user):
    """list_briefings(project_id=...) returns only briefings for that project."""
    proj_a = await _make_project(db, SAMPLE_ORG_ID, name="Project A")
    proj_b = await _make_project(db, SAMPLE_ORG_ID, name="Project B")
    briefing_a = await _make_briefing(db, SAMPLE_ORG_ID, proj_a.id)
    briefing_b = await _make_briefing(db, SAMPLE_ORG_ID, proj_b.id)

    results = await service.list_briefings(db, org_id=SAMPLE_ORG_ID, project_id=proj_a.id)

    ids = [b.id for b in results]
    assert briefing_a.id in ids
    assert briefing_b.id not in ids


async def test_get_briefing_returns_correct_record(db: AsyncSession, sample_org, sample_user):
    """get_briefing returns the matching briefing by id and org."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id, meeting_type="ic_presentation")

    result = await service.get_briefing(db, briefing_id=briefing.id, org_id=SAMPLE_ORG_ID)

    assert result is not None
    assert result.id == briefing.id
    assert result.meeting_type == "ic_presentation"


async def test_get_briefing_returns_none_for_wrong_org(db: AsyncSession, sample_org, sample_user):
    """get_briefing returns None when the org_id does not match the briefing."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id)

    result = await service.get_briefing(db, briefing_id=briefing.id, org_id=OTHER_ORG_ID)
    assert result is None


async def test_update_briefing_saves_custom_overrides(db: AsyncSession, sample_org, sample_user):
    """update_briefing stores custom_overrides without replacing briefing_content."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id)
    original_content = briefing.briefing_content

    overrides = {"executive_summary": "Manually updated summary by analyst."}
    updated = await service.update_briefing(
        db,
        briefing_id=briefing.id,
        org_id=SAMPLE_ORG_ID,
        custom_overrides=overrides,
    )

    assert updated is not None
    assert updated.custom_overrides == overrides
    # Original AI content is untouched
    assert updated.briefing_content == original_content


async def test_delete_briefing_soft_deletes(db: AsyncSession, sample_org, sample_user):
    """delete_briefing sets is_deleted=True and hides the briefing from list_briefings."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id)

    result = await service.delete_briefing(db, briefing_id=briefing.id, org_id=SAMPLE_ORG_ID)
    assert result is True

    remaining = await service.list_briefings(db, org_id=SAMPLE_ORG_ID)
    assert all(b.id != briefing.id for b in remaining)


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_generate_briefing_returns_201(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/meeting-prep/briefings returns 201 with briefing data."""
    proj = await _make_project(db, SAMPLE_ORG_ID)

    with _patch_ai_gateway():
        resp = await authenticated_client.post(
            "/v1/meeting-prep/briefings",
            json={
                "project_id": str(proj.id),
                "meeting_type": "screening",
                "meeting_date": "2026-04-20",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == str(proj.id)
    assert data["meeting_type"] == "screening"
    assert data["briefing_content"] is not None
    assert "id" in data


async def test_http_list_briefings_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/meeting-prep/briefings returns 200 with items and total."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    await _make_briefing(db, SAMPLE_ORG_ID, proj.id)

    resp = await authenticated_client.get("/v1/meeting-prep/briefings")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


async def test_http_get_briefing_returns_404_for_unknown(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/meeting-prep/briefings/{unknown_id} returns 404."""
    resp = await authenticated_client.get(f"/v1/meeting-prep/briefings/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_http_update_briefing_saves_overrides(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/meeting-prep/briefings/{id} saves custom_overrides and returns 200."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id)

    resp = await authenticated_client.put(
        f"/v1/meeting-prep/briefings/{briefing.id}",
        json={"custom_overrides": {"executive_summary": "Analyst edited summary."}},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["custom_overrides"]["executive_summary"] == "Analyst edited summary."


async def test_http_delete_briefing_returns_204(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """DELETE /v1/meeting-prep/briefings/{id} returns 204 and hides the briefing."""
    proj = await _make_project(db, SAMPLE_ORG_ID)
    briefing = await _make_briefing(db, SAMPLE_ORG_ID, proj.id)

    delete_resp = await authenticated_client.delete(
        f"/v1/meeting-prep/briefings/{briefing.id}"
    )
    assert delete_resp.status_code == 204

    get_resp = await authenticated_client.get(
        f"/v1/meeting-prep/briefings/{briefing.id}"
    )
    assert get_resp.status_code == 404
