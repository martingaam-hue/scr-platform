"""Tests for the Engagement tracking module — track open/page/close/download and analytics."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.core import Organization, User
from app.models.dataroom import Document
from app.models.engagement import DocumentEngagement
from app.models.enums import DocumentStatus, OrgType, UserRole
from app.modules.engagement.service import EngagementService
from app.schemas.auth import CurrentUser

# ── Constants ─────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

CURRENT_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="engage@example.com",
    external_auth_id="user_engage_001",
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user

    return _override


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def seed_data(db: AsyncSession) -> None:
    org = Organization(id=ORG_ID, name="Engage Org", slug="engage-org", type=OrgType.ALLY)
    user = User(
        id=USER_ID,
        org_id=ORG_ID,
        email="engage@example.com",
        full_name="Engage User",
        role=UserRole.ADMIN,
        external_auth_id="user_engage_001",
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
async def sample_document(db: AsyncSession, seed_data: None) -> Document:
    doc = Document(
        org_id=ORG_ID,
        name="Investment Memorandum.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        s3_key="docs/test/memo.pdf",
        s3_bucket="scr-test",
        file_size_bytes=204800,
        uploaded_by=USER_ID,
        checksum_sha256="a" * 64,
        status=DocumentStatus.READY,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@pytest.fixture
async def open_session(db: AsyncSession, sample_document: Document) -> DocumentEngagement:
    """A pre-existing open engagement session for tests that need one."""
    svc = EngagementService(db, ORG_ID)
    engagement = await svc.track_open(
        document_id=sample_document.id,
        user_id=USER_ID,
        session_id="sess-fixture-001",
        total_pages=10,
    )
    await db.commit()
    await db.refresh(engagement)
    return engagement


# ── Tests: track_open ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_track_open_creates_engagement_record(
    test_client: AsyncClient, sample_document: Document
) -> None:
    """POST /engagement/track/open creates a new DocumentEngagement session."""
    resp = await test_client.post(
        "/v1/engagement/track/open",
        json={
            "document_id": str(sample_document.id),
            "session_id": "sess-open-001",
            "total_pages": 15,
            "device_type": "desktop",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["document_id"] == str(sample_document.id)
    assert data["session_id"] == "sess-open-001"
    assert data["total_pages"] == 15
    assert data["downloaded"] is False
    assert data["pages_viewed_count"] == 0


@pytest.mark.anyio
async def test_track_open_records_referrer_and_device(
    test_client: AsyncClient, sample_document: Document
) -> None:
    """track/open stores referrer and device_type correctly."""
    resp = await test_client.post(
        "/v1/engagement/track/open",
        json={
            "document_id": str(sample_document.id),
            "session_id": "sess-device-001",
            "referrer": "/deals/123",
            "device_type": "mobile",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["referrer_page"] == "/deals/123"
    assert data["device_type"] == "mobile"


# ── Tests: track_page_view ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_track_page_view_updates_pages_viewed(
    test_client: AsyncClient, open_session: DocumentEngagement
) -> None:
    """POST /engagement/track/page adds page entry and updates pages_viewed_count."""
    resp = await test_client.post(
        "/v1/engagement/track/page",
        json={
            "engagement_id": str(open_session.id),
            "page_number": 3,
            "time_seconds": 45,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pages_viewed_count"] == 1
    assert any(p["page"] == 3 for p in data["pages_viewed"])
    assert data["total_time_seconds"] == 45


@pytest.mark.anyio
async def test_track_page_view_accumulates_time_for_same_page(
    db: AsyncSession, open_session: DocumentEngagement
) -> None:
    """Viewing the same page twice accumulates time instead of duplicating the entry."""
    svc = EngagementService(db, ORG_ID)
    await svc.track_page_view(open_session.id, page_number=2, time_seconds=30)
    engagement = await svc.track_page_view(open_session.id, page_number=2, time_seconds=20)

    # Should still be 1 unique page entry
    pages = [p for p in engagement.pages_viewed if p["page"] == 2]
    assert len(pages) == 1
    assert pages[0]["time_seconds"] == 50  # 30 + 20
    assert engagement.pages_viewed_count == 1


@pytest.mark.anyio
async def test_track_page_view_unknown_session_returns_404(
    test_client: AsyncClient,
) -> None:
    """track/page with unknown engagement_id returns 404."""
    resp = await test_client.post(
        "/v1/engagement/track/page",
        json={
            "engagement_id": str(uuid.uuid4()),
            "page_number": 1,
            "time_seconds": 10,
        },
    )
    assert resp.status_code == 404


# ── Tests: track_close ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_track_close_sets_closed_at(
    test_client: AsyncClient, open_session: DocumentEngagement
) -> None:
    """POST /engagement/track/close sets closed_at on the session."""
    resp = await test_client.post(
        "/v1/engagement/track/close",
        json={"engagement_id": str(open_session.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["closed_at"] is not None


# ── Tests: track_download ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_track_download_sets_downloaded_flag(
    test_client: AsyncClient, open_session: DocumentEngagement
) -> None:
    """POST /engagement/track/download marks downloaded=True on the session."""
    resp = await test_client.post(
        "/v1/engagement/track/download",
        json={"engagement_id": str(open_session.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["downloaded"] is True


# ── Tests: get_document_analytics ─────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_document_analytics_empty_for_no_sessions(
    test_client: AsyncClient, sample_document: Document
) -> None:
    """GET /engagement/document/{id} returns zero-value analytics when no sessions exist."""
    resp = await test_client.get(f"/v1/engagement/document/{sample_document.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_views"] == 0
    assert data["unique_viewers"] == 0
    assert data["download_count"] == 0
    assert data["page_heatmap"] == {}


@pytest.mark.anyio
async def test_get_document_analytics_aggregates_sessions(
    db: AsyncSession,
    test_client: AsyncClient,
    sample_document: Document,
) -> None:
    """Analytics endpoint correctly aggregates multiple sessions for a document."""
    svc = EngagementService(db, ORG_ID)

    # Session A: user views pages 1 and 2 and downloads
    eng_a = await svc.track_open(
        document_id=sample_document.id,
        user_id=USER_ID,
        session_id="sess-a",
        total_pages=5,
    )
    await svc.track_page_view(eng_a.id, page_number=1, time_seconds=60)
    await svc.track_page_view(eng_a.id, page_number=2, time_seconds=30)
    await svc.track_download(eng_a.id)

    # Session B: same user views page 1 again
    eng_b = await svc.track_open(
        document_id=sample_document.id,
        user_id=USER_ID,
        session_id="sess-b",
        total_pages=5,
    )
    await svc.track_page_view(eng_b.id, page_number=1, time_seconds=20)
    await db.commit()

    resp = await test_client.get(f"/v1/engagement/document/{sample_document.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_views"] == 2
    assert data["unique_viewers"] == 1
    assert data["download_count"] == 1
    # Page 1 appears in both sessions: heatmap should accumulate
    assert data["page_heatmap"].get("1", 0) == 80  # 60 + 20


# ── Tests: completion_pct calculation ─────────────────────────────────────────


@pytest.mark.anyio
async def test_completion_pct_is_fraction_of_unique_pages_viewed(
    db: AsyncSession, open_session: DocumentEngagement
) -> None:
    """completion_pct = (unique pages viewed / total_pages) * 100."""
    svc = EngagementService(db, ORG_ID)

    # open_session has total_pages=10; view 5 unique pages
    for page_num in range(1, 6):
        await svc.track_page_view(open_session.id, page_number=page_num, time_seconds=10)

    await db.refresh(open_session)
    assert open_session.pages_viewed_count == 5
    assert open_session.completion_pct == pytest.approx(50.0, abs=0.1)


# ── Tests: org scoping ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_org_scoping_service_only_returns_own_sessions(
    db: AsyncSession,
    sample_document: Document,
    seed_data: None,
) -> None:
    """EngagementService only returns sessions belonging to its own org_id."""
    # Create an engagement for ORG_ID
    svc_owner = EngagementService(db, ORG_ID)
    eng = await svc_owner.track_open(
        document_id=sample_document.id,
        user_id=USER_ID,
        session_id="sess-owner-001",
    )
    await db.flush()

    # A service scoped to a different org should not see this session
    svc_other = EngagementService(db, OTHER_ORG_ID)
    with pytest.raises(LookupError):
        await svc_other._load_engagement(eng.id)


@pytest.mark.anyio
async def test_analytics_not_crossed_between_orgs(
    db: AsyncSession,
    sample_document: Document,
    seed_data: None,
) -> None:
    """Document analytics for one org do not include sessions from another org."""
    # Seed a session for ORG_ID
    svc_owner = EngagementService(db, ORG_ID)
    await svc_owner.track_open(
        document_id=sample_document.id,
        user_id=USER_ID,
        session_id="sess-owned",
        total_pages=5,
    )
    await db.flush()

    # Query analytics from a different org — must see zero sessions
    svc_other = EngagementService(db, OTHER_ORG_ID)
    analytics = await svc_other.get_document_analytics(sample_document.id)
    assert analytics["total_views"] == 0
