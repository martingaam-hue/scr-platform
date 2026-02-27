"""Celery tasks for Deal Intelligence: screening and memo generation."""

import json
import uuid
from datetime import datetime, timezone

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("deal_intelligence", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 0; }}
  .header {{ background: #1E3A5F; color: white; padding: 2rem 3rem; }}
  .header h1 {{ margin: 0; font-size: 1.8rem; }}
  .header p {{ margin: 0.5rem 0 0; opacity: 0.8; font-size: 0.9rem; }}
  .content {{ padding: 2rem 3rem; max-width: 900px; }}
  h2 {{ color: #1E3A5F; border-bottom: 2px solid #E5E7EB; padding-bottom: 0.5rem; }}
  h3 {{ color: #374151; }}
  .badge {{ display: inline-block; padding: 0.2rem 0.75rem; border-radius: 9999px;
            font-size: 0.75rem; font-weight: 600; background: #DBEAFE; color: #1E40AF; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
  th {{ background: #F3F4F6; padding: 0.5rem 1rem; text-align: left; font-size: 0.85rem; }}
  td {{ padding: 0.5rem 1rem; border-bottom: 1px solid #E5E7EB; font-size: 0.875rem; }}
  .footer {{ background: #F9FAFB; padding: 1rem 3rem; font-size: 0.75rem; color: #6B7280;
             border-top: 1px solid #E5E7EB; margin-top: 3rem; }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <p>SCR Platform — Investment Intelligence Report &nbsp;|&nbsp; Generated {date}</p>
</div>
<div class="content">
{body}
</div>
<div class="footer">
  Confidential — This document is prepared for accredited investors only.
  SCR Platform &copy; {year}
</div>
</body>
</html>"""


def _parse_json_from_content(content: str) -> dict:
    """Extract JSON from AI response, handling markdown code fences."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last fence lines
        inner = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        return json.loads(inner)
    return json.loads(content)


# ── Screen Deal Task ─────────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def screen_deal_task(
    self,
    project_id: str,
    investor_org_id: str,
    task_log_id: str,
) -> dict:
    """AI-powered deal screening pipeline.

    Steps:
      1. Load AITaskLog → PROCESSING
      2. Load Project, SignalScore, InvestorMandate, DocumentExtractions
      3. Build screening prompt
      4. Call AI Gateway
      5. Parse JSON response
      6. Store in task_log.output_data
      7. task_log.status = COMPLETED
    """
    import time

    import httpx
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session as SyncSession

    from app.models.ai import AITaskLog
    from app.models.enums import AIAgentType, AITaskStatus
    from app.models.investors import InvestorMandate
    from app.models.projects import Project, SignalScore

    engine = create_engine(settings.DATABASE_URL_SYNC)
    task_log_uuid = uuid.UUID(task_log_id)
    project_uuid = uuid.UUID(project_id)
    investor_uuid = uuid.UUID(investor_org_id)
    start_time = time.time()

    with SyncSession(engine) as session:
        task_log = session.get(AITaskLog, task_log_uuid)
        if not task_log:
            logger.error("task_log_not_found", task_log_id=task_log_id)
            return {"status": "error", "detail": "Task log not found"}

        try:
            task_log.status = AITaskStatus.PROCESSING
            session.commit()

            # Load project
            project = session.execute(
                select(Project).where(Project.id == project_uuid)
            ).scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Load latest signal score
            signal_score = session.execute(
                select(SignalScore)
                .where(SignalScore.project_id == project_uuid)
                .order_by(SignalScore.version.desc())
                .limit(1)
            ).scalar_one_or_none()

            # Load investor mandate
            mandate = session.execute(
                select(InvestorMandate).where(
                    InvestorMandate.org_id == investor_uuid,
                    InvestorMandate.is_active.is_(True),
                ).limit(1)
            ).scalar_one_or_none()

            # Load document extractions text (via sync query on dataroom tables)
            from app.models.dataroom import Document, DocumentExtraction
            doc_ids = session.execute(
                select(Document.id).where(
                    Document.project_id == project_uuid,
                    Document.is_deleted.is_(False),
                )
            ).scalars().all()

            extraction_parts: list[str] = []
            if doc_ids:
                extractions = session.execute(
                    select(DocumentExtraction).where(
                        DocumentExtraction.document_id.in_(doc_ids),
                    ).limit(30)
                ).scalars().all()
                for ext in extractions:
                    if ext.extraction_data:
                        extraction_parts.append(
                            f"[{ext.extraction_type.value}] {json.dumps(ext.extraction_data)[:500]}"
                        )

            extraction_text = "\n".join(extraction_parts)[:6000] if extraction_parts else "No documents available."

            # Build prompt
            ss_overall = signal_score.overall_score if signal_score else "N/A"
            ss_tech = signal_score.technical_score if signal_score else "N/A"
            ss_fin = signal_score.financial_score if signal_score else "N/A"
            ss_esg = signal_score.esg_score if signal_score else "N/A"

            mandate_text = "No active mandate."
            if mandate:
                mandate_text = (
                    f"Sectors: {mandate.sectors or 'Any'} | "
                    f"Geographies: {mandate.geographies or 'Any'} | "
                    f"Stages: {mandate.stages or 'Any'} | "
                    f"Ticket: {mandate.ticket_size_min}–{mandate.ticket_size_max} {project.currency} | "
                    f"Risk Tolerance: {mandate.risk_tolerance.value}"
                )

            prompt = (
                f"You are evaluating a {project.project_type.value} project in "
                f"{project.geography_country} for an investor.\n\n"
                f"PROJECT: {project.name} | Stage: {project.stage.value} | "
                f"Investment: {project.total_investment_required} {project.currency}\n"
                f"{project.description[:1000]}\n\n"
                f"SIGNAL SCORE: {ss_overall}/100 "
                f"(Technical: {ss_tech}, Financial: {ss_fin}, ESG: {ss_esg})\n\n"
                f"INVESTOR MANDATE:\n{mandate_text}\n\n"
                f"DOCUMENT EXTRACTIONS:\n{extraction_text}\n\n"
                'Respond ONLY with valid JSON:\n'
                '{"fit_score": <0-100>, "executive_summary": "...", '
                '"strengths": [...], "risks": [...], '
                '"key_metrics": [{"label": "...", "value": "..."}], '
                '"mandate_alignment": [{"criterion": "...", "met": true/false, "notes": "..."}], '
                '"recommendation": "proceed|pass|need_more_info", '
                '"questions_to_ask": [...]}'
            )

            # Call AI Gateway
            response = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "prompt": prompt,
                    "task_type": "analysis",
                    "max_tokens": 2048,
                    "temperature": 0.3,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=120.0,
            )
            response.raise_for_status()
            resp_data = response.json()
            content = resp_data.get("content") or resp_data.get("choices", [{}])[0].get("text", "")

            parsed = _parse_json_from_content(content)
            parsed["project_id"] = str(project_id)
            parsed.setdefault("fit_score", 0)
            parsed.setdefault("recommendation", "need_more_info")

            elapsed_ms = int((time.time() - start_time) * 1000)
            task_log.status = AITaskStatus.COMPLETED
            task_log.output_data = parsed
            task_log.model_used = resp_data.get("model", "claude-sonnet-4-6")
            task_log.processing_time_ms = elapsed_ms
            session.commit()

            logger.info(
                "screen_deal_task_completed",
                project_id=project_id,
                fit_score=parsed.get("fit_score"),
                elapsed_ms=elapsed_ms,
            )
            return {"status": "success", "fit_score": parsed.get("fit_score")}

        except Exception as exc:
            session.rollback()
            with SyncSession(engine) as err_session:
                err_log = err_session.get(AITaskLog, task_log_uuid)
                if err_log:
                    err_log.status = AITaskStatus.FAILED
                    err_log.error_message = str(exc)[:1000]
                    err_log.processing_time_ms = int((time.time() - start_time) * 1000)
                    err_session.commit()

            logger.error(
                "screen_deal_task_failed",
                project_id=project_id,
                task_log_id=task_log_id,
                error=str(exc),
            )
            raise self.retry(exc=exc)


# ── Generate Memo Task ───────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_memo_task(
    self,
    project_id: str,
    investor_org_id: str,
    report_id: str,
) -> dict:
    """Generate investment memo as HTML and upload to S3.

    Steps:
      1. Load GeneratedReport → GENERATING
      2. Load Project, SignalScore, InvestorMandate, extractions
      3. Build memo prompt
      4. Call AI Gateway
      5. Wrap in HTML template
      6. Upload to S3
      7. report.status = READY
    """
    import time

    import boto3
    import httpx
    from botocore.config import Config as BotoConfig
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session as SyncSession

    from app.models.enums import ReportStatus
    from app.models.investors import InvestorMandate
    from app.models.projects import Project, SignalScore
    from app.models.reporting import GeneratedReport

    engine = create_engine(settings.DATABASE_URL_SYNC)
    report_uuid = uuid.UUID(report_id)
    project_uuid = uuid.UUID(project_id)
    investor_uuid = uuid.UUID(investor_org_id)
    start_time = time.time()

    with SyncSession(engine) as session:
        report = session.get(GeneratedReport, report_uuid)
        if not report:
            logger.error("report_not_found", report_id=report_id)
            return {"status": "error", "detail": "Report not found"}

        try:
            report.status = ReportStatus.GENERATING
            session.commit()

            # Load project
            project = session.execute(
                select(Project).where(Project.id == project_uuid)
            ).scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Load signal score
            signal_score = session.execute(
                select(SignalScore)
                .where(SignalScore.project_id == project_uuid)
                .order_by(SignalScore.version.desc())
                .limit(1)
            ).scalar_one_or_none()

            # Load mandate
            mandate = session.execute(
                select(InvestorMandate).where(
                    InvestorMandate.org_id == investor_uuid,
                    InvestorMandate.is_active.is_(True),
                ).limit(1)
            ).scalar_one_or_none()

            # Load extractions
            from app.models.dataroom import Document, DocumentExtraction
            doc_ids = session.execute(
                select(Document.id).where(
                    Document.project_id == project_uuid,
                    Document.is_deleted.is_(False),
                )
            ).scalars().all()

            extraction_parts: list[str] = []
            if doc_ids:
                extractions = session.execute(
                    select(DocumentExtraction).where(
                        DocumentExtraction.document_id.in_(doc_ids),
                    ).limit(40)
                ).scalars().all()
                for ext in extractions:
                    if ext.extraction_data:
                        extraction_parts.append(
                            f"[{ext.extraction_type.value}] {json.dumps(ext.extraction_data)[:400]}"
                        )

            extraction_text = "\n".join(extraction_parts)[:8000] if extraction_parts else "No documents available."

            ss_overall = signal_score.overall_score if signal_score else "N/A"
            mandate_text = "No active mandate on file." if not mandate else (
                f"Sectors: {mandate.sectors or 'Any'} | "
                f"Geographies: {mandate.geographies or 'Any'} | "
                f"Ticket: {mandate.ticket_size_min}–{mandate.ticket_size_max} {project.currency}"
            )

            prompt = (
                f"Write a professional investment memorandum for the following project. "
                f"Use investment banking prose. Structure with exactly these 8 sections:\n\n"
                f"1. Executive Summary\n"
                f"2. Investment Thesis\n"
                f"3. Market Opportunity\n"
                f"4. Financial Analysis\n"
                f"5. Risk Assessment\n"
                f"6. ESG & Impact\n"
                f"7. Key Terms\n"
                f"8. Recommendation\n\n"
                f"PROJECT: {project.name}\n"
                f"Type: {project.project_type.value} | Country: {project.geography_country} | "
                f"Stage: {project.stage.value}\n"
                f"Investment Required: {project.total_investment_required} {project.currency}\n"
                f"Description: {project.description[:1500]}\n\n"
                f"SIGNAL SCORE: {ss_overall}/100\n\n"
                f"INVESTOR MANDATE: {mandate_text}\n\n"
                f"DOCUMENT EXTRACTIONS:\n{extraction_text}\n\n"
                f"Format using HTML (h2 for section titles, p for paragraphs, ul/li for lists, "
                f"table for financial data). Do NOT include html/head/body tags."
            )

            response = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "prompt": prompt,
                    "task_type": "analysis",
                    "max_tokens": 4096,
                    "temperature": 0.5,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=180.0,
            )
            response.raise_for_status()
            resp_data = response.json()
            content = resp_data.get("content") or resp_data.get("choices", [{}])[0].get("text", "")

            # Wrap in branded HTML
            now = datetime.now(timezone.utc)
            html = _HTML_TEMPLATE.format(
                title=report.title,
                date=now.strftime("%B %d, %Y"),
                year=now.year,
                body=content,
            )
            html_bytes = html.encode("utf-8")

            # Upload to S3
            s3_key = f"{investor_org_id}/memos/{report_id}.html"
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
                Body=html_bytes,
                ContentType="text/html",
            )

            report.status = ReportStatus.READY
            report.s3_key = s3_key
            report.result_data = {"content": content[:10000]}
            report.completed_at = now
            session.commit()

            logger.info(
                "generate_memo_task_completed",
                project_id=project_id,
                report_id=report_id,
                size=len(html_bytes),
            )
            return {"status": "success", "s3_key": s3_key}

        except Exception as exc:
            session.rollback()
            with SyncSession(engine) as err_session:
                err_report = err_session.get(GeneratedReport, report_uuid)
                if err_report:
                    err_report.status = ReportStatus.ERROR
                    err_report.error_message = str(exc)[:1000]
                    err_session.commit()

            logger.error(
                "generate_memo_task_failed",
                project_id=project_id,
                report_id=report_id,
                error=str(exc),
            )
            raise self.retry(exc=exc)
