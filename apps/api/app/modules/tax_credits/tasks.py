"""Celery tasks for tax credit transfer document generation."""

import uuid
from datetime import datetime, timezone

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("tax_credits", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_transfer_doc_task(self, report_id: str) -> dict:
    """Generate tax credit transfer election documentation as HTML.

    Steps:
      1. Load GeneratedReport → GENERATING
      2. Load TaxCredit + Project details from parameters
      3. AI: generate transfer election language
      4. Build branded HTML document
      5. Upload to S3 → READY
    """
    import json

    import boto3
    import httpx
    from botocore.config import Config as BotoConfig
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.enums import ReportStatus
    from app.models.reporting import GeneratedReport

    engine = create_engine(settings.DATABASE_URL_SYNC)
    report_uuid = uuid.UUID(report_id)

    with SyncSession(engine) as session:
        report = session.get(GeneratedReport, report_uuid)
        if not report:
            logger.error("transfer_doc_report_not_found", report_id=report_id)
            return {"status": "error", "detail": "Report not found"}

        try:
            report.status = ReportStatus.GENERATING
            session.commit()

            params = report.parameters or {}
            credit_type = params.get("credit_type", "Tax Credit")
            project_name = params.get("project_name", "Project")
            estimated_value = params.get("estimated_value", "0")
            currency = params.get("currency", "USD")
            transferee_name = params.get("transferee_name", "Transferee")
            transferee_ein = params.get("transferee_ein", "")
            transfer_price = params.get("transfer_price")

            # AI: generate transfer election language
            doc_content = _generate_transfer_language(
                credit_type=credit_type,
                project_name=project_name,
                estimated_value=estimated_value,
                currency=currency,
                transferee_name=transferee_name,
                transferee_ein=transferee_ein,
                transfer_price=transfer_price,
            )

            html = _build_transfer_html(
                credit_type=credit_type,
                project_name=project_name,
                estimated_value=estimated_value,
                currency=currency,
                transferee_name=transferee_name,
                transferee_ein=transferee_ein,
                transfer_price=transfer_price,
                doc_content=doc_content,
                org_id=report.org_id,
            )

            s3_key = f"{report.org_id}/tax-credits/{report.id}.html"
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
                Body=html.encode("utf-8"),
                ContentType="text/html; charset=utf-8",
            )

            report.status = ReportStatus.READY
            report.s3_key = s3_key
            report.result_data = {
                "content": html[:10_000],
                "credit_type": credit_type,
                "project_name": project_name,
            }
            report.completed_at = datetime.now(timezone.utc)
            session.commit()

            logger.info("transfer_doc_generated", report_id=report_id)
            return {"status": "success", "s3_key": s3_key}

        except Exception as exc:
            session.rollback()
            with SyncSession(engine) as err_session:
                err_report = err_session.get(GeneratedReport, report_uuid)
                if err_report:
                    err_report.status = ReportStatus.ERROR
                    err_report.error_message = str(exc)[:1000]
                    err_session.commit()
            logger.error("transfer_doc_failed", report_id=report_id, error=str(exc))
            raise self.retry(exc=exc)


def _generate_transfer_language(
    credit_type: str,
    project_name: str,
    estimated_value: str,
    currency: str,
    transferee_name: str,
    transferee_ein: str,
    transfer_price: str | None,
) -> str:
    import httpx

    price_clause = (
        f"for a transfer price of {currency} {float(transfer_price):,.2f}"
        if transfer_price
        else "at fair market value to be determined at closing"
    )

    prompt = (
        f"You are a US tax attorney drafting a tax credit transfer election.\n\n"
        f"Draft the body text (3-4 paragraphs) for a {credit_type} transfer election under "
        f"IRA §6418 for:\n"
        f"- Project: {project_name}\n"
        f"- Credit amount: {currency} {estimated_value}\n"
        f"- Transferee: {transferee_name}"
        + (f" (EIN: {transferee_ein})" if transferee_ein else "")
        + f"\n- Transfer consideration: {price_clause}\n\n"
        "Include: election statement, credit description, transferor/transferee identification, "
        "consideration terms, and required representations. Use formal legal language."
    )

    try:
        resp = httpx.post(
            f"{settings.AI_GATEWAY_URL}/v1/completions",
            json={
                "prompt": prompt,
                "task_type": "analysis",
                "max_tokens": 800,
                "temperature": 0.3,
            },
            headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json().get("content", "").strip()
    except Exception:
        return (
            f"This document constitutes the election under IRC §6418 to transfer the "
            f"{credit_type} credit of {currency} {estimated_value} arising from "
            f"{project_name} to {transferee_name} {price_clause}. "
            "The transferor and transferee agree to the terms set forth herein and shall "
            "file all required returns consistent with this election."
        )


def _build_transfer_html(
    credit_type: str,
    project_name: str,
    estimated_value: str,
    currency: str,
    transferee_name: str,
    transferee_ein: str,
    transfer_price: str | None,
    doc_content: str,
    org_id: uuid.UUID,
) -> str:
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    price_display = (
        f"{currency} {float(transfer_price):,.2f}" if transfer_price else "To be determined"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Tax Credit Transfer Election — {credit_type}</title>
  <style>
    body {{ font-family: 'Times New Roman', serif; color: #1a1a1a; margin: 0; padding: 0;
           background: #fff; }}
    .header {{ background: #1E3A5F; color: white; padding: 24px 48px; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
    .header p {{ margin: 4px 0 0; font-size: 13px; opacity: 0.75; }}
    .content {{ padding: 40px 60px; max-width: 800px; margin: 0 auto; }}
    .section-title {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
                      font-family: sans-serif; color: #64748b; margin: 28px 0 8px; }}
    .kv-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    .kv-table td {{ padding: 8px 0; font-size: 14px; border-bottom: 1px solid #e2e8f0; }}
    .kv-table td:first-child {{ font-weight: 600; width: 200px; color: #374151; }}
    .body-text {{ font-size: 14px; line-height: 1.8; color: #374151; white-space: pre-wrap; }}
    .signature-block {{ margin-top: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }}
    .sig-box {{ border-top: 1px solid #374151; padding-top: 8px; font-size: 12px; color: #6b7280; }}
    .disclaimer {{ margin-top: 40px; padding: 16px; background: #f8fafc; border-radius: 6px;
                   font-size: 11px; color: #94a3b8; font-family: sans-serif; }}
    .footer {{ background: #f1f5f9; padding: 20px 48px; font-size: 11px;
               color: #94a3b8; font-family: sans-serif; margin-top: 48px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Tax Credit Transfer Election</h1>
    <p>IRC §6418 — {credit_type} · {today}</p>
  </div>
  <div class="content">
    <div class="section-title">Transaction Summary</div>
    <table class="kv-table">
      <tr><td>Credit Type</td><td>{credit_type}</td></tr>
      <tr><td>Project</td><td>{project_name}</td></tr>
      <tr><td>Credit Amount</td><td>{currency} {float(estimated_value):,.2f}</td></tr>
      <tr><td>Transferee</td><td>{transferee_name}{f" — EIN {transferee_ein}" if transferee_ein else ""}</td></tr>
      <tr><td>Transfer Price</td><td>{price_display}</td></tr>
      <tr><td>Election Date</td><td>{today}</td></tr>
    </table>

    <div class="section-title">Election Statement</div>
    <div class="body-text">{doc_content}</div>

    <div class="signature-block">
      <div class="sig-box">
        <p>Transferor Signature</p>
        <p>___________________________</p>
        <p>Name: ____________________</p>
        <p>Title: ____________________</p>
        <p>Date: ____________________</p>
      </div>
      <div class="sig-box">
        <p>Transferee Signature ({transferee_name})</p>
        <p>___________________________</p>
        <p>Name: ____________________</p>
        <p>Title: ____________________</p>
        <p>Date: ____________________</p>
      </div>
    </div>

    <div class="disclaimer">
      DRAFT — FOR REVIEW PURPOSES ONLY. This document is AI-assisted and must be reviewed by
      qualified tax counsel before execution. Tax credits transferred under IRC §6418 require
      election on an original tax return; consult your tax advisor regarding applicable deadlines,
      recapture rules, and compliance requirements.
    </div>
  </div>
  <div class="footer">
    Generated by SCR Platform · {today} · Confidential — Not for public distribution
  </div>
</body>
</html>"""
