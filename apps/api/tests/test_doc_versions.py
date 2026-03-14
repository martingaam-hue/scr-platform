"""Tests for the Document Versions module — version creation, listing, diff, and comparison."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.doc_versions import DocumentVersion
from app.models.enums import OrgType, UserRole
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio


# ── RBAC bypass ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def bypass_rbac():
    """Bypass RBAC permission checks in all doc_versions tests."""
    with patch("app.auth.dependencies.check_permission", return_value=True):
        yield


# ── Unique IDs ────────────────────────────────────────────────────────────────

DV_ORG_ID = uuid.UUID("00000000-0000-00D5-0000-000000000001")
DV_USER_ID = uuid.UUID("00000000-0000-00D5-0000-000000000002")
DV_DOC_ID = uuid.UUID("00000000-0000-00D5-0000-000000000003")

# A second org for isolation tests
DV_ORG2_ID = uuid.UUID("00000000-0000-00D5-0000-000000000010")

CURRENT_USER = CurrentUser(
    user_id=DV_USER_ID,
    org_id=DV_ORG_ID,
    role=UserRole.ADMIN,
    email="docver_test@example.com",
    external_auth_id="clerk_docver_test",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def dv_org(db: AsyncSession):
    from app.models.core import Organization

    org = Organization(
        id=DV_ORG_ID,
        name="DocVer Test Org",
        slug="docver-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def dv_user(db: AsyncSession, dv_org):
    from app.models.core import User

    user = User(
        id=DV_USER_ID,
        org_id=DV_ORG_ID,
        email="docver_test@example.com",
        full_name="DocVer Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_docver_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def version_v1(db: AsyncSession, dv_org):
    """First version of the test document."""
    v = DocumentVersion(
        document_id=DV_DOC_ID,
        org_id=DV_ORG_ID,
        version_number=1,
        s3_key="docs/test-doc/v1.pdf",
        file_size_bytes=102400,
        checksum_sha256="abc123" * 10 + "abcd",
        uploaded_by=DV_USER_ID,
        change_significance="minor",
    )
    db.add(v)
    await db.flush()
    return v


@pytest.fixture
async def version_v2(db: AsyncSession, dv_org, version_v1):
    """Second version of the test document with diff stats."""
    v = DocumentVersion(
        document_id=DV_DOC_ID,
        org_id=DV_ORG_ID,
        version_number=2,
        s3_key="docs/test-doc/v2.pdf",
        file_size_bytes=110000,
        checksum_sha256="def456" * 10 + "defa",
        uploaded_by=DV_USER_ID,
        diff_stats={"additions": 15, "deletions": 3, "similarity": 0.92, "total_changes": 18},
        diff_lines=["+  new clause added", "-  old clause removed"],
        change_summary="Minor updates to payment terms.",
        change_significance="minor",
        key_changes=["Updated payment terms"],
    )
    db.add(v)
    await db.flush()
    return v


def _override(db: AsyncSession):
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db


def _clear():
    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_create_version_first_gets_number_1(db: AsyncSession, dv_org):
    """create_version assigns version_number=1 when no prior versions exist."""
    from app.modules.doc_versions.service import create_version

    with patch(
        "app.modules.doc_versions.service.ai_summarize_changes",
        new_callable=AsyncMock,
        return_value={"summary": "Initial upload", "significance": "minor", "key_changes": []},
    ):
        version = await create_version(
            db,
            document_id=DV_DOC_ID,
            org_id=DV_ORG_ID,
            user_id=DV_USER_ID,
            new_s3_key="docs/test-doc/v1.pdf",
            file_size=50000,
            checksum="sha256checksum1",
            old_text=None,
            new_text=None,
        )

    assert version.version_number == 1
    assert version.document_id == DV_DOC_ID
    assert version.org_id == DV_ORG_ID
    assert version.s3_key == "docs/test-doc/v1.pdf"


async def test_create_version_increments_from_previous(db: AsyncSession, dv_org, version_v1):
    """create_version assigns version_number=2 when v1 already exists."""
    from app.modules.doc_versions.service import create_version

    version = await create_version(
        db,
        document_id=DV_DOC_ID,
        org_id=DV_ORG_ID,
        user_id=DV_USER_ID,
        new_s3_key="docs/test-doc/v2.pdf",
        file_size=60000,
        checksum="sha256checksum2",
    )

    assert version.version_number == 2


async def test_create_version_computes_diff_when_text_provided(db: AsyncSession, dv_org):
    """create_version populates diff_stats when old_text and new_text are given."""
    from app.modules.doc_versions.service import create_version

    old = "Line one.\nLine two.\nLine three."
    new = "Line one.\nLine two updated.\nLine three.\nLine four."

    with patch(
        "app.modules.doc_versions.service.ai_summarize_changes",
        new_callable=AsyncMock,
        return_value={
            "summary": "Added a line",
            "significance": "minor",
            "key_changes": ["Added Line four"],
        },
    ):
        version = await create_version(
            db,
            document_id=DV_DOC_ID,
            org_id=DV_ORG_ID,
            user_id=DV_USER_ID,
            new_s3_key="docs/test-doc/v1.pdf",
            file_size=1000,
            checksum=None,
            old_text=old,
            new_text=new,
        )

    assert version.diff_stats is not None
    assert version.diff_stats["additions"] >= 1
    assert version.diff_stats["total_changes"] >= 1
    assert version.change_summary is not None


async def test_list_versions_returns_all_in_desc_order(
    db: AsyncSession, dv_org, version_v1, version_v2
):
    """list_versions returns all versions ordered newest-first."""
    from app.modules.doc_versions.service import list_versions

    versions = await list_versions(db, document_id=DV_DOC_ID, org_id=DV_ORG_ID)

    assert len(versions) == 2
    assert versions[0].version_number == 2  # newest first
    assert versions[1].version_number == 1


async def test_list_versions_org_scoped(db: AsyncSession, dv_org, version_v1):
    """list_versions returns empty list for a different org."""
    from app.modules.doc_versions.service import list_versions

    versions = await list_versions(db, document_id=DV_DOC_ID, org_id=DV_ORG2_ID)

    assert versions == []


async def test_get_version_returns_correct_record(
    db: AsyncSession, dv_org, version_v1, version_v2
):
    """get_version fetches a version by its UUID."""
    from app.modules.doc_versions.service import get_version

    found = await get_version(db, version_id=version_v2.id, org_id=DV_ORG_ID)

    assert found is not None
    assert found.id == version_v2.id
    assert found.version_number == 2


async def test_get_version_returns_none_for_other_org(db: AsyncSession, dv_org, version_v1):
    """get_version returns None when the version belongs to a different org."""
    from app.modules.doc_versions.service import get_version

    found = await get_version(db, version_id=version_v1.id, org_id=DV_ORG2_ID)

    assert found is None


async def test_compare_versions_returns_both(
    db: AsyncSession, dv_org, version_v1, version_v2
):
    """compare_versions returns (ver_a, ver_b) keyed by version number."""
    from app.modules.doc_versions.service import compare_versions

    ver_a, ver_b = await compare_versions(
        db,
        document_id=DV_DOC_ID,
        org_id=DV_ORG_ID,
        version_a_num=1,
        version_b_num=2,
    )

    assert ver_a is not None
    assert ver_b is not None
    assert ver_a.version_number == 1
    assert ver_b.version_number == 2


async def test_compare_versions_returns_none_for_missing(db: AsyncSession, dv_org, version_v1):
    """compare_versions returns None for a version number that does not exist."""
    from app.modules.doc_versions.service import compare_versions

    ver_a, ver_b = await compare_versions(
        db,
        document_id=DV_DOC_ID,
        org_id=DV_ORG_ID,
        version_a_num=1,
        version_b_num=99,
    )

    assert ver_a is not None
    assert ver_b is None


# ── generate_diff unit tests ──────────────────────────────────────────────────


def test_generate_diff_counts_additions_and_deletions():
    """generate_diff correctly counts +/- lines."""
    from app.modules.doc_versions.service import generate_diff

    old_text = "line 1\nline 2\nline 3"
    new_text = "line 1\nline 2 updated\nline 3\nline 4 added"

    result = generate_diff(old_text, new_text)

    assert result["stats"]["additions"] >= 1
    assert result["stats"]["deletions"] >= 1
    assert 0.0 <= result["stats"]["similarity"] <= 1.0
    assert isinstance(result["diff_lines"], list)


def test_generate_diff_identical_texts():
    """generate_diff reports zero changes for identical inputs."""
    from app.modules.doc_versions.service import generate_diff

    text = "Same content\nNo changes here"
    result = generate_diff(text, text)

    assert result["stats"]["total_changes"] == 0
    assert result["stats"]["similarity"] == 1.0


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_api_create_version(db: AsyncSession, dv_org, dv_user):
    """POST /v1/documents/{id}/versions creates a new version record."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    payload = {
        "s3_key": "docs/test-doc/v1.pdf",
        "file_size_bytes": 102400,
        "checksum_sha256": "a" * 64,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/v1/documents/{DV_DOC_ID}/versions", json=payload)

    _clear()

    assert resp.status_code == 201
    data = resp.json()
    assert data["version_number"] == 1
    assert data["s3_key"] == "docs/test-doc/v1.pdf"
    assert data["org_id"] == str(DV_ORG_ID)


async def test_api_list_versions(db: AsyncSession, dv_org, dv_user, version_v1, version_v2):
    """GET /v1/documents/{id}/versions returns version list with total count."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/documents/{DV_DOC_ID}/versions")

    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    # Newest first
    assert data["items"][0]["version_number"] == 2


async def test_api_get_version(db: AsyncSession, dv_org, dv_user, version_v1):
    """GET /v1/documents/{doc_id}/versions/{ver_id} returns version details."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/documents/{DV_DOC_ID}/versions/{version_v1.id}")

    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(version_v1.id)
    assert data["version_number"] == 1


async def test_api_get_version_wrong_document_returns_404(
    db: AsyncSession, dv_org, dv_user, version_v1
):
    """GET /v1/documents/{doc_id}/versions/{ver_id} returns 404 if doc_id mismatch."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    wrong_doc_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/documents/{wrong_doc_id}/versions/{version_v1.id}")

    _clear()

    assert resp.status_code == 404


async def test_api_compare_versions(db: AsyncSession, dv_org, dv_user, version_v1, version_v2):
    """GET /v1/documents/{id}/compare?v1=1&v2=2 returns diff between versions."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/documents/{DV_DOC_ID}/compare?v1=1&v2=2")

    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert "version_a" in data
    assert "version_b" in data
    assert data["version_a"]["version_number"] == 1
    assert data["version_b"]["version_number"] == 2


async def test_api_compare_versions_missing_returns_404(
    db: AsyncSession, dv_org, dv_user, version_v1
):
    """GET /v1/documents/{id}/compare returns 404 when one version number is absent."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/v1/documents/{DV_DOC_ID}/compare?v1=1&v2=99")

    _clear()

    assert resp.status_code == 404
