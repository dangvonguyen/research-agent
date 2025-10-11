from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Attachment, Conversation, Message
from app.types import (
    ConversationCreate,
    ConversationDB,
    ConversationUpdate,
    MessageCreate,
    MessageDB,
    MessageUpdate,
)


async def create_conversation(
    session: AsyncSession, conversation: ConversationCreate
) -> ConversationDB:
    """Create a new conversation."""
    conv_db = Conversation(**conversation.model_dump(exclude_unset=True))
    session.add(conv_db)
    await session.commit()
    await session.refresh(conv_db)
    return ConversationDB.model_validate(conv_db)


async def get_conversations(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> list[ConversationDB]:
    """Get all conversations."""
    stmt = (
        select(Conversation)
        .offset(skip)
        .limit(limit)
        .order_by(Conversation.updated_at.desc())
    )
    result = await session.execute(stmt)
    convs = result.scalars().all()
    return [ConversationDB.model_validate(conv) for conv in convs]


async def get_conversation_by_id(
    session: AsyncSession, conversation_id: UUID
) -> ConversationDB | None:
    """Get a conversation by ID."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()
    return ConversationDB.model_validate(conv) if conv else None


async def update_conversation(
    session: AsyncSession, conversation_id: UUID, update_data: ConversationUpdate
) -> ConversationDB | None:
    """Update a conversation."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(conv, key, value)

    await session.commit()
    await session.refresh(conv)
    return ConversationDB.model_validate(conv)


async def delete_conversation(session: AsyncSession, conversation_id: UUID) -> bool:
    """Delete a conversation."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await session.execute(stmt)
    conv = result.scalar_one_or_none()
    if not conv:
        return False

    await session.delete(conv)
    await session.commit()
    return True


async def create_message(
    session: AsyncSession, conversation_id: UUID, message: MessageCreate
) -> MessageDB:
    """Create a new message."""
    message_db = Message(
        content=message.content,
        role=message.role,
        conversation_id=conversation_id,
    )
    session.add(message_db)
    await session.flush()  # Flush to get the message ID without committing

    # Create attachments if provided
    if message.attachments:
        attachment_objects = [
            Attachment(
                filename=att_data.filename,
                content_type=att_data.content_type,
                path=att_data.path,
                size=att_data.size,
                message_id=message_db.id,
            )
            for att_data in message.attachments
        ]
        session.add_all(attachment_objects)

    # Commit and refresh including attachments
    await session.commit()
    await session.refresh(message_db, ["attachments"])

    return MessageDB.model_validate(message_db)


async def get_messages_by_conversation_id(
    session: AsyncSession,
    conversation_id: UUID,
    skip: int | None = 0,
    limit: int | None = 100,
) -> list[MessageDB]:
    """Get messages for a conversation."""
    messages_stmt = (
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    if skip and limit:
        messages_stmt = messages_stmt.offset(skip).limit(limit)

    result = await session.execute(messages_stmt)
    messages = result.scalars().all()
    return [MessageDB.model_validate(msg) for msg in messages]


async def get_message_by_id(
    session: AsyncSession, message_id: UUID
) -> MessageDB | None:
    """Get a message by ID with optimized attachment loading."""
    stmt = (
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.id == message_id)
    )

    result = await session.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        return None

    return MessageDB.model_validate(message)


async def get_last_message_by_conversation_id(
    session: AsyncSession, conversation_id: UUID
) -> MessageDB | None:
    """Get the latest message in a conversation."""
    stmt = (
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        return None

    return MessageDB.model_validate(message)


async def update_message(
    session: AsyncSession, message_id: UUID, update_data: MessageUpdate
) -> MessageDB | None:
    """Update a message."""
    stmt = select(Message).where(Message.id == message_id)
    result = await session.execute(stmt)
    message = result.scalar_one_or_none()

    print("message:", message)  # Debugging line

    if not message:
        return None

    update_dict = update_data.model_dump(exclude_unset=True, exclude={"attachments"})
    for key, value in update_dict.items():
        setattr(message, key, value)

    await session.commit()
    await session.refresh(message, ["attachments"])
    return MessageDB.model_validate(message)
