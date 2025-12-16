"""Agent registry for dynamic agent discovery and management."""

from collections.abc import Callable

from llama_index.core.agent.workflow import AgentOutput
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from .base import AgentMetadata, BaseAgent


class AgentRegistry:
    """Registry for managing and discovering available agents.

    Provides centralized agent lifecycle management:
    - Agent registration and discovery
    - Metadata querying
    - Dynamic agent creation
    - Delegation tooling

    This decouples the orchestrator from specific agent implementations.
    """

    def __init__(self):
        self._agents: dict[str, type[BaseAgent]] = {}
        self._metadata: dict[str, AgentMetadata] = {}

    def register(self, agent_class: type[BaseAgent]) -> None:
        """Register an agent class with the registry.

        Args:
            agent_class: Agent class extending BaseAgent

        Raises:
            ValueError: If agent with same name already registered
        """
        # Instantiate temporarily to get metadata
        instance = agent_class()
        name = instance.name

        if name in self._agents:
            raise ValueError(f"Agent '{name}' is already registered")

        self._agents[name] = agent_class

        # Store metadata
        self._metadata[name] = AgentMetadata(
            name=name,
            description=instance.description,
            capabilities=instance.capabilities,
        )

    def get_agent(self, name: str) -> type[BaseAgent] | None:
        """Get an agent class by name.

        Args:
            name: Agent name

        Returns:
            Agent class or None if not found
        """
        return self._agents.get(name)

    def get_metadata(self, name: str) -> AgentMetadata | None:
        """Get agent metadata by name.

        Args:
            name: Agent name

        Returns:
            Agent metadata or None if not found
        """
        return self._metadata.get(name)

    def list_agents(self) -> list[AgentMetadata]:
        """List all registered agents with their metadata.

        Returns:
            List of agent metadata for all registered agents
        """
        return list(self._metadata.values())

    def list_enabled_agents(self) -> list[AgentMetadata]:
        """List only enabled agents.

        Returns:
            List of enabled agent metadata
        """
        return [meta for meta in self._metadata.values() if meta.enabled]

    def create_agent(self, name: str) -> BaseAgent:
        """Create an agent instance by name.

        Args:
            name: Agent name
            llm: Language model for the agent

        Returns:
            Instantiated agent

        Raises:
            ValueError: If agent not found
        """
        agent_class = self.get_agent(name)
        if not agent_class:
            raise ValueError(f"Agent '{name}' not found in registry")

        return agent_class()

    def create_delegation_tools(self, llm: LLM) -> list[FunctionTool]:
        """Create delegation tools for all enabled agents.

        This generates FunctionTools that the orchestrator can use
        to delegate tasks to sub-agents. Each tool wraps the agent
        execution in a clean interface.

        Args:
            llm: Language model to pass to sub-agents

        Returns:
            List of FunctionTools for agent delegation
        """
        tools = []

        for metadata in self.list_enabled_agents():
            agent_class = self._agents[metadata.name]
            instance = agent_class()

            # Create async wrapper that captures LLM and agent instance
            # Use default argument to capture instance in closure
            def create_delegation_fn(agent: BaseAgent = instance):
                async def delegate(task: str) -> str:
                    """Delegate task to sub-agent."""
                    result = await agent.run(llm=llm, user_msg=task)
                    return result

                return delegate

            # Build the tool
            delegation_fn = create_delegation_fn()

            tool = FunctionTool.from_defaults(
                async_fn=delegation_fn,
                name=metadata.name,
                description=metadata.description,
            )
            tools.append(tool)

        return tools

    def create_delegation_tools_with_streaming(
        self, llm: LLM, event_callback: Callable
    ) -> list[FunctionTool]:
        """Create delegation tools that emit sub-agent events.

        Args:
            llm: Language model
            event_callback: Async function(event, agent_name, agent_type)

        Returns:
            List of FunctionTools with streaming support
        """
        tools = []

        for metadata in self.list_enabled_agents():
            agent_class = self._agents[metadata.name]
            instance = agent_class()

            # Create async wrapper that captures LLM and agent instance
            # Use default argument to capture instance in closure
            def create_delegation_fn(
                agent: BaseAgent = instance, agent_name: str = metadata.name
            ):
                async def delegate(task: str) -> str:
                    """Delegate task, stream events, return result."""
                    handler = agent.get_handler(llm, user_msg=task)

                    result = ""

                    async for event in handler.stream_events():
                        # Stream to client via multiplexer
                        # ContentPartBuilder will capture and buffer these
                        await event_callback(event, agent_name, "sub-agent")

                        # Capture final result
                        if isinstance(event, AgentOutput):
                            result = str(event)

                    # Return ONLY the clean result, keeps parent context clean
                    return result

                return delegate

            # Build the tool
            delegation_fn = create_delegation_fn()

            tool = FunctionTool.from_defaults(
                async_fn=delegation_fn,
                name=metadata.name,
                description=metadata.description,
            )
            tools.append(tool)

        return tools


# Global registry instance
agent_registry = AgentRegistry()
