"""Celery tasks for async report generation."""

import uuid
from datetime import datetime, timezone

import structlog
from celery import Celery
from sqlalchemy import select

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("reporting", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ── Data Fetching ────────────────────────────────────────────────────────────


def _fetch_report_data(session, org_id: uuid.UUID, template, parameters: dict) -> dict:
    """Fetch data from DB based on template sections and parameters."""
    from app.models.investors import Portfolio, PortfolioHolding, PortfolioMetrics
    from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone

    data: dict = {
        "title": parameters.get("title", template.name),
        "parameters": parameters,
    }
    sections_config = template.sections or []
    section_names = [s.get("name", "") if isinstance(s, dict) else s for s in sections_config]

    # Portfolio-related sections
    portfolio_sections = {
        "portfolio_performance", "performance_summary", "holdings_detail",
        "nav_summary", "cash_flows", "attribution", "benchmark_comparison",
        "investment_thesis", "financial_analysis", "risk_assessment",
        "recommendation", "executive_summary",
    }
    if portfolio_sections & set(section_names):
        portfolio_id = parameters.get("portfolio_id")
        if portfolio_id:
            portfolio = session.execute(
                select(Portfolio).where(
                    Portfolio.id == uuid.UUID(portfolio_id),
                    Portfolio.org_id == org_id,
                    Portfolio.is_deleted.is_(False),
                )
            ).scalar_one_or_none()
            if portfolio:
                data["portfolio_performance"] = portfolio.to_dict()
                data["performance_summary"] = portfolio.to_dict()
                data["nav_summary"] = {
                    "name": portfolio.name,
                    "current_aum": str(portfolio.current_aum),
                    "target_aum": str(portfolio.target_aum),
                    "currency": portfolio.currency,
                    "strategy": portfolio.strategy.value,
                }

                holdings = session.execute(
                    select(PortfolioHolding).where(
                        PortfolioHolding.portfolio_id == portfolio.id,
                        PortfolioHolding.is_deleted.is_(False),
                    )
                ).scalars().all()
                data["holdings_detail"] = [h.to_dict() for h in holdings]

                metrics = session.execute(
                    select(PortfolioMetrics)
                    .where(PortfolioMetrics.portfolio_id == portfolio.id)
                    .order_by(PortfolioMetrics.as_of_date.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if metrics:
                    data["attribution"] = metrics.to_dict()
        else:
            # All portfolios for org
            portfolios = session.execute(
                select(Portfolio).where(
                    Portfolio.org_id == org_id,
                    Portfolio.is_deleted.is_(False),
                )
            ).scalars().all()
            data["portfolio_performance"] = [p.to_dict() for p in portfolios]
            data["performance_summary"] = [p.to_dict() for p in portfolios]

    # Project-related sections
    project_sections = {
        "project_overview", "milestones", "budget_summary", "signal_score",
        "recent_activity", "project_highlights",
    }
    if project_sections & set(section_names):
        project_id = parameters.get("project_id")
        if project_id:
            project = session.execute(
                select(Project).where(
                    Project.id == uuid.UUID(project_id),
                    Project.org_id == org_id,
                    Project.is_deleted.is_(False),
                )
            ).scalar_one_or_none()
            if project:
                data["project_overview"] = project.to_dict()
                data["project_highlights"] = project.to_dict()

                milestones = session.execute(
                    select(ProjectMilestone).where(
                        ProjectMilestone.project_id == project.id,
                        ProjectMilestone.is_deleted.is_(False),
                    )
                ).scalars().all()
                data["milestones"] = [m.to_dict() for m in milestones]

                budget_items = session.execute(
                    select(ProjectBudgetItem).where(
                        ProjectBudgetItem.project_id == project.id,
                        ProjectBudgetItem.is_deleted.is_(False),
                    )
                ).scalars().all()
                data["budget_summary"] = [b.to_dict() for b in budget_items]
        else:
            projects = session.execute(
                select(Project).where(
                    Project.org_id == org_id,
                    Project.is_deleted.is_(False),
                )
            ).scalars().all()
            data["project_overview"] = [p.to_dict() for p in projects]
            data["project_highlights"] = [p.to_dict() for p in projects]

    # Fill missing section keys with empty data
    for name in section_names:
        if name not in data:
            data[name] = {}

    return data


# ── Report Generation Task ──────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_report_task(self, report_id: str) -> dict:
    """Generate a report asynchronously.

    Steps:
      1. Load GeneratedReport record
      2. Update status → GENERATING
      3. Load template config + org settings
      4. Fetch data based on template sections
      5. Select generator based on output_format
      6. Generate file bytes
      7. Upload to S3
      8. Update report: status=READY, s3_key, completed_at
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    import boto3
    from botocore.config import Config as BotoConfig

    from app.models.core import Organization
    from app.models.enums import ReportStatus
    from app.models.reporting import GeneratedReport, ReportTemplate
    from app.modules.reporting.generators import PDFGenerator, PPTXGenerator, XLSXGenerator

    engine = create_engine(settings.DATABASE_URL_SYNC)
    report_uuid = uuid.UUID(report_id)

    with SyncSession(engine) as session:
        report = session.get(GeneratedReport, report_uuid)
        if not report:
            logger.error("report_not_found", report_id=report_id)
            return {"status": "error", "detail": "Report not found"}

        try:
            # Step 2: Update status
            report.status = ReportStatus.GENERATING
            session.commit()

            # Step 3: Load template and org settings
            template = session.get(ReportTemplate, report.template_id) if report.template_id else None
            template_config = template.template_config if template else {}
            sections_config = template.sections if template else []
            if isinstance(sections_config, dict):
                sections_config = sections_config.get("sections", [])

            org = session.get(Organization, report.org_id)
            org_settings = {
                "org_name": org.name if org else "SCR Platform",
                "brand_color": (org.settings or {}).get("brand_color", "#1E3A5F") if org else "#1E3A5F",
                "logo_url": (org.settings or {}).get("logo_url") if org else None,
            }

            # Step 4: Fetch data
            parameters = report.parameters or {}
            data = _fetch_report_data(session, report.org_id, template, parameters)
            data["title"] = report.title

            # Step 5: Select generator
            output_format = parameters.get("output_format", "pdf")
            generators = {
                "pdf": PDFGenerator,
                "xlsx": XLSXGenerator,
                "pptx": PPTXGenerator,
            }
            generator_cls = generators.get(output_format, PDFGenerator)
            generator = generator_cls(template_config, org_settings)

            # Normalize sections for generator
            sections = []
            for s in sections_config:
                if isinstance(s, str):
                    sections.append({"name": s})
                elif isinstance(s, dict):
                    sections.append(s)

            if not sections:
                sections = [{"name": k} for k in data.keys() if k not in ("title", "parameters")]

            # Step 6: Generate
            file_bytes, content_type = generator.generate(data, sections)

            # Step 7: Upload to S3
            ext_map = {"pdf": "html", "xlsx": "xlsx", "pptx": "pptx"}
            ext = ext_map.get(output_format, "html")
            s3_key = f"{report.org_id}/reports/{report.id}_{report.title[:50]}.{ext}"

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
                config=BotoConfig(signature_version="s3v4"),
            )
            s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )

            # Step 8: Update report
            report.status = ReportStatus.READY
            report.s3_key = s3_key
            report.result_data = {
                "file_size": len(file_bytes),
                "content_type": content_type,
                "sections_generated": len(sections),
            }
            report.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(
                "report_generated",
                report_id=report_id,
                format=output_format,
                size=len(file_bytes),
            )
            return {"status": "success", "s3_key": s3_key}

        except Exception as exc:
            session.rollback()
            # Update error status in fresh session
            with SyncSession(engine) as err_session:
                err_report = err_session.get(GeneratedReport, report_uuid)
                if err_report:
                    err_report.status = ReportStatus.ERROR
                    err_report.error_message = str(exc)[:1000]
                    err_session.commit()

            logger.error(
                "report_generation_failed",
                report_id=report_id,
                error=str(exc),
            )
            raise self.retry(exc=exc)
