"""FastAPI router for the Document Annotations module."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.document_annotations.schemas import (
    AnnotationResponse,
    CreateAnnotationRequest,
    UpdateAnnotationRequest,
)
from app.modules.document_annotations.service import AnnotationService
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/annotations", tags=["annotations"])


def _svc(db: AsyncSession = Depends(get_db)) -> AnnotationService:
    return AnnotationService(db)


# ── Create ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def create_annotation(
    body: CreateAnnotationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnnotationService = Depends(_svc),
) -> AnnotationResponse:
    """Create a new annotation on a document page."""
    annotation = await svc.create_annotation(
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        data=body,
    )
    return AnnotationResponse.model_validate(annotation)


# ── List ──────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[AnnotationResponse],
    dependencies=[Depends(require_permission("view", "document"))],
)
async def list_annotations(
    document_id: uuid.UUID = Query(..., description="Filter by document ID"),
    page: int | None = Query(None, ge=1, description="Optional page number filter"),
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnnotationService = Depends(_svc),
) -> list[AnnotationResponse]:
    """List all annotations for a document, optionally filtered by page number."""
    annotations = await svc.list_annotations(
        org_id=current_user.org_id,
        document_id=document_id,
        page_number=page,
    )
    return [AnnotationResponse.model_validate(a) for a in annotations]


# ── Get single ────────────────────────────────────────────────────────────────


@router.get(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_annotation(
    annotation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnnotationService = Depends(_svc),
) -> AnnotationResponse:
    """Retrieve a single annotation by ID."""
    annotation = await svc.get_annotation(
        org_id=current_user.org_id,
        annotation_id=annotation_id,
    )
    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found",
        )
    return AnnotationResponse.model_validate(annotation)


# ── Update ────────────────────────────────────────────────────────────────────


@router.patch(
    "/{annotation_id}",
    response_model=AnnotationResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def update_annotation(
    annotation_id: uuid.UUID,
    body: UpdateAnnotationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnnotationService = Depends(_svc),
) -> AnnotationResponse:
    """Update the content, color, or privacy of an annotation."""
    annotation = await svc.update_annotation(
        org_id=current_user.org_id,
        annotation_id=annotation_id,
        user_id=current_user.user_id,
        data=body,
    )
    if annotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found",
        )
    return AnnotationResponse.model_validate(annotation)


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete(
    "/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def delete_annotation(
    annotation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AnnotationService = Depends(_svc),
) -> None:
    """Delete an annotation. Only the creator may delete it."""
    deleted = await svc.delete_annotation(
        org_id=current_user.org_id,
        annotation_id=annotation_id,
        user_id=current_user.user_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found or you do not have permission to delete it",
        )
