from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.actions.title_generator import generate_title
from app.db.queries import conversation as conv_db
from app.types import (
    ConversationCreate,
    ConversationDB,
    ConversationUpdate,
    MessageContentPart,
    MessageCreate,
    MessageDB,
    MessageUpdate,
    Role,
)
from app.utils.content_util import create_text_content, extract_text_from_content


async def get_or_create_conversation(
    session: AsyncSession, conversation_id: UUID
) -> ConversationDB:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)

    if not conversation:
        conversation = await conv_db.create_conversation(
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


async def save_message(
    session: AsyncSession,
    conversation_id: UUID,
    role: Role,
    content: str | list[MessageContentPart],
) -> MessageDB:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    # Convert string to content parts for backward compatibility
    content_parts = (
        create_text_content(content) if isinstance(content, str) else content
    )

    msg = MessageCreate(
        role=role,
        content=content_parts,
    )
    result = await conv_db.create_message(session, conversation_id, msg)

    await update_conversation_updated_at(session, conversation_id)

    return result


async def update_message_content(
    session: AsyncSession,
    message_id: UUID,
    content: str | list[MessageContentPart],
) -> MessageDB:
    # Convert string to content parts for backward compatibility
    content_parts = (
        create_text_content(content) if isinstance(content, str) else content
    )

    updated_message = await conv_db.update_message(
        session, message_id, MessageUpdate(content=content_parts)
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


async def generate_conversation_name_from_message(
    session: AsyncSession,
    conversation_id: UUID,
    message: str | list[MessageContentPart],
) -> ConversationDB:
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")

    message_text = (
        extract_text_from_content(message) if isinstance(message, list) else message
    )
    new_title = await generate_title(message_text)

    updated_conversation = await conv_db.update_conversation(
        session, conversation_id, ConversationUpdate(name=new_title)
    )
    if not updated_conversation:
        raise ValueError("Failed to update conversation name")
    return updated_conversation
