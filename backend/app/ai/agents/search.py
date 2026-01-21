"""Search Agent - handles web-based research search and question answering."""

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool as LlamaBaseTool

from app.ai.prompt_agents import SEARCH_AGENT_PROMPT
from app.ai.tools.research_search import ResearchSearchTool

from .base import BaseAgent


class SearchAgent(BaseAgent):
    """Agent specialized in web-based research search and question answering.

    This agent uses web search to find current information and answer research questions
    by searching the web, extracting relevant documents, and synthesizing answers.
    """

    def __init__(self):
        """Initialize the SearchAgent."""
        pass

    @property
    def name(self) -> str:
        """Unique identifier for the agent."""
        return "web_search_agent"

    @property
    def description(self) -> str:
        """Concise explanation of the agent's research function."""
        return (
            "Searches the web to find current information and answer research questions. "
            "Uses comprehensive web search to gather information from multiple sources, "
            "selects the most relevant documents, and provides detailed answers. "
            "Use this agent when you need current information from the web, "
            "research on topics not in the local corpus, or when you need to find "
            "recent papers, publications, or information from the internet."
        )

    @property
    def system_prompt(self) -> str:
        """Return the system prompt that defines agent behavior."""
        return SEARCH_AGENT_PROMPT

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent provides."""
        return [
            "web_search",
            "research_search",
            "question_answering",
            "current_information",
            "external_resources",
        ]

    def get_tools(self) -> list[LlamaBaseTool]:
        """Return the list of tools this agent needs to function.

        Returns:
            List of LlamaIndex tools
        """
        research_search_tool = ResearchSearchTool()

        return [research_search_tool.as_tool()]

    def create(self, llm: LLM) -> FunctionAgent:
        """Create and configure the FunctionAgent instance with tools from get_tools().

        Args:
            llm: Language model to use for reasoning

        Returns:
            Configured FunctionAgent ready for execution with tools from get_tools()
        """
        return FunctionAgent(
            name=self.name,
            description=self.description,
            system_prompt=self.system_prompt,
            tools=self.get_tools(),
            llm=llm,
        )
