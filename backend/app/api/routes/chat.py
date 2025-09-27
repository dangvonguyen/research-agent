import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep
from app.services.chat_service import chat_service
from app.services.db_service import (
    load_history,
    save_ai_message,
    update_message_content,
)
from app.types import ChatRequest, ChatResponse, StreamChatChunk

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("")
async def chat(session: SessionDep, chat_request: ChatRequest) -> ChatResponse:
    """
    Send a message and get an AI response in a conversation.
    """
    conversation_id = chat_request.conversation_id
    user_message_id = chat_request.message_id

    # Load full history (including the recently created user message)
    history = await load_history(session, conversation_id)

    # Get the user message that was just created
    user_message = next((msg for msg in history if msg.id == user_message_id), None)
    if not user_message:
        raise ValueError(f"User_message {user_message_id} not found")

    # Generate reply
    ai_response = await chat_service.chat(user_message.content, history[:-1])
    ai_message_db = await save_ai_message(session, conversation_id, ai_response)

    return ChatResponse.create(
        assistant_data=ai_message_db,
        conversation_id=conversation_id,
    )


@router.post("/stream")
async def stream_chat(
    session: SessionDep, chat_request: ChatRequest, background_tasks: BackgroundTasks
) -> StreamingResponse:
    """
    Send a message and get a streaming AI response in a conversation.
    """
    conversation_id = chat_request.conversation_id
    user_message_id = chat_request.message_id

    # Load full history (including the recently created user message)
    history = await load_history(session, conversation_id)

    # Get the user message that was just created
    user_message = next((msg for msg in history if msg.id == user_message_id), None)
    if not user_message:
        raise ValueError(f"User_message {user_message_id} not found")

    # Save placeholder assistant message to be updated later
    ai_message_db = await save_ai_message(session, conversation_id, "")
    ai_message_id = ai_message_db.id

    async def generate_stream() -> AsyncGenerator[str, None]:
        parts: list[str] = []

        async for chunk in chat_service.stream_chat(user_message.content, history[:-1]):
            parts.append(chunk)
            chunk_data = StreamChatChunk.create(
                conversation_id=conversation_id,
                message_id=ai_message_id,
                chunk=chunk,
                is_final=False,
            )
            yield f"data: {chunk_data.model_dump_json()}\n\n"

        # Send final chunk
        final_chunk = StreamChatChunk.create(
            conversation_id=conversation_id,
            message_id=ai_message_id,
            chunk="",
            is_final=True,
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"

        # Update the assistant message content
        background_tasks.add_task(
            update_message_content, session, ai_message_id, "".join(parts)
        )

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
