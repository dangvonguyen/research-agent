import asyncio
from collections.abc import AsyncGenerator
from typing import Optional, cast
from uuid import UUID

from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.llms import ChatMessage, MessageRole

from app.ai.tools.multiple_tool import MultipleTool
from app.services.llm_service import llm_service
from app.services.stream_adapter import StreamAdapter
from app.types import (
    MessageContentPart,
    MessageDB,
    Role,
    StreamError,
    StreamEvent,
)
from app.utils.content_util import extract_text_from_content


class ChatService:
    """Service for handling chat operations with agent and AI tool support."""

    def __init__(self, system_prompt: Optional[str] = None):
        # Configure LlamaIndex settings
        self.llm = llm_service.get_default_llm()
        Settings.llm = self.llm

        # Default system prompt
        self.system_prompt = system_prompt or (
            "You are a helpful AI assistant. Provide clear, accurate, "
            "and helpful responses to user queries."
        )

        self.stream_adapter = StreamAdapter()

        # Initialize chat engine
        self.chat_engine = SimpleChatEngine.from_defaults(
            llm=self.llm,
            system_prompt=self.system_prompt,
        )

    async def chat(
        self, user_message: list[MessageContentPart], history: list[MessageDB]
    ) -> str:
        # Extract text from content parts
        user_text = extract_text_from_content(user_message)

        # Build conversation history
        chat_history = self._build_chat_history(history)

        # Reset chat engine to clear previous state
        self.chat_engine.reset()
        response = cast(
            AgentChatResponse, await self.chat_engine.achat(user_text, chat_history)
        )

        return str(response)

    async def stream_chat(
        self,
        user_message: list[MessageContentPart],
        history: list[MessageDB],
        conversation_id: UUID,
        message_id: UUID,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream chat response with AI tool support."""
        # Extract text from content parts
        user_text = extract_text_from_content(user_message)

        # Build conversation history
        chat_history = self._build_chat_history(history)

        try:
            agent = ReActAgent(
                system_prompt=self.system_prompt,
                tools=[MultipleTool.as_tool()],
                llm=self.llm,
            )

            # Run agent and get workflow handler
            handler = agent.run(user_msg=user_text, chat_history=chat_history)

            # Adapt LlamaIndex workflow events to stream events
            async for event in self.stream_adapter.adapt_stream(
                handler, conversation_id, message_id
            ):
                yield event

        except asyncio.CancelledError:
            raise

        except Exception as e:
            # Error handling
            yield StreamError(
                conversation_id=conversation_id,
                message_id=message_id,
                error=str(e),
            )
            raise

    def _build_chat_history(
        self, messages: list[MessageDB]
    ) -> list[ChatMessage] | None:
        if len(messages) == 0:
            return None

        chat_messages = []
        for msg in messages:
            if msg.role == Role.USER:
                role = MessageRole.USER
            elif msg.role == Role.ASSISTANT:
                role = MessageRole.ASSISTANT
            else:
                continue  # Skip other roles if any

            # Extract text content from content parts
            content_text = extract_text_from_content(msg.content)
            chat_messages.append(ChatMessage(role=role, content=content_text))

        return chat_messages


# Global instance
chat_service = ChatService()
