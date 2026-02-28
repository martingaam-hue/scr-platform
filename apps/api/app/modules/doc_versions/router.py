"""Document Version Control API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.doc_versions import service
from app.modules.doc_versions.schemas import (
    CompareVersionsResponse,
    CreateVersionRequest,
    DocumentVersionListResponse,
    DocumentVersionResponse,
    DiffStats,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/documents", tags=["document-versions"])


@router.post(
    "/{document_id}/versions",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    document_id: uuid.UUID,
    body: CreateVersionRequest,
    current_user: CurrentUser = Depends(require_permission("create", "document")),
    db: AsyncSession = Depends(get_db),
):
    """Register a new version of a document (file already uploaded to S3)."""
    version = await service.create_version(
        db,
        document_id=document_id,
        org_id=current_user.org_id,
        user_id=current_user.user_id,
        new_s3_key=body.s3_key,
        file_size=body.file_size_bytes,
        checksum=body.checksum_sha256,
    )
    await db.commit()
    await db.refresh(version)
    logger.info(
        "doc_version.created",
        document_id=str(document_id),
        version=version.version_number,
        org_id=str(current_user.org_id),
    )
    return DocumentVersionResponse.model_validate(version)


@router.get("/{document_id}/versions", response_model=DocumentVersionListResponse)
async def list_versions(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a document in descending order."""
    versions = await service.list_versions(db, document_id=document_id, org_id=current_user.org_id)
    return DocumentVersionListResponse(
        items=[DocumentVersionResponse.model_validate(v) for v in versions],
        total=len(versions),
    )


@router.get("/{document_id}/versions/{version_id}", response_model=DocumentVersionResponse)
async def get_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific version record."""
    version = await service.get_version(db, version_id=version_id, org_id=current_user.org_id)
    if not version or version.document_id != document_id:
        raise HTTPException(status_code=404, detail="Version not found")
    return DocumentVersionResponse.model_validate(version)


@router.get("/{document_id}/compare", response_model=CompareVersionsResponse)
async def compare_versions(
    document_id: uuid.UUID,
    v1: int = Query(..., description="Version number A"),
    v2: int = Query(..., description="Version number B"),
    current_user: CurrentUser = Depends(require_permission("view", "document")),
    db: AsyncSession = Depends(get_db),
):
    """Compare two versions of a document side-by-side."""
    ver_a, ver_b = await service.compare_versions(
        db,
        document_id=document_id,
        org_id=current_user.org_id,
        version_a_num=v1,
        version_b_num=v2,
    )
    if not ver_a or not ver_b:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    # Use ver_b's stored diff (it represents the change from A to B if they're sequential)
    # For non-sequential comparison we return the stored diff of B
    diff_stats = None
    diff_lines = ver_b.diff_lines or []
    if ver_b.diff_stats:
        diff_stats = DiffStats(**ver_b.diff_stats)

    return CompareVersionsResponse(
        version_a=DocumentVersionResponse.model_validate(ver_a),
        version_b=DocumentVersionResponse.model_validate(ver_b),
        diff_stats=diff_stats,
        diff_lines=diff_lines,
    )
