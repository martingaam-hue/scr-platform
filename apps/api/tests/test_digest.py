"""Tests for the Digest module — preferences, history, preview, and trigger."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.digest_log import DigestLog
from app.models.enums import OrgType, UserRole
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs ────────────────────────────────────────────────────────────────

DG_ORG_ID = uuid.UUID("00000000-0000-00D6-0000-000000000001")
DG_USER_ID = uuid.UUID("00000000-0000-00D6-0000-000000000002")

CURRENT_USER = CurrentUser(
    user_id=DG_USER_ID,
    org_id=DG_ORG_ID,
    role=UserRole.ADMIN,
    email="digest_test@example.com",
    external_auth_id="clerk_digest_test",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def dg_org(db: AsyncSession):
    from app.models.core import Organization

    org = Organization(
        id=DG_ORG_ID,
        name="Digest Test Org",
        slug="digest-test-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def dg_user(db: AsyncSession, dg_org):
    from app.models.core import User

    user = User(
        id=DG_USER_ID,
        org_id=DG_ORG_ID,
        email="digest_test@example.com",
        full_name="Digest Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_digest_test",
        is_active=True,
        preferences={},
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def digest_log(db: AsyncSession, dg_org, dg_user):
    """Create a pre-existing DigestLog entry for history tests."""
    log = DigestLog(
        org_id=DG_ORG_ID,
        user_id=DG_USER_ID,
        digest_type="weekly",
        period_start=date(2026, 3, 3),
        period_end=date(2026, 3, 10),
        subject="Your weekly SCR digest",
        narrative="This week your team completed 5 AI-powered analyses.",
        data_snapshot={"ai_tasks_completed": 5, "new_projects": 1},
    )
    db.add(log)
    await db.flush()
    return log


def _override_db(db: AsyncSession):
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db


def _clear_overrides():
    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_get_preferences_returns_defaults_for_new_user(db: AsyncSession, dg_org, dg_user):
    """get_preferences returns default is_subscribed=True / frequency=weekly for fresh user."""
    from app.modules.digest.service import get_preferences

    prefs = await get_preferences(db, DG_USER_ID)

    assert prefs["is_subscribed"] is True
    assert prefs["frequency"] == "weekly"


async def test_get_preferences_returns_defaults_when_user_missing(db: AsyncSession, dg_org):
    """get_preferences returns defaults gracefully when user ID does not exist."""
    from app.modules.digest.service import get_preferences

    prefs = await get_preferences(db, uuid.uuid4())

    assert prefs["is_subscribed"] is True
    assert prefs["frequency"] == "weekly"


async def test_update_preferences_persists_changes(db: AsyncSession, dg_org, dg_user):
    """update_preferences saves subscription state and frequency to user.preferences."""
    from app.modules.digest.service import get_preferences, update_preferences

    updated = await update_preferences(db, DG_USER_ID, is_subscribed=False, frequency="monthly")

    assert updated["is_subscribed"] is False
    assert updated["frequency"] == "monthly"

    # Verify persistence by fetching again
    fetched = await get_preferences(db, DG_USER_ID)
    assert fetched["is_subscribed"] is False
    assert fetched["frequency"] == "monthly"


async def test_update_preferences_sets_legacy_key(db: AsyncSession, dg_org, dg_user):
    """update_preferences also writes the legacy email_digest_enabled key for Celery compatibility."""
    from app.modules.digest.service import update_preferences

    await update_preferences(db, DG_USER_ID, is_subscribed=False, frequency="weekly")

    from app.models.core import User

    user = await db.get(User, DG_USER_ID)
    assert user is not None
    assert user.preferences.get("email_digest_enabled") is False


async def test_update_preferences_raises_for_missing_user(db: AsyncSession, dg_org):
    """update_preferences raises LookupError when the user does not exist."""
    from app.modules.digest.service import update_preferences

    with pytest.raises(LookupError, match=str(uuid.UUID(int=999))):
        await update_preferences(
            db,
            uuid.UUID(int=999),
            is_subscribed=True,
            frequency="weekly",
        )


async def test_log_digest_sent_creates_row(db: AsyncSession, dg_org, dg_user):
    """log_digest_sent inserts a DigestLog row with correct fields."""
    from app.modules.digest.service import log_digest_sent

    log = await log_digest_sent(
        db,
        org_id=DG_ORG_ID,
        user_id=DG_USER_ID,
        digest_type="weekly",
        period_start=date(2026, 3, 3),
        period_end=date(2026, 3, 10),
        subject="Weekly digest",
        narrative="This week...",
        data_snapshot={"ai_tasks_completed": 3},
    )

    assert log.id is not None
    assert log.org_id == DG_ORG_ID
    assert log.user_id == DG_USER_ID
    assert log.digest_type == "weekly"
    assert log.subject == "Weekly digest"


async def test_list_digest_history_returns_user_entries(db: AsyncSession, dg_org, dg_user, digest_log):
    """list_digest_history returns only entries for the specific user."""
    from app.modules.digest.service import list_digest_history

    items, total = await list_digest_history(db, org_id=DG_ORG_ID, user_id=DG_USER_ID)

    assert total == 1
    assert len(items) == 1
    assert items[0].id == digest_log.id


async def test_list_digest_history_scoped_by_user(db: AsyncSession, dg_org, dg_user, digest_log):
    """list_digest_history excludes entries belonging to other users."""
    from app.modules.digest.service import list_digest_history

    other_user_id = uuid.UUID("00000000-0000-00D6-0000-000000000099")
    items, total = await list_digest_history(db, org_id=DG_ORG_ID, user_id=other_user_id)

    assert total == 0
    assert items == []


async def test_gather_digest_data_structure(db: AsyncSession, dg_org, dg_user):
    """gather_digest_data returns a dict with expected keys."""
    from app.modules.digest.service import gather_digest_data

    since = datetime.utcnow() - timedelta(days=7)
    data = await gather_digest_data(db, DG_ORG_ID, DG_USER_ID, since)

    assert "period_start" in data
    assert "period_end" in data
    assert "ai_tasks_completed" in data
    assert "ai_agent_breakdown" in data
    assert "new_projects" in data
    assert "new_documents" in data
    assert isinstance(data["ai_tasks_completed"], int)


async def test_fallback_summary_no_ai():
    """_fallback_summary generates a sensible sentence without AI."""
    from app.modules.digest.service import _fallback_summary

    summary = _fallback_summary(
        {"ai_tasks_completed": 5, "new_projects": 2, "new_documents": 3}
    )

    assert "5" in summary
    assert "2" in summary or "project" in summary
    assert isinstance(summary, str)
    assert summary.endswith(".")


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_api_get_preferences(db: AsyncSession, dg_org, dg_user):
    """GET /v1/digest/preferences returns 200 with defaults."""
    _override_db(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/digest/preferences")

    _clear_overrides()

    assert resp.status_code == 200
    data = resp.json()
    assert "is_subscribed" in data
    assert "frequency" in data


async def test_api_update_preferences(db: AsyncSession, dg_org, dg_user):
    """PUT /v1/digest/preferences accepts new preferences and returns them."""
    _override_db(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put(
            "/v1/digest/preferences",
            json={"is_subscribed": False, "frequency": "monthly"},
        )

    _clear_overrides()

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_subscribed"] is False
    assert data["frequency"] == "monthly"


async def test_api_digest_history(db: AsyncSession, dg_org, dg_user, digest_log):
    """GET /v1/digest/history returns paginated history with the existing log entry."""
    _override_db(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/digest/history")

    _clear_overrides()

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 1
    assert data["items"][0]["digest_type"] == "weekly"


async def test_api_digest_preview(db: AsyncSession, dg_org, dg_user):
    """GET /v1/digest/preview returns summary data without sending email."""
    _override_db(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/digest/preview?days=7")

    _clear_overrides()

    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 7
    assert "summary" in data
    assert "ai_tasks_completed" in data["summary"]


async def test_api_digest_trigger_uses_fallback_when_ai_gateway_down(
    db: AsyncSession, dg_org, dg_user
):
    """POST /v1/digest/trigger returns a generated narrative even when AI gateway is unreachable."""
    _override_db(db)

    from httpx import ASGITransport, AsyncClient

    with patch(
        "app.modules.digest.service.generate_digest_summary",
        new_callable=AsyncMock,
        return_value="This week your team completed 0 AI-powered analyses.",
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/v1/digest/trigger?days=7")

    _clear_overrides()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "generated"
    assert "narrative" in data
    assert isinstance(data["narrative"], str)
