"""ResourceOwnership model — explicit object-level access control grants."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PermissionLevel(str, enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"


class ResourceOwnership(BaseModel):
    """Grants a specific user explicit access to a specific resource object.

    Used by check_object_permission() to decide whether viewer/analyst roles
    may access a resource they do not own by org membership alone.

    Admins and managers bypass this table entirely (see ROLE_HIERARCHY fast-path).
    """

    __tablename__ = "resource_ownership"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # e.g. "project", "deal_room", "document", "conversation", "lp_report"
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    permission_level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PermissionLevel.VIEWER.value,
        server_default=PermissionLevel.VIEWER.value,
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "resource_type",
            "resource_id",
            name="uq_resource_ownership_user_type_id",
        ),
        Index("ix_resource_ownership_type_id", "resource_type", "resource_id"),
        Index("ix_resource_ownership_user_type", "user_id", "resource_type"),
    )
