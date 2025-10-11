import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.api.deps import SessionDep
from app.db.queries import conversation as conv_db
from app.services.db_service import (
    generate_conversation_name_from_message,
    get_or_create_conversation,
    update_conversation_updated_at,
)
from app.types import (
    ConversationCreate,
    ConversationDB,
    ConversationUpdate,
    MessageCreate,
    MessageDB,
    Response,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=Response[ConversationDB])
async def create_conversation(
    session: SessionDep, conversation: ConversationCreate
) -> Any:
    """
    Create a new conversation.
    """
    logger.debug("Creating new conversation '%s'", conversation.name)
    result = await conv_db.create_conversation(session, conversation)
    logger.debug(
        "Successfully created conversation '%s' with ID '%s'",
        conversation.name,
        result.id,
    )
    return {
        "data": result,
        "metadata": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.get("", response_model=Response[list[ConversationDB]])
async def get_conversations(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> Any:
    """
    List all conversations.
    """
    logger.debug("Retrieving conversations with skip=%d, limit=%d", skip, limit)
    result = await conv_db.get_conversations(session, skip=skip, limit=limit)
    return {
        "data": result,
        "metadata": {
            "limit": limit,
            "skip": skip,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.post("/messages", response_model=Response[MessageDB])
async def create_message(
    session: SessionDep,
    message: MessageCreate,
    conversation_id: Annotated[UUID, Query()],
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create a new message in a new or existing conversation.
    """
    conversation = await conv_db.get_conversation_by_id(session, conversation_id)

    is_new = False
    if not conversation:
        is_new = True
        conversation = await get_or_create_conversation(session, conversation_id)

    result = await conv_db.create_message(session, conversation_id, message)
    logger.debug(
        "Successfully created message '%s' in conversation '%s'",
        result.id,
        conversation_id,
    )

    await update_conversation_updated_at(session, conversation_id)

    if is_new and message.role == "user":
        background_tasks.add_task(
            generate_conversation_name_from_message,
            session,
            conversation_id,
            message.content,
        )

    return {
        "data": result,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "message_id": result.id,
            "conversation_id": conversation_id,
        },
    }


@router.get("/messages/last", response_model=Response[MessageDB])
async def get_last_message(session: SessionDep, conversation_id: UUID) -> Any:
    """
    Get the latest message in a conversation.
    """
    logger.debug("Retrieving latest message in conversation '%s'", conversation_id)
    message = await conv_db.get_last_message_by_conversation_id(
        session, conversation_id
    )
    if not message:
        raise HTTPException(status_code=404, detail="No messages found in conversation")
    return {
        "data": message,
        "metadata": {
            "conversation_id": conversation_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/messages/{message_id}", response_model=Response[MessageDB])
async def get_message(session: SessionDep, message_id: UUID) -> Any:
    """
    Get a specific message by ID.
    """
    logger.debug("Retrieving message with ID '%s'", message_id)
    message = await conv_db.get_message_by_id(session, message_id)
    if not message:
        logger.warning("Message '%s' not found", message_id)
        raise HTTPException(status_code=404, detail="Message not found")
    return {
        "data": message,
        "metadata": {
            "conversation_id": message.conversation_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/{conversation_id}", response_model=Response[ConversationDB])
async def get_conversation(session: SessionDep, conversation_id: UUID) -> Any:
    """
    Get a specific conversation.
    """
    logger.debug("Retrieving conversation with ID '%s'", conversation_id)
    conv = await conv_db.get_conversation_by_id(session, conversation_id)
    if not conv:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "data": conv,
        "metadata": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.patch("/{conversation_id}", response_model=Response[ConversationDB])
async def update_conversation(
    session: SessionDep, conversation_id: UUID, conversation: ConversationUpdate
) -> Any:
    """
    Update a conversation.
    """
    logger.debug("Updating conversation '%s'", conversation_id)
    result = await conv_db.update_conversation(session, conversation_id, conversation)
    if not result:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "data": result,
        "metadata": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.delete("/{conversation_id}", response_model=Response[None])
async def delete_conversation(session: SessionDep, conversation_id: UUID) -> Any:
    """
    Delete a conversation.
    """
    logger.debug("Deleting conversation '%s'", conversation_id)
    success = await conv_db.delete_conversation(session, conversation_id)
    if not success:
        logger.warning("Conversation '%s' not found", conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "data": None,
        "metadata": {
            "deleted": True,
            "conversation_id": str(conversation_id),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/{conversation_id}/messages", response_model=Response[list[MessageDB]])
async def get_messages(
    session: SessionDep, conversation_id: UUID, skip: int = 0, limit: int = 100
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
        conversation_id,
        skip,
        limit,
    )
    result = await conv_db.get_messages_by_conversation_id(
        session, conversation_id, skip=skip, limit=limit
    )
    return {
        "data": result,
        "metadata": {
            "limit": limit,
            "skip": skip,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
