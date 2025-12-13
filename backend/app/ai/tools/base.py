from typing import Any

from llama_index.core.tools import FunctionTool
from pydantic import BaseModel

from app.types import ToolResultOutput as ToolOutput


class BaseTool:
    """Base class for defining tools compatible with LlamaIndex."""

    name: str
    description: str
    input_schema: type[BaseModel] | None = None

    def run(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """Synchronous execution entry point for the tool."""
        raise NotImplementedError("Sync run() not implemented.")

    async def arun(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """Asynchronous execution entry point for the tool."""
        raise NotImplementedError("Async arun() not implemented.")

    def as_tool(self) -> FunctionTool:
        """Convert to a LlamaIndex tool for agent integration."""
        # Check which method the subclass implemented
        has_run = "run" in self.__class__.__dict__
        has_arun = "arun" in self.__class__.__dict__

        if not (has_run or has_arun):
            raise ValueError("Subclass must override at least `run` or `arun`")

        return FunctionTool.from_defaults(
            fn=self.run if has_run else None,
            async_fn=self.arun if has_arun else None,
            name=self.name,
            description=self.description,
            fn_schema=self.input_schema,
        )
