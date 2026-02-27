"""Matching service — investor/ally recommendations and match lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization
from app.models.enums import MatchInitiator, MatchStatus, RiskTolerance
from app.models.investors import InvestorMandate
from app.models.matching import MatchMessage, MatchResult
from app.models.projects import Project, SignalScore
from app.modules.matching.algorithm import AlignmentScore, MatchingAlgorithm
from app.modules.matching.schemas import (
    AlignmentBreakdownResponse,
    AllyRecommendationsResponse,
    InvestorRecommendationsResponse,
    MatchMessageResponse,
    MatchingInvestorResponse,
    MatchStatusResponse,
    MandateResponse,
    MessagesResponse,
    RecommendedProjectResponse,
)

logger = structlog.get_logger()

_algo = MatchingAlgorithm()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _latest_signal_score(
    db: AsyncSession, project_id: uuid.UUID
) -> SignalScore | None:
    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_match_or_raise(
    db: AsyncSession, match_id: uuid.UUID, org_id: uuid.UUID
) -> MatchResult:
    stmt = select(MatchResult).where(
        MatchResult.id == match_id,
        MatchResult.is_deleted.is_(False),
        or_(
            MatchResult.investor_org_id == org_id,
            MatchResult.ally_org_id == org_id,
        ),
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if not match:
        raise LookupError(f"Match {match_id} not found")
    return match


def _alignment_to_response(a: AlignmentScore) -> AlignmentBreakdownResponse:
    return AlignmentBreakdownResponse(
        overall=a.overall,
        sector=a.sector,
        geography=a.geography,
        ticket_size=a.ticket_size,
        stage=a.stage,
        risk_return=a.risk_return,
        esg=a.esg,
        breakdown=a.breakdown,
    )


def _mandate_to_response(m: InvestorMandate) -> MandateResponse:
    return MandateResponse(
        id=m.id,
        org_id=m.org_id,
        name=m.name,
        sectors=m.sectors,
        geographies=m.geographies,
        stages=m.stages,
        ticket_size_min=str(m.ticket_size_min),
        ticket_size_max=str(m.ticket_size_max),
        target_irr_min=str(m.target_irr_min) if m.target_irr_min else None,
        risk_tolerance=m.risk_tolerance.value,
        esg_requirements=m.esg_requirements,
        exclusions=m.exclusions,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── Investor recommendations ──────────────────────────────────────────────────


async def get_investor_recommendations(
    db: AsyncSession,
    investor_org_id: uuid.UUID,
    *,
    sector: str | None = None,
    geography: str | None = None,
    min_alignment: int | None = None,
    sort_by: str = "alignment",  # alignment|signal_score|recency
    limit: int = 50,
) -> InvestorRecommendationsResponse:
    # Load all active mandates for this investor
    mandate_stmt = select(InvestorMandate).where(
        InvestorMandate.org_id == investor_org_id,
        InvestorMandate.is_active.is_(True),
        InvestorMandate.is_deleted.is_(False),
    )
    mandate_result = await db.execute(mandate_stmt)
    mandates = list(mandate_result.scalars().all())

    if not mandates:
        return InvestorRecommendationsResponse(items=[], total=0)

    # Load all published projects
    proj_stmt = select(Project).where(
        Project.is_published.is_(True),
        Project.is_deleted.is_(False),
    )
    if sector:
        proj_stmt = proj_stmt.where(Project.project_type.in_([sector]))
    if geography:
        proj_stmt = proj_stmt.where(Project.geography_country.ilike(f"%{geography}%"))

    proj_result = await db.execute(proj_stmt)
    projects = list(proj_result.scalars().all())

    # Load existing matches for investor (to get status)
    existing_stmt = select(MatchResult).where(
        MatchResult.investor_org_id == investor_org_id,
        MatchResult.is_deleted.is_(False),
    )
    existing_result = await db.execute(existing_stmt)
    existing_by_project: dict[uuid.UUID, MatchResult] = {
        m.project_id: m for m in existing_result.scalars().all()
    }

    # Score each project against best matching mandate
    scored: list[tuple[Project, SignalScore | None, AlignmentScore, InvestorMandate]] = []
    for proj in projects:
        ss = await _latest_signal_score(db, proj.id)
        best_score: AlignmentScore | None = None
        best_mandate: InvestorMandate | None = None
        for mandate in mandates:
            score = _algo.calculate_alignment(mandate, proj, ss)
            if best_score is None or score.overall > best_score.overall:
                best_score = score
                best_mandate = mandate
        if best_score is not None and best_mandate is not None:
            scored.append((proj, ss, best_score, best_mandate))

    # Filter by min alignment
    if min_alignment is not None:
        scored = [(p, ss, s, m) for p, ss, s, m in scored if s.overall >= min_alignment]

    # Sort
    if sort_by == "signal_score":
        scored.sort(key=lambda x: (x[1].overall_score if x[1] else 0), reverse=True)
    elif sort_by == "recency":
        scored.sort(
            key=lambda x: existing_by_project[x[0].id].updated_at
            if x[0].id in existing_by_project else x[0].created_at,
            reverse=True,
        )
    else:  # alignment (default)
        scored.sort(key=lambda x: x[2].overall, reverse=True)

    scored = scored[:limit]

    items: list[RecommendedProjectResponse] = []
    for proj, ss, alignment, mandate in scored:
        existing = existing_by_project.get(proj.id)
        items.append(
            RecommendedProjectResponse(
                match_id=existing.id if existing else None,
                project_id=proj.id,
                project_name=proj.name,
                project_type=proj.project_type.value,
                geography_country=proj.geography_country,
                stage=proj.stage.value,
                total_investment_required=str(proj.total_investment_required),
                currency=proj.currency,
                cover_image_url=proj.cover_image_url,
                signal_score=ss.overall_score if ss else None,
                alignment=_alignment_to_response(alignment),
                status=existing.status.value if existing else "new",
                mandate_id=mandate.id,
                mandate_name=mandate.name,
                updated_at=existing.updated_at if existing else proj.updated_at,
            )
        )

    return InvestorRecommendationsResponse(items=items, total=len(items))


# ── Ally recommendations ──────────────────────────────────────────────────────


async def get_ally_recommendations(
    db: AsyncSession,
    project_id: uuid.UUID,
    ally_org_id: uuid.UUID,
) -> AllyRecommendationsResponse:
    # Verify project belongs to ally
    proj_stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == ally_org_id,
        Project.is_deleted.is_(False),
    )
    proj_result = await db.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")

    ss = await _latest_signal_score(db, project_id)

    # Load all active mandates across all investors
    mandate_stmt = select(InvestorMandate).where(
        InvestorMandate.is_active.is_(True),
        InvestorMandate.is_deleted.is_(False),
    )
    mandate_result = await db.execute(mandate_stmt)
    mandates = list(mandate_result.scalars().all())

    # Existing matches for this project
    existing_stmt = select(MatchResult).where(
        MatchResult.project_id == project_id,
        MatchResult.is_deleted.is_(False),
    )
    existing_result = await db.execute(existing_stmt)
    existing_by_investor: dict[uuid.UUID, MatchResult] = {
        m.investor_org_id: m for m in existing_result.scalars().all()
    }

    # Load investor org details
    investor_org_ids = {m.org_id for m in mandates}
    org_stmt = select(Organization).where(Organization.id.in_(investor_org_ids))
    org_result = await db.execute(org_stmt)
    orgs: dict[uuid.UUID, Organization] = {o.id: o for o in org_result.scalars().all()}

    scored: list[tuple[InvestorMandate, AlignmentScore, Organization]] = []
    for mandate in mandates:
        org = orgs.get(mandate.org_id)
        if not org:
            continue
        alignment = _algo.calculate_alignment(mandate, project, ss)
        scored.append((mandate, alignment, org))

    scored.sort(key=lambda x: x[1].overall, reverse=True)

    items: list[MatchingInvestorResponse] = []
    for mandate, alignment, org in scored:
        existing = existing_by_investor.get(mandate.org_id)
        items.append(
            MatchingInvestorResponse(
                match_id=existing.id if existing else None,
                investor_org_id=mandate.org_id,
                investor_name=org.name,
                logo_url=org.logo_url,
                mandate_id=mandate.id,
                mandate_name=mandate.name,
                ticket_size_min=str(mandate.ticket_size_min),
                ticket_size_max=str(mandate.ticket_size_max),
                sectors=mandate.sectors or [],
                geographies=mandate.geographies or [],
                risk_tolerance=mandate.risk_tolerance.value,
                alignment=_alignment_to_response(alignment),
                status=existing.status.value if existing else "new",
                initiated_by=existing.initiated_by.value if existing else None,
                updated_at=existing.updated_at if existing else None,
            )
        )

    return AllyRecommendationsResponse(
        project_id=project_id,
        project_name=project.name,
        items=items,
        total=len(items),
    )


# ── Match lifecycle ───────────────────────────────────────────────────────────


async def _get_or_create_match(
    db: AsyncSession,
    project_id: uuid.UUID,
    investor_org_id: uuid.UUID,
    ally_org_id: uuid.UUID,
    mandate_id: uuid.UUID | None,
    overall_score: int,
    score_breakdown: dict,
    initiator: MatchInitiator,
) -> MatchResult:
    stmt = select(MatchResult).where(
        MatchResult.project_id == project_id,
        MatchResult.investor_org_id == investor_org_id,
        MatchResult.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if match:
        return match

    match = MatchResult(
        investor_org_id=investor_org_id,
        ally_org_id=ally_org_id,
        project_id=project_id,
        mandate_id=mandate_id,
        overall_score=overall_score,
        score_breakdown=score_breakdown,
        status=MatchStatus.SUGGESTED,
        initiated_by=initiator,
    )
    db.add(match)
    await db.flush()
    return match


async def express_interest(
    db: AsyncSession,
    match_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MatchStatusResponse:
    match = await _get_match_or_raise(db, match_id, org_id)
    match.status = MatchStatus.INTERESTED

    # Add system message
    msg = MatchMessage(
        match_id=match.id,
        sender_id=user_id,
        content="Expressed interest in this project.",
        is_system=True,
    )
    db.add(msg)
    await db.flush()

    return MatchStatusResponse(
        match_id=match.id,
        status=match.status.value,
        updated_at=match.updated_at,
    )


async def request_intro(
    db: AsyncSession,
    match_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MatchStatusResponse:
    match = await _get_match_or_raise(db, match_id, org_id)
    match.status = MatchStatus.INTRO_REQUESTED

    msg = MatchMessage(
        match_id=match.id,
        sender_id=user_id,
        content="Introduction requested. Our team will facilitate the connection.",
        is_system=True,
    )
    db.add(msg)
    await db.flush()

    return MatchStatusResponse(
        match_id=match.id,
        status=match.status.value,
        updated_at=match.updated_at,
    )


async def update_match_status(
    db: AsyncSession,
    match_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    notes: str | None,
) -> MatchStatusResponse:
    try:
        new_status = MatchStatus(status)
    except ValueError:
        raise ValueError(f"Invalid status: {status}")

    match = await _get_match_or_raise(db, match_id, org_id)
    old_status = match.status.value
    match.status = new_status

    if notes:
        if match.investor_org_id == org_id:
            match.investor_notes = notes
        else:
            match.ally_notes = notes

    if old_status != status:
        msg = MatchMessage(
            match_id=match.id,
            sender_id=user_id,
            content=f"Status updated: {old_status} → {status}",
            is_system=True,
        )
        db.add(msg)

    await db.flush()
    return MatchStatusResponse(
        match_id=match.id,
        status=match.status.value,
        updated_at=match.updated_at,
    )


# ── Messaging ─────────────────────────────────────────────────────────────────


async def get_messages(
    db: AsyncSession,
    match_id: uuid.UUID,
    org_id: uuid.UUID,
) -> MessagesResponse:
    await _get_match_or_raise(db, match_id, org_id)

    stmt = (
        select(MatchMessage)
        .where(MatchMessage.match_id == match_id)
        .order_by(MatchMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().all())

    return MessagesResponse(
        items=[
            MatchMessageResponse(
                id=m.id,
                match_id=m.match_id,
                sender_id=m.sender_id,
                content=m.content,
                is_system=m.is_system,
                created_at=m.created_at,
            )
            for m in messages
        ],
        total=len(messages),
    )


async def send_message(
    db: AsyncSession,
    match_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    content: str,
) -> MatchMessageResponse:
    match = await _get_match_or_raise(db, match_id, org_id)

    # Auto-advance to VIEWED if investor is initiating contact
    if match.status == MatchStatus.SUGGESTED and match.investor_org_id == org_id:
        match.status = MatchStatus.VIEWED

    msg = MatchMessage(
        match_id=match_id,
        sender_id=user_id,
        content=content,
        is_system=False,
    )
    db.add(msg)
    await db.flush()

    return MatchMessageResponse(
        id=msg.id,
        match_id=msg.match_id,
        sender_id=msg.sender_id,
        content=msg.content,
        is_system=msg.is_system,
        created_at=msg.created_at,
    )


# ── Mandate CRUD ──────────────────────────────────────────────────────────────


async def list_mandates(
    db: AsyncSession, org_id: uuid.UUID
) -> list[InvestorMandate]:
    stmt = (
        select(InvestorMandate)
        .where(
            InvestorMandate.org_id == org_id,
            InvestorMandate.is_deleted.is_(False),
        )
        .order_by(InvestorMandate.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_mandate(
    db: AsyncSession,
    org_id: uuid.UUID,
    data,
) -> InvestorMandate:
    try:
        risk_tolerance = RiskTolerance(data.risk_tolerance)
    except ValueError:
        raise ValueError(f"Invalid risk_tolerance: {data.risk_tolerance}")

    mandate = InvestorMandate(
        org_id=org_id,
        name=data.name,
        sectors=data.sectors,
        geographies=data.geographies,
        stages=data.stages,
        ticket_size_min=data.ticket_size_min,
        ticket_size_max=data.ticket_size_max,
        target_irr_min=data.target_irr_min,
        risk_tolerance=risk_tolerance,
        esg_requirements=data.esg_requirements,
        exclusions=data.exclusions,
        is_active=data.is_active,
    )
    db.add(mandate)
    await db.flush()
    return mandate


async def update_mandate(
    db: AsyncSession,
    org_id: uuid.UUID,
    mandate_id: uuid.UUID,
    data,
) -> InvestorMandate:
    stmt = select(InvestorMandate).where(
        InvestorMandate.id == mandate_id,
        InvestorMandate.org_id == org_id,
        InvestorMandate.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    mandate = result.scalar_one_or_none()
    if not mandate:
        raise LookupError(f"Mandate {mandate_id} not found")

    if data.name is not None:
        mandate.name = data.name
    if data.sectors is not None:
        mandate.sectors = data.sectors
    if data.geographies is not None:
        mandate.geographies = data.geographies
    if data.stages is not None:
        mandate.stages = data.stages
    if data.ticket_size_min is not None:
        mandate.ticket_size_min = data.ticket_size_min
    if data.ticket_size_max is not None:
        mandate.ticket_size_max = data.ticket_size_max
    if data.target_irr_min is not None:
        mandate.target_irr_min = data.target_irr_min
    if data.risk_tolerance is not None:
        mandate.risk_tolerance = RiskTolerance(data.risk_tolerance)
    if data.esg_requirements is not None:
        mandate.esg_requirements = data.esg_requirements
    if data.exclusions is not None:
        mandate.exclusions = data.exclusions
    if data.is_active is not None:
        mandate.is_active = data.is_active

    await db.flush()
    return mandate
