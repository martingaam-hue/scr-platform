"""Core models: Organization, User, AuditLog, Notification."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BaseModel, ModelMixin, TimestampedModel
from app.models.enums import (
    NotificationType,
    OrgType,
    SubscriptionStatus,
    SubscriptionTier,
    UserRole,
)


class Organization(BaseModel):
    __tablename__ = "organizations"
    __table_args__ = (
        Index("ix_organizations_slug", "slug", unique=True),
        Index("ix_organizations_type", "type"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    type: Mapped[OrgType] = mapped_column(nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(512))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        nullable=False, default=SubscriptionTier.FOUNDATION
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        nullable=False, default=SubscriptionStatus.TRIAL
    )
    # Per-org AI spend cap in USD/month (NULL = use tier default from settings)
    ai_monthly_budget: Mapped[float | None] = mapped_column()

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="organization", foreign_keys="[Project.org_id]"
    )
    portfolios: Mapped[list["Portfolio"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="organization"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name!r}, type={self.type.value})>"


class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_org_id", "org_id"),
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_external_auth_id", "external_auth_id", unique=True),
        Index("ix_users_org_id_role", "org_id", "role"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(nullable=False, default=UserRole.VIEWER)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    mfa_enabled: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    external_auth_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    last_login_at: Mapped[datetime | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="users")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r}, role={self.role.value})>"


class AuditLog(Base, ModelMixin):
    """Immutable audit log. No updated_at, no soft delete."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_org_id", "org_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action!r}, entity_type={self.entity_type!r})>"


class Notification(TimestampedModel):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_org_id", "org_id"),
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(1000))
    is_read: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
