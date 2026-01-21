import logging
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

from app.services.event_multiplexer import EventMultiplexer
from app.services.ui_event_parser import parse_ui_events_from_text
from app.types import (
    CustomUIEvent,
    StreamContentDelta,
    StreamContentEnd,
    StreamContentStart,
    StreamContentType,
    StreamError,
    StreamEvent,
    StreamMessageEnd,
)

logger = logging.getLogger(__name__)


class StreamAdapter:
    """Adapts LlamaIndex workflow events to StreamEvent system."""

    async def adapt_stream(
        self,
        multiplexer: EventMultiplexer,
        conversation_id: UUID,
        message_id: UUID,
    ) -> AsyncGenerator[StreamEvent, None]:
        content_index = 0
        current_block_type: StreamContentType | None = None
        current_agent_name: str | None = None
        current_agent_type: str | None = None

        # === STATE MACHINE FOR CODE BLOCK ===
        # States: "normal", "waiting_start", "inside_block", "waiting_end"
        block_state = "normal"
        code_block_buffer: str = ""
        pending_char: str | None = None  # Track pending char for marker detection

        # ---------- helpers ----------
        def start_block(block_type: StreamContentType, **extra):
            return StreamContentStart(
                conversation_id=conversation_id,
                message_id=message_id,
                index=content_index,
                content_type=block_type,
                agent_name=current_agent_name,
                agent_type=current_agent_type,
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
            nonlocal content_index
            block = StreamContentEnd(
                conversation_id=conversation_id,
                message_id=message_id,
                index=content_index,
            )
            content_index += 1
            return block

        async def ensure_block(block_type: StreamContentType):
            nonlocal current_block_type
            if current_block_type != block_type:
                if current_block_type is not None:
                    yield end_block()
                yield start_block(block_type)
                current_block_type = block_type

        async def close_active_block():
            nonlocal current_block_type
            if current_block_type is not None:
                yield end_block()
                current_block_type = None

        # ---------- main loop ----------
        try:
            async for attributed_event in multiplexer.stream_events():
                event = attributed_event.event
                current_agent_name = attributed_event.agent_name
                current_agent_type = attributed_event.agent_type

                # -------- AgentInput --------
                if isinstance(event, AgentInput):
                    continue

                # -------- AgentStream --------
                elif isinstance(event, AgentStream):
                    # ---- reasoning ----
                    if event.thinking_delta:
                        async for item in ensure_block(StreamContentType.REASONING):
                            yield item
                        yield delta_block(event.thinking_delta)

                    # ---- text stream ----
                    if event.delta:
                        delta = event.delta

                        if current_agent_type == "orchestrator":
                            for ch in delta:
                                # State machine for detecting << and >> markers
                                if block_state == "normal":
                                    if ch == "<":
                                        # Possible start of <<, wait for next char
                                        pending_char = "<"
                                        block_state = "waiting_start"
                                    else:
                                        # Normal text, stream it
                                        async for item in ensure_block(
                                            StreamContentType.TEXT
                                        ):
                                            yield item
                                        yield delta_block(ch)

                                elif block_state == "waiting_start":
                                    if ch == "<":
                                        # Confirmed << marker, enter block
                                        block_state = "inside_block"
                                        code_block_buffer = ""
                                        pending_char = None
                                    else:
                                        # Not <<, stream the pending < and current char
                                        async for item in ensure_block(
                                            StreamContentType.TEXT
                                        ):
                                            yield item
                                        yield delta_block(pending_char)
                                        yield delta_block(ch)
                                        block_state = "normal"
                                        pending_char = None

                                elif block_state == "inside_block":
                                    if ch == ">":
                                        # Possible start of >>, wait for next char
                                        pending_char = ">"
                                        block_state = "waiting_end"
                                    else:
                                        # Normal content inside block, add to buffer
                                        code_block_buffer += ch

                                elif block_state == "waiting_end":
                                    if ch == ">":
                                        # Confirmed >> marker, exit block and parse
                                        block_state = "normal"
                                        pending_char = None

                                        events = parse_ui_events_from_text(
                                            code_block_buffer
                                        )
                                        if events:
                                            ui_event, _, _ = events[0]

                                            async for item in close_active_block():
                                                yield item

                                            yield start_block(
                                                StreamContentType.UI_EVENT
                                            )
                                            yield delta_block(
                                                {
                                                    "event_type": ui_event.event_type,
                                                    "data": ui_event.data,
                                                }
                                            )
                                            yield end_block()

                                        code_block_buffer = ""
                                    else:
                                        # Not >>, add pending > and current char to buffer
                                        code_block_buffer += pending_char
                                        code_block_buffer += ch
                                        block_state = "inside_block"
                                        pending_char = None

                        else:
                            async for item in ensure_block(StreamContentType.TEXT):
                                yield item
                            yield delta_block(delta)

                # -------- AgentOutput --------
                elif isinstance(event, AgentOutput):
                    async for item in close_active_block():
                        yield item

                # -------- ToolCall --------
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

                # -------- ToolCallResult --------
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

                # -------- Custom UI Event --------
                elif isinstance(event, CustomUIEvent):
                    async for item in close_active_block():
                        yield item

                    yield start_block(StreamContentType.UI_EVENT)
                    yield delta_block(
                        {"event_type": event.event_type, "data": event.data}
                    )
                    yield end_block()

            async for item in close_active_block():
                yield item

            yield StreamMessageEnd(
                conversation_id=conversation_id, message_id=message_id
            )

        except Exception as e:
            yield StreamError(
                conversation_id=conversation_id,
                message_id=message_id,
                error=str(e),
            )

    def normalize_output(self, raw: Any) -> str | dict[str, Any]:
        if isinstance(raw, (str, dict)):
            return raw
        if isinstance(raw, BaseModel):
            return raw.model_dump()
        return str(raw)
