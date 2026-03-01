"""OrgApiKey model — per-org API keys for programmatic access (e.g. Excel Add-in)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class OrgApiKey(Base, ModelMixin):
    """Hashed API key scoped to an organisation.

    The raw key is shown once at creation time; only the SHA-256 hash is
    persisted so that a DB breach does not expose live credentials.
    """

    __tablename__ = "org_api_keys"
    __table_args__ = (
        UniqueConstraint("key_hash", name="uq_org_api_keys_key_hash"),
        Index("ix_org_api_keys_org_id", "org_id"),
        Index("ix_org_api_keys_key_hash", "key_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    # Human-readable label, e.g. "Excel Add-in", "CRM Integration"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # SHA-256 hex digest of the raw key
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # First 8 chars of raw key — safe to display in the UI for identification
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    # Allowed operations: "read", "write"
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=["read"],
        server_default="{read}",
    )
    rate_limit_per_min: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Stamped on every successful authentication (best-effort)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # NULL means the key never expires
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<OrgApiKey(id={self.id}, prefix={self.key_prefix!r}, org={self.org_id})>"
