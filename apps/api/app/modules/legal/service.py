"""Legal Document Manager service layer."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.enums import LegalDocumentStatus, LegalDocumentType
from app.models.legal import LegalDocument
from app.modules.legal.schemas import (
    LegalDocumentCreate,
    LegalDocumentResponse,
    ReviewResultResponse,
    ClauseAnalysis,
)
from app.modules.legal.templates import SYSTEM_TEMPLATES


# ── Helpers ─────────────────────────────────────────────────────────────────


def _get_template(template_id: str) -> dict | None:
    return next((t for t in SYSTEM_TEMPLATES if t["id"] == template_id), None)


def _doc_to_response(doc: LegalDocument, download_url: str | None = None) -> LegalDocumentResponse:
    meta = doc.metadata_ or {}
    return LegalDocumentResponse(
        id=doc.id,
        title=doc.title,
        doc_type=doc.doc_type.value,
        status=doc.status.value,
        template_id=meta.get("template_id"),
        project_id=doc.project_id,
        content=doc.content,
        s3_key=doc.s3_key,
        version=doc.version,
        signed_date=doc.signed_date,
        expiry_date=doc.expiry_date,
        questionnaire_answers=meta.get("questionnaire_answers"),
        generation_status=meta.get("generation_status"),
        download_url=download_url,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


# ── Template queries ─────────────────────────────────────────────────────────


def list_templates() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "doc_type": t["doc_type"],
            "description": t["description"],
            "estimated_pages": t["estimated_pages"],
        }
        for t in SYSTEM_TEMPLATES
    ]


def get_template_detail(template_id: str) -> dict | None:
    return _get_template(template_id)


# ── Document CRUD ─────────────────────────────────────────────────────────────


async def create_document(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: LegalDocumentCreate,
) -> LegalDocument:
    template = _get_template(body.template_id)
    if not template:
        raise ValueError(f"Template '{body.template_id}' not found")

    doc_type_map = {
        "nda": LegalDocumentType.NDA,
        "term_sheet": LegalDocumentType.TERM_SHEET,
        "subscription_agreement": LegalDocumentType.SUBSCRIPTION_AGREEMENT,
        "side_letter": LegalDocumentType.SIDE_LETTER,
        "spv_incorporation": LegalDocumentType.SPV_INCORPORATION,
    }
    doc_type = doc_type_map.get(template["doc_type"], LegalDocumentType.NDA)

    doc = LegalDocument(
        org_id=org_id,
        project_id=body.project_id,
        title=body.title,
        doc_type=doc_type,
        status=LegalDocumentStatus.DRAFT,
        content="",
        metadata_={
            "template_id": body.template_id,
            "questionnaire_answers": {},
            "generation_status": "not_started",
            "created_by": str(user_id),
        },
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    await db.commit()
    return doc


async def update_document_answers(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
    answers: dict[str, Any],
) -> LegalDocument:
    doc = await _get_doc_or_raise(db, doc_id, org_id)
    meta = dict(doc.metadata_ or {})
    meta["questionnaire_answers"] = answers
    doc.metadata_ = meta
    await db.flush()
    await db.commit()
    await db.refresh(doc)
    return doc


async def get_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
    generate_url: bool = False,
) -> LegalDocument:
    doc = await _get_doc_or_raise(db, doc_id, org_id)
    return doc


async def list_documents(
    db: AsyncSession,
    org_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[LegalDocument], int]:
    base = (
        select(LegalDocument)
        .where(
            LegalDocument.org_id == org_id,
            LegalDocument.is_deleted.is_(False),
        )
        .order_by(LegalDocument.created_at.desc())
    )
    total_q = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_q.scalar() or 0

    result = await db.execute(base.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().all()), total


async def trigger_generation(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    fmt: str = "docx",
) -> LegalDocument:
    """Mark document as pending generation and enqueue Celery task."""
    from app.modules.legal.tasks import generate_legal_doc_task

    doc = await _get_doc_or_raise(db, doc_id, org_id)
    meta = dict(doc.metadata_ or {})
    meta["generation_status"] = "pending"
    meta["output_format"] = fmt
    doc.metadata_ = meta
    await db.flush()
    await db.commit()
    await db.refresh(doc)

    generate_legal_doc_task.delay(str(doc_id), str(org_id), str(user_id))
    return doc


async def trigger_review(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    document_id: uuid.UUID | None,
    document_text: str | None,
    mode: str,
    jurisdiction: str,
) -> uuid.UUID:
    """Create a review task (stored as a special LegalDocument with doc_type=NDA as placeholder)."""
    from app.models.ai import AITaskLog
    from app.models.enums import AIAgentType, AITaskStatus
    from app.modules.legal.tasks import review_legal_doc_task

    task_log = AITaskLog(
        org_id=org_id,
        user_id=user_id,
        agent_type=AIAgentType.COMPLIANCE,
        entity_type="legal_document",
        entity_id=document_id,
        status=AITaskStatus.PENDING,
        input_data={
            "mode": mode,
            "jurisdiction": jurisdiction,
            "document_id": str(document_id) if document_id else None,
            "document_text": (document_text or "")[:10000],
        },
    )
    db.add(task_log)
    await db.flush()
    await db.refresh(task_log)
    await db.commit()

    review_legal_doc_task.delay(
        str(task_log.id),
        str(org_id),
        str(document_id) if document_id else None,
        document_text,
        mode,
        jurisdiction,
    )
    return task_log.id


async def get_review_result(
    db: AsyncSession,
    review_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ReviewResultResponse | None:
    from app.models.ai import AITaskLog

    stmt = select(AITaskLog).where(
        AITaskLog.id == review_id,
        AITaskLog.org_id == org_id,
    )
    result = await db.execute(stmt)
    task_log = result.scalar_one_or_none()
    if not task_log:
        return None

    output = task_log.output_data or {}
    input_data = task_log.input_data or {}

    clauses = [
        ClauseAnalysis(**c) for c in output.get("clause_analyses", [])
    ]

    return ReviewResultResponse(
        review_id=task_log.id,
        document_id=task_log.entity_id,
        mode=input_data.get("mode", "risk_focused"),
        jurisdiction=input_data.get("jurisdiction", ""),
        status=task_log.status.value,
        overall_risk_score=output.get("overall_risk_score"),
        summary=output.get("summary"),
        clause_analyses=clauses,
        missing_clauses=output.get("missing_clauses", []),
        jurisdiction_issues=output.get("jurisdiction_issues", []),
        recommendations=output.get("recommendations", []),
        model_used=task_log.model_used,
        created_at=task_log.created_at,
    )


async def get_download_url(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
) -> str | None:
    doc = await _get_doc_or_raise(db, doc_id, org_id)
    if not doc.s3_key:
        return None

    import boto3
    from botocore.config import Config as BotoConfig
    from app.core.config import settings

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": doc.s3_key},
        ExpiresIn=3600,
    )


# ── Internal ─────────────────────────────────────────────────────────────────


async def _get_doc_or_raise(
    db: AsyncSession,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
) -> LegalDocument:
    stmt = select(LegalDocument).where(
        LegalDocument.id == doc_id,
        LegalDocument.org_id == org_id,
        LegalDocument.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise LookupError(f"Legal document {doc_id} not found")
    return doc
