"""Citations API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.citations.service import CitationService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/citations", tags=["citations"])


@router.get("/output/{ai_task_log_id}")
async def get_citations_for_output(
    ai_task_log_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all citations for an AI output."""
    svc = CitationService(db, current_user.org_id)
    citations = await svc.get_citations_for_output(ai_task_log_id)
    return [
        {
            "id": str(c.id),
            "claim_text": c.claim_text,
            "claim_index": c.claim_index,
            "source_type": c.source_type,
            "document_id": str(c.document_id) if c.document_id else None,
            "document_name": c.document_name,
            "page_or_section": c.page_or_section,
            "confidence": c.confidence,
            "verified": c.verified,
        }
        for c in citations
    ]


@router.post("/{citation_id}/verify")
async def verify_citation(
    citation_id: uuid.UUID,
    is_correct: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Human verify a citation's accuracy."""
    svc = CitationService(db, current_user.org_id)
    try:
        citation = await svc.verify_citation(citation_id, current_user.user_id, is_correct)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"id": str(citation.id), "verified": citation.verified, "confidence": citation.confidence}


@router.get("/stats")
async def get_citation_stats(
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Citation accuracy statistics (admin/manager)."""
    svc = CitationService(db, current_user.org_id)
    return await svc.get_stats()
