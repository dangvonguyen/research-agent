"""Analysis Agent - handles research paper retrieval and analysis."""

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool as LlamaBaseTool, FunctionTool

from app.ai.prompts import ANALYSIS_AGENT_PROMPT
from app.services.rag_service import RAGService

from .base import BaseAgent
from .retrieval import RetrievalAgent


class AnalysisAgent(BaseAgent):
    """Agent specialized in retrieving and analyzing research papers."""

    def __init__(self, rag_service: RAGService | None = None):
        """Initialize the AnalysisAgent.

        Args:
            rag_service: Optional RAGService instance. If not provided, will be created when tools are needed.
                This will be shared with the RetrievalAgent.
        """
        self._rag_service = rag_service
        self._llm: LLM | None = None

    @property
    def name(self) -> str:
        """Unique identifier for the agent."""
        return "analysis_tool"

    @property
    def description(self) -> str:
        """Concise explanation of the agent's research function."""
        return (
            "Retrieves and analyzes research papers from the corpus. "
            "Use this agent when you need to search for relevant papers, "
            "find specific information, or explore research topics. "
            "This agent performs semantic search and returns relevant paper chunks with metadata."
        )

    @property
    def system_prompt(self) -> str:
        """Return the system prompt that defines agent behavior."""
        return ANALYSIS_AGENT_PROMPT

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent provides."""
        return ["semantic_search", "paper_retrieval", "research_analysis"]

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
            print(f"[DEBUG] delegate_to_retrieval called with task: {task}")
            result = await retrieval_agent.run(llm=self._llm, user_msg=task)
            return result

        # Create delegation tool
        retrieval_tool = FunctionTool.from_defaults(
            async_fn=delegate_to_retrieval,
            name="retrieval_tool",
            description=retrieval_agent.description,
        )

        return [retrieval_tool]

    def create(self, llm: LLM):
        """Create and configure the FunctionAgent instance.

        Overrides base method to store LLM for tool creation.

        Args:
            llm: Language model to use for reasoning

        Returns:
            Configured FunctionAgent ready for execution
        """
        # Store LLM for use in get_tools()
        self._llm = llm

        return FunctionAgent(
            name=self.name,
            system_prompt=self.system_prompt,
            tools=self.get_tools(),
            llm=llm,
        )
