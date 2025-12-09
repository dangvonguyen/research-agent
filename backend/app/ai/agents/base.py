"""Base agent abstraction for building specialized agents."""

from abc import ABC, abstractmethod

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool as LlamaBaseTool
from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    """Metadata describing an agent's capabilities and purpose.

    This provides a declarative way to define agent properties
    without modifying orchestrator code.
    """

    name: str = Field(description="Unique identifier for this agent")
    description: str = Field(
        description="High-level summary of the agent's research role"
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Semantic capability tags used for routing and planning",
    )
    enabled: bool = Field(
        default=True, description="Whether this agent is currently enabled"
    )

    class Config:
        frozen = True  # Immutable metadata


class BaseAgent(ABC):
    """Abstract base class for specialized agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the agent."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Concise explanation of the agent's research function."""
        pass

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent provides.

        Used by the orchestrator for routing decisions.
        Example: ['hypothesis_generation', 'dataset_analysis']
        """
        return []

    @abstractmethod
    def get_tools(self) -> list[LlamaBaseTool]:
        """Return the list of tools this agent needs to function."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt that defines agent behavior."""
        pass

    def create(self, llm: LLM) -> FunctionAgent:
        """Create and configure the FunctionAgent instance.

        This is the standard factory method for agent instantiation.
        Can be overridden for custom agent types.

        Args:
            llm: Language model to use for reasoning

        Returns:
            Configured FunctionAgent ready for execution
        """
        return FunctionAgent(
            system_prompt=self.get_system_prompt(),
            tools=self.get_tools(),
            llm=llm,
        )

    async def run(self, llm: LLM, user_msg: str, **kwargs):
        """Convenience method to create and run the agent in one call.

        Args:
            llm: Language model to use
            user_msg: User message to process
            **kwargs: Additional arguments passed to agent.run()

        Returns:
            Agent execution result
        """
        agent = self.create(llm)
        return await agent.run(user_msg=user_msg, **kwargs)
