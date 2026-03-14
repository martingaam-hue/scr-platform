"""Tests for the warm introductions module — connections, intro paths, and requests."""

import itertools
import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connections import IntroductionRequest, ProfessionalConnection
from app.models.core import Organization
from app.models.enums import OrgType, UserRole
from app.modules.warm_intros import service
from app.modules.warm_intros.schemas import (
    ConnectionCreateRequest,
    ConnectionUpdateRequest,
    IntroRequestCreateRequest,
)
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio


# ── RBAC bypass ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def bypass_rbac():
    """Bypass RBAC permission checks in all warm_intros tests."""
    with patch("app.auth.dependencies.check_permission", return_value=True):
        yield


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    strength: str = "moderate",
    days_since_interaction: int | None = 30,
) -> ProfessionalConnection:
    """Build (but don't flush) a ProfessionalConnection."""
    last_date = (date.today() - timedelta(days=days_since_interaction)) if days_since_interaction is not None else None
    conn = ProfessionalConnection(
        user_id=user_id,
        org_id=org_id,
        connection_type="advisor",
        connected_org_name="Acme Capital",
        connected_person_name="Alice Smith",
        connected_person_email="alice@acme.com",
        relationship_strength=strength,
        last_interaction_date=last_date,
        notes="Met at conference",
    )
    db.add(conn)
    return conn


# ── Connection CRUD ────────────────────────────────────────────────────────────


async def test_create_connection_success(db: AsyncSession, sample_org, sample_user):
    """Creating a valid connection returns the persisted record."""
    req = ConnectionCreateRequest(
        connection_type="advisor",
        connected_org_name="GreenFund",
        connected_person_name="Bob Jones",
        relationship_strength="strong",
        last_interaction_date=date.today() - timedelta(days=10),
    )
    conn = await service.create_connection(db, sample_user.id, sample_org.id, req)

    assert conn.id is not None
    assert conn.connected_org_name == "GreenFund"
    assert conn.relationship_strength == "strong"
    assert conn.org_id == sample_org.id
    assert conn.user_id == sample_user.id
    assert conn.is_deleted is False


async def test_create_connection_invalid_type_raises(db: AsyncSession, sample_org, sample_user):
    """Invalid connection_type raises ValueError."""
    req = ConnectionCreateRequest(
        connection_type="unknown_type",
        connected_org_name="BadFund",
        relationship_strength="moderate",
    )
    with pytest.raises(ValueError, match="Invalid connection_type"):
        await service.create_connection(db, sample_user.id, sample_org.id, req)


async def test_list_connections_scoped_to_user(db: AsyncSession, sample_org, sample_user):
    """get_connections only returns connections for the given user within the org."""
    other_user_id = uuid.uuid4()

    _make_connection(db, sample_user.id, sample_org.id)
    # Connection belonging to a different user — must not appear in results
    other_conn = ProfessionalConnection(
        user_id=other_user_id,
        org_id=sample_org.id,
        connection_type="co_investor",
        connected_org_name="Other Fund",
        relationship_strength="weak",
    )
    db.add(other_conn)
    await db.flush()

    results = await service.get_connections(db, sample_user.id, sample_org.id)
    ids = {c.id for c in results}
    assert other_conn.id not in ids
    # All returned connections belong to sample_user
    for c in results:
        assert c.user_id == sample_user.id


async def test_update_connection_changes_strength(db: AsyncSession, sample_org, sample_user):
    """update_connection mutates the target record and returns it."""
    _make_connection(db, sample_user.id, sample_org.id, strength="weak")
    await db.flush()
    conns = await service.get_connections(db, sample_user.id, sample_org.id)
    target = conns[0]

    update = ConnectionUpdateRequest(relationship_strength="strong", notes="Updated notes")
    updated = await service.update_connection(
        db, sample_user.id, sample_org.id, target.id, update
    )

    assert updated.relationship_strength == "strong"
    assert updated.notes == "Updated notes"


async def test_delete_connection_soft_deletes(db: AsyncSession, sample_org, sample_user):
    """delete_connection marks the record as deleted; it no longer appears in listings."""
    _make_connection(db, sample_user.id, sample_org.id)
    await db.flush()
    conns = await service.get_connections(db, sample_user.id, sample_org.id)
    target = conns[0]

    await service.delete_connection(db, sample_user.id, sample_org.id, target.id)
    await db.flush()

    after = await service.get_connections(db, sample_user.id, sample_org.id)
    assert all(c.id != target.id for c in after)


async def test_update_connection_not_found_raises(db: AsyncSession, sample_org, sample_user):
    """Updating a non-existent connection raises LookupError."""
    update = ConnectionUpdateRequest(notes="phantom")
    with pytest.raises(LookupError):
        await service.update_connection(
            db, sample_user.id, sample_org.id, uuid.uuid4(), update
        )


# ── Introduction requests ──────────────────────────────────────────────────────


async def test_create_intro_request(db: AsyncSession, sample_org, sample_user):
    """request_introduction persists a pending intro request."""
    investor_id = uuid.uuid4()
    project_id = uuid.uuid4()
    path = {"type": "ally_connection", "connector_org": "Acme", "warmth": 72.5}

    req = await service.request_introduction(
        db,
        requester_id=sample_user.id,
        requester_org_id=sample_org.id,
        target_investor_id=investor_id,
        project_id=project_id,
        path=path,
        message="Please introduce us!",
    )

    assert req.id is not None
    assert req.status == "pending"
    assert req.warmth_score == pytest.approx(72.5)
    assert req.requester_org_id == sample_org.id
    assert req.project_id == project_id


async def test_list_intro_requests_org_scoped(db: AsyncSession, sample_org, sample_user):
    """list_introduction_requests returns only requests from the caller's org."""
    other_org_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    # Own request
    await service.request_introduction(
        db,
        requester_id=sample_user.id,
        requester_org_id=sample_org.id,
        target_investor_id=uuid.uuid4(),
        project_id=None,
        path={"warmth": 50.0},
        message="Hi",
    )
    # Other org's request — must not appear
    other_req = IntroductionRequest(
        requester_id=other_user_id,
        requester_org_id=other_org_id,
        target_investor_id=uuid.uuid4(),
        status="pending",
        message="Other",
    )
    db.add(other_req)
    await db.flush()

    results = await service.list_introduction_requests(db, sample_user.id, sample_org.id)
    result_ids = {r.id for r in results}
    assert other_req.id not in result_ids
    for r in results:
        assert r.requester_org_id == sample_org.id


async def test_update_request_status_transition(db: AsyncSession, sample_org, sample_user):
    """update_request_status advances the status field correctly."""
    req = await service.request_introduction(
        db,
        requester_id=sample_user.id,
        requester_org_id=sample_org.id,
        target_investor_id=uuid.uuid4(),
        project_id=None,
        path={"warmth": 60.0},
        message="Hello",
    )
    await db.flush()

    updated = await service.update_request_status(db, sample_org.id, req.id, "accepted")
    assert updated.status == "accepted"

    declined = await service.update_request_status(db, sample_org.id, req.id, "declined")
    assert declined.status == "declined"


async def test_update_request_status_not_found_raises(db: AsyncSession, sample_org, sample_user):
    """update_request_status raises LookupError for unknown request id."""
    with pytest.raises(LookupError):
        await service.update_request_status(db, sample_org.id, uuid.uuid4(), "accepted")


# ── Warmth scoring ─────────────────────────────────────────────────────────────


async def test_warmth_scoring_recent_strong_connection(db: AsyncSession):
    """A strong connection with recent interaction scores higher than a weak stale one."""
    recent_strong = ProfessionalConnection(
        user_id=SAMPLE_USER_ID,
        org_id=SAMPLE_ORG_ID,
        connection_type="advisor",
        connected_org_name="TopFund",
        relationship_strength="strong",
        last_interaction_date=date.today() - timedelta(days=30),
    )
    old_weak = ProfessionalConnection(
        user_id=SAMPLE_USER_ID,
        org_id=SAMPLE_ORG_ID,
        connection_type="advisor",
        connected_org_name="OldFund",
        relationship_strength="weak",
        last_interaction_date=date.today() - timedelta(days=400),
    )
    strong_score = service.score_warmth_single(recent_strong)
    weak_score = service.score_warmth_single(old_weak)

    assert strong_score > weak_score
    assert 0 <= weak_score <= 100
    assert 0 <= strong_score <= 100


# ── Introduction path suggestions ─────────────────────────────────────────────


async def test_find_introduction_paths_returns_top5(db: AsyncSession, sample_org, sample_user):
    """find_introduction_paths returns at most 5 paths, sorted by warmth descending."""
    # Seed 7 connections
    for i in range(7):
        conn = ProfessionalConnection(
            user_id=sample_user.id,
            org_id=sample_org.id,
            connection_type="advisor",
            connected_org_name=f"Fund {i}",
            relationship_strength="moderate",
        )
        db.add(conn)
    await db.flush()

    paths = await service.find_introduction_paths(
        db, sample_user.id, sample_org.id, uuid.uuid4()
    )

    assert len(paths) <= 5
    # Sorted descending by warmth
    for a, b in itertools.pairwise(paths):
        assert a.warmth >= b.warmth


# ── HTTP endpoints ─────────────────────────────────────────────────────────────


async def test_api_list_connections_empty(authenticated_client, sample_org, sample_user):
    """GET /v1/warm-intros/connections returns 200 with empty list when no connections."""
    resp = await authenticated_client.get("/v1/warm-intros/connections")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_api_create_and_list_connection(authenticated_client, sample_org, sample_user):
    """POST /v1/warm-intros/connections creates a connection; GET returns it."""
    payload = {
        "connection_type": "co_investor",
        "connected_org_name": "ImpactVC",
        "connected_person_name": "Carol White",
        "relationship_strength": "strong",
    }
    create_resp = await authenticated_client.post("/v1/warm-intros/connections", json=payload)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["connected_org_name"] == "ImpactVC"
    assert data["relationship_strength"] == "strong"

    list_resp = await authenticated_client.get("/v1/warm-intros/connections")
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert data["id"] in ids


async def test_api_delete_connection_returns_404_for_wrong_org(
    authenticated_client, db: AsyncSession
):
    """DELETE on a connection that belongs to another org returns 404."""
    other_conn = ProfessionalConnection(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        connection_type="advisor",
        connected_org_name="Foreign Fund",
        relationship_strength="weak",
    )
    db.add(other_conn)
    await db.flush()

    resp = await authenticated_client.delete(f"/v1/warm-intros/connections/{other_conn.id}")
    assert resp.status_code == 404
