"""Reporting API router: templates, report generation, schedules."""

import math
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.models.enums import ReportCategory, ReportStatus
from app.modules.reporting import service
from app.modules.reporting.schemas import (
    CreateScheduleRequest,
    GenerateReportAcceptedResponse,
    GenerateReportRequest,
    GeneratedReportListResponse,
    GeneratedReportResponse,
    OutputFormat,
    ReportTemplateListResponse,
    ReportTemplateResponse,
    ScheduledReportListResponse,
    ScheduledReportResponse,
    UpdateScheduleRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/reports", tags=["reports"])


# ── Helpers ─────────────────────────────────────────────────────────────────


def _template_to_response(t) -> ReportTemplateResponse:
    return ReportTemplateResponse(
        id=t.id,
        org_id=t.org_id,
        name=t.name,
        category=t.category,
        description=t.description,
        template_config=t.template_config,
        sections=t.sections,
        is_system=t.is_system,
        version=t.version,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _report_to_response(r, download_url: str | None = None) -> GeneratedReportResponse:
    return GeneratedReportResponse(
        id=r.id,
        org_id=r.org_id,
        template_id=r.template_id,
        title=r.title,
        status=r.status,
        parameters=r.parameters,
        result_data=r.result_data,
        s3_key=r.s3_key,
        error_message=r.error_message,
        generated_by=r.generated_by,
        completed_at=r.completed_at,
        download_url=download_url,
        template_name=r.template.name if r.template else None,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _schedule_to_response(s) -> ScheduledReportResponse:
    return ScheduledReportResponse(
        id=s.id,
        org_id=s.org_id,
        template_id=s.template_id,
        name=s.name,
        frequency=s.frequency,
        parameters=s.parameters,
        recipients=s.recipients,
        is_active=s.is_active,
        last_run_at=s.last_run_at,
        next_run_at=s.next_run_at,
        template_name=s.template.name if s.template else None,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


# ── Templates ───────────────────────────────────────────────────────────────


@router.get("/templates", response_model=ReportTemplateListResponse)
async def list_templates(
    category: ReportCategory | None = None,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    templates = await service.list_templates(db, current_user.org_id, category)
    return ReportTemplateListResponse(
        items=[_template_to_response(t) for t in templates],
        total=len(templates),
    )


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    template = await service.get_template(db, template_id, current_user.org_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


# ── Generate ────────────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=GenerateReportAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_report(
    body: GenerateReportRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    # Validate template
    template = await service.get_template(db, body.template_id, current_user.org_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    title = body.title or f"{template.name} — {body.output_format.value.upper()}"
    report = await service.create_generated_report(
        db, current_user, body.template_id, title, body.parameters, body.output_format,
    )
    await db.commit()

    # Dispatch Celery task
    try:
        from app.modules.reporting.tasks import generate_report_task

        generate_report_task.delay(str(report.id))
    except Exception:
        logger.warning("celery_dispatch_failed", report_id=str(report.id))

    return GenerateReportAcceptedResponse(
        report_id=report.id,
        status=ReportStatus.QUEUED,
        message=f"Report '{title}' queued for generation.",
    )


# ── Schedules ───────────────────────────────────────────────────────────────


@router.get("/schedules", response_model=ScheduledReportListResponse)
async def list_schedules(
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    schedules = await service.list_schedules(db, current_user.org_id)
    return ScheduledReportListResponse(
        items=[_schedule_to_response(s) for s in schedules],
        total=len(schedules),
    )


@router.post(
    "/schedules",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    body: CreateScheduleRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    # Validate template
    template = await service.get_template(db, body.template_id, current_user.org_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    schedule = await service.create_schedule(
        db,
        current_user,
        body.template_id,
        body.name,
        body.frequency,
        body.parameters,
        body.recipients,
        body.output_format,
    )
    await db.commit()
    # Reload with template
    await db.refresh(schedule, ["template"])
    return _schedule_to_response(schedule)


@router.put("/schedules/{schedule_id}", response_model=ScheduledReportResponse)
async def update_schedule(
    schedule_id: uuid.UUID,
    body: UpdateScheduleRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    schedule = await service.update_schedule(
        db,
        schedule_id,
        current_user.org_id,
        name=body.name,
        frequency=body.frequency,
        parameters=body.parameters,
        recipients=body.recipients,
        output_format=body.output_format,
        is_active=body.is_active,
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.commit()
    # Re-query after commit to get fresh data with eagerly loaded template
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.reporting import ScheduledReport as _ScheduledReport

    stmt = (
        select(_ScheduledReport)
        .options(selectinload(_ScheduledReport.template))
        .where(_ScheduledReport.id == schedule_id)
    )
    result = await db.execute(stmt)
    schedule = result.scalar_one()
    return _schedule_to_response(schedule)


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("delete", "report")),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_schedule(db, schedule_id, current_user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.commit()


# ── Generated Reports ───────────────────────────────────────────────────────


@router.get("", response_model=GeneratedReportListResponse)
async def list_reports(
    status_filter: ReportStatus | None = Query(None, alias="status"),
    template_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    reports, total = await service.list_generated_reports(
        db, current_user.org_id, status_filter, template_id, page, page_size,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return GeneratedReportListResponse(
        items=[_report_to_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{report_id}", response_model=GeneratedReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    report = await service.get_generated_report(db, report_id, current_user.org_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    download_url = None
    if report.status == ReportStatus.READY and report.s3_key:
        try:
            download_url = service.generate_download_url(report.s3_key)
        except Exception:
            logger.warning("presigned_url_failed", report_id=str(report_id))

    return _report_to_response(report, download_url)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("delete", "report")),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_generated_report(db, report_id, current_user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.commit()
