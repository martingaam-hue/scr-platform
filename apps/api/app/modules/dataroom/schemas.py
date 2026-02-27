"""Pydantic schemas for Data Room endpoints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    DocumentAccessAction,
    DocumentClassification,
    DocumentStatus,
    ExtractionType,
)

# ── Constants ────────────────────────────────────────────────────────────────

ALLOWED_FILE_TYPES = {"pdf", "docx", "xlsx", "pptx", "csv", "jpg", "png"}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

MIME_TYPE_MAP: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
    "jpg": "image/jpeg",
    "png": "image/png",
}


# ── Folders ──────────────────────────────────────────────────────────────────


class FolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_folder_id: uuid.UUID | None = None
    project_id: uuid.UUID


class FolderUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    parent_folder_id: uuid.UUID | None = None


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    project_id: uuid.UUID | None
    parent_folder_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class FolderTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    parent_folder_id: uuid.UUID | None
    document_count: int = 0
    children: list["FolderTreeNode"] = []


# ── Documents ────────────────────────────────────────────────────────────────


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=500)
    file_type: str
    file_size_bytes: int = Field(..., gt=0)
    project_id: uuid.UUID
    folder_id: uuid.UUID | None = None
    checksum_sha256: str = Field(..., min_length=64, max_length=64)

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        v = v.lower().lstrip(".")
        if v not in ALLOWED_FILE_TYPES:
            raise ValueError(
                f"File type '{v}' not allowed. Allowed: {', '.join(sorted(ALLOWED_FILE_TYPES))}"
            )
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {v} bytes exceeds maximum of {MAX_FILE_SIZE_BYTES} bytes (100 MB)"
            )
        return v


class PresignedUploadResponse(BaseModel):
    upload_url: str
    document_id: uuid.UUID
    s3_key: str


class UploadConfirmRequest(BaseModel):
    document_id: uuid.UUID


class UploadConfirmResponse(BaseModel):
    document_id: uuid.UUID
    status: DocumentStatus
    message: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    name: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    classification: DocumentClassification | None = None
    version: int
    parent_version_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    checksum_sha256: str
    watermark_enabled: bool
    metadata: dict[str, Any] | None = None
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    extractions: list["ExtractionResponse"] = []
    version_count: int = 1


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    folder_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None
    watermark_enabled: bool | None = None


class PresignedDownloadResponse(BaseModel):
    download_url: str
    expires_in: int = 3600  # seconds


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: int
    file_size_bytes: int
    status: DocumentStatus
    checksum_sha256: str
    uploaded_by: uuid.UUID
    created_at: datetime


class NewVersionRequest(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=500)
    file_type: str
    file_size_bytes: int = Field(..., gt=0)
    checksum_sha256: str = Field(..., min_length=64, max_length=64)

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        v = v.lower().lstrip(".")
        if v not in ALLOWED_FILE_TYPES:
            raise ValueError(
                f"File type '{v}' not allowed. Allowed: {', '.join(sorted(ALLOWED_FILE_TYPES))}"
            )
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {v} bytes exceeds maximum of {MAX_FILE_SIZE_BYTES} bytes (100 MB)"
            )
        return v


# ── Access Log ───────────────────────────────────────────────────────────────


class AccessLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    action: DocumentAccessAction
    ip_address: str | None = None
    timestamp: datetime


class AccessLogListResponse(BaseModel):
    items: list[AccessLogResponse]
    total: int


# ── Bulk Operations ─────────────────────────────────────────────────────────


class BulkUploadFileItem(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=500)
    file_type: str
    file_size_bytes: int = Field(..., gt=0)
    checksum_sha256: str = Field(..., min_length=64, max_length=64)

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        v = v.lower().lstrip(".")
        if v not in ALLOWED_FILE_TYPES:
            raise ValueError(f"File type '{v}' not allowed.")
        return v

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        if v > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds 100 MB limit.")
        return v


class BulkUploadRequest(BaseModel):
    files: list[BulkUploadFileItem] = Field(..., min_length=1, max_length=50)
    project_id: uuid.UUID
    folder_id: uuid.UUID | None = None


class BulkUploadResponse(BaseModel):
    uploads: list[PresignedUploadResponse]


class BulkMoveRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    target_folder_id: uuid.UUID


class BulkDeleteRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=100)


class BulkOperationResponse(BaseModel):
    success_count: int
    failure_count: int
    errors: list[str] = []


# ── AI Extraction ────────────────────────────────────────────────────────────


class ExtractionRequest(BaseModel):
    extraction_types: list[ExtractionType] | None = None  # None = run all types


class ExtractionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    extraction_type: ExtractionType
    result: dict[str, Any]
    model_used: str
    confidence_score: float
    tokens_used: int
    processing_time_ms: int
    created_at: datetime


class ExtractionListResponse(BaseModel):
    items: list[ExtractionResponse]


class ProjectExtractionSummary(BaseModel):
    project_id: uuid.UUID
    document_count: int
    extraction_count: int
    kpis: list[dict[str, Any]] = []
    deadlines: list[dict[str, Any]] = []
    financials: list[dict[str, Any]] = []
    classifications: dict[str, int] = {}  # classification -> count
    summaries: list[dict[str, Any]] = []


# ── Sharing ──────────────────────────────────────────────────────────────────


class ShareCreateRequest(BaseModel):
    document_id: uuid.UUID
    expires_at: datetime | None = None
    password: str | None = Field(None, min_length=4, max_length=128)
    watermark_enabled: bool = False
    allow_download: bool = True
    max_views: int | None = Field(None, gt=0)


class ShareResponse(BaseModel):
    id: uuid.UUID
    share_token: str
    document_id: uuid.UUID
    expires_at: datetime | None = None
    watermark_enabled: bool
    allow_download: bool
    max_views: int | None = None
    view_count: int
    is_active: bool
    created_at: datetime


class ShareAccessResponse(BaseModel):
    document_name: str
    file_type: str
    file_size_bytes: int
    allow_download: bool
    watermark_enabled: bool


class ShareAccessRequest(BaseModel):
    password: str | None = None
