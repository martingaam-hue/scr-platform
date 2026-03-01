"""FastAPI router for the AI Document Redaction module."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.redaction.schemas import (
    ENTITY_TYPES,
    HIGH_SENSITIVITY,
    AnalyzeRequest,
    ApproveRedactionsRequest,
    EntityTypeInfo,
    RedactionJobResponse,
    RedactionRulesResponse,
)
from app.modules.redaction.service import RedactionService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/redaction", tags=["redaction"])


# ── Helper ────────────────────────────────────────────────────────────────────


def _to_response(job) -> RedactionJobResponse:
    return RedactionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        detected_entities=job.detected_entities,
        approved_redactions=job.approved_redactions,
        entity_count=job.entity_count,
        approved_count=job.approved_count,
        redacted_document_id=job.redacted_document_id,
        redacted_s3_key=job.redacted_s3_key,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/rules",
    response_model=RedactionRulesResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_redaction_rules() -> RedactionRulesResponse:
    """Return the list of detectable entity types and which are high-sensitivity."""
    return RedactionRulesResponse(
        entity_types=[
            EntityTypeInfo(
                entity_type=et,
                is_high_sensitivity=et in HIGH_SENSITIVITY,
            )
            for et in ENTITY_TYPES
        ],
        high_sensitivity_types=list(HIGH_SENSITIVITY),
    )


@router.get(
    "/jobs",
    response_model=list[RedactionJobResponse],
    dependencies=[Depends(require_permission("view", "document"))],
)
async def list_jobs(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    document_id: uuid.UUID | None = Query(None),
) -> list[RedactionJobResponse]:
    """List redaction jobs for the org, optionally filtered by document."""
    svc = RedactionService(db)
    jobs = await svc.list_jobs(current_user.org_id, document_id)
    return [_to_response(j) for j in jobs]


@router.post(
    "/analyze/{document_id}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("edit", "document"))],
)
async def analyze_document(
    document_id: uuid.UUID,
    body: AnalyzeRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a redaction job and queue PII analysis via Celery.

    If ``document_text`` is provided in the request body it is passed directly
    to the analysis task.  Otherwise the task uses a placeholder — in production
    the pipeline would read the document text from the extraction cache.
    """
    svc = RedactionService(db)
    job = await svc.create_job(current_user.org_id, current_user.user_id, document_id)

    document_text = (body.document_text if body else None) or "Document text placeholder"

    # Queue analysis — import here to avoid circular imports at module load time
    from app.modules.redaction.tasks import analyze_redaction_job_task

    try:
        analyze_redaction_job_task.delay(str(job.id), document_text)
    except Exception:
        # Celery not available in this context — run synchronously (dev/test)
        analyze_redaction_job_task(str(job.id), document_text)

    return {"job_id": str(job.id), "status": job.status}


@router.get(
    "/jobs/{job_id}",
    response_model=RedactionJobResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_job(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedactionJobResponse:
    """Get the current state of a redaction job."""
    svc = RedactionService(db)
    job = await svc.get_job(current_user.org_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redaction job not found")
    return _to_response(job)


@router.post(
    "/jobs/{job_id}/approve",
    response_model=RedactionJobResponse,
    dependencies=[Depends(require_permission("edit", "document"))],
)
async def approve_redactions(
    job_id: uuid.UUID,
    body: ApproveRedactionsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedactionJobResponse:
    """User approves a subset of detected entities for actual redaction.

    The job must be in `review` status. Transitions job to `applying`.
    Call POST /jobs/{job_id}/apply next to generate the redacted PDF.
    """
    svc = RedactionService(db)
    job = await svc.approve_redactions(
        current_user.org_id, job_id, body.approved_entity_ids
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Redaction job not found or not in review status",
        )
    return _to_response(job)


@router.post(
    "/jobs/{job_id}/apply",
    response_model=RedactionJobResponse,
    dependencies=[Depends(require_permission("edit", "document"))],
)
async def apply_redaction(
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedactionJobResponse:
    """Queue PDF generation with redaction boxes applied.

    The job must already be in `applying` status (set by POST /approve).
    Transitions job to `done` once the redacted PDF is stored.
    """
    svc = RedactionService(db)
    job = await svc.get_job(current_user.org_id, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Redaction job not found"
        )
    if job.status != "applying":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job must be in 'applying' status to apply redaction (current: {job.status})",
        )

    from app.modules.redaction.tasks import apply_redaction_task

    try:
        apply_redaction_task.delay(str(job_id))
    except Exception:
        apply_redaction_task(str(job_id))

    # Return refreshed state (the task may have already finished synchronously)
    job = await svc.get_job(current_user.org_id, job_id)
    return _to_response(job)
