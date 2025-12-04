import asyncio
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.api.deps import Session, SessionDep
from app.services.chat_service import chat_service
from app.services.db_service import (
    load_history,
    save_message,
    update_message_content,
)
from app.services.stream_assembler import ContentPartBuilder
from app.types import (
    ChatRequest,
    ChatResponse,
    Role,
    StreamAbort,
    StreamChatChunk,
    StreamContentDelta,
    StreamContentEnd,
    StreamContentStart,
    StreamError,
    StreamMessageEnd,
)

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
    ai_message_db = await save_message(
        session, conversation_id, Role.ASSISTANT, ai_response
    )

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
    ai_message_db = await save_message(session, conversation_id, Role.ASSISTANT, "")
    ai_message_id = ai_message_db.id

    async def generate_stream() -> AsyncGenerator[str, None]:
        builder = ContentPartBuilder()

        try:
            # Stream from AI service with typed events
            async for event in chat_service.stream_chat(
                user_message.content, history[:-1], conversation_id, ai_message_id
            ):
                # Wrap event and send to client
                chunk = StreamChatChunk.create(event=event)
                yield f"data: {chunk.model_dump_json()}\n\n"

                # Build content parts as we stream
                if isinstance(event, StreamContentStart):
                    builder.start_content(
                        event.content_type,
                        event.index,
                        tool_call_id=event.tool_call_id,
                        tool_name=event.tool_name,
                    )

                elif isinstance(event, StreamContentDelta):
                    builder.add_delta(event.index, event.delta)

                elif isinstance(event, StreamContentEnd):
                    builder.end_content(event.index)

            # Send message_end event
            end_event = StreamMessageEnd(
                conversation_id=conversation_id,
                message_id=ai_message_id,
            )
            final_chunk = StreamChatChunk.create(event=end_event)
            yield f"data: {final_chunk.model_dump_json()}\n\n"

        except asyncio.CancelledError:
            # Handle cancellation gracefully
            cancelled_event = StreamAbort(
                conversation_id=conversation_id,
                message_id=ai_message_id,
                reason="stream_cancelled",
            )
            cancel_chunk = StreamChatChunk.create(event=cancelled_event)
            yield f"data: {cancel_chunk.model_dump_json()}\n\n"
            raise

        except Exception as e:
            logger.exception("Error during streaming")
            # Send error event
            error_event = StreamError(
                conversation_id=conversation_id,
                message_id=ai_message_id,
                error=str(e),
            )
            error_chunk = StreamChatChunk.create(event=error_event)
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            raise

        finally:
            # Save final assembled content even on error/cancel
            final_content = builder.get_all_parts()

            # Update database with final content (non-blocking)
            # Create a new session for the background task because the
            # request session will be closed before the task runs
            async def save_final_content():
                async with Session() as bg_session:
                    try:
                        await update_message_content(
                            bg_session,
                            ai_message_id,
                            final_content,
                        )
                    except Exception as e:
                        logger.exception(f"Failed to save final content: {e}")

            background_tasks.add_task(save_final_content)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
