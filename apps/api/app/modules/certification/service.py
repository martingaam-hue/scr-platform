"""Investor Readiness Certification service layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certification import InvestorReadinessCertification
from app.models.projects import Project, SignalScore
from app.modules.certification.schemas import (
    CertificationBadge,
    CertificationRequirementsResponse,
    LeaderboardEntry,
)

logger = structlog.get_logger()

CERTIFICATION_THRESHOLD = 80.0
SUSPENSION_THRESHOLD = 75.0
MIN_DIMENSION_SCORE = 65.0


def _build_dimension_scores(score: SignalScore) -> dict:
    """Build a dimension scores dict from individual SignalScore columns."""
    return {
        "technical": score.project_viability_score,
        "financial": score.financial_planning_score,
        "esg": score.esg_score,
        "regulatory": score.risk_assessment_score,
        "team": score.team_strength_score,
        "market_opportunity": score.market_opportunity_score,
    }


def determine_tier(score: float) -> str:
    """Determine certification tier from overall score."""
    if score >= 96:
        return "elite"
    if score >= 90:
        return "premium"
    return "standard"


async def evaluate_certification(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> InvestorReadinessCertification:
    """Evaluate and update certification status for a project.

    Called automatically after each signal score calculation.
    """
    # 1. Get latest signal score
    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    score = result.scalar_one_or_none()

    # 2. Get or create certification record
    cert_stmt = select(InvestorReadinessCertification).where(
        InvestorReadinessCertification.project_id == project_id,
        InvestorReadinessCertification.is_deleted.is_(False),
    )
    cert_result = await db.execute(cert_stmt)
    cert = cert_result.scalar_one_or_none()

    if cert is None:
        cert = InvestorReadinessCertification(
            project_id=project_id,
            org_id=org_id,
            status="not_certified",
            certification_count=0,
            consecutive_months_certified=0,
        )
        db.add(cert)
        await db.flush()

    now = datetime.now(timezone.utc)

    if score is None:
        # No score available — ensure status remains not_certified
        await db.commit()
        return cert

    dimension_scores = _build_dimension_scores(score)
    overall = float(score.overall_score)

    # 3. Check qualification criteria
    overall_qualifies = overall >= CERTIFICATION_THRESHOLD
    all_dimensions_qualify = all(
        v >= MIN_DIMENSION_SCORE for v in dimension_scores.values()
    )
    qualifies = overall_qualifies and all_dimensions_qualify

    # 4. Apply state machine transitions
    if cert.status in ("not_certified", "suspended") and qualifies:
        cert.status = "certified"
        cert.certified_at = now
        cert.certification_score = overall
        cert.dimension_scores = dimension_scores
        cert.tier = determine_tier(overall)
        cert.certification_count = (cert.certification_count or 0) + 1
        cert.last_verified_at = now
        logger.info(
            "certification_granted",
            project_id=str(project_id),
            score=overall,
            tier=cert.tier,
        )

    elif cert.status == "certified":
        cert.last_verified_at = now
        cert.dimension_scores = dimension_scores

        if overall < SUSPENSION_THRESHOLD:
            cert.status = "suspended"
            cert.suspended_at = now
            cert.consecutive_months_certified = 0
            logger.info(
                "certification_suspended",
                project_id=str(project_id),
                score=overall,
            )
        else:
            new_tier = determine_tier(overall)
            cert.tier = new_tier
            cert.certification_score = overall

    await db.commit()
    return cert


async def get_certification_badge(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> CertificationBadge:
    """Return badge data for a project. Returns uncertified badge if not found."""
    stmt = select(InvestorReadinessCertification).where(
        InvestorReadinessCertification.project_id == project_id,
        InvestorReadinessCertification.status == "certified",
        InvestorReadinessCertification.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    cert = result.scalar_one_or_none()

    if cert is None:
        return CertificationBadge(certified=False)

    certified_since: str | None = None
    if cert.certified_at:
        certified_since = cert.certified_at.isoformat()

    return CertificationBadge(
        certified=True,
        tier=cert.tier,
        score=cert.certification_score,
        certified_since=certified_since,
        consecutive_months=cert.consecutive_months_certified,
    )


async def get_certification_requirements(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> CertificationRequirementsResponse:
    """Analyse what a project needs to achieve certification."""
    # Get latest signal score (no org check here — called internally after verify)
    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    score = result.scalar_one_or_none()

    if score is None:
        return CertificationRequirementsResponse(
            eligible=False,
            current_score=None,
            gaps=[{"type": "signal_score", "current": 0, "needed": int(CERTIFICATION_THRESHOLD)}],
        )

    overall = float(score.overall_score)
    dimension_scores = _build_dimension_scores(score)
    gaps: list[dict] = []

    if overall < CERTIFICATION_THRESHOLD:
        gaps.append({
            "type": "overall_score",
            "current": overall,
            "needed": CERTIFICATION_THRESHOLD,
        })

    for dim_name, dim_score in dimension_scores.items():
        if float(dim_score) < MIN_DIMENSION_SCORE:
            gaps.append({
                "type": "dimension_score",
                "dimension": dim_name,
                "current": float(dim_score),
                "needed": MIN_DIMENSION_SCORE,
            })

    eligible = len(gaps) == 0

    return CertificationRequirementsResponse(
        eligible=eligible,
        current_score=overall,
        gaps=gaps,
    )


async def get_certified_projects(
    db: AsyncSession,
    org_id: uuid.UUID,
    limit: int = 20,
) -> list[LeaderboardEntry]:
    """Return leaderboard of certified projects for an org, ordered by score desc."""
    stmt = (
        select(InvestorReadinessCertification, Project.name)
        .join(Project, Project.id == InvestorReadinessCertification.project_id)
        .where(
            InvestorReadinessCertification.org_id == org_id,
            InvestorReadinessCertification.status == "certified",
            InvestorReadinessCertification.is_deleted.is_(False),
            Project.is_deleted.is_(False),
        )
        .order_by(InvestorReadinessCertification.certification_score.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    entries = []
    for cert, project_name in rows:
        certified_since = ""
        if cert.certified_at:
            certified_since = cert.certified_at.isoformat()

        entries.append(
            LeaderboardEntry(
                project_id=cert.project_id,
                project_name=project_name,
                tier=cert.tier or "standard",
                score=cert.certification_score or 0.0,
                certified_since=certified_since,
            )
        )

    return entries
