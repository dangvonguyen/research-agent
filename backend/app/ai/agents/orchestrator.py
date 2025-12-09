"""Orchestrator Agent - coordinates specialized sub-agents."""

from collections.abc import Callable

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.llms import LLM

from app.ai.prompts import ORCHESTRATOR_AGENT_PROMPT

from .calculator import CalculatorAgent
from .registry import agent_registry
from .weather import WeatherAgent


def initialize_agent_registry() -> None:
    """Initialize the global agent registry with available agents.

    This registers all specialized agents that the orchestrator can delegate to.
    """
    # Register all available agents
    agent_registry.register(CalculatorAgent)
    agent_registry.register(WeatherAgent)


def create_orchestrator_agent(llm: LLM, event_callback: Callable) -> FunctionAgent:
    """Create the top-level orchestrator agent.

    The orchestrator delegates to specialized sub-agents for domain-specific
    tasks using the agent registry pattern. Sub-agents operate with isolated
    context - they receive only the specific task routed to them, not the full
    conversation history.

    Args:
        llm: Language model for the orchestrator

    Returns:
        Configured FunctionAgent for orchestration
    """
    # Ensure registry is initialized
    if not agent_registry.list_agents():
        initialize_agent_registry()

    # Get delegation tools from registry
    tools = agent_registry.create_delegation_tools_with_streaming(llm, event_callback)

    return FunctionAgent(
        system_prompt=ORCHESTRATOR_AGENT_PROMPT,
        tools=tools,
        llm=llm,
    )
