"""Document Version Control — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DiffStats(BaseModel):
    additions: int
    deletions: int
    similarity: float
    total_changes: int


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    org_id: uuid.UUID
    version_number: int
    s3_key: str
    file_size_bytes: int | None
    checksum_sha256: str | None
    uploaded_by: uuid.UUID | None
    diff_stats: dict[str, Any] | None
    diff_lines: list[str] | None
    change_summary: str | None
    change_significance: str | None
    key_changes: list[str] | None
    created_at: datetime


class DocumentVersionListResponse(BaseModel):
    items: list[DocumentVersionResponse]
    total: int


class CompareVersionsResponse(BaseModel):
    version_a: DocumentVersionResponse
    version_b: DocumentVersionResponse
    diff_stats: DiffStats | None
    diff_lines: list[str]


class CreateVersionRequest(BaseModel):
    """Body for creating a new version record (after file has been uploaded to S3)."""
    s3_key: str
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None
