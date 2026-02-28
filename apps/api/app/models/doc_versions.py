"""Document Version Control model — append-only version history with diff and AI summaries."""

import uuid

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class DocumentVersion(TimestampedModel):
    """Append-only record of each uploaded version of a document.

    Stores the S3 key, a unified diff vs the previous version (first 500 lines),
    diff statistics, and an AI-generated change summary with significance rating.
    """

    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # File metadata
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Diff vs previous version
    diff_stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {additions: int, deletions: int, similarity: float, total_changes: int}
    diff_lines: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # First 500 lines of unified diff

    # AI-generated change summary
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_significance: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    # minor | moderate | major | critical
    key_changes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # e.g. ["Added indemnification clause", "Modified payment terms from Net-30 to Net-60"]

    __table_args__ = (
        Index("ix_doc_version_doc_num", "document_id", "version_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentVersion(id={self.id}, document_id={self.document_id}, "
            f"v={self.version_number})>"
        )
