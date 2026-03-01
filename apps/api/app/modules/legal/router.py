"""Legal Document Manager API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.legal import service
from app.modules.legal.schemas import (
    CompareRequest,
    GenerateDocumentRequest,
    GenerateDocumentResponse,
    LegalDocumentCreate,
    LegalDocumentListResponse,
    LegalDocumentResponse,
    LegalDocumentUpdate,
    ReviewRequest,
    ReviewResponse,
    ReviewResultResponse,
    SendDocumentRequest,
    TemplateDetail,
    TemplateListItem,
)
from app.modules.legal.templates import (
    REVIEW_MODES,
    SUPPORTED_JURISDICTIONS,
    SYSTEM_TEMPLATES,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/legal", tags=["legal"])


# ── Templates ─────────────────────────────────────────────────────────────────


@router.get("/templates", response_model=list[TemplateListItem])
async def list_templates(
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all available legal document templates."""
    return service.list_templates()


@router.get("/templates/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a template with its full questionnaire definition."""
    tmpl = service.get_template_detail(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return TemplateDetail(
        id=tmpl["id"],
        name=tmpl["name"],
        doc_type=tmpl["doc_type"],
        description=tmpl["description"],
        estimated_pages=tmpl["estimated_pages"],
        questionnaire=tmpl["questionnaire"],
    )


@router.get("/jurisdictions", response_model=list[str])
async def list_jurisdictions(
    current_user: CurrentUser = Depends(get_current_user),
):
    """List supported jurisdictions for document generation and review."""
    return SUPPORTED_JURISDICTIONS


# ── Documents ─────────────────────────────────────────────────────────────────


@router.post(
    "/documents",
    response_model=LegalDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    body: LegalDocumentCreate,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Start a new legal document from a template."""
    try:
        doc = await service.create_document(db, current_user.org_id, current_user.user_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return service._doc_to_response(doc)


@router.get("/documents", response_model=LegalDocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """List all legal documents for the current organisation."""
    docs, total = await service.list_documents(db, current_user.org_id, page, page_size)
    items = [service._doc_to_response(d) for d in docs]
    return LegalDocumentListResponse(items=items, total=total)


@router.get("/documents/{document_id}", response_model=LegalDocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Get a legal document by ID."""
    try:
        doc = await service.get_document(db, document_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    download_url = await service.get_download_url(db, document_id, current_user.org_id)
    return service._doc_to_response(doc, download_url)


@router.put("/documents/{document_id}", response_model=LegalDocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    body: LegalDocumentUpdate,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Update questionnaire answers for a legal document."""
    try:
        doc = await service.update_document_answers(
            db, document_id, current_user.org_id, body.questionnaire_answers
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return service._doc_to_response(doc)


@router.post(
    "/documents/{document_id}/generate",
    response_model=GenerateDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_document(
    document_id: uuid.UUID,
    body: GenerateDocumentRequest = GenerateDocumentRequest(),
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a legal document from completed questionnaire answers."""
    try:
        doc = await service.trigger_generation(
            db, document_id, current_user.org_id, current_user.user_id, body.format
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return GenerateDocumentResponse(
        document_id=doc.id,
        status="accepted",
        message="Document generation queued. Poll GET /legal/documents/{id} for status.",
    )


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Get a pre-signed download URL for a generated legal document."""
    try:
        url = await service.get_download_url(db, document_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not url:
        raise HTTPException(status_code=404, detail="Document not yet generated")
    return {"download_url": url}


@router.post(
    "/documents/{document_id}/send",
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_document(
    document_id: uuid.UUID,
    body: SendDocumentRequest,
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Send document to signatories for review (stub — email integration pending)."""
    try:
        await service.get_document(db, document_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    logger.info(
        "legal_doc_send_requested",
        doc_id=str(document_id),
        recipients=body.recipient_emails,
    )
    return {
        "status": "accepted",
        "message": f"Document will be sent to {len(body.recipient_emails)} recipient(s).",
        "recipients": body.recipient_emails,
    }


# ── Review ────────────────────────────────────────────────────────────────────


@router.post(
    "/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def review_document(
    body: ReviewRequest,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a document for AI-powered legal review."""
    if not body.document_id and not body.document_text:
        raise HTTPException(
            status_code=422,
            detail="Provide either document_id or document_text",
        )
    if body.mode not in REVIEW_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"mode must be one of {list(REVIEW_MODES.keys())}",
        )

    review_id = await service.trigger_review(
        db,
        current_user.org_id,
        current_user.user_id,
        body.document_id,
        body.document_text,
        body.mode,
        body.jurisdiction,
    )
    return ReviewResponse(
        review_id=review_id,
        status="accepted",
        message="Review queued. Poll GET /legal/review/{review_id} for results.",
    )


@router.get("/review/{review_id}", response_model=ReviewResultResponse)
async def get_review(
    review_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Get the results of a document review."""
    result = await service.get_review_result(db, review_id, current_user.org_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    return result


@router.post("/compare")
async def compare_documents(
    body: CompareRequest,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Compare two document versions and return a unified diff with similarity score."""
    try:
        result = await service.compare_documents(
            db, body.document_id_a, body.document_id_b, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result
