import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.db.queries import conversation as conv_db
from app.types import (
    ConversationCreate,
    ConversationDB,
    ConversationUpdate,
    MessageCreate,
    MessageDB,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ConversationDB)
async def create_conversation(
    session: SessionDep, conversation: ConversationCreate
) -> Any:
    """
    Create a new conversation.
    """
    logger.info("Creating new conversation '%s'", conversation.name)
    result = await conv_db.create_conversation(session, conversation)
    logger.info(
        "Successfully created conversation '%s' with ID '%s'",
        conversation.name, result.id,
    )
    return result


@router.get("", response_model=list[ConversationDB])
async def get_conversations(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> Any:
    """
    List all conversations.
    """
    logger.debug(
        "Retrieving conversations with skip=%d, limit=%d", skip, limit
    )
    return await conv_db.get_conversations(session, skip=skip, limit=limit)


@router.get("/messages/{message_id}", response_model=MessageDB)
async def get_message(session: SessionDep, message_id: str) -> Any:
    """
    Get a specific message by ID.
    """
    logger.debug("Retrieving message with ID '%s'", message_id)
    message = await conv_db.get_message_by_id(session, message_id)
    if not message:
        logger.warning("Message '%s' not found", message_id)
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.get("/{conversation_id}", response_model=ConversationDB)
async def get_conversation(session: SessionDep, conversation_id: str) -> Any:
    """
    Get a specific conversation.
    """
    logger.debug("Retrieving conversation with ID '%s'", conversation_id)
    conv = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conv:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conversation_id}", response_model=ConversationDB)
async def update_conversation(
    session: SessionDep, conversation_id: str, conversation: ConversationUpdate
) -> Any:
    """
    Update a conversation.
    """
    logger.debug("Updating conversation '%s'", conversation_id)
    result = await conv_db.update_conversation(session, conversation_id, conversation)
    if not result:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.delete("/{conversation_id}")
async def delete_conversation(
    session: SessionDep, conversation_id: str
) -> dict[str, str]:
    """
    Delete a conversation.
    """
    logger.debug("Deleting conversation '%s'", conversation_id)
    success = await conv_db.delete_conversation(session, conversation_id)
    if not success:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted successfully"}


@router.post("/{conversation_id}/messages", response_model=MessageDB)
async def create_message(
    session: SessionDep, conversation_id: UUID, message: MessageCreate
) -> Any:
    """
    Create a new message in a conversation.
    """
    # Verify conversation exists
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")

    logger.info(
        "Creating new message in conversation '%s' with role '%s'",
        conversation_id, message.role.value,
    )
    result = await conv_db.create_message(session, message)
    logger.info(
        "Successfully created message '%s' in conversation '%s'",
        result.id, conversation_id,
    )
    return result


@router.get("/{conversation_id}/messages", response_model=list[MessageDB])
async def get_messages(
    session: SessionDep, conversation_id: str, skip: int = 0, limit: int = 100
) -> Any:
    """
    List all messages in a conversation.
    """
    # Verify conversation exists
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conversation:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")

    logger.debug(
        "Retrieving messages for conversation '%s' with skip=%d, limit=%d",
        conversation_id, skip, limit
    )
    return await conv_db.get_messages_by_conversation_id(
        session, conversation_id, skip=skip, limit=limit
    )
