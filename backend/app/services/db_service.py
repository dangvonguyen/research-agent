from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.queries import conversation as conv_db
from app.types import (
    ConversationCreate,
    ConversationDB,
    ConversationUpdate,
    MessageCreate,
    MessageDB,
    MessageUpdate,
    Role,
)


async def get_or_create_conversation(
    session: AsyncSession, conversation_id: UUID | None
) -> ConversationDB:
    if not conversation_id:
        return await conv_db.create_conversation(
            session, ConversationCreate(name="New Chat")
        )

    conversation = await conv_db.get_conversation_by_id(session, conversation_id)

    if not conversation:
        await conv_db.create_conversation(
            session, ConversationCreate(id=conversation_id, name="New Chat")
        )

    return conversation


async def update_conversation_updated_at(
    session: AsyncSession, conversation_id: UUID
) -> ConversationDB:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    updated_conversation = await conv_db.update_conversation(
        session, conversation_id, ConversationUpdate()
    )
    if not updated_conversation:
        raise ValueError("Failed to update conversation")
    return updated_conversation


async def save_user_message(
    session: AsyncSession, conversation_id: UUID, content: str
) -> MessageDB:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    msg = MessageCreate(
        content=content,
        role=Role.USER,
        conversation_id=conversation_id,
    )
    result = await conv_db.create_message(session, msg)

    await update_conversation_updated_at(session, conversation_id)

    return result


async def save_ai_message(
    session: AsyncSession, conversation_id: UUID, content: str
) -> MessageDB:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    msg = MessageCreate(
        content=content,
        role=Role.ASSISTANT,
        conversation_id=conversation_id,
    )
    result = await conv_db.create_message(session, conversation_id, msg)

    await update_conversation_updated_at(session, conversation_id)

    return result


async def update_message_content(
    session: AsyncSession, message_id: UUID, content: str
) -> MessageDB:
    updated_message = await conv_db.update_message(
        session, message_id, MessageUpdate(content=content)
    )
    if not updated_message:
        raise ValueError("Message not found")

    await update_conversation_updated_at(session, updated_message.conversation_id)

    return updated_message


async def load_history(session: AsyncSession, conversation_id: UUID) -> list[MessageDB]:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    history = conv_db.get_messages_by_conversation_id(session, conversation_id)
    if not history:
        raise ValueError("Conversation has no messages")
    return await history
