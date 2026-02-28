"""Warm Introduction Scoring service."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connections import IntroductionRequest, ProfessionalConnection
from app.models.core import Organization
from app.modules.warm_intros.schemas import (
    ConnectionCreateRequest,
    ConnectionUpdateRequest,
    IntroPathResponse,
    IntroRequestResponse,
    WarmIntroSuggestion,
)

logger = structlog.get_logger()

_VALID_CONNECTION_TYPES = {
    "advisor",
    "co_investor",
    "service_provider",
    "board_member",
    "lp_relationship",
}
_VALID_STRENGTHS = {"weak", "moderate", "strong"}
_VALID_STATUSES = {"pending", "sent", "accepted", "declined"}


# ── Warmth scoring ────────────────────────────────────────────────────────────


def score_warmth_single(conn: ProfessionalConnection) -> float:
    """Score a single connection's contribution to warmth (0-100)."""
    strength_map = {"strong": 75.0, "moderate": 55.0, "weak": 35.0}
    base = strength_map.get(conn.relationship_strength, 40.0)
    if conn.last_interaction_date:
        days = (date.today() - conn.last_interaction_date).days
        if days < 90:
            base = min(base + 15.0, 100.0)
        elif days < 180:
            base = min(base + 8.0, 100.0)
    return base


def score_warmth(
    ally_conn: ProfessionalConnection,
    investor_conn: ProfessionalConnection,
) -> float:
    """Score 0-100 based on connection strength, recency, shared org."""
    strength_bonus = {"strong": 30.0, "moderate": 15.0, "weak": 5.0}
    base = 50.0
    base += strength_bonus.get(ally_conn.relationship_strength, 0.0) / 2
    base += strength_bonus.get(investor_conn.relationship_strength, 0.0) / 2
    if ally_conn.last_interaction_date:
        days = (date.today() - ally_conn.last_interaction_date).days
        if days < 90:
            base += 15.0
        elif days < 180:
            base += 8.0
        elif days < 365:
            base += 3.0
    return min(base, 100.0)


# ── Connection CRUD ───────────────────────────────────────────────────────────


async def get_connections(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
) -> list[ProfessionalConnection]:
    """Get all active professional connections for a user within their org."""
    stmt = (
        select(ProfessionalConnection)
        .where(
            ProfessionalConnection.user_id == user_id,
            ProfessionalConnection.org_id == org_id,
            ProfessionalConnection.is_deleted.is_(False),
        )
        .order_by(ProfessionalConnection.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    data: ConnectionCreateRequest,
) -> ProfessionalConnection:
    """Create a new professional connection."""
    if data.connection_type not in _VALID_CONNECTION_TYPES:
        raise ValueError(
            f"Invalid connection_type: {data.connection_type}. "
            f"Must be one of {sorted(_VALID_CONNECTION_TYPES)}"
        )
    if data.relationship_strength not in _VALID_STRENGTHS:
        raise ValueError(
            f"Invalid relationship_strength: {data.relationship_strength}. "
            f"Must be one of {sorted(_VALID_STRENGTHS)}"
        )

    conn = ProfessionalConnection(
        user_id=user_id,
        org_id=org_id,
        connection_type=data.connection_type,
        connected_org_name=data.connected_org_name,
        connected_person_name=data.connected_person_name,
        connected_person_email=data.connected_person_email,
        relationship_strength=data.relationship_strength,
        last_interaction_date=data.last_interaction_date,
        notes=data.notes,
    )
    db.add(conn)
    await db.flush()
    return conn


async def update_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    connection_id: uuid.UUID,
    data: ConnectionUpdateRequest,
) -> ProfessionalConnection:
    """Update an existing professional connection."""
    stmt = select(ProfessionalConnection).where(
        ProfessionalConnection.id == connection_id,
        ProfessionalConnection.org_id == org_id,
        ProfessionalConnection.user_id == user_id,
        ProfessionalConnection.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise LookupError(f"Connection {connection_id} not found")

    if data.connection_type is not None:
        if data.connection_type not in _VALID_CONNECTION_TYPES:
            raise ValueError(f"Invalid connection_type: {data.connection_type}")
        conn.connection_type = data.connection_type
    if data.connected_org_name is not None:
        conn.connected_org_name = data.connected_org_name
    if data.connected_person_name is not None:
        conn.connected_person_name = data.connected_person_name
    if data.connected_person_email is not None:
        conn.connected_person_email = data.connected_person_email
    if data.relationship_strength is not None:
        if data.relationship_strength not in _VALID_STRENGTHS:
            raise ValueError(
                f"Invalid relationship_strength: {data.relationship_strength}"
            )
        conn.relationship_strength = data.relationship_strength
    if data.last_interaction_date is not None:
        conn.last_interaction_date = data.last_interaction_date
    if data.notes is not None:
        conn.notes = data.notes

    await db.flush()
    return conn


async def delete_connection(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    """Soft-delete a professional connection."""
    stmt = select(ProfessionalConnection).where(
        ProfessionalConnection.id == connection_id,
        ProfessionalConnection.org_id == org_id,
        ProfessionalConnection.user_id == user_id,
        ProfessionalConnection.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise LookupError(f"Connection {connection_id} not found")

    conn.is_deleted = True
    await db.flush()


# ── Introduction paths ────────────────────────────────────────────────────────


async def find_introduction_paths(
    db: AsyncSession,
    ally_user_id: uuid.UUID,
    ally_org_id: uuid.UUID,
    investor_user_id: uuid.UUID,
) -> list[IntroPathResponse]:
    """Find warm introduction paths between an ally user and an investor."""
    ally_connections = await get_connections(db, ally_user_id, ally_org_id)

    paths: list[IntroPathResponse] = []

    # Build paths from ally's connections — each connection represents a
    # potential warm intro path through that organisation or person.
    for conn in ally_connections:
        warmth = score_warmth_single(conn)
        paths.append(
            IntroPathResponse(
                type="ally_connection",
                connector_org=conn.connected_org_name,
                connector_person=conn.connected_person_name,
                connection_type=conn.connection_type,
                warmth=warmth,
            )
        )

    # Sort by warmth descending, return top 5
    paths.sort(key=lambda p: p.warmth, reverse=True)
    return paths[:5]


# ── Suggestions ───────────────────────────────────────────────────────────────


async def suggest_warm_intros(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 10,
) -> list[WarmIntroSuggestion]:
    """For a project, suggest investors with warmest intro paths."""
    # Load the requesting user's connections
    ally_connections = await get_connections(db, user_id, org_id)

    if not ally_connections:
        return []

    # Load all investor organisations (other orgs in the platform)
    org_stmt = select(Organization).where(
        Organization.id != org_id,
        Organization.is_deleted.is_(False),
    )
    org_result = await db.execute(org_stmt)
    investor_orgs = list(org_result.scalars().all())

    suggestions: list[WarmIntroSuggestion] = []

    for inv_org in investor_orgs:
        # Build paths: for each ally connection, compute warmth toward this org
        paths: list[IntroPathResponse] = []
        for conn in ally_connections:
            warmth = score_warmth_single(conn)
            paths.append(
                IntroPathResponse(
                    type="ally_connection",
                    connector_org=conn.connected_org_name,
                    connector_person=conn.connected_person_name,
                    connection_type=conn.connection_type,
                    warmth=warmth,
                )
            )

        if not paths:
            continue

        paths.sort(key=lambda p: p.warmth, reverse=True)
        best = paths[0]
        warmth_score = best.warmth

        suggestions.append(
            WarmIntroSuggestion(
                investor_org_id=inv_org.id,
                investor_name=inv_org.name,
                warmth_score=warmth_score,
                best_path=best,
                all_paths=paths[:5],
            )
        )

    suggestions.sort(key=lambda s: s.warmth_score, reverse=True)
    return suggestions[:limit]


# ── Introduction requests ─────────────────────────────────────────────────────


def _intro_request_to_response(req: IntroductionRequest) -> IntroRequestResponse:
    return IntroRequestResponse(
        id=req.id,
        requester_id=req.requester_id,
        requester_org_id=req.requester_org_id,
        target_investor_id=req.target_investor_id,
        connector_id=req.connector_id,
        project_id=req.project_id,
        warmth_score=req.warmth_score,
        introduction_path=req.introduction_path,
        status=req.status,
        message=req.message,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


async def request_introduction(
    db: AsyncSession,
    requester_id: uuid.UUID,
    requester_org_id: uuid.UUID,
    target_investor_id: uuid.UUID,
    project_id: uuid.UUID | None,
    path: dict,
    message: str,
) -> IntroductionRequest:
    """Create an introduction request."""
    warmth_score: float | None = path.get("warmth") if path else None

    req = IntroductionRequest(
        requester_id=requester_id,
        requester_org_id=requester_org_id,
        target_investor_id=target_investor_id,
        project_id=project_id,
        warmth_score=warmth_score,
        introduction_path=path,
        status="pending",
        message=message,
    )
    db.add(req)
    await db.flush()
    return req


async def list_introduction_requests(
    db: AsyncSession,
    requester_id: uuid.UUID,
    requester_org_id: uuid.UUID,
) -> list[IntroductionRequest]:
    """List all introduction requests made by this user."""
    stmt = (
        select(IntroductionRequest)
        .where(
            IntroductionRequest.requester_id == requester_id,
            IntroductionRequest.requester_org_id == requester_org_id,
            IntroductionRequest.is_deleted.is_(False),
        )
        .order_by(IntroductionRequest.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_request_status(
    db: AsyncSession,
    org_id: uuid.UUID,
    request_id: uuid.UUID,
    new_status: str,
) -> IntroductionRequest:
    """Update the status of an introduction request (connector accepts/declines)."""
    if new_status not in _VALID_STATUSES:
        raise ValueError(
            f"Invalid status: {new_status}. Must be one of {sorted(_VALID_STATUSES)}"
        )

    stmt = select(IntroductionRequest).where(
        IntroductionRequest.id == request_id,
        IntroductionRequest.requester_org_id == org_id,
        IntroductionRequest.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()
    if not req:
        raise LookupError(f"Introduction request {request_id} not found")

    req.status = new_status
    await db.flush()
    return req
