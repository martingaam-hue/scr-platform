"""AI models: AIConversation, AIMessage, AITaskLog."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from decimal import Decimal
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
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int | None] = mapped_column(Integer)  # legacy total; prefer tokens_input+tokens_output
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )


class PromptTemplate(BaseModel):
    """Versioned prompt template for AI task types.

    Centralises all LLM prompts with A/B testing and quality tracking.
    Managed via the /admin/prompts API.
    """

    __tablename__ = "prompt_templates"
    __table_args__ = (
        sa.UniqueConstraint("task_type", "version", name="uq_prompt_task_version"),
        Index("ix_prompt_templates_task_type", "task_type"),
        Index("ix_prompt_templates_active", "is_active"),
    )

    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    system_prompt: Mapped[str | None] = mapped_column(Text)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    output_format_instruction: Mapped[str | None] = mapped_column(Text)

    model_override: Mapped[str | None] = mapped_column(String(100))
    temperature_override: Mapped[float | None] = mapped_column()
    max_tokens_override: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    traffic_percentage: Mapped[int] = mapped_column(Integer, default=100, server_default="100", nullable=False)

    total_uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    avg_confidence: Mapped[float | None] = mapped_column()
    positive_feedback_rate: Mapped[float | None] = mapped_column()
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    notes: Mapped[str | None] = mapped_column(Text)


class AIOutputFeedback(TimestampedModel):
    """User feedback on AI-generated outputs.

    Collects 👍/👎 ratings, edit tracking, and accept signals to drive
    prompt quality improvement and track model performance over time.
    """

    __tablename__ = "ai_output_feedback"
    __table_args__ = (
        Index("ix_ai_output_feedback_task_log_id", "task_log_id"),
        Index("ix_ai_output_feedback_org_id", "org_id"),
        Index("ix_ai_output_feedback_user_id", "user_id"),
        Index("ix_ai_output_feedback_task_type", "task_type"),
        Index("ix_ai_output_feedback_rating", "rating"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_task_logs.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Denormalised for fast filtering without joins
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Rating: 1 = positive (👍), -1 = negative (👎), 0 = neutral / implicit
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Edit tracking: did the user modify the AI output?
    was_edited: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    original_content: Mapped[str | None] = mapped_column(Text)
    edited_content: Mapped[str | None] = mapped_column(Text)
    edit_distance_pct: Mapped[float | None] = mapped_column()

    # Acceptance: was the output directly used without modification?
    was_accepted: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)

    # Free-text comment from user
    comment: Mapped[str | None] = mapped_column(Text)

    # Metadata (e.g. UI context, section name, version)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
