"""Tests for the Document Annotations module — CRUD, position, types, and org scoping."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.document_annotations import DocumentAnnotation
from app.models.enums import OrgType, UserRole
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs ────────────────────────────────────────────────────────────────

AN_ORG_ID = uuid.UUID("00000000-0000-00A4-0000-000000000001")
AN_USER_ID = uuid.UUID("00000000-0000-00A4-0000-000000000002")
AN_DOC_ID = uuid.UUID("00000000-0000-00A4-0000-000000000003")

# A second user in the same org (for delete-permission tests)
AN_OTHER_USER_ID = uuid.UUID("00000000-0000-00A4-0000-000000000004")

# A second org for isolation tests
AN_ORG2_ID = uuid.UUID("00000000-0000-00A4-0000-000000000010")

CURRENT_USER = CurrentUser(
    user_id=AN_USER_ID,
    org_id=AN_ORG_ID,
    role=UserRole.ADMIN,
    email="annot_test@example.com",
    external_auth_id="clerk_annot_test",
)

OTHER_USER = CurrentUser(
    user_id=AN_OTHER_USER_ID,
    org_id=AN_ORG_ID,
    role=UserRole.ANALYST,
    email="other_annot@example.com",
    external_auth_id="clerk_annot_other",
)

ORG2_USER = CurrentUser(
    user_id=uuid.UUID("00000000-0000-00A4-0000-000000000011"),
    org_id=AN_ORG2_ID,
    role=UserRole.ADMIN,
    email="annot_org2@example.com",
    external_auth_id="clerk_annot_org2",
)

_POSITION = {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.05}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def an_org(db: AsyncSession):
    from app.models.core import Organization

    org = Organization(
        id=AN_ORG_ID,
        name="Annotation Test Org",
        slug="annotation-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def an_user(db: AsyncSession, an_org):
    from app.models.core import User

    user = User(
        id=AN_USER_ID,
        org_id=AN_ORG_ID,
        email="annot_test@example.com",
        full_name="Annotation Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_annot_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def an_annotation(db: AsyncSession, an_org):
    """A pre-existing highlight annotation for the test document."""
    ann = DocumentAnnotation(
        org_id=AN_ORG_ID,
        document_id=AN_DOC_ID,
        created_by=AN_USER_ID,
        annotation_type="highlight",
        page_number=3,
        position=_POSITION,
        content="Important clause",
        color="#FFFF00",
        is_private=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(ann)
    await db.flush()
    return ann


@pytest.fixture
async def an_note(db: AsyncSession, an_org):
    """A note annotation on page 5."""
    ann = DocumentAnnotation(
        org_id=AN_ORG_ID,
        document_id=AN_DOC_ID,
        created_by=AN_USER_ID,
        annotation_type="note",
        page_number=5,
        position={"x": 0.3, "y": 0.4, "width": 0.2, "height": 0.03},
        content="Review this later",
        color="#00FF00",
        is_private=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(ann)
    await db.flush()
    return ann


def _override(db: AsyncSession, current_user: CurrentUser = CURRENT_USER):
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db


def _clear():
    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_create_annotation_persists_fields(db: AsyncSession, an_org):
    """create_annotation stores all fields correctly."""
    from app.modules.document_annotations.schemas import CreateAnnotationRequest
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    req = CreateAnnotationRequest(
        document_id=AN_DOC_ID,
        annotation_type="highlight",
        page_number=2,
        position=_POSITION,
        content="Key risk paragraph",
        color="#FF0000",
        is_private=False,
    )

    ann = await svc.create_annotation(org_id=AN_ORG_ID, user_id=AN_USER_ID, data=req)

    assert ann.id is not None
    assert ann.org_id == AN_ORG_ID
    assert ann.document_id == AN_DOC_ID
    assert ann.annotation_type == "highlight"
    assert ann.page_number == 2
    assert ann.content == "Key risk paragraph"
    assert ann.color == "#FF0000"
    assert ann.is_private is False
    assert ann.created_by == AN_USER_ID


async def test_create_annotation_bookmark_type(db: AsyncSession, an_org):
    """create_annotation works for bookmark type without content."""
    from app.modules.document_annotations.schemas import CreateAnnotationRequest
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    req = CreateAnnotationRequest(
        document_id=AN_DOC_ID,
        annotation_type="bookmark",
        page_number=10,
        position={"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.01},
        content=None,
    )

    ann = await svc.create_annotation(org_id=AN_ORG_ID, user_id=AN_USER_ID, data=req)

    assert ann.annotation_type == "bookmark"
    assert ann.content is None


async def test_list_annotations_returns_all_for_document(
    db: AsyncSession, an_org, an_annotation, an_note
):
    """list_annotations returns all annotations for the document regardless of page."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    annotations = await svc.list_annotations(org_id=AN_ORG_ID, document_id=AN_DOC_ID)

    assert len(annotations) == 2
    types = {a.annotation_type for a in annotations}
    assert "highlight" in types
    assert "note" in types


async def test_list_annotations_filtered_by_page(
    db: AsyncSession, an_org, an_annotation, an_note
):
    """list_annotations with page_number only returns annotations on that page."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    page3_annotations = await svc.list_annotations(
        org_id=AN_ORG_ID, document_id=AN_DOC_ID, page_number=3
    )

    assert len(page3_annotations) == 1
    assert page3_annotations[0].annotation_type == "highlight"
    assert page3_annotations[0].page_number == 3


async def test_list_annotations_org_scoped(db: AsyncSession, an_org, an_annotation):
    """list_annotations returns empty list for a different org."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    annotations = await svc.list_annotations(org_id=AN_ORG2_ID, document_id=AN_DOC_ID)

    assert annotations == []


async def test_get_annotation_returns_correct_record(db: AsyncSession, an_org, an_annotation):
    """get_annotation fetches a single annotation by its ID."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    found = await svc.get_annotation(org_id=AN_ORG_ID, annotation_id=an_annotation.id)

    assert found is not None
    assert found.id == an_annotation.id


async def test_get_annotation_returns_none_wrong_org(db: AsyncSession, an_org, an_annotation):
    """get_annotation returns None for an annotation belonging to a different org."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    found = await svc.get_annotation(org_id=AN_ORG2_ID, annotation_id=an_annotation.id)

    assert found is None


async def test_update_annotation_changes_content_and_color(db: AsyncSession, an_org, an_annotation):
    """update_annotation modifies content and color and persists the changes."""
    from app.modules.document_annotations.schemas import UpdateAnnotationRequest
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    update = UpdateAnnotationRequest(content="Updated note text", color="#0000FF")

    updated = await svc.update_annotation(
        org_id=AN_ORG_ID,
        annotation_id=an_annotation.id,
        user_id=AN_USER_ID,
        data=update,
    )

    assert updated is not None
    assert updated.content == "Updated note text"
    assert updated.color == "#0000FF"


async def test_update_annotation_privacy_flag(db: AsyncSession, an_org, an_annotation):
    """update_annotation can toggle the is_private flag."""
    from app.modules.document_annotations.schemas import UpdateAnnotationRequest
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    update = UpdateAnnotationRequest(is_private=True)

    updated = await svc.update_annotation(
        org_id=AN_ORG_ID,
        annotation_id=an_annotation.id,
        user_id=AN_USER_ID,
        data=update,
    )

    assert updated is not None
    assert updated.is_private is True


async def test_update_annotation_returns_none_when_not_found(db: AsyncSession, an_org):
    """update_annotation returns None when the annotation does not exist."""
    from app.modules.document_annotations.schemas import UpdateAnnotationRequest
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    result = await svc.update_annotation(
        org_id=AN_ORG_ID,
        annotation_id=uuid.uuid4(),
        user_id=AN_USER_ID,
        data=UpdateAnnotationRequest(content="irrelevant"),
    )

    assert result is None


async def test_delete_annotation_by_creator(db: AsyncSession, an_org, an_annotation):
    """delete_annotation returns True and removes the record when called by creator."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    deleted = await svc.delete_annotation(
        org_id=AN_ORG_ID, annotation_id=an_annotation.id, user_id=AN_USER_ID
    )

    assert deleted is True

    # Confirm it is gone
    found = await svc.get_annotation(org_id=AN_ORG_ID, annotation_id=an_annotation.id)
    assert found is None


async def test_delete_annotation_denied_for_non_creator(db: AsyncSession, an_org, an_annotation):
    """delete_annotation returns False when called by a different user."""
    from app.modules.document_annotations.service import AnnotationService

    svc = AnnotationService(db)
    deleted = await svc.delete_annotation(
        org_id=AN_ORG_ID,
        annotation_id=an_annotation.id,
        user_id=AN_OTHER_USER_ID,  # not the creator
    )

    assert deleted is False

    # Annotation should still exist
    found = await svc.get_annotation(org_id=AN_ORG_ID, annotation_id=an_annotation.id)
    assert found is not None


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_api_create_annotation(db: AsyncSession, an_org, an_user):
    """POST /v1/annotations creates an annotation and returns 201."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    payload = {
        "document_id": str(AN_DOC_ID),
        "annotation_type": "highlight",
        "page_number": 1,
        "position": {"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.05},
        "content": "Highlight this",
        "color": "#FFFF00",
        "is_private": False,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/annotations", json=payload)

    _clear()

    assert resp.status_code == 201
    data = resp.json()
    assert data["annotation_type"] == "highlight"
    assert data["page_number"] == 1
    assert data["content"] == "Highlight this"
    assert "id" in data


async def test_api_list_annotations(db: AsyncSession, an_org, an_user, an_annotation, an_note):
    """GET /v1/annotations?document_id=... returns all annotations for the document."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/annotations?document_id={AN_DOC_ID}")

    _clear()

    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) == 2


async def test_api_list_annotations_filter_by_page(
    db: AsyncSession, an_org, an_user, an_annotation, an_note
):
    """GET /v1/annotations?document_id=...&page=3 returns only page-3 annotations."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/annotations?document_id={AN_DOC_ID}&page=3")

    _clear()

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["page_number"] == 3


async def test_api_get_annotation(db: AsyncSession, an_org, an_user, an_annotation):
    """GET /v1/annotations/{id} returns the annotation details."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/annotations/{an_annotation.id}")

    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(an_annotation.id)
    assert data["annotation_type"] == "highlight"


async def test_api_get_annotation_not_found(db: AsyncSession, an_org, an_user):
    """GET /v1/annotations/{id} returns 404 for unknown annotation."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/annotations/{uuid.uuid4()}")

    _clear()

    assert resp.status_code == 404


async def test_api_update_annotation(db: AsyncSession, an_org, an_user, an_annotation):
    """PATCH /v1/annotations/{id} updates content and returns 200."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/v1/annotations/{an_annotation.id}",
            json={"content": "Updated content", "color": "#FF0000"},
        )

    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Updated content"
    assert data["color"] == "#FF0000"


async def test_api_delete_annotation_by_creator(db: AsyncSession, an_org, an_user, an_annotation):
    """DELETE /v1/annotations/{id} returns 204 when called by the creator."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(f"/v1/annotations/{an_annotation.id}")

    _clear()

    assert resp.status_code == 204


async def test_api_delete_annotation_not_owner_returns_404(
    db: AsyncSession, an_org, an_user, an_annotation
):
    """DELETE /v1/annotations/{id} returns 404 when the caller is not the creator."""
    # Override with OTHER_USER (different user_id than the annotation creator)
    _override(db, OTHER_USER)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(f"/v1/annotations/{an_annotation.id}")

    _clear()

    assert resp.status_code == 404
