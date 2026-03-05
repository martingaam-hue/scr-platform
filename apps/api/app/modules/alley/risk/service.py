"""Alley-side Risk service — project holder view of project risks."""
from __future__ import annotations
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.projects import Project, SignalScore
from app.models.alley import RiskMitigationStatus
from app.modules.alley.risk.schemas import (
    DomainRiskItem,
    DomainRiskResponse,
    MitigationProgressResponse,
    ProjectRiskDetailResponse,
    ProjectRiskSummary,
    RiskItemSummary,
    RiskListResponse,
    RunCheckResponse,
)

logger = structlog.get_logger()

_SEVERITY_WEIGHTS = {"critical": 100, "high": 75, "medium": 50, "low": 25}
_DOMAINS = ["technical", "financial", "regulatory", "esg", "market"]


async def _get_project(db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
    stmt = select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")
    return project


def _extract_risks_from_score(score: SignalScore) -> list[dict]:
    """Extract risk items from the score's risk_assessment_details / score_factors."""
    risks = []
    gaps = score.gaps or {}

    risk_dims = ["risk_assessment", "regulatory", "esg"]
    item_id = 1
    for dim in risk_dims:
        dim_gaps = gaps.get(dim, []) if isinstance(gaps, dict) else []
        for gap in (dim_gaps if isinstance(dim_gaps, list) else []):
            if isinstance(gap, dict):
                severity = "high" if gap.get("priority") in ("critical", "high") else "medium"
                # Map to canonical domains
                canonical = {
                    "risk_assessment": "regulatory",
                    "regulatory": "regulatory",
                    "esg": "esg",
                }.get(dim, dim)
                risks.append({
                    "id": uuid.uuid5(score.project_id, f"{dim}_{item_id}"),
                    "title": gap.get("criterion_name", f"Risk {item_id}"),
                    "description": gap.get("recommendation", ""),
                    "severity": severity,
                    "dimension": canonical,
                    "source": "auto",
                })
                item_id += 1

    # If no gaps, synthesise from dimension scores
    if not risks:
        dim_map = {
            "technical": score.project_viability_score,
            "financial": score.financial_planning_score,
            "regulatory": score.risk_assessment_score,
            "esg": score.esg_score,
            "market": score.market_opportunity_score,
        }
        for dim_name, dim_score in dim_map.items():
            if dim_score is not None and dim_score < 60:
                severity = "critical" if dim_score < 40 else "high" if dim_score < 50 else "medium"
                risks.append({
                    "id": uuid.uuid5(score.project_id, dim_name),
                    "title": f"{dim_name.replace('_', ' ').title()} Risk",
                    "description": f"Score of {dim_score}/100 indicates areas requiring attention",
                    "severity": severity,
                    "dimension": dim_name,
                    "source": "auto",
                })
    return risks


def _calculate_risk_score(risks: list[dict], mitigation_map: dict) -> float:
    """Return 0–100 risk score: severity-weighted, reduced by mitigation progress."""
    if not risks:
        return 0.0
    total = 0.0
    for risk in risks:
        weight = _SEVERITY_WEIGHTS.get(risk["severity"], 25)
        rec = mitigation_map.get(str(risk["id"]))
        status = rec.status if rec else "unaddressed"
        if status in ("mitigated", "accepted"):
            weight = 0.0
        elif status == "in_progress":
            weight *= 0.5
        total += weight
    return round(total / len(risks), 1)


async def _get_mitigation_statuses(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> dict[str, RiskMitigationStatus]:
    result = await db.execute(
        select(RiskMitigationStatus).where(
            RiskMitigationStatus.project_id == project_id,
            RiskMitigationStatus.org_id == org_id,
        )
    )
    statuses = result.scalars().all()
    return {str(s.risk_item_id): s for s in statuses}


async def list_risk_summaries(db: AsyncSession, org_id: uuid.UUID) -> RiskListResponse:
    stmt = select(Project).where(Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    summaries = []
    portfolio_risk_scores = []
    total_auto = 0
    total_logged = 0

    for project in projects:
        score_result = await db.execute(
            select(SignalScore)
            .where(SignalScore.project_id == project.id)
            .order_by(SignalScore.version.desc())
            .limit(1)
        )
        score = score_result.scalar_one_or_none()
        if not score:
            continue

        risks = _extract_risks_from_score(score)
        mitigation_map = await _get_mitigation_statuses(db, project.id, org_id)

        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        addressed = 0
        for risk in risks:
            counts[risk["severity"]] = counts.get(risk["severity"], 0) + 1
            status_rec = mitigation_map.get(str(risk["id"]))
            if status_rec and status_rec.status in ("mitigated", "accepted"):
                addressed += 1

        auto_count = sum(1 for r in risks if r.get("source") == "auto")
        logged_count = sum(1 for r in risks if r.get("source") == "logged")
        total_auto += auto_count
        total_logged += logged_count

        total = len(risks)
        progress = int((addressed / total) * 100) if total > 0 else 0
        risk_score = _calculate_risk_score(risks, mitigation_map)
        portfolio_risk_scores.append(risk_score)

        summaries.append(ProjectRiskSummary(
            project_id=project.id,
            project_name=project.name,
            total_risks=total,
            critical_count=counts.get("critical", 0),
            high_count=counts.get("high", 0),
            medium_count=counts.get("medium", 0),
            low_count=counts.get("low", 0),
            mitigation_progress_pct=progress,
            overall_risk_score=risk_score,
            auto_identified_count=auto_count,
            logged_count=logged_count,
        ))

    portfolio_risk_score = (
        round(sum(portfolio_risk_scores) / len(portfolio_risk_scores), 1)
        if portfolio_risk_scores else 0.0
    )
    return RiskListResponse(
        items=summaries,
        total=len(summaries),
        portfolio_risk_score=portfolio_risk_score,
        total_auto_identified=total_auto,
        total_logged=total_logged,
    )


async def get_project_risk_detail(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> ProjectRiskDetailResponse:
    project = await _get_project(db, project_id, org_id)
    score_result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    score = score_result.scalar_one_or_none()
    if not score:
        raise LookupError("No score calculated yet — risk profile not available")

    risks = _extract_risks_from_score(score)
    mitigation_map = await _get_mitigation_statuses(db, project_id, org_id)

    items = []
    addressed = 0
    for risk in risks:
        status_rec = mitigation_map.get(str(risk["id"]))
        status = status_rec.status if status_rec else "unaddressed"
        if status in ("mitigated", "accepted"):
            addressed += 1
        items.append(RiskItemSummary(
            id=risk["id"],
            title=risk["title"],
            description=risk["description"],
            severity=risk["severity"],
            dimension=risk["dimension"],
            mitigation_status=status,
            guidance=status_rec.guidance if status_rec else None,
            evidence_document_ids=list(status_rec.evidence_document_ids or []) if status_rec else [],
            notes=status_rec.notes if status_rec else None,
            source=risk.get("source", "auto"),
        ))

    total = len(items)
    risk_score = _calculate_risk_score(risks, mitigation_map)
    return ProjectRiskDetailResponse(
        project_id=project_id,
        project_name=project.name,
        risk_items=items,
        total_risks=total,
        addressed_risks=addressed,
        mitigation_progress_pct=int((addressed / total) * 100) if total > 0 else 0,
        overall_risk_score=risk_score,
    )


async def get_domain_breakdown(db: AsyncSession, org_id: uuid.UUID) -> DomainRiskResponse:
    """Return risk breakdown by domain across all org projects."""
    stmt = select(Project).where(Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    domain_counts: dict[str, dict] = {
        d: {"critical": 0, "high": 0, "medium": 0, "low": 0, "weighted": 0.0, "n": 0}
        for d in _DOMAINS
    }

    for project in projects:
        score_result = await db.execute(
            select(SignalScore)
            .where(SignalScore.project_id == project.id)
            .order_by(SignalScore.version.desc())
            .limit(1)
        )
        score = score_result.scalar_one_or_none()
        if not score:
            continue

        risks = _extract_risks_from_score(score)
        mitigation_map = await _get_mitigation_statuses(db, project.id, org_id)

        for risk in risks:
            dom = risk["dimension"] if risk["dimension"] in _DOMAINS else "technical"
            bucket = domain_counts[dom]
            bucket[risk["severity"]] = bucket.get(risk["severity"], 0) + 1
            bucket["n"] += 1
            # Weighted contribution (mitigation-adjusted)
            rec = mitigation_map.get(str(risk["id"]))
            status = rec.status if rec else "unaddressed"
            w = _SEVERITY_WEIGHTS.get(risk["severity"], 25)
            if status in ("mitigated", "accepted"):
                w = 0.0
            elif status == "in_progress":
                w *= 0.5
            bucket["weighted"] += w

    domains = []
    all_scores = []
    for dom in _DOMAINS:
        bucket = domain_counts[dom]
        n = bucket["n"]
        score = round(bucket["weighted"] / n, 1) if n > 0 else 0.0
        all_scores.append(score)
        domains.append(DomainRiskItem(
            domain=dom,
            risk_score=score,
            critical_count=bucket.get("critical", 0),
            high_count=bucket.get("high", 0),
            medium_count=bucket.get("medium", 0),
            low_count=bucket.get("low", 0),
            total=n,
        ))

    portfolio_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
    return DomainRiskResponse(domains=domains, portfolio_risk_score=portfolio_score)


async def run_risk_check(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> RunCheckResponse:
    """Re-derive risks from the latest signal score and return a task_id placeholder."""
    await _get_project(db, project_id, org_id)
    # Risks are derived on-the-fly from SignalScore.gaps — no separate task needed.
    # Return a synthetic task_id so the UI can poll if needed.
    task_id = str(uuid.uuid4())
    return RunCheckResponse(
        task_id=task_id,
        message="Risk check complete — risks refreshed from latest signal score",
    )


async def update_mitigation_status(
    db: AsyncSession,
    project_id: uuid.UUID,
    risk_id: uuid.UUID,
    org_id: uuid.UUID,
    status: str,
    notes: str | None,
) -> RiskMitigationStatus:
    await _get_project(db, project_id, org_id)
    result = await db.execute(
        select(RiskMitigationStatus).where(
            RiskMitigationStatus.project_id == project_id,
            RiskMitigationStatus.risk_item_id == risk_id,
            RiskMitigationStatus.org_id == org_id,
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        rec = RiskMitigationStatus(
            project_id=project_id,
            risk_item_id=risk_id,
            org_id=org_id,
            status=status,
            notes=notes,
            evidence_document_ids=[],
        )
        db.add(rec)
    else:
        rec.status = status
        if notes is not None:
            rec.notes = notes
    await db.commit()
    await db.refresh(rec)
    return rec


async def add_evidence(
    db: AsyncSession,
    project_id: uuid.UUID,
    risk_id: uuid.UUID,
    org_id: uuid.UUID,
    document_id: uuid.UUID,
) -> RiskMitigationStatus:
    await _get_project(db, project_id, org_id)
    result = await db.execute(
        select(RiskMitigationStatus).where(
            RiskMitigationStatus.project_id == project_id,
            RiskMitigationStatus.risk_item_id == risk_id,
            RiskMitigationStatus.org_id == org_id,
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        rec = RiskMitigationStatus(
            project_id=project_id,
            risk_item_id=risk_id,
            org_id=org_id,
            status="acknowledged",
            evidence_document_ids=[document_id],
        )
        db.add(rec)
    else:
        existing = list(rec.evidence_document_ids or [])
        if document_id not in existing:
            existing.append(document_id)
        rec.evidence_document_ids = existing
    await db.commit()
    await db.refresh(rec)
    return rec


async def get_mitigation_progress(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> MitigationProgressResponse:
    project = await _get_project(db, project_id, org_id)
    score_result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    score = score_result.scalar_one_or_none()
    if not score:
        return MitigationProgressResponse(
            project_id=project_id, total_risks=0, addressed=0,
            in_progress=0, mitigated=0, accepted=0, unaddressed=0, progress_pct=0,
        )

    risks = _extract_risks_from_score(score)
    mitigation_map = await _get_mitigation_statuses(db, project_id, org_id)

    counts: dict[str, int] = {"acknowledged": 0, "in_progress": 0, "mitigated": 0, "accepted": 0, "unaddressed": 0}
    for risk in risks:
        rec = mitigation_map.get(str(risk["id"]))
        status = rec.status if rec else "unaddressed"
        counts[status] = counts.get(status, 0) + 1

    total = len(risks)
    addressed = counts["mitigated"] + counts["accepted"]
    return MitigationProgressResponse(
        project_id=project_id,
        total_risks=total,
        addressed=addressed,
        in_progress=counts["in_progress"],
        mitigated=counts["mitigated"],
        accepted=counts["accepted"],
        unaddressed=counts["unaddressed"],
        progress_pct=int((addressed / total) * 100) if total > 0 else 0,
    )
