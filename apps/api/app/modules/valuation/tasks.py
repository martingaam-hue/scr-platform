"""Celery tasks for async valuation report generation."""

import uuid
from datetime import datetime, timezone

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("valuation", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_valuation_report_task(self, report_id: str) -> dict:
    """Generate a valuation report as HTML and upload to S3.

    Steps:
      1. Load GeneratedReport → GENERATING
      2. Load Valuation + Project + AIAssistant narrative
      3. Build HTML report with valuation details
      4. Upload to S3
      5. report.status = READY, commit
    """
    import json

    import boto3
    import httpx
    from botocore.config import Config as BotoConfig
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session as SyncSession

    from app.models.enums import ReportStatus
    from app.models.financial import Valuation
    from app.models.projects import Project
    from app.models.reporting import GeneratedReport

    engine = create_engine(settings.DATABASE_URL_SYNC)
    report_uuid = uuid.UUID(report_id)

    with SyncSession(engine) as session:
        report = session.get(GeneratedReport, report_uuid)
        if not report:
            logger.error("valuation_report_not_found", report_id=report_id)
            return {"status": "error", "detail": "Report not found"}

        try:
            report.status = ReportStatus.GENERATING
            session.commit()

            # Load valuation and project
            params = report.parameters or {}
            valuation_id = uuid.UUID(params["valuation_id"])
            valuation = session.get(Valuation, valuation_id)
            if not valuation:
                raise LookupError(f"Valuation {valuation_id} not found")

            project = session.get(Project, valuation.project_id)
            project_name = project.name if project else "Project"
            project_type = project.project_type.value if project else "unknown"
            geography = project.geography_country if project else "unknown"

            # Generate AI narrative (sync call)
            assumptions = valuation.assumptions or {}
            narrative = _generate_narrative_sync(
                method=valuation.method.value,
                enterprise_value=float(valuation.enterprise_value),
                equity_value=float(valuation.equity_value),
                currency=valuation.currency,
                project_type=project_type,
                geography=geography,
                assumptions_summary=assumptions,
            )

            # Build HTML report
            html_content = _build_html_report(
                project_name=project_name,
                project_type=project_type,
                geography=geography,
                valuation=valuation,
                narrative=narrative,
                assumptions=assumptions,
                model_inputs=valuation.model_inputs or {},
            )

            # Upload to S3
            s3_key = f"{report.org_id}/valuations/{report.id}.html"
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
                Body=html_content.encode("utf-8"),
                ContentType="text/html; charset=utf-8",
            )

            report.status = ReportStatus.READY
            report.s3_key = s3_key
            report.result_data = {
                "content": html_content[:10_000],
                "narrative": narrative,
                "file_size": len(html_content),
            }
            report.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info("valuation_report_generated", report_id=report_id)
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
                "valuation_report_failed", report_id=report_id, error=str(exc)
            )
            raise self.retry(exc=exc)


def _generate_narrative_sync(
    method: str,
    enterprise_value: float,
    equity_value: float,
    currency: str,
    project_type: str,
    geography: str,
    assumptions_summary: dict,
) -> str:
    """Synchronous AI narrative call for Celery context."""
    import json

    import httpx

    prompt = (
        f"You are a senior investment analyst writing a valuation section for an LP report.\n\n"
        f"Write 2-3 concise sentences summarising this project valuation:\n"
        f"- Method: {method.replace('_', ' ').upper()}\n"
        f"- Enterprise Value: {currency} {enterprise_value:,.0f}\n"
        f"- Equity Value: {currency} {equity_value:,.0f}\n"
        f"- Project type: {project_type}\n"
        f"- Geography: {geography}\n"
        f"- Key inputs: {json.dumps(assumptions_summary, indent=2)}\n\n"
        "Write in professional investment banking style. Be specific about methodology and conclusion.\n"
        "Do NOT use bullet points. Output plain prose only."
    )
    try:
        resp = httpx.post(
            f"{settings.AI_GATEWAY_URL}/v1/completions",
            json={
                "prompt": prompt,
                "task_type": "analysis",
                "max_tokens": 250,
                "temperature": 0.4,
            },
            headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json().get("content", "").strip()
    except Exception:
        return (
            f"The {method.replace('_', ' ').upper()} analysis yields an enterprise value "
            f"of {currency} {enterprise_value:,.0f} and equity value of "
            f"{currency} {equity_value:,.0f}."
        )


def _build_html_report(
    project_name: str,
    project_type: str,
    geography: str,
    valuation,
    narrative: str,
    assumptions: dict,
    model_inputs: dict,
) -> str:
    """Build a branded HTML valuation report."""
    import json
    from decimal import Decimal

    method_label = valuation.method.value.replace("_", " ").upper()
    ev = f"{valuation.currency} {float(valuation.enterprise_value):,.2f}"
    eq = f"{valuation.currency} {float(valuation.equity_value):,.2f}"
    status_label = valuation.status.value.upper()
    valued_at = valuation.valued_at.strftime("%d %b %Y") if valuation.valued_at else "—"

    assumptions_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in assumptions.items()
        if k != "method"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Valuation Report — {project_name}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           color: #1a1a2e; margin: 0; padding: 0; background: #f8fafc; }}
    .header {{ background: #1E3A5F; color: white; padding: 32px 48px; }}
    .header h1 {{ margin: 0 0 4px; font-size: 24px; font-weight: 700; }}
    .header p {{ margin: 0; opacity: 0.7; font-size: 14px; }}
    .content {{ padding: 40px 48px; max-width: 900px; }}
    .kv-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 24px 0; }}
    .kv-card {{ background: white; border-radius: 8px; padding: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .kv-card .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em;
                       color: #64748b; margin-bottom: 4px; }}
    .kv-card .value {{ font-size: 24px; font-weight: 700; color: #1E3A5F; }}
    .narrative {{ background: white; border-left: 4px solid #1E3A5F; border-radius: 0 8px 8px 0;
                  padding: 20px 24px; margin: 24px 0; font-size: 15px; line-height: 1.7;
                  color: #374151; }}
    table {{ width: 100%; border-collapse: collapse; background: white;
             border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    th {{ background: #f1f5f9; text-align: left; padding: 12px 16px;
          font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }}
    td {{ padding: 12px 16px; border-top: 1px solid #f1f5f9; font-size: 14px; }}
    h2 {{ font-size: 18px; font-weight: 600; color: #1E3A5F; margin: 32px 0 16px; }}
    .badge {{ display: inline-block; padding: 3px 10px; border-radius: 9999px;
              font-size: 12px; font-weight: 600; background: #dbeafe; color: #1d4ed8; }}
    .footer {{ background: #f1f5f9; padding: 24px 48px; font-size: 12px; color: #94a3b8;
               margin-top: 48px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Valuation Report</h1>
    <p>{project_name} &middot; {project_type} &middot; {geography}</p>
  </div>
  <div class="content">
    <div class="kv-grid">
      <div class="kv-card">
        <div class="label">Enterprise Value</div>
        <div class="value">{ev}</div>
      </div>
      <div class="kv-card">
        <div class="label">Equity Value</div>
        <div class="value">{eq}</div>
      </div>
      <div class="kv-card">
        <div class="label">Method</div>
        <div class="value" style="font-size:18px">{method_label}</div>
      </div>
      <div class="kv-card">
        <div class="label">Valued at</div>
        <div class="value" style="font-size:18px">{valued_at}
          <span class="badge" style="margin-left:8px">{status_label}</span>
        </div>
      </div>
    </div>

    <h2>Executive Summary</h2>
    <div class="narrative">{narrative}</div>

    <h2>Key Assumptions</h2>
    <table>
      <thead><tr><th>Assumption</th><th>Value</th></tr></thead>
      <tbody>{assumptions_rows}</tbody>
    </table>
  </div>
  <div class="footer">
    Generated by SCR Platform &middot; Version {valuation.version} &middot;
    For institutional use only. Not for public distribution.
  </div>
</body>
</html>"""
