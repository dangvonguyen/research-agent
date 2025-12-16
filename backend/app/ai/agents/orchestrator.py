"""Orchestrator Agent - coordinates RAG for research assistance."""

from collections.abc import Callable

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.llms import LLM

from app.ai.prompts import ORCHESTRATOR_AGENT_PROMPT

from .analysis import AnalysisAgent
from .registry import agent_registry
from .synthesis import SynthesisAgent


def initialize_agent_registry() -> None:
    """Initialize the global agent registry with available agents.

    This registers all specialized agents that the orchestrator can delegate to.
    """

    # Register all available agents
    agent_registry.register(AnalysisAgent)
    agent_registry.register(SynthesisAgent)


def create_orchestrator_agent(llm: LLM, event_callback: Callable) -> FunctionAgent:
    """Create the top-level orchestrator agent.

    Args:
        llm: Language model for the orchestrator
        event_callback: Callback for streaming events

    Returns:
        Configured FunctionAgent for orchestration
    """
    # Ensure registry is initialized
    if not agent_registry.list_agents():
        initialize_agent_registry()

    # Get delegation tools from registry
    delegation_tools = agent_registry.create_delegation_tools_with_streaming(
        llm=llm, event_callback=event_callback
    )

    return FunctionAgent(
        name="Orchestrator_agent",
        system_prompt=ORCHESTRATOR_AGENT_PROMPT,
        tools=delegation_tools,
        llm=llm,
    )
