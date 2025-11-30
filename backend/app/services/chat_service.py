from collections.abc import AsyncGenerator
from typing import Optional, cast

from llama_index.core import Settings
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.chat_engine.types import (
    AgentChatResponse,
    StreamingAgentChatResponse,
)
from llama_index.core.llms import ChatMessage, MessageRole

from app.services.llm_service import llm_service
from app.types import MessageDB, Role


class ChatService:
    """Service for handling chat operations with LlamaIndex integration."""

    def __init__(self, system_prompt: Optional[str] = None):
        # Configure LlamaIndex settings
        self.llm = llm_service.get_default_llm()
        Settings.llm = self.llm

        # Default system prompt
        self.system_prompt = system_prompt or (
            "You are a helpful AI assistant. Provide clear, accurate, "
            "and helpful responses to user queries."
        )

        # Initialize chat engine
        self.chat_engine = SimpleChatEngine.from_defaults(
            llm=self.llm,
            system_prompt=self.system_prompt,
        )

    async def chat(self, user_message: str, history: list[MessageDB]) -> str:
        # Build conversation history
        chat_history = self._build_chat_history(history)

        # Reset chat engine to clear previous state
        self.chat_engine.reset()
        response = cast(
            AgentChatResponse, await self.chat_engine.achat(user_message, chat_history)
        )

        return str(response)

    async def stream_chat(
        self, user_message: str, history: list[MessageDB]
    ) -> AsyncGenerator[str, None]:
        # Build conversation history
        chat_history = self._build_chat_history(history)

        # Reset chat engine to clear previous state
        self.chat_engine.reset()
        response = cast(
            StreamingAgentChatResponse,
            await self.chat_engine.astream_chat(user_message, chat_history),
        )

        async for chunk in response.async_response_gen():
            yield chunk

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

            chat_messages.append(ChatMessage(role=role, content=msg.content))

        return chat_messages


# Global instance
chat_service = ChatService()
