"""Data Room models: Document, DocumentFolder, DocumentExtraction, DocumentAccessLog."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseModel, ModelMixin, TimestampedModel
from app.models.enums import DocumentAccessAction, DocumentClassification, DocumentStatus, ExtractionType


class Document(BaseModel):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_org_id", "org_id"),
        Index("ix_documents_project_id", "project_id"),
        Index("ix_documents_portfolio_id", "portfolio_id"),
        Index("ix_documents_folder_id", "folder_id"),
        Index("ix_documents_org_id_status", "org_id", "status"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_folders.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
    )
    status: Mapped[DocumentStatus] = mapped_column(
        nullable=False, default=DocumentStatus.UPLOADING
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[DocumentClassification | None] = mapped_column(nullable=True)
    watermark_enabled: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    # Relationships
    folder: Mapped["DocumentFolder | None"] = relationship(back_populates="documents")
    extractions: Mapped[list["DocumentExtraction"]] = relationship(back_populates="document")
    parent_version: Mapped["Document | None"] = relationship(remote_side="Document.id")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, name={self.name!r}, status={self.status.value})>"


class DocumentFolder(BaseModel):
    __tablename__ = "document_folders"
    __table_args__ = (
        Index("ix_document_folders_org_id", "org_id"),
        Index("ix_document_folders_project_id", "project_id"),
        Index("ix_document_folders_parent", "parent_folder_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
    )
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_folders.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="folder")
    children: Mapped[list["DocumentFolder"]] = relationship(
        back_populates="parent_folder",
    )
    parent_folder: Mapped["DocumentFolder | None"] = relationship(
        back_populates="children",
        remote_side="DocumentFolder.id",
    )

    def __repr__(self) -> str:
        return f"<DocumentFolder(id={self.id}, name={self.name!r})>"


class DocumentExtraction(TimestampedModel):
    __tablename__ = "document_extractions"
    __table_args__ = (
        Index("ix_document_extractions_document_id", "document_id"),
        Index("ix_document_extractions_type", "extraction_type"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    extraction_type: Mapped[ExtractionType] = mapped_column(nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="extractions")


class DocumentAccessLog(Base, ModelMixin):
    """Immutable access log for documents."""

    __tablename__ = "document_access_logs"
    __table_args__ = (
        Index("ix_document_access_logs_document_id", "document_id"),
        Index("ix_document_access_logs_user_id", "user_id"),
        Index("ix_document_access_logs_org_id", "org_id"),
        Index("ix_document_access_logs_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[DocumentAccessAction] = mapped_column(nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    timestamp: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )


class ShareLink(BaseModel):
    """Shareable link for document access with optional restrictions."""

    __tablename__ = "share_links"
    __table_args__ = (
        Index("ix_share_links_token", "share_token", unique=True),
        Index("ix_share_links_document_id", "document_id"),
        Index("ix_share_links_org_id", "org_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    share_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    watermark_enabled: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    allow_download: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    max_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship()

    def __repr__(self) -> str:
        return f"<ShareLink(id={self.id}, token={self.share_token[:8]}...)>"
