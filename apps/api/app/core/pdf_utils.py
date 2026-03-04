"""Shared utility: convert HTML to PDF and upload to S3.

Used by: legal, deal_intelligence, tax_credits, valuation, reporting.
"""

import io
import structlog

import boto3
from botocore.config import Config as BotoConfig
from xhtml2pdf import pisa

from app.core.config import settings

logger = structlog.get_logger()


def html_to_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using xhtml2pdf."""
    pdf_buffer = io.BytesIO()
    status = pisa.CreatePDF(
        io.StringIO(html),
        dest=pdf_buffer,
        encoding="utf-8",
    )
    if status.err:
        raise RuntimeError(f"PDF conversion failed with {status.err} error(s)")
    return pdf_buffer.getvalue()


def upload_pdf_to_s3(
    pdf_bytes: bytes,
    s3_key: str,
    filename: str | None = None,
) -> str:
    """Upload PDF bytes to the configured S3 bucket. Returns the s3_key."""
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )
    extra: dict = {
        "ContentType": "application/pdf",
    }
    if filename:
        safe_name = filename.replace('"', "'")
        extra["ContentDisposition"] = f'attachment; filename="{safe_name}"'

    s3.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=s3_key,
        Body=pdf_bytes,
        **extra,
    )
    logger.info("pdf_uploaded_to_s3", s3_key=s3_key, size=len(pdf_bytes))
    return s3_key


def convert_and_upload(
    html: str,
    s3_key: str,
    filename: str | None = None,
) -> tuple[bytes, str]:
    """One-call convenience: HTML → PDF → S3. Returns (pdf_bytes, s3_key)."""
    pdf_bytes = html_to_pdf(html)
    upload_pdf_to_s3(pdf_bytes, s3_key, filename=filename)
    return pdf_bytes, s3_key
