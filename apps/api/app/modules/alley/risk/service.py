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
    MitigationProgressResponse,
    ProjectRiskDetailResponse,
    ProjectRiskSummary,
    RiskItemSummary,
)

logger = structlog.get_logger()


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
    details = score.scoring_details or {}
    # Try to find risk items in score_factors or gaps
    factors = score.score_factors or {}
    gaps = score.gaps or {}

    risk_dims = ["risk_assessment", "regulatory", "esg"]
    item_id = 1
    for dim in risk_dims:
        dim_gaps = gaps.get(dim, []) if isinstance(gaps, dict) else []
        for gap in (dim_gaps if isinstance(dim_gaps, list) else []):
            if isinstance(gap, dict):
                severity = "high" if gap.get("priority") in ("critical", "high") else "medium"
                risks.append({
                    "id": uuid.uuid5(score.project_id, f"{dim}_{item_id}"),
                    "title": gap.get("criterion_name", f"Risk {item_id}"),
                    "description": gap.get("recommendation", ""),
                    "severity": severity,
                    "dimension": dim,
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
            if dim_score < 60:
                severity = "critical" if dim_score < 40 else "high" if dim_score < 50 else "medium"
                risks.append({
                    "id": uuid.uuid5(score.project_id, dim_name),
                    "title": f"{dim_name.replace('_', ' ').title()} Risk",
                    "description": f"Score of {dim_score}/100 indicates areas requiring attention",
                    "severity": severity,
                    "dimension": dim_name,
                })
    return risks


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


async def list_risk_summaries(db: AsyncSession, org_id: uuid.UUID) -> list[ProjectRiskSummary]:
    stmt = select(Project).where(Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    projects = result.scalars().all()

    summaries = []
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

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        addressed = 0
        for risk in risks:
            counts[risk["severity"]] = counts.get(risk["severity"], 0) + 1
            status_rec = mitigation_map.get(str(risk["id"]))
            if status_rec and status_rec.status in ("mitigated", "accepted"):
                addressed += 1

        total = len(risks)
        progress = int((addressed / total) * 100) if total > 0 else 0

        summaries.append(ProjectRiskSummary(
            project_id=project.id,
            project_name=project.name,
            total_risks=total,
            critical_count=counts.get("critical", 0),
            high_count=counts.get("high", 0),
            medium_count=counts.get("medium", 0),
            low_count=counts.get("low", 0),
            mitigation_progress_pct=progress,
        ))
    return summaries


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
        ))

    total = len(items)
    return ProjectRiskDetailResponse(
        project_id=project_id,
        project_name=project.name,
        risk_items=items,
        total_risks=total,
        addressed_risks=addressed,
        mitigation_progress_pct=int((addressed / total) * 100) if total > 0 else 0,
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

    counts = {"acknowledged": 0, "in_progress": 0, "mitigated": 0, "accepted": 0, "unaddressed": 0}
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
