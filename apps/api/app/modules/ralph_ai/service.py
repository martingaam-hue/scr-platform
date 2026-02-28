"""Ralph AI — async CRUD service for conversations and messages."""

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant import tenant_filter
from app.models.ai import AIConversation, AIMessage
from app.models.enums import AIContextType, AIMessageRole
from app.modules.ralph_ai.schemas import ConversationCreate

logger = structlog.get_logger()


async def create_conversation(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: ConversationCreate,
) -> AIConversation:
    try:
        context_type = AIContextType(body.context_type)
    except ValueError:
        context_type = AIContextType.GENERAL

    conversation = AIConversation(
        org_id=org_id,
        user_id=user_id,
        context_type=context_type,
        context_entity_id=body.context_entity_id,
        title=body.title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    logger.info("ralph_conversation_created", conversation_id=str(conversation.id), org_id=str(org_id))
    return conversation


async def list_conversations(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[AIConversation]:
    stmt = (
        select(AIConversation)
        .where(
            AIConversation.org_id == org_id,
            AIConversation.user_id == user_id,
            AIConversation.is_deleted.is_(False),
        )
        .order_by(AIConversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession,
    conv_id: uuid.UUID,
    org_id: uuid.UUID,
) -> AIConversation | None:
    stmt = (
        select(AIConversation)
        .where(
            AIConversation.id == conv_id,
            AIConversation.org_id == org_id,
            AIConversation.is_deleted.is_(False),
        )
        .options(
            selectinload(AIConversation.messages)
        )
        .execution_options(populate_existing=True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_conversation(
    db: AsyncSession,
    conv_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> bool:
    conversation = await get_conversation(db, conv_id, org_id)
    if conversation is None:
        return False
    if user_id is not None and conversation.user_id != user_id:
        return False
    conversation.is_deleted = True  # type: ignore[assignment]
    await db.flush()
    logger.info("ralph_conversation_deleted", conversation_id=str(conv_id))
    return True


async def append_message(
    db: AsyncSession,
    conv_id: uuid.UUID,
    role: AIMessageRole,
    content: str,
    tool_calls: dict[str, Any] | None = None,
    tool_results: dict[str, Any] | None = None,
    model_used: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> AIMessage:
    message = AIMessage(
        conversation_id=conv_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        model_used=model_used,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_conversation_messages(
    db: AsyncSession,
    conv_id: uuid.UUID,
) -> list[AIMessage]:
    stmt = (
        select(AIMessage)
        .where(AIMessage.conversation_id == conv_id)
        .order_by(AIMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
