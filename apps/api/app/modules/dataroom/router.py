"""Data Room API router: folders, documents, bulk ops, AI extraction, sharing."""

import uuid
from math import ceil

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.models.enums import DocumentAccessAction, DocumentStatus, ExtractionType
from app.modules.dataroom import service
from app.modules.dataroom.schemas import (
    AccessLogListResponse,
    AccessLogResponse,
    BulkDeleteRequest,
    BulkMoveRequest,
    BulkOperationResponse,
    BulkUploadRequest,
    BulkUploadResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentVersionResponse,
    ExtractionListResponse,
    ExtractionRequest,
    ExtractionResponse,
    FolderCreateRequest,
    FolderResponse,
    FolderTreeNode,
    FolderUpdateRequest,
    NewVersionRequest,
    PresignedDownloadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    ProjectExtractionSummary,
    ShareAccessRequest,
    ShareAccessResponse,
    ShareCreateRequest,
    ShareResponse,
    UploadConfirmRequest,
    UploadConfirmResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/dataroom", tags=["dataroom"])


# ── Folders ──────────────────────────────────────────────────────────────────


@router.post(
    "/folders",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def create_folder(
    body: FolderCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new folder within a project."""
    try:
        folder = await service.create_folder(
            db=db,
            current_user=current_user,
            name=body.name,
            project_id=body.project_id,
            parent_folder_id=body.parent_folder_id,
        )
        return FolderResponse(
            id=folder.id,
            name=folder.name,
            project_id=folder.project_id,
            parent_folder_id=folder.parent_folder_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/folders/{project_id}",
    response_model=list[FolderTreeNode],
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_folder_tree(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full folder tree for a project, including document counts."""
    return await service.get_folder_tree(db, current_user.org_id, project_id)


@router.put(
    "/folders/{folder_id}",
    response_model=FolderResponse,
    dependencies=[Depends(require_permission("edit", "document"))],
)
async def update_folder(
    folder_id: uuid.UUID,
    body: FolderUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename or move a folder."""
    try:
        folder = await service.update_folder(
            db=db,
            folder_id=folder_id,
            org_id=current_user.org_id,
            name=body.name,
            parent_folder_id=body.parent_folder_id,
        )
        return FolderResponse(
            id=folder.id,
            name=folder.name,
            project_id=folder.project_id,
            parent_folder_id=folder.parent_folder_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/folders/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("delete", "document"))],
)
async def delete_folder(
    folder_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a folder. Must be empty."""
    try:
        await service.delete_folder(db, folder_id, current_user.org_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Document Upload ──────────────────────────────────────────────────────────


@router.post(
    "/upload/presigned",
    response_model=PresignedUploadResponse,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def get_presigned_upload_url(
    body: PresignedUploadRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an S3 pre-signed upload URL. Client uploads directly to S3."""
    try:
        upload_url, doc = await service.generate_presigned_upload(
            db=db,
            current_user=current_user,
            file_name=body.file_name,
            file_type=body.file_type,
            file_size_bytes=body.file_size_bytes,
            project_id=body.project_id,
            checksum_sha256=body.checksum_sha256,
            folder_id=body.folder_id,
        )
        return PresignedUploadResponse(
            upload_url=upload_url,
            document_id=doc.id,
            s3_key=doc.s3_key,
        )
    except Exception as e:
        logger.error("presigned_upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post(
    "/upload/confirm",
    response_model=UploadConfirmResponse,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def confirm_upload(
    body: UploadConfirmRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm S3 upload completed. Triggers document processing pipeline."""
    try:
        doc = await service.confirm_upload(db, body.document_id, current_user.org_id)

        # Trigger async processing
        from app.modules.dataroom.tasks import process_document
        process_document.delay(str(doc.id))

        return UploadConfirmResponse(
            document_id=doc.id,
            status=doc.status,
            message="Upload confirmed. Document processing has been queued.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Document CRUD ────────────────────────────────────────────────────────────


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def list_documents(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    project_id: uuid.UUID | None = Query(None),
    folder_id: uuid.UUID | None = Query(None),
    file_type: str | None = Query(None),
    doc_status: DocumentStatus | None = Query(None, alias="status"),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """List documents with filtering, pagination, and sorting."""
    items, total = await service.list_documents(
        db=db,
        org_id=current_user.org_id,
        project_id=project_id,
        folder_id=folder_id,
        file_type=file_type,
        status=doc_status,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return DocumentListResponse(
        items=[_doc_to_response(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document details including extractions."""
    try:
        doc = await service.get_document_detail(db, document_id, current_user.org_id)

        # Log view access
        await service.log_document_access(
            db=db,
            document_id=document_id,
            user_id=current_user.user_id,
            org_id=current_user.org_id,
            action=DocumentAccessAction.VIEW,
            ip_address=request.client.host if request.client else None,
        )

        extractions = [
            ExtractionResponse(
                id=e.id,
                document_id=e.document_id,
                extraction_type=e.extraction_type,
                result=e.result,
                model_used=e.model_used,
                confidence_score=e.confidence_score,
                tokens_used=e.tokens_used,
                processing_time_ms=e.processing_time_ms,
                created_at=e.created_at,
            )
            for e in doc.extractions
        ]

        # Count versions
        versions = await service.list_versions(db, document_id, current_user.org_id)

        resp = _doc_to_response(doc)
        return DocumentDetailResponse(
            **resp.model_dump(),
            extractions=extractions,
            version_count=len(versions),
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/documents/{document_id}/download",
    response_model=PresignedDownloadResponse,
    dependencies=[Depends(require_permission("download", "document"))],
)
async def download_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a pre-signed download URL. Access is logged."""
    try:
        url = await service.generate_download_url(
            db=db,
            document_id=document_id,
            org_id=current_user.org_id,
            user_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
        )
        return PresignedDownloadResponse(download_url=url)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("edit", "document"))],
)
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update document metadata, move to folder, toggle watermark."""
    try:
        doc = await service.update_document(
            db=db,
            document_id=document_id,
            org_id=current_user.org_id,
            name=body.name,
            folder_id=body.folder_id,
            metadata=body.metadata,
            watermark_enabled=body.watermark_enabled,
        )
        return _doc_to_response(doc)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("delete", "document"))],
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a document."""
    try:
        await service.soft_delete_document(db, document_id, current_user.org_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Versioning ───────────────────────────────────────────────────────────────


@router.post(
    "/documents/{document_id}/versions",
    response_model=PresignedUploadResponse,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def create_new_version(
    document_id: uuid.UUID,
    body: NewVersionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new version of a document. Returns a pre-signed upload URL."""
    try:
        upload_url, doc = await service.create_new_version(
            db=db,
            current_user=current_user,
            parent_document_id=document_id,
            file_name=body.file_name,
            file_type=body.file_type,
            file_size_bytes=body.file_size_bytes,
            checksum_sha256=body.checksum_sha256,
        )
        return PresignedUploadResponse(
            upload_url=upload_url,
            document_id=doc.id,
            s3_key=doc.s3_key,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/documents/{document_id}/versions",
    response_model=list[DocumentVersionResponse],
    dependencies=[Depends(require_permission("view", "document"))],
)
async def list_versions(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a document."""
    try:
        versions = await service.list_versions(db, document_id, current_user.org_id)
        return [
            DocumentVersionResponse(
                id=v.id,
                name=v.name,
                version=v.version,
                file_size_bytes=v.file_size_bytes,
                status=v.status,
                checksum_sha256=v.checksum_sha256,
                uploaded_by=v.uploaded_by,
                created_at=v.created_at,
            )
            for v in versions
        ]
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/documents/{document_id}/access-log",
    response_model=AccessLogListResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_access_log(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """View who accessed this document and when."""
    items, total = await service.get_access_log(
        db, document_id, current_user.org_id, limit=limit, offset=offset
    )
    return AccessLogListResponse(
        items=[
            AccessLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                ip_address=log.ip_address,
                timestamp=log.timestamp,
            )
            for log in items
        ],
        total=total,
    )


# ── Bulk Operations ─────────────────────────────────────────────────────────


@router.post(
    "/bulk/upload",
    response_model=BulkUploadResponse,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def bulk_upload(
    body: BulkUploadRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate pre-signed upload URLs for multiple files."""
    uploads = []
    for file_item in body.files:
        upload_url, doc = await service.generate_presigned_upload(
            db=db,
            current_user=current_user,
            file_name=file_item.file_name,
            file_type=file_item.file_type,
            file_size_bytes=file_item.file_size_bytes,
            project_id=body.project_id,
            checksum_sha256=file_item.checksum_sha256,
            folder_id=body.folder_id,
        )
        uploads.append(PresignedUploadResponse(
            upload_url=upload_url,
            document_id=doc.id,
            s3_key=doc.s3_key,
        ))
    return BulkUploadResponse(uploads=uploads)


@router.post(
    "/bulk/move",
    response_model=BulkOperationResponse,
    dependencies=[Depends(require_permission("edit", "document"))],
)
async def bulk_move(
    body: BulkMoveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move multiple documents to a target folder."""
    try:
        success, errors = await service.bulk_move(
            db, body.document_ids, body.target_folder_id, current_user.org_id
        )
        return BulkOperationResponse(
            success_count=success,
            failure_count=len(errors),
            errors=errors,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/bulk/delete",
    response_model=BulkOperationResponse,
    dependencies=[Depends(require_permission("delete", "document"))],
)
async def bulk_delete(
    body: BulkDeleteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete multiple documents."""
    success, errors = await service.bulk_delete(
        db, body.document_ids, current_user.org_id
    )
    return BulkOperationResponse(
        success_count=success,
        failure_count=len(errors),
        errors=errors,
    )


# ── AI Extraction ────────────────────────────────────────────────────────────


@router.post(
    "/documents/{document_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def trigger_extraction(
    document_id: uuid.UUID,
    body: ExtractionRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI extraction (or re-extraction) for a document."""
    try:
        # Verify document exists and belongs to org
        await service.get_document_detail(db, document_id, current_user.org_id)

        from app.modules.dataroom.tasks import trigger_extraction as trigger_task
        extraction_types = (
            [t.value for t in body.extraction_types] if body and body.extraction_types else None
        )
        trigger_task.delay(str(document_id), extraction_types)

        return {"message": "Extraction queued", "document_id": str(document_id)}
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/documents/{document_id}/extractions",
    response_model=ExtractionListResponse,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_extractions(
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all extraction results for a document."""
    try:
        extractions = await service.get_extractions(db, document_id, current_user.org_id)
        return ExtractionListResponse(
            items=[
                ExtractionResponse(
                    id=e.id,
                    document_id=e.document_id,
                    extraction_type=e.extraction_type,
                    result=e.result,
                    model_used=e.model_used,
                    confidence_score=e.confidence_score,
                    tokens_used=e.tokens_used,
                    processing_time_ms=e.processing_time_ms,
                    created_at=e.created_at,
                )
                for e in extractions
            ]
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/extractions/summary/{project_id}",
    response_model=ProjectExtractionSummary,
    dependencies=[Depends(require_permission("view", "document"))],
)
async def get_project_extraction_summary(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated extraction results for all documents in a project."""
    summary = await service.get_project_extraction_summary(
        db, project_id, current_user.org_id
    )
    return ProjectExtractionSummary(**summary)


# ── Sharing ──────────────────────────────────────────────────────────────────


@router.post(
    "/share",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("upload", "document"))],
)
async def create_share_link(
    body: ShareCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a sharing link for a document."""
    try:
        share = await service.create_share_link(
            db=db,
            current_user=current_user,
            document_id=body.document_id,
            expires_at=body.expires_at,
            password=body.password,
            watermark_enabled=body.watermark_enabled,
            allow_download=body.allow_download,
            max_views=body.max_views,
        )
        return ShareResponse(
            id=share.id,
            share_token=share.share_token,
            document_id=share.document_id,
            expires_at=share.expires_at,
            watermark_enabled=share.watermark_enabled,
            allow_download=share.allow_download,
            max_views=share.max_views,
            view_count=share.view_count,
            is_active=not share.is_deleted,
            created_at=share.created_at,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/share/{share_token}", response_model=ShareAccessResponse)
async def access_share_link(
    share_token: str,
    password: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Access a shared document via share token. No auth required."""
    try:
        share, doc = await service.access_share_link(db, share_token, password)
        return ShareAccessResponse(
            document_name=doc.name,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            allow_download=share.allow_download,
            watermark_enabled=share.watermark_enabled,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete(
    "/share/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("delete", "document"))],
)
async def revoke_share_link(
    share_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a sharing link."""
    try:
        await service.revoke_share_link(db, share_id, current_user.org_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Helpers ──────────────────────────────────────────────────────────────────


def _doc_to_response(doc) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        name=doc.name,
        file_type=doc.file_type,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status,
        classification=doc.classification,
        version=doc.version,
        parent_version_id=doc.parent_version_id,
        project_id=doc.project_id,
        folder_id=doc.folder_id,
        checksum_sha256=doc.checksum_sha256,
        watermark_enabled=doc.watermark_enabled,
        metadata=doc.metadata_,
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
