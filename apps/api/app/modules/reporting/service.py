"""Reporting service: template, generated report, and schedule business logic."""

import math
import uuid

import boto3
import structlog
from botocore.config import Config as BotoConfig
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.middleware.tenant import tenant_filter
from app.models.enums import ReportCategory, ReportFrequency, ReportStatus
from app.models.reporting import GeneratedReport, ReportTemplate, ScheduledReport
from app.modules.reporting.schemas import OutputFormat
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()


# ── S3 Client ────────────────────────────────────────────────────────────────


def _get_s3_client():
    """Create a boto3 S3 client configured for MinIO / AWS."""
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


# ── Template Service ─────────────────────────────────────────────────────────


async def list_templates(
    db: AsyncSession,
    org_id: uuid.UUID,
    category: ReportCategory | None = None,
) -> list[ReportTemplate]:
    """List templates: org-owned + system templates."""
    stmt = select(ReportTemplate).where(
        or_(
            ReportTemplate.org_id == org_id,
            ReportTemplate.is_system.is_(True),
        ),
        ReportTemplate.is_deleted.is_(False),
    )
    if category:
        stmt = stmt.where(ReportTemplate.category == category)
    stmt = stmt.order_by(ReportTemplate.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ReportTemplate | None:
    """Get a single template (system or org-owned)."""
    stmt = select(ReportTemplate).where(
        ReportTemplate.id == template_id,
        or_(
            ReportTemplate.org_id == org_id,
            ReportTemplate.is_system.is_(True),
        ),
        ReportTemplate.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Generated Report Service ─────────────────────────────────────────────────


async def list_generated_reports(
    db: AsyncSession,
    org_id: uuid.UUID,
    status: ReportStatus | None = None,
    template_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[GeneratedReport], int]:
    """List generated reports with pagination."""
    base = select(GeneratedReport).options(
        selectinload(GeneratedReport.template)
    )
    base = tenant_filter(base, org_id, GeneratedReport)
    base = base.where(GeneratedReport.is_deleted.is_(False))

    if status:
        base = base.where(GeneratedReport.status == status)
    if template_id:
        base = base.where(GeneratedReport.template_id == template_id)

    # Count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginate
    stmt = base.order_by(GeneratedReport.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_generated_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    org_id: uuid.UUID,
) -> GeneratedReport | None:
    """Get a single generated report with template loaded."""
    stmt = (
        select(GeneratedReport)
        .options(selectinload(GeneratedReport.template))
        .where(
            GeneratedReport.id == report_id,
            GeneratedReport.is_deleted.is_(False),
        )
    )
    stmt = tenant_filter(stmt, org_id, GeneratedReport)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_generated_report(
    db: AsyncSession,
    current_user: CurrentUser,
    template_id: uuid.UUID,
    title: str,
    parameters: dict,
    output_format: OutputFormat,
) -> GeneratedReport:
    """Create a QUEUED report record."""
    report = GeneratedReport(
        org_id=current_user.org_id,
        template_id=template_id,
        title=title,
        status=ReportStatus.QUEUED,
        parameters={**parameters, "output_format": output_format.value},
        generated_by=current_user.user_id,
    )
    db.add(report)
    await db.flush()
    return report


async def delete_generated_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """Soft-delete a generated report."""
    report = await get_generated_report(db, report_id, org_id)
    if not report:
        return False
    report.is_deleted = True
    await db.flush()
    return True


def generate_download_url(s3_key: str) -> str:
    """Generate a pre-signed S3 download URL."""
    s3 = _get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": s3_key,
        },
        ExpiresIn=3600,
    )


# ── Schedule Service ─────────────────────────────────────────────────────────


async def list_schedules(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[ScheduledReport]:
    """List all schedules for an org."""
    stmt = (
        select(ScheduledReport)
        .options(selectinload(ScheduledReport.template))
        .where(ScheduledReport.is_deleted.is_(False))
    )
    stmt = tenant_filter(stmt, org_id, ScheduledReport)
    stmt = stmt.order_by(ScheduledReport.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_schedule(
    db: AsyncSession,
    current_user: CurrentUser,
    template_id: uuid.UUID,
    name: str,
    frequency: ReportFrequency,
    parameters: dict,
    recipients: list[str],
    output_format: OutputFormat,
) -> ScheduledReport:
    """Create a new scheduled report."""
    schedule = ScheduledReport(
        org_id=current_user.org_id,
        template_id=template_id,
        name=name,
        frequency=frequency,
        parameters={**parameters, "output_format": output_format.value},
        recipients={"emails": recipients},
        is_active=True,
    )
    db.add(schedule)
    await db.flush()
    return schedule


async def update_schedule(
    db: AsyncSession,
    schedule_id: uuid.UUID,
    org_id: uuid.UUID,
    name: str | None = None,
    frequency: ReportFrequency | None = None,
    parameters: dict | None = None,
    recipients: list[str] | None = None,
    output_format: OutputFormat | None = None,
    is_active: bool | None = None,
) -> ScheduledReport | None:
    """Update a scheduled report."""
    stmt = (
        select(ScheduledReport)
        .options(selectinload(ScheduledReport.template))
        .where(
            ScheduledReport.id == schedule_id,
            ScheduledReport.is_deleted.is_(False),
        )
    )
    stmt = tenant_filter(stmt, org_id, ScheduledReport)
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        return None

    if name is not None:
        schedule.name = name
    if frequency is not None:
        schedule.frequency = frequency
    if parameters is not None:
        current_params = schedule.parameters or {}
        schedule.parameters = {**current_params, **parameters}
    if recipients is not None:
        schedule.recipients = {"emails": recipients}
    if output_format is not None:
        params = schedule.parameters or {}
        params["output_format"] = output_format.value
        schedule.parameters = params
    if is_active is not None:
        schedule.is_active = is_active

    await db.flush()
    return schedule


async def delete_schedule(
    db: AsyncSession,
    schedule_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """Soft-delete a scheduled report."""
    stmt = select(ScheduledReport).where(
        ScheduledReport.id == schedule_id,
        ScheduledReport.is_deleted.is_(False),
    )
    stmt = tenant_filter(stmt, org_id, ScheduledReport)
    result = await db.execute(stmt)
    schedule = result.scalar_one_or_none()
    if not schedule:
        return False
    schedule.is_deleted = True
    await db.flush()
    return True
