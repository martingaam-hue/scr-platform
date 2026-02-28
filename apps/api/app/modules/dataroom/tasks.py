"""Celery tasks for async document processing, AI extraction, and cleanup."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from celery import Celery
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("dataroom", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ── Document Processing Pipeline ────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document(self, document_id: str) -> dict:
    """Full document processing pipeline triggered after upload confirmation.

    Steps:
      1. Validate file integrity (checksum)
      2. Extract text content
      3. Classify document type
      4. Extract KPIs, key clauses, deadlines
      5. Generate summary
      6. Update document status to READY
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.dataroom import Document, DocumentExtraction
    from app.models.enums import DocumentStatus, ExtractionType

    engine = create_engine(settings.DATABASE_URL_SYNC)
    doc_uuid = uuid.UUID(document_id)

    with SyncSession(engine) as session:
        doc = session.get(Document, doc_uuid)
        if not doc:
            logger.error("process_document_not_found", document_id=document_id)
            return {"status": "error", "detail": "Document not found"}

        if doc.status != DocumentStatus.PROCESSING:
            logger.warning(
                "process_document_wrong_status",
                document_id=document_id,
                status=doc.status.value,
            )
            return {"status": "skipped", "detail": f"Document in {doc.status.value} state"}

        try:
            # Step 1: Validate checksum
            _validate_checksum(doc)

            # Step 2: Extract text
            text_content = _extract_text(doc)

            # Step 3: Classify document
            classification = _classify_document(doc, text_content)
            session.add(DocumentExtraction(
                document_id=doc.id,
                extraction_type=ExtractionType.CLASSIFICATION,
                result={"classification": classification, "source_name": doc.name},
                model_used="rule-based",
                confidence_score=0.8,
                tokens_used=0,
                processing_time_ms=50,
            ))

            # Step 4: Extract structured data based on classification
            _extract_structured_data(session, doc, text_content, classification)

            # Step 5: Generate summary
            session.add(DocumentExtraction(
                document_id=doc.id,
                extraction_type=ExtractionType.SUMMARY,
                result={
                    "summary": f"Document '{doc.name}' ({doc.file_type}) classified as {classification}.",
                    "word_count": len(text_content.split()) if text_content else 0,
                    "page_count_estimate": max(1, len(text_content) // 3000) if text_content else 1,
                },
                model_used="rule-based",
                confidence_score=0.7,
                tokens_used=0,
                processing_time_ms=30,
            ))

            # Step 6: Index in vector store for RAG search
            _index_in_vector_store(doc, text_content, classification)

            # Step 7: Mark as ready
            doc.status = DocumentStatus.READY
            doc.classification = classification
            session.commit()

            logger.info(
                "document_processed",
                document_id=document_id,
                classification=classification,
            )
            return {"status": "success", "classification": classification}

        except Exception as exc:
            session.rollback()
            # Reopen session to update status
            with SyncSession(engine) as err_session:
                err_doc = err_session.get(Document, doc_uuid)
                if err_doc:
                    err_doc.status = DocumentStatus.ERROR
                    err_doc.metadata_ = {
                        **(err_doc.metadata_ or {}),
                        "processing_error": str(exc),
                    }
                    err_session.commit()

            logger.error(
                "document_processing_failed",
                document_id=document_id,
                error=str(exc),
            )
            raise self.retry(exc=exc)


def _validate_checksum(doc) -> None:
    """Verify file integrity by checking S3 object against stored checksum."""
    import boto3
    from botocore.config import Config as BotoConfig

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )

    response = s3.get_object(Bucket=doc.s3_bucket, Key=doc.s3_key)
    body = response["Body"].read()

    actual_hash = hashlib.sha256(body).hexdigest()
    if actual_hash != doc.checksum_sha256:
        raise ValueError(
            f"Checksum mismatch: expected {doc.checksum_sha256}, got {actual_hash}"
        )


def _extract_text(doc) -> str:
    """Extract text content from document based on file type."""
    import boto3
    from botocore.config import Config as BotoConfig

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )

    response = s3.get_object(Bucket=doc.s3_bucket, Key=doc.s3_key)
    body = response["Body"].read()

    if doc.file_type == "pdf":
        return _extract_pdf_text(body)
    elif doc.file_type == "csv":
        return body.decode("utf-8", errors="replace")
    elif doc.file_type in ("jpg", "png"):
        # OCR placeholder — would queue to an OCR service
        logger.info("ocr_placeholder", document_id=str(doc.id), file_type=doc.file_type)
        return f"[Image file: {doc.name} — OCR processing not yet available]"
    elif doc.file_type in ("docx", "xlsx", "pptx"):
        # Placeholder for Office document extraction
        logger.info("office_extraction_placeholder", document_id=str(doc.id))
        return f"[Office file: {doc.name} — text extraction placeholder]"
    else:
        return ""


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        import io

        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("pypdf2_not_installed")
        return "[PDF text extraction unavailable — PyPDF2 not installed]"
    except Exception as e:
        logger.warning("pdf_extraction_failed", error=str(e))
        return f"[PDF extraction failed: {e}]"


def _classify_document(doc, text_content: str) -> str:
    """Classify document type based on name and content.

    In production, this would call the AI Gateway for ML-based classification.
    """
    name_lower = doc.name.lower()
    text_lower = (text_content or "").lower()

    # Rule-based classification as baseline
    if any(kw in name_lower for kw in ("financial", "income", "balance", "cashflow", "p&l")):
        return "financial_statement"
    elif any(kw in name_lower for kw in ("agreement", "contract", "nda", "mou", "terms")):
        return "legal_agreement"
    elif any(kw in name_lower for kw in ("technical", "feasibility", "engineering")):
        return "technical_study"
    elif any(kw in name_lower for kw in ("environmental", "eia", "esia", "impact")):
        return "environmental_report"
    elif any(kw in name_lower for kw in ("permit", "license", "licence", "approval")):
        return "permit"
    elif any(kw in name_lower for kw in ("insurance", "policy", "coverage")):
        return "insurance"
    elif any(kw in name_lower for kw in ("valuation", "appraisal")):
        return "valuation"
    elif any(kw in name_lower for kw in ("business plan", "pitch", "deck")):
        return "business_plan"
    elif any(kw in name_lower for kw in ("presentation", "slides")):
        return "presentation"
    elif any(kw in name_lower for kw in ("letter", "email", "memo", "correspondence")):
        return "correspondence"

    # Content-based fallback
    if "revenue" in text_lower and "net income" in text_lower:
        return "financial_statement"
    elif "hereby agree" in text_lower or "parties hereto" in text_lower:
        return "legal_agreement"

    return "other"


def _extract_structured_data(session, doc, text_content: str, classification: str) -> None:
    """Extract KPIs, deadlines, and financial data based on document classification.

    In production, this would route through the AI Gateway to Claude/GPT-4o.
    """
    from app.models.dataroom import DocumentExtraction
    from app.models.enums import ExtractionType

    # Placeholder extraction — in production, call AI Gateway
    if classification == "financial_statement":
        session.add(DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.FINANCIAL,
            result={
                "source": doc.name,
                "note": "AI financial extraction placeholder",
                "metrics_found": [],
            },
            model_used="placeholder",
            confidence_score=0.0,
            tokens_used=0,
            processing_time_ms=10,
        ))

    if classification in ("legal_agreement", "permit"):
        session.add(DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.DEADLINE,
            result={
                "source": doc.name,
                "note": "AI deadline extraction placeholder",
                "deadlines_found": [],
            },
            model_used="placeholder",
            confidence_score=0.0,
            tokens_used=0,
            processing_time_ms=10,
        ))
        session.add(DocumentExtraction(
            document_id=doc.id,
            extraction_type=ExtractionType.CLAUSE,
            result={
                "source": doc.name,
                "note": "AI clause extraction placeholder",
                "clauses_found": [],
            },
            model_used="placeholder",
            confidence_score=0.0,
            tokens_used=0,
            processing_time_ms=10,
        ))

    # Always extract KPIs
    session.add(DocumentExtraction(
        document_id=doc.id,
        extraction_type=ExtractionType.KPI,
        result={
            "source": doc.name,
            "note": "AI KPI extraction placeholder",
            "kpis_found": [],
        },
        model_used="placeholder",
        confidence_score=0.0,
        tokens_used=0,
        processing_time_ms=10,
    ))


# ── Bulk Processing ─────────────────────────────────────────────────────────


@celery_app.task
def process_bulk_upload(document_ids: list[str]) -> dict:
    """Process multiple documents sequentially."""
    results = []
    for doc_id in document_ids:
        result = process_document.delay(doc_id)
        results.append({"document_id": doc_id, "task_id": str(result.id)})
    return {"queued": len(results), "tasks": results}


# ── Cleanup ──────────────────────────────────────────────────────────────────


@celery_app.task
def cleanup_orphaned_uploads() -> dict:
    """Clean up documents stuck in UPLOADING state for more than 24 hours.

    These are records where the client requested a pre-signed URL but never
    confirmed the upload. Marks them as deleted and removes S3 objects.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    import boto3
    from botocore.config import Config as BotoConfig

    from app.models.dataroom import Document
    from app.models.enums import DocumentStatus

    engine = create_engine(settings.DATABASE_URL_SYNC)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )

    cleaned = 0
    with SyncSession(engine) as session:
        stmt = select(Document).where(
            Document.status == DocumentStatus.UPLOADING,
            Document.is_deleted.is_(False),
            Document.created_at < cutoff,
        )
        orphans = session.execute(stmt).scalars().all()

        for doc in orphans:
            try:
                s3.delete_object(Bucket=doc.s3_bucket, Key=doc.s3_key)
            except Exception as e:
                logger.warning("orphan_s3_cleanup_failed", key=doc.s3_key, error=str(e))

            doc.is_deleted = True
            cleaned += 1

        session.commit()

    logger.info("orphaned_uploads_cleaned", count=cleaned)
    return {"cleaned": cleaned}


# ── AI Re-extraction ────────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def trigger_extraction(self, document_id: str, extraction_types: list[str] | None = None) -> dict:
    """Trigger AI extraction (or re-extraction) for specific extraction types.

    In production, this would call the AI Gateway for each extraction type.
    For now, re-runs the rule-based pipeline.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.dataroom import Document, DocumentExtraction
    from app.models.enums import DocumentStatus, ExtractionType

    engine = create_engine(settings.DATABASE_URL_SYNC)
    doc_uuid = uuid.UUID(document_id)

    types_to_run = (
        [ExtractionType(t) for t in extraction_types]
        if extraction_types
        else list(ExtractionType)
    )

    with SyncSession(engine) as session:
        doc = session.get(Document, doc_uuid)
        if not doc:
            return {"status": "error", "detail": "Document not found"}

        if doc.status not in (DocumentStatus.READY, DocumentStatus.PROCESSING):
            return {"status": "error", "detail": f"Document in {doc.status.value} state"}

        try:
            text_content = _extract_text(doc)

            for ext_type in types_to_run:
                if ext_type == ExtractionType.CLASSIFICATION:
                    classification = _classify_document(doc, text_content)
                    session.add(DocumentExtraction(
                        document_id=doc.id,
                        extraction_type=ExtractionType.CLASSIFICATION,
                        result={"classification": classification, "source_name": doc.name},
                        model_used="rule-based",
                        confidence_score=0.8,
                        tokens_used=0,
                        processing_time_ms=50,
                    ))
                elif ext_type == ExtractionType.SUMMARY:
                    session.add(DocumentExtraction(
                        document_id=doc.id,
                        extraction_type=ExtractionType.SUMMARY,
                        result={
                            "summary": f"Re-extracted summary for '{doc.name}'.",
                            "word_count": len(text_content.split()) if text_content else 0,
                        },
                        model_used="rule-based",
                        confidence_score=0.7,
                        tokens_used=0,
                        processing_time_ms=30,
                    ))
                else:
                    # Placeholder for AI-powered extraction
                    session.add(DocumentExtraction(
                        document_id=doc.id,
                        extraction_type=ext_type,
                        result={
                            "source": doc.name,
                            "note": f"AI {ext_type.value} extraction placeholder",
                        },
                        model_used="placeholder",
                        confidence_score=0.0,
                        tokens_used=0,
                        processing_time_ms=10,
                    ))

            session.commit()
            return {"status": "success", "extractions": len(types_to_run)}

        except Exception as exc:
            session.rollback()
            logger.error("extraction_failed", document_id=document_id, error=str(exc))
            raise self.retry(exc=exc)


# ── Vector Store Indexing ────────────────────────────────────────────────────


def _index_in_vector_store(doc, text_content: str, classification: str) -> None:
    """Send document text to AI Gateway for vector indexing (RAG support).

    This call is non-blocking — a failure here does NOT fail document processing.
    Documents without extracted text are silently skipped.
    """
    import httpx

    if not text_content or text_content.startswith("["):
        # No real text content (placeholder, image OCR, etc.) — skip indexing
        logger.info(
            "rag_index_skipped",
            document_id=str(doc.id),
            reason="no_extractable_text",
        )
        return

    payload = {
        "document_id": str(doc.id),
        "text": text_content[:50_000],  # Truncate to avoid gateway limits
        "org_id": str(doc.org_id),
        "index_type": "document_chunks",
        "metadata": {
            "document_name": doc.name,
            "file_type": doc.file_type,
            "classification": classification,
            "project_id": str(doc.project_id) if doc.project_id else None,
            "s3_key": doc.s3_key,
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{settings.AI_GATEWAY_URL}/v1/ingest",
                json=payload,
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "rag_index_success",
                document_id=str(doc.id),
                chunks_stored=data.get("chunks_stored", 0),
            )
    except Exception as exc:
        # Non-fatal — document still becomes READY; RAG search just won't include it
        logger.warning(
            "rag_index_failed",
            document_id=str(doc.id),
            error=str(exc),
        )
