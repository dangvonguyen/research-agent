from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from llama_index.core.agent.workflow import (
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult,
)
from pydantic import BaseModel
from workflows.handler import WorkflowHandler

from app.types import (
    StreamContentDelta,
    StreamContentEnd,
    StreamContentStart,
    StreamContentType,
    StreamError,
    StreamEvent,
    StreamMessageEnd,
)


class StreamAdapter:
    """Adapts LlamaIndex workflow events to StreamEvent system."""

    async def adapt_stream(
        self,
        handler: WorkflowHandler,
        conversation_id: UUID,
        message_id: UUID,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Adapt LlamaIndex workflow events to StreamEvents."""
        content_index = 0
        current_block_type: StreamContentType | None = None

        def start_block(block_type: StreamContentType, **extra):
            return StreamContentStart(
                conversation_id=conversation_id,
                message_id=message_id,
                index=content_index,
                content_type=block_type,
                **extra,
            )

        def delta_block(delta: str | dict[str, Any]):
            return StreamContentDelta(
                conversation_id=conversation_id,
                message_id=message_id,
                index=content_index,
                delta=delta,
            )

        def end_block():
            return StreamContentEnd(
                conversation_id=conversation_id,
                message_id=message_id,
                index=content_index,
            )

        async def ensure_block(block_type: StreamContentType):
            """Open the requested block; close previous block if switching."""
            nonlocal current_block_type
            if current_block_type != block_type:
                if current_block_type is not None:
                    yield end_block()
                yield start_block(block_type)
                current_block_type = block_type

        async def close_active_block():
            """Close current reasoning/text block if any."""
            nonlocal current_block_type
            if current_block_type is not None:
                yield end_block()
                current_block_type = None

        try:
            async for event in handler.stream_events():
                if isinstance(event, AgentInput):
                    pass

                elif isinstance(event, AgentStream):
                    if event.thinking_delta:
                        async for item in ensure_block(StreamContentType.REASONING):
                            yield item
                        yield delta_block(event.thinking_delta)

                    if event.delta:
                        async for item in ensure_block(StreamContentType.TEXT):
                            yield item
                        yield delta_block(event.delta)

                elif isinstance(event, AgentOutput):
                    # Only close if we opened a block
                    async for item in close_active_block():
                        yield item

                    content_index += 1

                elif isinstance(event, ToolCall):
                    async for item in close_active_block():
                        yield item

                    yield start_block(
                        StreamContentType.TOOL_CALL,
                        tool_call_id=event.tool_id,
                        tool_name=event.tool_name,
                    )
                    yield delta_block(event.tool_kwargs)
                    yield end_block()

                    content_index += 1

                elif isinstance(event, ToolCallResult):
                    async for item in close_active_block():
                        yield item

                    normalized = self.normalize_output(event.tool_output.raw_output)

                    yield start_block(
                        StreamContentType.TOOL_RESULT,
                        tool_call_id=event.tool_id,
                        tool_name=event.tool_name,
                    )
                    yield delta_block(normalized)
                    yield end_block()

                    content_index += 1

            async for item in close_active_block():
                yield item

            yield StreamMessageEnd(
                conversation_id=conversation_id, message_id=message_id
            )

        except Exception as e:
            yield StreamError(
                conversation_id=conversation_id, message_id=message_id, error=str(e)
            )

    def normalize_output(self, raw: Any) -> str | dict[str, Any]:
        if isinstance(raw, str | dict):
            return raw
        elif isinstance(raw, BaseModel):
            return raw.model_dump()
        return str(raw)
