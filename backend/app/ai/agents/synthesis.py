"""Synthesis Agent - handles broad research synthesis across many papers."""

from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool as LlamaBaseTool
from llama_index.core.tools import FunctionTool

from app.ai.prompts import SYNTHESIS_AGENT_PROMPT
from app.ai.tools.structure_extract import StructuredExtractorTool
from app.ai.tools.tavily_search import TavilySearchTool
from app.services.rag_service import RAGService

from .base import BaseAgent
from .retrieval import RetrievalAgent


class SynthesisAgent(BaseAgent):
    """Agent specialized in broad research synthesis across many papers.

    This agent is optimized for breadth over depth: it analyzes patterns,
    trends, and insights across 10-50+ papers rather than deep-diving into 1-2 papers.
    """

    def __init__(self, rag_service: RAGService | None = None):
        """Initialize the SynthesisAgent.

        Args:
            rag_service: Optional RAGService instance. If not provided, will be created when tools are needed.
                This will be shared with the RetrievalAgent.
        """
        self._rag_service = rag_service
        self._llm: LLM | None = None

    @property
    def name(self) -> str:
        """Unique identifier for the agent."""
        return "synthesis_agent"

    @property
    def description(self) -> str:
        """Concise explanation of the agent's research function."""
        return (
            "Synthesizes research insights across many papers (10-50+) to identify trends, "
            "compare approaches, track evolution, and map the research landscape. "
            "Use this agent for broad survey-style questions about fields, approaches, "
            "consensus/disagreement, temporal trends, and comparative analysis. "
            "Optimized for breadth over depth."
        )

    @property
    def system_prompt(self) -> str:
        """Return the system prompt that defines agent behavior."""
        return SYNTHESIS_AGENT_PROMPT

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent provides."""
        return [
            "trend_analysis",
            "comparative_analysis",
            "research_landscape_mapping",
            "temporal_evolution_tracking",
            "consensus_building",
            "broad_survey_synthesis",
        ]

    def _get_rag_service(self) -> RAGService:
        """Get or create RAG service instance.

        Returns:
            RAGService instance

        Raises:
            ValueError: If LLM has not been set via create() method
        """
        if self._llm is None:
            raise ValueError(
                "LLM must be set before getting tools. Call create() first."
            )
        if self._rag_service is None:
            self._rag_service = RAGService(llm=self._llm)
        return self._rag_service

    def get_tools(self) -> list[LlamaBaseTool]:
        """Return the list of tools this agent needs to function.

        Creates a delegation tool for RetrievalAgent to handle document retrieval.

        Returns:
            List of LlamaIndex tools

        Raises:
            ValueError: If LLM has not been set via create() method
        """
        if self._llm is None:
            raise ValueError(
                "LLM must be set before getting tools. Call create() first."
            )

        # Create RetrievalAgent instance
        retrieval_agent = RetrievalAgent(rag_service=self._rag_service)

        # Create delegation function for RetrievalAgent
        async def delegate_to_retrieval(task: str) -> str:
            """Delegate retrieval task to RetrievalAgent."""
            print(
                f"[DEBUG] SynthesisAgent delegate_to_retrieval called with task: {task}"
            )
            result = await retrieval_agent.run(llm=self._llm, user_msg=task)
            return result

        # Create delegation tool
        retrieval_tool = FunctionTool.from_defaults(
            async_fn=delegate_to_retrieval,
            name="retrieval_tool",
            description=retrieval_agent.description,
        )
        extractor_tool = StructuredExtractorTool()
        tavily_search = TavilySearchTool()

        return [retrieval_tool, extractor_tool.as_tool(), tavily_search.as_tool()]

    def create(self, llm: LLM):
        # Store LLM for use in get_tools()
        self._llm = llm

        return super().create(llm)
