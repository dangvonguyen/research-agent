from llama_index.core.llms import ChatMessage

from app.ai.prompts import TITLE_PROMPT
from app.services.llm_service import default_llm


async def generate_title(message: str) -> str:
    """Generate a title from the user's message."""
    messages = [
        ChatMessage(role="system", content=TITLE_PROMPT),
        ChatMessage(role="user", content=message),
    ]
    response = await default_llm.achat(messages)
    return response.message.content or "New Chat"
