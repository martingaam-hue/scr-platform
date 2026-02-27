"""Data Room business logic: S3 operations, folder management, document processing."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

import boto3
import structlog
from botocore.config import Config as BotoConfig
from sqlalchemy import Select, and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.middleware.tenant import tenant_filter
from app.models.dataroom import (
    Document,
    DocumentAccessLog,
    DocumentExtraction,
    DocumentFolder,
    ShareLink,
)
from app.models.enums import (
    DocumentAccessAction,
    DocumentClassification,
    DocumentStatus,
    ExtractionType,
)
from app.modules.dataroom.schemas import (
    MIME_TYPE_MAP,
    FolderTreeNode,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()


# ── S3 Client ────────────────────────────────────────────────────────────────


def _get_s3_client():
    """Create a boto3 S3 client configured for MinIO / AWS."""
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


# ── Folder Service ───────────────────────────────────────────────────────────


async def create_folder(
    db: AsyncSession,
    current_user: CurrentUser,
    name: str,
    project_id: uuid.UUID,
    parent_folder_id: uuid.UUID | None = None,
) -> DocumentFolder:
    """Create a new folder, validating parent belongs to same org."""
    if parent_folder_id:
        parent = await _get_folder_or_raise(db, parent_folder_id, current_user.org_id)
        if parent.project_id != project_id:
            raise ValueError("Parent folder belongs to a different project")

    folder = DocumentFolder(
        org_id=current_user.org_id,
        project_id=project_id,
        parent_folder_id=parent_folder_id,
        name=name,
    )
    db.add(folder)
    await db.flush()
    return folder


async def get_folder_tree(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[FolderTreeNode]:
    """Return nested folder structure with document counts for a project."""
    # Load all folders for this project
    stmt = (
        select(DocumentFolder)
        .where(
            DocumentFolder.project_id == project_id,
            DocumentFolder.is_deleted.is_(False),
        )
    )
    stmt = tenant_filter(stmt, org_id, DocumentFolder)
    result = await db.execute(stmt)
    folders = list(result.scalars().all())

    # Count documents per folder
    count_stmt = (
        select(Document.folder_id, func.count(Document.id))
        .where(
            Document.project_id == project_id,
            Document.is_deleted.is_(False),
            Document.folder_id.isnot(None),
        )
        .group_by(Document.folder_id)
    )
    count_stmt = tenant_filter(count_stmt, org_id, Document)
    count_result = await db.execute(count_stmt)
    doc_counts: dict[uuid.UUID, int] = dict(count_result.all())

    # Also count documents with no folder (root-level)
    root_count_stmt = (
        select(func.count(Document.id))
        .where(
            Document.project_id == project_id,
            Document.is_deleted.is_(False),
            Document.folder_id.is_(None),
        )
    )
    root_count_stmt = tenant_filter(root_count_stmt, org_id, Document)

    # Build tree
    folder_map: dict[uuid.UUID, FolderTreeNode] = {}
    for f in folders:
        folder_map[f.id] = FolderTreeNode(
            id=f.id,
            name=f.name,
            parent_folder_id=f.parent_folder_id,
            document_count=doc_counts.get(f.id, 0),
        )

    # Link children to parents
    roots: list[FolderTreeNode] = []
    for node in folder_map.values():
        if node.parent_folder_id and node.parent_folder_id in folder_map:
            folder_map[node.parent_folder_id].children.append(node)
        else:
            roots.append(node)

    return roots


async def update_folder(
    db: AsyncSession,
    folder_id: uuid.UUID,
    org_id: uuid.UUID,
    name: str | None = None,
    parent_folder_id: uuid.UUID | None = None,
) -> DocumentFolder:
    folder = await _get_folder_or_raise(db, folder_id, org_id)

    if name is not None:
        folder.name = name
    if parent_folder_id is not None:
        # Prevent circular references
        if parent_folder_id == folder_id:
            raise ValueError("Folder cannot be its own parent")
        folder.parent_folder_id = parent_folder_id

    await db.flush()
    await db.refresh(folder)
    return folder


async def delete_folder(
    db: AsyncSession,
    folder_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    """Soft-delete a folder. Must be empty (no docs, no child folders)."""
    folder = await _get_folder_or_raise(db, folder_id, org_id)

    # Check for documents
    doc_count_stmt = (
        select(func.count(Document.id))
        .where(Document.folder_id == folder_id, Document.is_deleted.is_(False))
    )
    result = await db.execute(doc_count_stmt)
    if result.scalar_one() > 0:
        raise ValueError("Cannot delete folder: contains documents")

    # Check for child folders
    child_count_stmt = (
        select(func.count(DocumentFolder.id))
        .where(
            DocumentFolder.parent_folder_id == folder_id,
            DocumentFolder.is_deleted.is_(False),
        )
    )
    result = await db.execute(child_count_stmt)
    if result.scalar_one() > 0:
        raise ValueError("Cannot delete folder: contains subfolders")

    folder.is_deleted = True
    await db.flush()


async def _get_folder_or_raise(
    db: AsyncSession, folder_id: uuid.UUID, org_id: uuid.UUID
) -> DocumentFolder:
    stmt = select(DocumentFolder).where(
        DocumentFolder.id == folder_id,
        DocumentFolder.is_deleted.is_(False),
    )
    stmt = tenant_filter(stmt, org_id, DocumentFolder)
    result = await db.execute(stmt)
    folder = result.scalar_one_or_none()
    if folder is None:
        raise LookupError(f"Folder {folder_id} not found")
    return folder


# ── Document Upload ──────────────────────────────────────────────────────────


async def generate_presigned_upload(
    db: AsyncSession,
    current_user: CurrentUser,
    file_name: str,
    file_type: str,
    file_size_bytes: int,
    project_id: uuid.UUID,
    checksum_sha256: str,
    folder_id: uuid.UUID | None = None,
) -> tuple[str, Document]:
    """Create a Document record in UPLOADING state and return a pre-signed PUT URL."""
    file_uuid = uuid.uuid4()
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    folder_segment = str(folder_id) if folder_id else "root"
    s3_key = f"{current_user.org_id}/{project_id}/{folder_segment}/{file_uuid}_{safe_name}"

    mime_type = MIME_TYPE_MAP.get(file_type, "application/octet-stream")

    doc = Document(
        org_id=current_user.org_id,
        project_id=project_id,
        folder_id=folder_id,
        name=file_name,
        file_type=file_type,
        mime_type=mime_type,
        s3_key=s3_key,
        s3_bucket=settings.AWS_S3_BUCKET,
        file_size_bytes=file_size_bytes,
        status=DocumentStatus.UPLOADING,
        uploaded_by=current_user.user_id,
        checksum_sha256=checksum_sha256,
    )
    db.add(doc)
    await db.flush()

    s3 = _get_s3_client()
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": s3_key,
            "ContentType": mime_type,
        },
        ExpiresIn=3600,
    )

    return upload_url, doc


async def confirm_upload(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Document:
    """Mark document as PROCESSING after client confirms S3 upload completed."""
    doc = await _get_document_or_raise(db, document_id, org_id)

    if doc.status != DocumentStatus.UPLOADING:
        raise ValueError(f"Document is in '{doc.status.value}' state, expected 'uploading'")

    # Verify file exists in S3
    s3 = _get_s3_client()
    try:
        head = s3.head_object(Bucket=doc.s3_bucket, Key=doc.s3_key)
        actual_size = head["ContentLength"]
        # Update size if different (S3 is source of truth)
        if actual_size != doc.file_size_bytes:
            doc.file_size_bytes = actual_size
    except s3.exceptions.ClientError:
        doc.status = DocumentStatus.ERROR
        doc.metadata_ = {"error": "File not found in S3 after upload confirmation"}
        await db.flush()
        raise ValueError("File not found in S3. Upload may have failed.")

    # Virus scan placeholder
    _scan_for_viruses(doc.s3_bucket, doc.s3_key)

    doc.status = DocumentStatus.PROCESSING
    await db.flush()
    return doc


def _scan_for_viruses(bucket: str, key: str) -> None:
    """Placeholder for virus scanning integration (e.g. ClamAV)."""
    logger.info("virus_scan_placeholder", bucket=bucket, key=key, result="skipped")


# ── Document CRUD ────────────────────────────────────────────────────────────


async def list_documents(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    folder_id: uuid.UUID | None = None,
    file_type: str | None = None,
    status: DocumentStatus | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[Document], int]:
    """List documents with filters, pagination, and sorting."""
    base = select(Document).where(Document.is_deleted.is_(False))
    base = tenant_filter(base, org_id, Document)

    if project_id:
        base = base.where(Document.project_id == project_id)
    if folder_id:
        base = base.where(Document.folder_id == folder_id)
    if file_type:
        base = base.where(Document.file_type == file_type)
    if status:
        base = base.where(Document.status == status)
    if search:
        base = base.where(Document.name.ilike(f"%{search}%"))

    # Count total
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Sort
    sort_col = getattr(Document, sort_by, Document.created_at)
    if sort_order == "asc":
        base = base.order_by(sort_col.asc())
    else:
        base = base.order_by(sort_col.desc())

    # Paginate
    base = base.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(base)
    return list(result.scalars().all()), total


async def get_document_detail(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Document:
    """Get document with extractions loaded."""
    stmt = (
        select(Document)
        .options(selectinload(Document.extractions))
        .where(Document.id == document_id, Document.is_deleted.is_(False))
    )
    stmt = tenant_filter(stmt, org_id, Document)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise LookupError(f"Document {document_id} not found")
    return doc


async def update_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
    name: str | None = None,
    folder_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    watermark_enabled: bool | None = None,
) -> Document:
    doc = await _get_document_or_raise(db, document_id, org_id)

    if name is not None:
        doc.name = name
    if folder_id is not None:
        doc.folder_id = folder_id
    if metadata is not None:
        existing = doc.metadata_ or {}
        existing.update(metadata)
        doc.metadata_ = existing
    if watermark_enabled is not None:
        doc.watermark_enabled = watermark_enabled

    await db.flush()
    await db.refresh(doc)
    return doc


async def soft_delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    doc = await _get_document_or_raise(db, document_id, org_id)
    doc.is_deleted = True
    await db.flush()


async def generate_download_url(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    ip_address: str | None = None,
) -> str:
    """Generate a pre-signed download URL and log access."""
    doc = await _get_document_or_raise(db, document_id, org_id)

    s3 = _get_s3_client()
    download_url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": doc.s3_bucket,
            "Key": doc.s3_key,
            "ResponseContentDisposition": f'attachment; filename="{doc.name}"',
        },
        ExpiresIn=3600,
    )

    # Log the access
    access_log = DocumentAccessLog(
        document_id=document_id,
        user_id=user_id,
        org_id=org_id,
        action=DocumentAccessAction.DOWNLOAD,
        ip_address=ip_address,
    )
    db.add(access_log)
    await db.flush()

    return download_url


# ── Versioning ───────────────────────────────────────────────────────────────


async def create_new_version(
    db: AsyncSession,
    current_user: CurrentUser,
    parent_document_id: uuid.UUID,
    file_name: str,
    file_type: str,
    file_size_bytes: int,
    checksum_sha256: str,
) -> tuple[str, Document]:
    """Create a new version of an existing document."""
    parent = await _get_document_or_raise(db, parent_document_id, current_user.org_id)

    # Determine next version number
    version_stmt = (
        select(func.max(Document.version))
        .where(
            # All versions share the same root parent or are the parent
            ((Document.parent_version_id == parent_document_id) | (Document.id == parent_document_id)),
            Document.is_deleted.is_(False),
        )
    )
    result = await db.execute(version_stmt)
    max_version = result.scalar_one() or parent.version

    upload_url, doc = await generate_presigned_upload(
        db=db,
        current_user=current_user,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        project_id=parent.project_id,  # type: ignore[arg-type]
        checksum_sha256=checksum_sha256,
        folder_id=parent.folder_id,
    )
    doc.parent_version_id = parent_document_id
    doc.version = max_version + 1
    await db.flush()
    return upload_url, doc


async def list_versions(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
) -> list[Document]:
    """List all versions of a document (including the root and all children)."""
    stmt = (
        select(Document)
        .where(
            ((Document.id == document_id) | (Document.parent_version_id == document_id)),
            Document.is_deleted.is_(False),
        )
        .order_by(Document.version.asc())
    )
    stmt = tenant_filter(stmt, org_id, Document)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Access Log ───────────────────────────────────────────────────────────────


async def get_access_log(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DocumentAccessLog], int]:
    base = select(DocumentAccessLog).where(
        DocumentAccessLog.document_id == document_id,
        DocumentAccessLog.org_id == org_id,
    )
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = base.order_by(DocumentAccessLog.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


# ── Bulk Operations ──────────────────────────────────────────────────────────


async def bulk_move(
    db: AsyncSession,
    document_ids: list[uuid.UUID],
    target_folder_id: uuid.UUID,
    org_id: uuid.UUID,
) -> tuple[int, list[str]]:
    """Move multiple documents to a target folder. Returns (success_count, errors)."""
    # Validate target folder exists
    await _get_folder_or_raise(db, target_folder_id, org_id)

    success = 0
    errors: list[str] = []
    for doc_id in document_ids:
        try:
            doc = await _get_document_or_raise(db, doc_id, org_id)
            doc.folder_id = target_folder_id
            success += 1
        except LookupError:
            errors.append(f"Document {doc_id} not found")

    await db.flush()
    return success, errors


async def bulk_delete(
    db: AsyncSession,
    document_ids: list[uuid.UUID],
    org_id: uuid.UUID,
) -> tuple[int, list[str]]:
    """Soft-delete multiple documents. Returns (success_count, errors)."""
    success = 0
    errors: list[str] = []
    for doc_id in document_ids:
        try:
            doc = await _get_document_or_raise(db, doc_id, org_id)
            doc.is_deleted = True
            success += 1
        except LookupError:
            errors.append(f"Document {doc_id} not found")

    await db.flush()
    return success, errors


# ── AI Extraction ────────────────────────────────────────────────────────────


async def get_extractions(
    db: AsyncSession,
    document_id: uuid.UUID,
    org_id: uuid.UUID,
) -> list[DocumentExtraction]:
    """Get all extractions for a document."""
    # Verify document belongs to org
    await _get_document_or_raise(db, document_id, org_id)

    stmt = (
        select(DocumentExtraction)
        .where(DocumentExtraction.document_id == document_id)
        .order_by(DocumentExtraction.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_project_extraction_summary(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict:
    """Aggregate all extractions for a project."""
    # Get all documents for this project
    doc_stmt = (
        select(Document.id)
        .where(
            Document.project_id == project_id,
            Document.is_deleted.is_(False),
        )
    )
    doc_stmt = tenant_filter(doc_stmt, org_id, Document)
    doc_result = await db.execute(doc_stmt)
    doc_ids = [row[0] for row in doc_result.all()]

    if not doc_ids:
        return {
            "project_id": project_id,
            "document_count": 0,
            "extraction_count": 0,
            "kpis": [],
            "deadlines": [],
            "financials": [],
            "classifications": {},
            "summaries": [],
        }

    # Fetch all extractions
    ext_stmt = (
        select(DocumentExtraction)
        .where(DocumentExtraction.document_id.in_(doc_ids))
        .order_by(DocumentExtraction.created_at.desc())
    )
    ext_result = await db.execute(ext_stmt)
    extractions = list(ext_result.scalars().all())

    # Categorize
    kpis = []
    deadlines = []
    financials = []
    summaries = []
    classifications: dict[str, int] = {}

    for ext in extractions:
        if ext.extraction_type == ExtractionType.KPI:
            kpis.append(ext.result)
        elif ext.extraction_type == ExtractionType.DEADLINE:
            deadlines.append(ext.result)
        elif ext.extraction_type == ExtractionType.FINANCIAL:
            financials.append(ext.result)
        elif ext.extraction_type == ExtractionType.SUMMARY:
            summaries.append(ext.result)
        elif ext.extraction_type == ExtractionType.CLASSIFICATION:
            label = ext.result.get("classification", "other")
            classifications[label] = classifications.get(label, 0) + 1

    return {
        "project_id": project_id,
        "document_count": len(doc_ids),
        "extraction_count": len(extractions),
        "kpis": kpis,
        "deadlines": deadlines,
        "financials": financials,
        "classifications": classifications,
        "summaries": summaries,
    }


# ── Sharing ──────────────────────────────────────────────────────────────────


async def create_share_link(
    db: AsyncSession,
    current_user: CurrentUser,
    document_id: uuid.UUID,
    expires_at: datetime | None = None,
    password: str | None = None,
    watermark_enabled: bool = False,
    allow_download: bool = True,
    max_views: int | None = None,
) -> ShareLink:
    """Create a sharing link for a document."""
    await _get_document_or_raise(db, document_id, current_user.org_id)

    token = secrets.token_urlsafe(32)
    password_hash = hashlib.sha256(password.encode()).hexdigest() if password else None

    # Strip timezone info — DB uses TIMESTAMP WITHOUT TIME ZONE (stores UTC)
    naive_expires = expires_at.replace(tzinfo=None) if expires_at and expires_at.tzinfo else expires_at

    share = ShareLink(
        document_id=document_id,
        org_id=current_user.org_id,
        created_by=current_user.user_id,
        share_token=token,
        expires_at=naive_expires,
        password_hash=password_hash,
        watermark_enabled=watermark_enabled,
        allow_download=allow_download,
        max_views=max_views,
    )
    db.add(share)
    await db.flush()

    # Log the share action
    access_log = DocumentAccessLog(
        document_id=document_id,
        user_id=current_user.user_id,
        org_id=current_user.org_id,
        action=DocumentAccessAction.SHARE,
    )
    db.add(access_log)
    await db.flush()

    return share


async def access_share_link(
    db: AsyncSession,
    share_token: str,
    password: str | None = None,
) -> tuple[ShareLink, Document]:
    """Validate and access a shared document. Returns (share_link, document)."""
    stmt = select(ShareLink).where(
        ShareLink.share_token == share_token,
        ShareLink.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()

    if share is None:
        raise LookupError("Share link not found or has been revoked")

    # Check expiration (DB stores naive UTC timestamps)
    if share.expires_at and share.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise PermissionError("Share link has expired")

    # Check max views
    if share.max_views and share.view_count >= share.max_views:
        raise PermissionError("Share link has reached maximum view count")

    # Check password
    if share.password_hash:
        if not password:
            raise PermissionError("Password required to access this document")
        if hashlib.sha256(password.encode()).hexdigest() != share.password_hash:
            raise PermissionError("Invalid password")

    # Load document
    doc_stmt = select(Document).where(
        Document.id == share.document_id,
        Document.is_deleted.is_(False),
    )
    doc_result = await db.execute(doc_stmt)
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise LookupError("Shared document no longer exists")

    # Increment view count
    share.view_count += 1
    await db.flush()

    return share, doc


async def revoke_share_link(
    db: AsyncSession,
    share_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    stmt = select(ShareLink).where(
        ShareLink.id == share_id,
        ShareLink.is_deleted.is_(False),
    )
    stmt = tenant_filter(stmt, org_id, ShareLink)
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if share is None:
        raise LookupError(f"Share link {share_id} not found")
    share.is_deleted = True
    await db.flush()


# ── Watermark ────────────────────────────────────────────────────────────────


def generate_watermark(pdf_bytes: bytes, user_name: str, timestamp: str) -> bytes:
    """Add diagonal watermark to a PDF. Returns watermarked PDF bytes.

    Uses reportlab to create the watermark overlay if available,
    otherwise returns the original bytes with a log warning.
    """
    try:
        import io

        from PyPDF2 import PdfReader, PdfWriter
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas as rl_canvas

        # Create watermark overlay
        packet = io.BytesIO()
        c = rl_canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica", 40)
        c.setFillAlpha(0.15)
        c.saveState()
        c.translate(300, 400)
        c.rotate(45)
        c.drawCentredString(0, 0, f"{user_name} — {timestamp}")
        c.restoreState()
        c.save()
        packet.seek(0)

        watermark_reader = PdfReader(packet)
        original_reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()

        for page in original_reader.pages:
            page.merge_page(watermark_reader.pages[0])
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    except ImportError:
        logger.warning("watermark_libraries_unavailable", detail="PyPDF2 or reportlab not installed")
        return pdf_bytes


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _get_document_or_raise(
    db: AsyncSession, document_id: uuid.UUID, org_id: uuid.UUID
) -> Document:
    stmt = select(Document).where(
        Document.id == document_id,
        Document.is_deleted.is_(False),
    )
    stmt = tenant_filter(stmt, org_id, Document)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if doc is None:
        raise LookupError(f"Document {document_id} not found")
    return doc


async def log_document_access(
    db: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    action: DocumentAccessAction,
    ip_address: str | None = None,
) -> None:
    """Record an immutable access log entry."""
    entry = DocumentAccessLog(
        document_id=document_id,
        user_id=user_id,
        org_id=org_id,
        action=action,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
