"""Legal models: LegalDocument, LegalTemplate."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import LegalDocumentStatus, LegalDocumentType


class LegalDocument(BaseModel):
    __tablename__ = "legal_documents"
    __table_args__ = (
        Index("ix_legal_documents_org_id", "org_id"),
        Index("ix_legal_documents_project_id", "project_id"),
        Index("ix_legal_documents_status", "status"),
        Index("ix_legal_documents_doc_type", "doc_type"),
        Index("ix_legal_documents_org_id_status", "org_id", "status"),
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
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_templates.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[LegalDocumentType] = mapped_column(nullable=False)
    status: Mapped[LegalDocumentStatus] = mapped_column(
        nullable=False, default=LegalDocumentStatus.DRAFT
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    s3_key: Mapped[str | None] = mapped_column(String(1000))
    counterparty_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
    )
    signed_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    def __repr__(self) -> str:
        return f"<LegalDocument(id={self.id}, title={self.title!r}, status={self.status.value})>"


class LegalTemplate(BaseModel):
    __tablename__ = "legal_templates"
    __table_args__ = (
        Index("ix_legal_templates_org_id", "org_id"),
        Index("ix_legal_templates_doc_type", "doc_type"),
    )

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[LegalDocumentType] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<LegalTemplate(id={self.id}, name={self.name!r})>"
