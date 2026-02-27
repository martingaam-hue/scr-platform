"""Investor Signal Score service."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import InvestorSignalScore
from app.models.investors import InvestorMandate
from app.models.projects import Project, SignalScore
from app.modules.investor_signal_score import scorer
from app.modules.investor_signal_score.schemas import (
    DealAlignmentResponse,
    DimensionScore,
    InvestorSignalScoreResponse,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_dimension(dim_data: dict) -> DimensionScore:
    return DimensionScore(
        score=float(dim_data.get("score", 0)),
        weight=float(dim_data.get("weight", 0)),
        details=dim_data.get("details"),
        gaps=dim_data.get("gaps", []),
        recommendations=dim_data.get("recommendations", []),
    )


def _orm_to_response(record: InvestorSignalScore, scored: dict) -> InvestorSignalScoreResponse:
    """Map ORM record + scorer output dict to response schema."""
    dims = scored.get("dimensions", {})
    return InvestorSignalScoreResponse(
        id=record.id,
        org_id=record.org_id,
        overall_score=float(record.overall_score),
        financial_capacity=_build_dimension(dims.get("financial_capacity", {})),
        risk_management=_build_dimension(dims.get("risk_management", {})),
        investment_strategy=_build_dimension(dims.get("investment_strategy", {})),
        team_experience=_build_dimension(dims.get("team_experience", {})),
        esg_commitment=_build_dimension(dims.get("esg_commitment", {})),
        platform_readiness=_build_dimension(dims.get("platform_readiness", {})),
        score_change=(
            float(record.score_change) if record.score_change is not None else None
        ),
        previous_score=(
            float(record.previous_score) if record.previous_score is not None else None
        ),
        calculated_at=record.calculated_at,
    )


def _extract_stored_dimensions(record: InvestorSignalScore) -> dict:
    """Re-hydrate dimension data stored in the record's JSONB fields."""
    return {
        "financial_capacity": {
            "score": float(record.financial_capacity_score),
            "weight": scorer.DIMENSION_WEIGHTS["financial_capacity"],
            "details": record.financial_capacity_details,
            "gaps": (record.gaps or {}).get("financial_capacity", []),
            "recommendations": (record.recommendations or {}).get("financial_capacity", []),
        },
        "risk_management": {
            "score": float(record.risk_management_score),
            "weight": scorer.DIMENSION_WEIGHTS["risk_management"],
            "details": record.risk_management_details,
            "gaps": (record.gaps or {}).get("risk_management", []),
            "recommendations": (record.recommendations or {}).get("risk_management", []),
        },
        "investment_strategy": {
            "score": float(record.investment_strategy_score),
            "weight": scorer.DIMENSION_WEIGHTS["investment_strategy"],
            "details": record.investment_strategy_details,
            "gaps": (record.gaps or {}).get("investment_strategy", []),
            "recommendations": (record.recommendations or {}).get("investment_strategy", []),
        },
        "team_experience": {
            "score": float(record.team_experience_score),
            "weight": scorer.DIMENSION_WEIGHTS["team_experience"],
            "details": record.team_experience_details,
            "gaps": (record.gaps or {}).get("team_experience", []),
            "recommendations": (record.recommendations or {}).get("team_experience", []),
        },
        "esg_commitment": {
            "score": float(record.esg_commitment_score),
            "weight": scorer.DIMENSION_WEIGHTS["esg_commitment"],
            "details": record.esg_commitment_details,
            "gaps": (record.gaps or {}).get("esg_commitment", []),
            "recommendations": (record.recommendations or {}).get("esg_commitment", []),
        },
        "platform_readiness": {
            "score": float(record.platform_readiness_score),
            "weight": scorer.DIMENSION_WEIGHTS["platform_readiness"],
            "details": record.platform_readiness_details,
            "gaps": (record.gaps or {}).get("platform_readiness", []),
            "recommendations": (record.recommendations or {}).get("platform_readiness", []),
        },
    }


# ── Service functions ─────────────────────────────────────────────────────────


async def calculate_score(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> InvestorSignalScoreResponse:
    """Calculate a new InvestorSignalScore from the latest InvestorMandate."""
    # Load first/active mandate for the org
    stmt = (
        select(InvestorMandate)
        .where(InvestorMandate.org_id == org_id)
        .order_by(InvestorMandate.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    mandate = result.scalar_one_or_none()

    if mandate is None:
        raise LookupError("No InvestorMandate found for this organisation. Create a mandate first.")

    # Run scorer
    scored = scorer.score_investor(mandate)
    dims = scored["dimensions"]
    overall = scored["overall_score"]

    # Load previous score to compute change
    prev_stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    prev_result = await db.execute(prev_stmt)
    previous_record = prev_result.scalar_one_or_none()

    previous_score: Decimal | None = None
    score_change: Decimal | None = None
    if previous_record is not None:
        previous_score = previous_record.overall_score
        score_change = Decimal(str(overall)) - previous_score

    # Build per-dimension gaps/recommendations dicts (keyed by dimension)
    gaps_dict = {k: v["gaps"] for k, v in dims.items()}
    recs_dict = {k: v["recommendations"] for k, v in dims.items()}

    now = datetime.now(timezone.utc)
    record = InvestorSignalScore(
        org_id=org_id,
        overall_score=Decimal(str(overall)),
        financial_capacity_score=Decimal(str(dims["financial_capacity"]["score"])),
        financial_capacity_details={"mandate_id": str(mandate.id)},
        risk_management_score=Decimal(str(dims["risk_management"]["score"])),
        risk_management_details=None,
        investment_strategy_score=Decimal(str(dims["investment_strategy"]["score"])),
        investment_strategy_details={"sectors": getattr(mandate, "sectors", None)},
        team_experience_score=Decimal(str(dims["team_experience"]["score"])),
        team_experience_details=None,
        esg_commitment_score=Decimal(str(dims["esg_commitment"]["score"])),
        esg_commitment_details={"has_requirements": bool(getattr(mandate, "esg_requirements", None))},
        platform_readiness_score=Decimal(str(dims["platform_readiness"]["score"])),
        platform_readiness_details={"mandate_active": getattr(mandate, "is_active", False)},
        gaps=gaps_dict,
        recommendations=recs_dict,
        score_factors={"dimension_weights": scorer.DIMENSION_WEIGHTS},
        data_sources={"mandate_id": str(mandate.id), "source": "investor_mandate"},
        calculated_at=now,
        previous_score=previous_score,
        score_change=score_change,
    )

    db.add(record)
    await db.flush()
    await db.refresh(record)

    return _orm_to_response(record, {"dimensions": _extract_stored_dimensions(record)})


async def get_latest_score(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> InvestorSignalScoreResponse | None:
    """Get the most recent InvestorSignalScore for the org, or None."""
    stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return None

    rehydrated = _extract_stored_dimensions(record)
    return _orm_to_response(record, {"dimensions": rehydrated})


async def get_deal_alignment(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> DealAlignmentResponse:
    """
    Compute alignment between the investor's signal score and a given project.

    Uses the project's SignalScore dimensions compared against the investor's
    6 InvestorSignalScore dimensions. Returns a 0-100 alignment score.
    """
    # Load investor's latest score
    investor_record_stmt = (
        select(InvestorSignalScore)
        .where(InvestorSignalScore.org_id == org_id)
        .order_by(InvestorSignalScore.calculated_at.desc())
        .limit(1)
    )
    investor_result = await db.execute(investor_record_stmt)
    investor_record = investor_result.scalar_one_or_none()

    investor_overall = float(investor_record.overall_score) if investor_record else 50.0

    # Load project
    project_stmt = select(Project).where(
        Project.id == project_id,
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    if project is None:
        raise LookupError(f"Project {project_id} not found")

    # Load project's SignalScore if available
    ss_stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.calculated_at.desc())
        .limit(1)
    )
    ss_result = await db.execute(ss_stmt)
    signal_score = ss_result.scalar_one_or_none()

    # Build alignment factors comparing investor vs project
    # Investor dimensions map loosely to project signal score dimensions
    investor_dims: dict[str, float] = {}
    if investor_record:
        investor_dims = {
            "financial_capacity": float(investor_record.financial_capacity_score),
            "risk_management": float(investor_record.risk_management_score),
            "investment_strategy": float(investor_record.investment_strategy_score),
            "team_experience": float(investor_record.team_experience_score),
            "esg_commitment": float(investor_record.esg_commitment_score),
            "platform_readiness": float(investor_record.platform_readiness_score),
        }

    # Project signal score dimensions (if available)
    project_dim_scores: dict[str, float] = {}
    if signal_score and signal_score.scoring_details:
        dims_data = signal_score.scoring_details.get("dimensions", {})
        # Map project dimension IDs to our investor dimension keys
        project_dim_scores = {
            "financial_capacity": float(dims_data.get("financial", {}).get("score", 50)),
            "risk_management": float(dims_data.get("regulatory", {}).get("score", 50)),
            "investment_strategy": float(dims_data.get("market_opportunity", {}).get("score", 50)),
            "team_experience": float(dims_data.get("team", {}).get("score", 50)),
            "esg_commitment": float(dims_data.get("esg", {}).get("score", 50)),
            "platform_readiness": float(dims_data.get("technical", {}).get("score", 50)),
        }
    else:
        # No project signal score: use neutral 50 for all
        project_dim_scores = {k: 50.0 for k in investor_dims}

    # Compute per-dimension alignment
    alignment_factors: list[dict] = []
    total_alignment = 0.0
    weight_sum = 0.0

    for dim, inv_score_val in investor_dims.items():
        proj_score_val = project_dim_scores.get(dim, 50.0)
        weight = scorer.DIMENSION_WEIGHTS.get(dim, 0.0)

        # Alignment: how well investor readiness matches project requirements
        # If investor score >= project score → good alignment; gap penalised
        gap = inv_score_val - proj_score_val
        dim_alignment = max(0.0, min(100.0, 50.0 + gap * 0.5))

        impact = "high" if weight >= 0.20 else ("medium" if weight >= 0.15 else "low")
        alignment_factors.append({
            "dimension": dim,
            "investor_score": round(inv_score_val, 1),
            "project_score": round(proj_score_val, 1),
            "score": round(dim_alignment, 1),
            "impact": impact,
        })
        total_alignment += dim_alignment * weight
        weight_sum += weight

    overall_alignment = int(round(total_alignment / weight_sum)) if weight_sum > 0 else 50

    # Map alignment score to recommendation
    if overall_alignment >= 80:
        recommendation = "strong_fit"
    elif overall_alignment >= 65:
        recommendation = "good_fit"
    elif overall_alignment >= 45:
        recommendation = "marginal_fit"
    else:
        recommendation = "poor_fit"

    return DealAlignmentResponse(
        project_id=project_id,
        investor_score=investor_overall,
        alignment_score=overall_alignment,
        alignment_factors=alignment_factors,
        recommendation=recommendation,
    )
