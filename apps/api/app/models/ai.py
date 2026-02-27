"""AI models: AIConversation, AIMessage, AITaskLog."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampedModel
from app.models.enums import AIAgentType, AIContextType, AIMessageRole, AITaskStatus


class AIConversation(BaseModel):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index("ix_ai_conversations_org_id", "org_id"),
        Index("ix_ai_conversations_user_id", "user_id"),
        Index("ix_ai_conversations_context_type", "context_type"),
        Index("ix_ai_conversations_user_context", "user_id", "context_type"),
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
    context_type: Mapped[AIContextType] = mapped_column(
        nullable=False, default=AIContextType.GENERAL
    )
    context_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="New conversation")
    summary: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    # Relationships
    messages: Mapped[list["AIMessage"]] = relationship(back_populates="conversation")

    def __repr__(self) -> str:
        return f"<AIConversation(id={self.id}, context={self.context_type.value})>"


class AIMessage(TimestampedModel):
    __tablename__ = "ai_messages"
    __table_args__ = (
        Index("ix_ai_messages_conversation_id", "conversation_id"),
        Index("ix_ai_messages_role", "role"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[AIMessageRole] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100))
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tool_results: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Relationships
    conversation: Mapped["AIConversation"] = relationship(back_populates="messages")


class AITaskLog(TimestampedModel):
    __tablename__ = "ai_task_logs"
    __table_args__ = (
        Index("ix_ai_task_logs_org_id", "org_id"),
        Index("ix_ai_task_logs_agent_type", "agent_type"),
        Index("ix_ai_task_logs_status", "status"),
        Index("ix_ai_task_logs_entity", "entity_type", "entity_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_type: Mapped[AIAgentType] = mapped_column(nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[AITaskStatus] = mapped_column(
        nullable=False, default=AITaskStatus.PENDING
    )
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(100))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
