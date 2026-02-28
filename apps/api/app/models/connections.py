"""Professional connections and introduction request models."""

import uuid
from datetime import date

from sqlalchemy import Date, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ProfessionalConnection(BaseModel):
    __tablename__ = "professional_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    connection_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # advisor, co_investor, service_provider, board_member, lp_relationship
    connected_org_name: Mapped[str] = mapped_column(String(200), nullable=False)
    connected_person_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    connected_person_email: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    relationship_strength: Mapped[str] = mapped_column(
        String(20), default="moderate", nullable=False
    )
    # weak, moderate, strong
    last_interaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntroductionRequest(BaseModel):
    __tablename__ = "introduction_requests"

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    requester_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    target_investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    warmth_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    introduction_path: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # {type, connector_org, ally_contact, investor_contact, warmth}
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending, sent, accepted, declined
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
