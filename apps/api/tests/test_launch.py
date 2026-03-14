"""Tests for the launch module: feature flags, overrides, waitlist, usage events."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.launch import FeatureFlag, FeatureFlagOverride, UsageEvent, WaitlistEntry
from app.modules.launch.service import DEFAULT_FLAGS, LaunchService
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000077")


# ── RBAC bypass ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def bypass_rbac():
    """Bypass RBAC permission checks in all launch tests."""
    with patch("app.auth.dependencies.check_permission", return_value=True):
        yield


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_flag(
    db: AsyncSession,
    name: str,
    *,
    enabled_globally: bool = True,
    rollout_pct: int = 100,
) -> FeatureFlag:
    flag = FeatureFlag(
        name=name,
        description=f"Test flag: {name}",
        enabled_globally=enabled_globally,
        rollout_pct=rollout_pct,
    )
    db.add(flag)
    await db.flush()
    await db.refresh(flag)
    return flag


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_is_feature_enabled_returns_global_default(
    db: AsyncSession, sample_org, sample_user
):
    """is_feature_enabled falls back to enabled_globally when no org override exists."""
    await _make_flag(db, "test_flag_on", enabled_globally=True)
    await _make_flag(db, "test_flag_off", enabled_globally=False)

    svc = LaunchService(db)

    assert await svc.is_feature_enabled("test_flag_on", SAMPLE_ORG_ID) is True
    assert await svc.is_feature_enabled("test_flag_off", SAMPLE_ORG_ID) is False


async def test_is_feature_enabled_returns_false_for_unknown_flag(
    db: AsyncSession, sample_org, sample_user
):
    """is_feature_enabled returns False for a flag name that does not exist."""
    svc = LaunchService(db)
    result = await svc.is_feature_enabled("nonexistent_flag_xyz", SAMPLE_ORG_ID)
    assert result is False


async def test_set_org_override_creates_override_and_overrides_global(
    db: AsyncSession, sample_org, sample_user
):
    """set_org_override creates a per-org override that takes priority over global setting."""
    # Global flag is enabled
    await _make_flag(db, "overridden_flag", enabled_globally=True)

    svc = LaunchService(db)
    # Disable for this specific org
    override = await svc.set_org_override("overridden_flag", SAMPLE_ORG_ID, enabled=False)

    assert override.flag_name == "overridden_flag"
    assert override.org_id == SAMPLE_ORG_ID
    assert override.enabled is False

    # is_feature_enabled should now return False for this org
    result = await svc.is_feature_enabled("overridden_flag", SAMPLE_ORG_ID)
    assert result is False

    # But for another org, the global True still applies
    result_other = await svc.is_feature_enabled("overridden_flag", OTHER_ORG_ID)
    assert result_other is True


async def test_set_org_override_updates_existing_override(
    db: AsyncSession, sample_org, sample_user
):
    """set_org_override updates an existing override rather than creating a duplicate."""
    await _make_flag(db, "toggle_flag", enabled_globally=True)

    svc = LaunchService(db)
    # First override: disable
    await svc.set_org_override("toggle_flag", SAMPLE_ORG_ID, enabled=False)
    assert await svc.is_feature_enabled("toggle_flag", SAMPLE_ORG_ID) is False

    # Second override: re-enable
    await svc.set_org_override("toggle_flag", SAMPLE_ORG_ID, enabled=True)
    assert await svc.is_feature_enabled("toggle_flag", SAMPLE_ORG_ID) is True


async def test_list_flags_includes_all_flags_with_override_info(
    db: AsyncSession, sample_org, sample_user
):
    """list_flags returns all flags with the org override value when set."""
    await _make_flag(db, "flag_no_override", enabled_globally=True)
    await _make_flag(db, "flag_with_override", enabled_globally=True)

    # Create an override for flag_with_override
    override = FeatureFlagOverride(
        flag_name="flag_with_override",
        org_id=SAMPLE_ORG_ID,
        enabled=False,
    )
    db.add(override)
    await db.flush()

    svc = LaunchService(db)
    flags = await svc.list_flags(SAMPLE_ORG_ID)

    flag_map = {f.name: f for f in flags}

    assert "flag_no_override" in flag_map
    assert flag_map["flag_no_override"].org_override is None

    assert "flag_with_override" in flag_map
    assert flag_map["flag_with_override"].org_override is False


async def test_record_usage_stores_event(db: AsyncSession, sample_org, sample_user):
    """record_usage persists a UsageEvent for the org/user."""
    svc = LaunchService(db)
    entity_id = uuid.uuid4()

    event = await svc.record_usage(
        org_id=SAMPLE_ORG_ID,
        user_id=SAMPLE_USER_ID,
        event_type="document_viewed",
        entity_type="document",
        entity_id=entity_id,
        metadata={"source": "data_room"},
    )

    assert event.id is not None
    assert event.org_id == SAMPLE_ORG_ID
    assert event.user_id == SAMPLE_USER_ID
    assert event.event_type == "document_viewed"
    assert event.entity_type == "document"
    assert event.entity_id == entity_id
    assert event.event_metadata == {"source": "data_room"}


async def test_get_usage_summary_aggregates_by_event_type(
    db: AsyncSession, sample_org, sample_user
):
    """get_usage_summary returns event counts grouped by event_type."""
    svc = LaunchService(db)

    # Record several events of different types
    for _ in range(3):
        await svc.record_usage(SAMPLE_ORG_ID, SAMPLE_USER_ID, event_type="page_view")
    for _ in range(2):
        await svc.record_usage(SAMPLE_ORG_ID, SAMPLE_USER_ID, event_type="ai_query")

    summary = await svc.get_usage_summary(SAMPLE_ORG_ID, days=30)

    assert summary["org_id"] == str(SAMPLE_ORG_ID)
    assert summary["total_events"] >= 5
    assert summary["totals"].get("page_view", 0) >= 3
    assert summary["totals"].get("ai_query", 0) >= 2


async def test_create_waitlist_entry_stores_pending_entry(
    db: AsyncSession, sample_org, sample_user
):
    """create_waitlist_entry creates a new entry with status=pending."""
    svc = LaunchService(db)

    entry = await svc.create_waitlist_entry(
        email="newuser@example.com",
        name="New User",
        company="Acme Corp",
        use_case="Impact investing",
    )

    assert entry.id is not None
    assert entry.email == "newuser@example.com"
    assert entry.name == "New User"
    assert entry.company == "Acme Corp"
    assert entry.status == "pending"
    assert entry.approved_at is None


async def test_create_waitlist_entry_is_idempotent(db: AsyncSession, sample_org, sample_user):
    """create_waitlist_entry returns the existing entry when called twice with same email."""
    svc = LaunchService(db)

    entry1 = await svc.create_waitlist_entry(email="idempotent@example.com", name="First")
    entry2 = await svc.create_waitlist_entry(email="idempotent@example.com", name="Second")

    assert entry1.id == entry2.id


async def test_approve_waitlist_entry_transitions_status(
    db: AsyncSession, sample_org, sample_user
):
    """approve_waitlist_entry sets status=approved and sets approved_at."""
    svc = LaunchService(db)
    entry = await svc.create_waitlist_entry(email="toapprove@example.com")

    approved = await svc.approve_waitlist_entry(entry.id)

    assert approved is not None
    assert approved.status == "approved"
    assert approved.approved_at is not None


async def test_default_flags_list_contains_expected_names():
    """DEFAULT_FLAGS constant contains the 7 expected feature flag names."""
    flag_names = [name for name, _, _ in DEFAULT_FLAGS]
    assert "deal_rooms" in flag_names
    assert "ai_redaction" in flag_names
    assert "webhooks" in flag_names
    assert "pdf_annotations" in flag_names
    assert "expert_insights" in flag_names
    assert "market_data" in flag_names
    assert "score_backtesting" in flag_names
    assert len(DEFAULT_FLAGS) == 7


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_list_flags_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/launch/flags returns 200 with a list of feature flags."""
    await _make_flag(db, "http_list_flag")

    resp = await authenticated_client.get("/v1/launch/flags")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = [f["name"] for f in data]
    assert "http_list_flag" in names


async def test_http_record_usage_returns_204(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/launch/usage returns 204 No Content."""
    resp = await authenticated_client.post(
        "/v1/launch/usage",
        json={"event_type": "feature_used", "entity_type": "project"},
    )
    assert resp.status_code == 204


async def test_http_waitlist_create_returns_201(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/launch/waitlist returns 201 with entry data."""
    resp = await authenticated_client.post(
        "/v1/launch/waitlist",
        json={
            "email": "waitlisted@example.com",
            "name": "Waitlist Person",
            "company": "Startup Ltd",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "waitlisted@example.com"
    assert data["status"] == "pending"
    assert "id" in data


async def test_http_set_flag_override_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/launch/flags/{name}/override returns 200 with updated flag."""
    await _make_flag(db, "http_override_flag")

    resp = await authenticated_client.put(
        "/v1/launch/flags/http_override_flag/override",
        json={"enabled": False},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "http_override_flag"
    assert data["org_override"] is False
