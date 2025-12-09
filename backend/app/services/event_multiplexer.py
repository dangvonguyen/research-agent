"""Multiplexes orchestrator and sub-agent event streams."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, Literal


class AgentEvent:
    """Event wrapper with agent attribution."""

    def __init__(
        self,
        event: Any,  # LlamaIndex event
        agent_name: str,
        agent_type: Literal["orchestrator", "sub-agent"],
    ):
        self.event = event
        self.agent_name = agent_name
        self.agent_type = agent_type


class EventMultiplexer:
    """Merges multiple agent streams into one ordered stream."""

    def __init__(self):
        self.event_queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()

    async def emit_event(
        self,
        event: Any,
        agent_name: str,
        agent_type: Literal["orchestrator", "sub-agent"],
    ) -> None:
        """Emit event with attribution to multiplexed stream."""
        await self.event_queue.put(AgentEvent(event, agent_name, agent_type))

    async def stream_events(self) -> AsyncGenerator[AgentEvent, None]:
        """Consume multiplexed events in FIFO order."""
        while True:
            event = await self.event_queue.get()
            if event is None:
                break
            yield event

    async def close(self) -> None:
        """Signal no more events will be emitted."""
        await self.event_queue.put(None)
