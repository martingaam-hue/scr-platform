"""Deal Intelligence service: pipeline, discovery, screening, comparison, memo."""

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AITaskLog
from app.models.enums import (
    AIAgentType,
    AITaskStatus,
    MatchStatus,
    ReportStatus,
)
from app.models.investors import InvestorMandate
from app.models.matching import MatchResult
from app.models.projects import Project, SignalScore
from app.models.reporting import GeneratedReport
from app.modules.deal_intelligence.schemas import (
    CompareResponse,
    CompareRow,
    DealCardResponse,
    DealPipelineResponse,
    DiscoveryDealResponse,
    DiscoveryResponse,
    MemoResponse,
    ScreeningReportResponse,
)
from app.modules.reporting.service import generate_download_url

logger = structlog.get_logger()

# MatchStatus → pipeline column mapping
_STATUS_TO_COLUMN: dict[MatchStatus, str] = {
    MatchStatus.SUGGESTED: "discovered",
    MatchStatus.VIEWED: "screening",
    MatchStatus.INTERESTED: "due_diligence",
    MatchStatus.INTRO_REQUESTED: "negotiation",
    MatchStatus.ENGAGED: "negotiation",
    MatchStatus.PASSED: "passed",
    MatchStatus.DECLINED: "passed",
}


# ── Latest SignalScore subquery helper ───────────────────────────────────────


async def _get_latest_signal_score(
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


# ── Alignment calculation (pure/deterministic) ───────────────────────────────


def _calc_alignment(
    project: Project,
    mandate: InvestorMandate | None,
    signal_score: SignalScore | None,
) -> tuple[int, list[str]]:
    """Compute alignment score (0-100) and reasons list."""
    score = 0
    reasons: list[str] = []

    if mandate is None:
        return score, reasons

    sectors = mandate.sectors or []
    geographies = mandate.geographies or []
    stages = mandate.stages or []

    # Sector match: 30 pts
    if project.project_type.value in sectors:
        score += 30
        reasons.append(f"Sector match: {project.project_type.value}")

    # Geography match: 20 pts
    if project.geography_country in geographies:
        score += 20
        reasons.append(f"Geography match: {project.geography_country}")

    # Stage match: 20 pts
    if project.stage.value in stages:
        score += 20
        reasons.append(f"Stage match: {project.stage.value}")

    # Ticket size in range: 20 pts
    investment = project.total_investment_required
    if (
        mandate.ticket_size_min <= investment <= mandate.ticket_size_max
    ):
        score += 20
        reasons.append("Investment size within mandate range")

    # Signal score ≥ 60: 10 pts
    if signal_score and signal_score.overall_score >= 60:
        score += 10
        reasons.append(f"Signal score {signal_score.overall_score}/100")

    return score, reasons


# ── Pipeline ─────────────────────────────────────────────────────────────────


async def get_deal_pipeline(
    db: AsyncSession,
    investor_org_id: uuid.UUID,
) -> DealPipelineResponse:
    """Load all MatchResults for investor and group by pipeline column."""
    stmt = (
        select(MatchResult, Project)
        .join(Project, MatchResult.project_id == Project.id)
        .where(
            MatchResult.investor_org_id == investor_org_id,
            Project.is_deleted.is_(False),
        )
        .order_by(MatchResult.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    columns: dict[str, list[DealCardResponse]] = {
        "discovered": [],
        "screening": [],
        "due_diligence": [],
        "negotiation": [],
        "passed": [],
    }

    # Load mandate for alignment scoring
    mandate = await _get_active_mandate(db, investor_org_id)

    for match, project in rows:
        signal_score = await _get_latest_signal_score(db, project.id)
        alignment_score, _ = _calc_alignment(project, mandate, signal_score)

        card = DealCardResponse(
            project_id=project.id,
            match_id=match.id,
            project_name=project.name,
            project_type=project.project_type.value,
            geography_country=project.geography_country,
            stage=project.stage.value,
            total_investment_required=str(project.total_investment_required),
            currency=project.currency,
            signal_score=signal_score.overall_score if signal_score else None,
            alignment_score=alignment_score,
            status=match.status.value,
            cover_image_url=project.cover_image_url,
            updated_at=match.updated_at,
        )
        column = _STATUS_TO_COLUMN.get(match.status, "discovered")
        columns[column].append(card)

    return DealPipelineResponse(**columns)


# ── Discovery ─────────────────────────────────────────────────────────────────


async def _get_active_mandate(
    db: AsyncSession, investor_org_id: uuid.UUID
) -> InvestorMandate | None:
    stmt = (
        select(InvestorMandate)
        .where(
            InvestorMandate.org_id == investor_org_id,
            InvestorMandate.is_active.is_(True),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_pipeline_project_ids(
    db: AsyncSession, investor_org_id: uuid.UUID
) -> set[uuid.UUID]:
    stmt = select(MatchResult.project_id).where(
        MatchResult.investor_org_id == investor_org_id
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


async def discover_deals(
    db: AsyncSession,
    investor_org_id: uuid.UUID,
    *,
    sector: str | None = None,
    geography: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
) -> DiscoveryResponse:
    """Discover published projects not yet in the investor's pipeline."""
    mandate = await _get_active_mandate(db, investor_org_id)
    pipeline_ids = await _get_pipeline_project_ids(db, investor_org_id)

    stmt = select(Project).where(
        Project.is_published.is_(True),
        Project.is_deleted.is_(False),
    )
    if sector:
        stmt = stmt.where(Project.project_type.in_([sector]))
    if geography:
        stmt = stmt.where(Project.geography_country.ilike(f"%{geography}%"))

    result = await db.execute(stmt)
    projects = result.scalars().all()

    items: list[DiscoveryDealResponse] = []
    for project in projects:
        is_in_pipeline = project.id in pipeline_ids
        signal_score = await _get_latest_signal_score(db, project.id)
        alignment_score, alignment_reasons = _calc_alignment(
            project, mandate, signal_score
        )

        ss_val = signal_score.overall_score if signal_score else None

        # Apply score filters
        if score_min is not None and (ss_val is None or ss_val < score_min):
            continue
        if score_max is not None and (ss_val is not None and ss_val > score_max):
            continue

        items.append(
            DiscoveryDealResponse(
                project_id=project.id,
                project_name=project.name,
                project_type=project.project_type.value,
                geography_country=project.geography_country,
                stage=project.stage.value,
                total_investment_required=str(project.total_investment_required),
                currency=project.currency,
                signal_score=ss_val,
                alignment_score=alignment_score,
                alignment_reasons=alignment_reasons,
                cover_image_url=project.cover_image_url,
                is_in_pipeline=is_in_pipeline,
            )
        )

    # Sort by alignment_score desc, limit 50
    items.sort(key=lambda x: x.alignment_score, reverse=True)
    items = items[:50]

    return DiscoveryResponse(
        items=items,
        total=len(items),
        mandate_name=mandate.name if mandate else None,
    )


# ── Screening ─────────────────────────────────────────────────────────────────


async def get_screening_report(
    db: AsyncSession,
    project_id: uuid.UUID,
    investor_org_id: uuid.UUID,
) -> ScreeningReportResponse | None:
    """Get latest screening report from AITaskLog."""
    stmt = (
        select(AITaskLog)
        .where(
            AITaskLog.entity_id == project_id,
            AITaskLog.agent_type == AIAgentType.MATCHING,
            AITaskLog.org_id == investor_org_id,
        )
        .order_by(AITaskLog.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    task_log = result.scalar_one_or_none()

    if not task_log:
        return None

    output = task_log.output_data or {}

    if task_log.status != AITaskStatus.COMPLETED:
        # Return partial response for pending/processing/failed
        return ScreeningReportResponse(
            task_log_id=task_log.id,
            project_id=project_id,
            fit_score=output.get("fit_score", 0),
            executive_summary=output.get("executive_summary", ""),
            strengths=output.get("strengths", []),
            risks=output.get("risks", []),
            key_metrics=output.get("key_metrics", []),
            mandate_alignment=output.get("mandate_alignment", []),
            recommendation=output.get("recommendation", ""),
            questions_to_ask=output.get("questions_to_ask", []),
            model_used=task_log.model_used or "",
            status=task_log.status.value,
            created_at=task_log.created_at,
        )

    return ScreeningReportResponse(
        task_log_id=task_log.id,
        project_id=uuid.UUID(str(output.get("project_id", project_id))),
        fit_score=output.get("fit_score", 0),
        executive_summary=output.get("executive_summary", ""),
        strengths=output.get("strengths", []),
        risks=output.get("risks", []),
        key_metrics=output.get("key_metrics", []),
        mandate_alignment=output.get("mandate_alignment", []),
        recommendation=output.get("recommendation", ""),
        questions_to_ask=output.get("questions_to_ask", []),
        model_used=task_log.model_used or "",
        status=task_log.status.value,
        created_at=task_log.created_at,
    )


async def trigger_screening(
    db: AsyncSession,
    project_id: uuid.UUID,
    investor_org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AITaskLog:
    """Create AITaskLog and dispatch screening Celery task."""
    from app.modules.deal_intelligence.tasks import screen_deal_task

    # Verify project exists and is published
    stmt = select(Project).where(
        Project.id == project_id,
        Project.is_published.is_(True),
        Project.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Published project {project_id} not found")

    task_log = AITaskLog(
        org_id=investor_org_id,
        agent_type=AIAgentType.MATCHING,
        entity_type="project",
        entity_id=project_id,
        status=AITaskStatus.PENDING,
        triggered_by=user_id,
        input_data={"project_id": str(project_id), "investor_org_id": str(investor_org_id)},
    )
    db.add(task_log)
    await db.flush()

    screen_deal_task.delay(
        str(project_id),
        str(investor_org_id),
        str(task_log.id),
    )

    return task_log


# ── Compare ──────────────────────────────────────────────────────────────────


async def compare_projects(
    db: AsyncSession,
    project_ids: list[uuid.UUID],
    investor_org_id: uuid.UUID,
) -> CompareResponse:
    """Build comparison matrix for given projects."""
    projects: list[Project] = []
    scores: list[SignalScore | None] = []

    for pid in project_ids:
        stmt = select(Project).where(
            Project.id == pid,
            Project.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        projects.append(project)
        scores.append(await _get_latest_signal_score(db, pid) if project else None)

    project_names = [p.name if p else "Unknown" for p in projects]

    def _best_worst(
        values: list, higher_is_better: bool = True
    ) -> tuple[int | None, int | None]:
        numeric = [(i, v) for i, v in enumerate(values) if v is not None]
        if len(numeric) < 2:
            return None, None
        sorted_vals = sorted(numeric, key=lambda x: x[1], reverse=higher_is_better)
        return sorted_vals[0][0], sorted_vals[-1][0]

    def _row(
        dimension: str,
        values: list,
        higher_is_better: bool = True,
    ) -> CompareRow:
        best, worst = _best_worst(values, higher_is_better)
        return CompareRow(
            dimension=dimension,
            values=values,
            best_index=best,
            worst_index=worst,
        )

    def _str_row(dimension: str, values: list) -> CompareRow:
        return CompareRow(
            dimension=dimension, values=values, best_index=None, worst_index=None
        )

    rows: list[CompareRow] = [
        _str_row("Project Type", [p.project_type.value if p else None for p in projects]),
        _str_row("Stage", [p.stage.value if p else None for p in projects]),
        _str_row("Geography", [p.geography_country if p else None for p in projects]),
        _row(
            "Investment Required",
            [int(p.total_investment_required) if p else None for p in projects],
            higher_is_better=False,
        ),
        _row("Signal Score", [s.overall_score if s else None for s in scores]),
        _row("Viability Score", [s.project_viability_score if s else None for s in scores]),
        _row("Financial Score", [s.financial_planning_score if s else None for s in scores]),
        _row("ESG Score", [s.esg_score if s else None for s in scores]),
        _row("Risk Score", [s.risk_assessment_score if s else None for s in scores]),
        _row("Team Score", [s.team_strength_score if s else None for s in scores]),
        _row(
            "Capacity (MW)",
            [
                float(p.capacity_mw) if p and p.capacity_mw else None
                for p in projects
            ],
        ),
    ]

    return CompareResponse(
        project_ids=project_ids,
        project_names=project_names,
        rows=rows,
    )


# ── Memo ─────────────────────────────────────────────────────────────────────


async def trigger_memo(
    db: AsyncSession,
    project_id: uuid.UUID,
    investor_org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GeneratedReport:
    """Create GeneratedReport and dispatch memo Celery task."""
    from app.modules.deal_intelligence.tasks import generate_memo_task

    stmt = select(Project).where(
        Project.id == project_id,
        Project.is_published.is_(True),
        Project.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Published project {project_id} not found")

    report = GeneratedReport(
        org_id=investor_org_id,
        template_id=None,
        title=f"Investment Memo — {project.name}",
        status=ReportStatus.QUEUED,
        parameters={"project_id": str(project_id)},
        generated_by=user_id,
    )
    db.add(report)
    await db.flush()

    generate_memo_task.delay(
        str(project_id),
        str(investor_org_id),
        str(report.id),
    )

    return report


async def get_memo(
    db: AsyncSession,
    project_id: uuid.UUID,
    memo_id: uuid.UUID,
    investor_org_id: uuid.UUID,
) -> MemoResponse | None:
    """Load memo from GeneratedReport."""
    stmt = select(GeneratedReport).where(
        GeneratedReport.id == memo_id,
        GeneratedReport.org_id == investor_org_id,
        GeneratedReport.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    if not report:
        return None

    download_url: str | None = None
    if report.status == ReportStatus.READY and report.s3_key:
        try:
            download_url = generate_download_url(report.s3_key)
        except Exception:
            pass

    result_data = report.result_data or {}
    content = result_data.get("content") if report.status == ReportStatus.READY else None

    return MemoResponse(
        memo_id=report.id,
        project_id=project_id,
        title=report.title,
        status=report.status.value,
        content=content,
        download_url=download_url,
        model_used=None,
        created_at=report.created_at,
    )


# ── Deal Status Update ────────────────────────────────────────────────────────


async def update_deal_status(
    db: AsyncSession,
    project_id: uuid.UUID,
    investor_org_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    notes: str | None,
) -> MatchResult:
    """Update or create a MatchResult for the given project/investor pair."""
    try:
        new_status = MatchStatus(status)
    except ValueError:
        raise ValueError(f"Invalid status: {status}")

    stmt = select(MatchResult).where(
        MatchResult.project_id == project_id,
        MatchResult.investor_org_id == investor_org_id,
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()

    if not match:
        # Load project to get ally_org_id
        proj_stmt = select(Project).where(Project.id == project_id)
        proj_result = await db.execute(proj_stmt)
        project = proj_result.scalar_one_or_none()
        if not project:
            raise LookupError(f"Project {project_id} not found")

        match = MatchResult(
            investor_org_id=investor_org_id,
            ally_org_id=project.org_id,
            project_id=project_id,
            overall_score=0,
            status=MatchStatus.SUGGESTED,
        )
        db.add(match)
        await db.flush()

    match.status = new_status
    if notes is not None:
        match.investor_notes = notes

    await db.flush()
    return match
