"""Tax Credit Orchestrator — identification, optimization, and transfer docs."""

from __future__ import annotations

import json
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ReportStatus, TaxCreditQualification
from app.models.financial import TaxCredit
from app.models.investors import Portfolio, PortfolioHolding
from app.models.projects import Project
from app.models.reporting import GeneratedReport
from app.modules.tax_credits.schemas import (
    IdentificationResponse,
    IdentifiedCredit,
    OptimizationAction,
    OptimizationRequest,
    OptimizationResult,
    TaxCreditInventoryResponse,
    TaxCreditResponse,
    TaxCreditSummaryResponse,
    TransferDocRequest,
    TransferDocResponse,
)

logger = structlog.get_logger()

_TIMEOUT = 90.0

# ── Thresholds for optimization ───────────────────────────────────────────────

_TRANSFER_MIN_VALUE = 500_000.0   # USD: below this, claim directly (overhead not worth it)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_response(tc: TaxCredit, project_name: str | None = None) -> TaxCreditResponse:
    return TaxCreditResponse(
        id=tc.id,
        project_id=tc.project_id,
        org_id=tc.org_id,
        credit_type=tc.credit_type,
        estimated_value=str(tc.estimated_value),
        claimed_value=str(tc.claimed_value) if tc.claimed_value is not None else None,
        currency=tc.currency,
        qualification=tc.qualification.value,
        qualification_details=tc.qualification_details,
        effective_date=tc.effective_date,
        expiry_date=tc.expiry_date,
        project_name=project_name,
        created_at=tc.created_at,
        updated_at=tc.updated_at,
    )


async def _load_credits_for_projects(
    db: AsyncSession,
    project_ids: list[uuid.UUID],
    org_id: uuid.UUID,
) -> list[tuple[TaxCredit, str | None]]:
    """Load TaxCredit rows with project names for a set of project IDs."""
    result = await db.execute(
        select(TaxCredit, Project.name)
        .outerjoin(Project, TaxCredit.project_id == Project.id)
        .where(
            TaxCredit.project_id.in_(project_ids),
            TaxCredit.org_id == org_id,
            TaxCredit.is_deleted.is_(False),
        )
    )
    return list(result.all())


# ── Inventory ─────────────────────────────────────────────────────────────────


async def get_inventory(
    db: AsyncSession, portfolio_id: uuid.UUID, org_id: uuid.UUID
) -> TaxCreditInventoryResponse:
    # Load portfolio (scoped to org)
    portfolio = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.org_id == org_id,
            Portfolio.is_deleted.is_(False),
        )
    )
    portfolio = portfolio.scalar_one_or_none()
    if not portfolio:
        raise LookupError(f"Portfolio {portfolio_id} not found")

    # Collect project IDs from active holdings
    holdings_result = await db.execute(
        select(PortfolioHolding.project_id).where(
            PortfolioHolding.portfolio_id == portfolio_id,
            PortfolioHolding.project_id.isnot(None),
            PortfolioHolding.is_deleted.is_(False),
        )
    )
    project_ids = list(holdings_result.scalars().all())

    if not project_ids:
        return TaxCreditInventoryResponse(
            portfolio_id=portfolio_id,
            total_estimated=0.0,
            total_claimed=0.0,
            credits_by_type={},
            credits=[],
            currency=portfolio.currency,
        )

    rows = await _load_credits_for_projects(db, project_ids, org_id)

    credits = [_to_response(tc, name) for tc, name in rows]
    total_estimated = sum(float(tc.estimated_value) for tc, _ in rows)
    total_claimed = sum(
        float(tc.claimed_value) for tc, _ in rows if tc.claimed_value is not None
    )
    credits_by_type: dict[str, float] = {}
    for tc, _ in rows:
        credits_by_type[tc.credit_type] = (
            credits_by_type.get(tc.credit_type, 0.0) + float(tc.estimated_value)
        )

    return TaxCreditInventoryResponse(
        portfolio_id=portfolio_id,
        total_estimated=round(total_estimated, 2),
        total_claimed=round(total_claimed, 2),
        credits_by_type={k: round(v, 2) for k, v in credits_by_type.items()},
        credits=credits,
        currency=portfolio.currency,
    )


# ── Identification ────────────────────────────────────────────────────────────


async def identify_credits(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> IdentificationResponse:
    project = await db.get(Project, project_id)
    if not project or project.is_deleted or project.org_id != org_id:
        raise LookupError(f"Project {project_id} not found")

    capacity = float(project.capacity_mw) if project.capacity_mw else None
    investment = float(project.total_investment_required)

    prompt = f"""You are a US tax credit specialist for renewable energy and infrastructure projects.

Identify applicable US federal (and relevant state) tax credits for this project:
- Project name: {project.name}
- Project type: {project.project_type.value}
- Stage: {project.stage.value}
- Geography: {project.geography_country}
- Capacity: {f"{capacity} MW" if capacity else "N/A"}
- Total investment: {project.currency} {investment:,.0f}

Consider:
- ITC (Investment Tax Credit, IRA §48): solar, wind, storage — 30% base, up to 70% with bonuses
- PTC (Production Tax Credit, IRA §45): wind, solar (operational projects) — per-kWh credit
- 45Y (Clean Electricity Production Credit): post-2025 replacement for PTC
- 48E (Clean Electricity Investment Credit): post-2025 replacement for ITC
- 179D (Energy Efficient Commercial Buildings): $5/sqft for commercial projects
- 45L (Energy Efficient New Homes): residential / mixed-use
- NMTC (New Markets Tax Credit): projects in low-income census tracts
- Relevant state incentives for {project.geography_country}

Respond ONLY with valid JSON array:
[
  {{
    "credit_type": "ITC",
    "program_name": "Investment Tax Credit (IRA §48)",
    "estimated_value": <float in USD>,
    "qualification": "qualified" or "potential",
    "criteria_met": ["<criterion>"],
    "criteria_missing": ["<criterion>"],
    "notes": "<brief explanation>",
    "expiry_year": <year or null>
  }}
]"""

    identified: list[IdentifiedCredit] = []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "prompt": prompt,
                    "task_type": "analysis",
                    "max_tokens": 1500,
                    "temperature": 0.2,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            content = resp.json().get("content", "")

        match = re.search(r"\[.*\]", content, re.DOTALL)
        raw_list: list[dict[str, Any]] = json.loads(match.group() if match else content)

        for item in raw_list:
            identified.append(
                IdentifiedCredit(
                    credit_type=str(item["credit_type"]),
                    program_name=str(item["program_name"]),
                    estimated_value=float(item.get("estimated_value", 0)),
                    qualification=str(item.get("qualification", "potential")),
                    criteria_met=list(item.get("criteria_met", [])),
                    criteria_missing=list(item.get("criteria_missing", [])),
                    notes=str(item.get("notes", "")),
                    expiry_year=item.get("expiry_year"),
                )
            )
    except Exception as exc:
        logger.warning("identify_credits_ai_failed", error=str(exc))
        identified = _fallback_credits(project.project_type.value, investment)

    # Persist newly identified credits
    for credit in identified:
        # Check for existing record with same type
        existing = await db.execute(
            select(TaxCredit).where(
                TaxCredit.project_id == project_id,
                TaxCredit.org_id == org_id,
                TaxCredit.credit_type == credit.credit_type,
                TaxCredit.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none() is None:
            tc = TaxCredit(
                project_id=project_id,
                org_id=org_id,
                credit_type=credit.credit_type,
                estimated_value=Decimal(str(round(credit.estimated_value, 4))),
                currency=project.currency,
                qualification=TaxCreditQualification(
                    "qualified" if credit.qualification == "qualified" else "potential"
                ),
                qualification_details={
                    "program_name": credit.program_name,
                    "criteria_met": credit.criteria_met,
                    "criteria_missing": credit.criteria_missing,
                    "notes": credit.notes,
                },
                expiry_date=date(credit.expiry_year, 12, 31) if credit.expiry_year else None,
            )
            db.add(tc)

    total = sum(c.estimated_value for c in identified)
    return IdentificationResponse(
        project_id=project_id,
        project_name=project.name,
        identified=identified,
        total_estimated_value=round(total, 2),
        currency=project.currency,
    )


def _fallback_credits(
    project_type: str, investment: float
) -> list[IdentifiedCredit]:
    """Rule-based fallback when AI Gateway is unavailable."""
    credits: list[IdentifiedCredit] = []
    if project_type in ("solar", "wind", "geothermal", "hydro"):
        credits.append(
            IdentifiedCredit(
                credit_type="ITC",
                program_name="Investment Tax Credit (IRA §48)",
                estimated_value=round(investment * 0.30, 2),
                qualification="qualified",
                criteria_met=["Qualifying clean energy technology", "US-based project"],
                criteria_missing=[],
                notes="30% base ITC for qualified clean energy facilities.",
                expiry_year=2032,
            )
        )
    if project_type in ("solar", "wind"):
        credits.append(
            IdentifiedCredit(
                credit_type="PTC",
                program_name="Production Tax Credit (IRA §45)",
                estimated_value=round(investment * 0.08, 2),
                qualification="potential",
                criteria_met=["Qualifying technology"],
                criteria_missing=["Operational status required to claim"],
                notes="Per-kWh credit available once project is operational.",
                expiry_year=2032,
            )
        )
    if not credits:
        credits.append(
            IdentifiedCredit(
                credit_type="NMTC",
                program_name="New Markets Tax Credit",
                estimated_value=round(investment * 0.05, 2),
                qualification="potential",
                criteria_met=[],
                criteria_missing=["Low-income census tract qualification", "CDFI intermediary required"],
                notes="Available if project is located in a qualified low-income census tract.",
                expiry_year=None,
            )
        )
    return credits


# ── Optimization ──────────────────────────────────────────────────────────────


async def model_optimization(
    db: AsyncSession,
    req: OptimizationRequest,
    org_id: uuid.UUID,
) -> OptimizationResult:
    """Deterministic optimization: claim vs transfer, with timing recommendations."""
    portfolio = await db.execute(
        select(Portfolio).where(
            Portfolio.id == req.portfolio_id,
            Portfolio.org_id == org_id,
            Portfolio.is_deleted.is_(False),
        )
    )
    portfolio = portfolio.scalar_one_or_none()
    if not portfolio:
        raise LookupError(f"Portfolio {req.portfolio_id} not found")

    holdings_result = await db.execute(
        select(PortfolioHolding.project_id).where(
            PortfolioHolding.portfolio_id == req.portfolio_id,
            PortfolioHolding.project_id.isnot(None),
            PortfolioHolding.is_deleted.is_(False),
        )
    )
    project_ids = list(holdings_result.scalars().all())

    rows = await _load_credits_for_projects(db, project_ids, org_id)

    # Load project stages for timing determination
    projects: dict[uuid.UUID, Project] = {}
    if project_ids:
        proj_result = await db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        for proj in proj_result.scalars().all():
            projects[proj.id] = proj

    actions: list[OptimizationAction] = []
    total_value = claim_value = transfer_value = 0.0

    today = date.today()

    for tc, proj_name in rows:
        if tc.qualification in (TaxCreditQualification.CLAIMED, TaxCreditQualification.TRANSFERRED):
            continue  # Already actioned

        value = float(tc.estimated_value)
        total_value += value
        project = projects.get(tc.project_id)
        stage = project.stage.value if project else "unknown"

        # Timing
        if stage in ("operational",):
            timing = "immediate"
        elif stage in ("under_construction", "construction_ready"):
            timing = "upon_completion"
        else:
            timing = "pending_qualification"

        # Expiry check: avoid transfer if expiring within 12 months
        expiring_soon = (
            tc.expiry_date is not None
            and (tc.expiry_date - today).days < 365
        )

        # Decision: transfer if high value, qualified, and not expiring soon
        if (
            value >= _TRANSFER_MIN_VALUE
            and tc.qualification == TaxCreditQualification.QUALIFIED
            and not expiring_soon
        ):
            action = "transfer"
            transfer_value += value
            reason = (
                f"Value ({portfolio.currency} {value:,.0f}) exceeds transfer threshold; "
                "direct monetization recommended for cash flow."
            )
        else:
            action = "claim"
            claim_value += value
            if expiring_soon:
                reason = "Expiring within 12 months — claim immediately."
            elif tc.qualification != TaxCreditQualification.QUALIFIED:
                reason = "Pending qualification — claim after verification."
            else:
                reason = "Value below transfer threshold; claim directly."

        actions.append(
            OptimizationAction(
                credit_id=tc.id,
                project_name=proj_name or "Unknown Project",
                credit_type=tc.credit_type,
                estimated_value=round(value, 2),
                action=action,  # type: ignore[arg-type]
                timing=timing,
                reason=reason,
            )
        )

    transfer_count = sum(1 for a in actions if a.action == "transfer")
    claim_count = sum(1 for a in actions if a.action == "claim")

    summary = (
        f"Portfolio tax credit portfolio: {portfolio.currency} {total_value:,.0f} total across "
        f"{len(actions)} credits. Recommend transferring {transfer_count} credits "
        f"({portfolio.currency} {transfer_value:,.0f}) and claiming {claim_count} credits "
        f"({portfolio.currency} {claim_value:,.0f}) directly."
    )

    return OptimizationResult(
        total_value=round(total_value, 2),
        claim_value=round(claim_value, 2),
        transfer_value=round(transfer_value, 2),
        actions=actions,
        summary=summary,
        currency=portfolio.currency,
    )


# ── Transfer Documentation ────────────────────────────────────────────────────


async def generate_transfer_docs(
    db: AsyncSession,
    req: TransferDocRequest,
    org_id: uuid.UUID,
) -> GeneratedReport:
    tc = await db.execute(
        select(TaxCredit).where(
            TaxCredit.id == req.credit_id,
            TaxCredit.org_id == org_id,
            TaxCredit.is_deleted.is_(False),
        )
    )
    tc = tc.scalar_one_or_none()
    if not tc:
        raise LookupError(f"Tax credit {req.credit_id} not found")

    project = await db.get(Project, tc.project_id)
    project_name = project.name if project else "Project"

    report = GeneratedReport(
        org_id=org_id,
        title=f"Tax Credit Transfer Docs — {tc.credit_type} — {project_name}",
        status=ReportStatus.QUEUED,
        parameters={
            "credit_id": str(tc.id),
            "project_id": str(tc.project_id),
            "project_name": project_name,
            "credit_type": tc.credit_type,
            "estimated_value": str(tc.estimated_value),
            "currency": tc.currency,
            "transferee_name": req.transferee_name,
            "transferee_ein": req.transferee_ein,
            "transfer_price": str(req.transfer_price) if req.transfer_price else None,
        },
    )
    db.add(report)
    return report


# ── Summary ───────────────────────────────────────────────────────────────────


async def get_summary(
    db: AsyncSession, entity_id: uuid.UUID, org_id: uuid.UUID
) -> TaxCreditSummaryResponse:
    """Summary for a project or portfolio entity."""
    # Try project first
    project = await db.get(Project, entity_id)
    if project and project.org_id == org_id and not project.is_deleted:
        rows = await db.execute(
            select(TaxCredit).where(
                TaxCredit.project_id == entity_id,
                TaxCredit.org_id == org_id,
                TaxCredit.is_deleted.is_(False),
            )
        )
        credits = list(rows.scalars().all())
        return _build_summary(entity_id, "project", credits, project.name, project.currency)

    # Try portfolio
    portfolio = await db.execute(
        select(Portfolio).where(
            Portfolio.id == entity_id,
            Portfolio.org_id == org_id,
            Portfolio.is_deleted.is_(False),
        )
    )
    portfolio = portfolio.scalar_one_or_none()
    if portfolio:
        holdings_result = await db.execute(
            select(PortfolioHolding.project_id).where(
                PortfolioHolding.portfolio_id == entity_id,
                PortfolioHolding.project_id.isnot(None),
                PortfolioHolding.is_deleted.is_(False),
            )
        )
        project_ids = list(holdings_result.scalars().all())
        if project_ids:
            rows_result = await db.execute(
                select(TaxCredit).where(
                    TaxCredit.project_id.in_(project_ids),
                    TaxCredit.org_id == org_id,
                    TaxCredit.is_deleted.is_(False),
                )
            )
            credits = list(rows_result.scalars().all())
        else:
            credits = []
        return _build_summary(entity_id, "portfolio", credits, portfolio.name, portfolio.currency)

    raise LookupError(f"Entity {entity_id} not found")


def _build_summary(
    entity_id: uuid.UUID,
    entity_type: str,
    credits: list[TaxCredit],
    name: str,
    currency: str,
) -> TaxCreditSummaryResponse:
    total_estimated = sum(float(tc.estimated_value) for tc in credits)
    total_claimed = sum(
        float(tc.claimed_value) for tc in credits
        if tc.qualification == TaxCreditQualification.CLAIMED and tc.claimed_value
    )
    total_transferred = sum(
        float(tc.estimated_value) for tc in credits
        if tc.qualification == TaxCreditQualification.TRANSFERRED
    )
    by_qualification: dict[str, float] = {}
    by_credit_type: dict[str, float] = {}
    for tc in credits:
        q = tc.qualification.value
        by_qualification[q] = by_qualification.get(q, 0.0) + float(tc.estimated_value)
        by_credit_type[tc.credit_type] = (
            by_credit_type.get(tc.credit_type, 0.0) + float(tc.estimated_value)
        )

    return TaxCreditSummaryResponse(
        entity_id=entity_id,
        entity_type=entity_type,
        total_estimated=round(total_estimated, 2),
        total_claimed=round(total_claimed, 2),
        total_transferred=round(total_transferred, 2),
        by_qualification={k: round(v, 2) for k, v in by_qualification.items()},
        by_credit_type={k: round(v, 2) for k, v in by_credit_type.items()},
        credits=[_to_response(tc) for tc in credits],
        currency=currency,
    )
