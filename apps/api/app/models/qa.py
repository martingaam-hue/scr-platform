"""Q&A Workflow models: QAQuestion and QAAnswer."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class QAQuestion(BaseModel):
    __tablename__ = "qa_questions"
    __table_args__ = (
        Index("ix_qa_questions_org_id", "org_id"),
        Index("ix_qa_questions_project_id", "project_id"),
        Index("ix_qa_questions_org_project", "org_id", "project_id"),
        Index("ix_qa_questions_status", "status"),
        Index("ix_qa_questions_project_status", "project_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    deal_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal_rooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", server_default="normal")

    asked_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_team: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", server_default="open")
    sla_deadline: Mapped[datetime | None] = mapped_column(nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    linked_documents: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True, default=list
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )

    # Relationships
    answers: Mapped[list["QAAnswer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QAAnswer.created_at",
    )

    def __repr__(self) -> str:
        return f"<QAQuestion(id={self.id}, number={self.question_number}, status={self.status!r})>"


class QAAnswer(BaseModel):
    __tablename__ = "qa_answers"
    __table_args__ = (
        Index("ix_qa_answers_question_id", "question_id"),
        Index("ix_qa_answers_answered_by", "answered_by"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qa_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_documents: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True, default=list
    )

    # Relationships
    question: Mapped["QAQuestion"] = relationship(back_populates="answers")

    def __repr__(self) -> str:
        return f"<QAAnswer(id={self.id}, question_id={self.question_id}, is_official={self.is_official})>"
