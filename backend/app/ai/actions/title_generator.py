import logging

from llama_index.core.agent.workflow import FunctionAgent
from pydantic import BaseModel, Field

from app.ai.prompts import TITLE_PROMPT

logger = logging.getLogger(__name__)


class TitleResult(BaseModel):
    title: str = Field(description="Generated a title", min_length=4, max_length=80)


async def generate_title(message: str) -> str:
    """Generate a title from the user's message."""
    agent = FunctionAgent(
        name="title_generator",
        system_prompt=TITLE_PROMPT,
        output_cls=TitleResult,
    )
    response = await agent.run(message)
    return response.structured_response["title"]
