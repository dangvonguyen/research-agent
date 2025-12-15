"""Retrieval Agent - autonomous multi-strategy document retrieval."""

from llama_index.core.llms import LLM
from llama_index.core.tools import BaseTool as LlamaBaseTool

from app.ai.prompts import RETRIEVAL_AGENT_PROMPT
from app.ai.tools.retrieval import (
    DenseRetrieverTool,
    LexicalRetrieverTool,
    MetadataRetrieverTool,
)
from app.services.rag_service import RAGService

from .base import BaseAgent


class RetrievalAgent(BaseAgent):
    """Agent specialized in autonomous multi-strategy document retrieval.

    Intelligently orchestrates semantic, keyword, and metadata search to provide
    comprehensive, deduplicated, and re-ranked results.
    """

    def __init__(self, rag_service: RAGService | None = None):
        self._rag_service = rag_service
        self._llm: LLM | None = None

    @property
    def name(self) -> str:
        return "retrieval_agent"

    @property
    def description(self) -> str:
        return (
            "Autonomous retrieval agent that intelligently combines semantic search, "
            "keyword search, and metadata filtering to find relevant document chunks. "
            "Use for comprehensive retrieval with automatic strategy selection, "
            "query enhancement, and result merging. Returns deduplicated and re-ranked "
            "results with metadata from the corpus."
        )

    @property
    def system_prompt(self) -> str:
        return RETRIEVAL_AGENT_PROMPT

    @property
    def capabilities(self) -> list[str]:
        return [
            "hybrid_retrieval",
            "multi_strategy_search",
            "query_enhancement",
            "result_deduplication",
        ]

    def _get_rag_service(self) -> RAGService:
        if self._llm is None:
            raise ValueError(
                "LLM must be set before getting tools. Call create() first."
            )
        if self._rag_service is None:
            self._rag_service = RAGService(llm=self._llm)
        return self._rag_service

    def get_tools(self) -> list[LlamaBaseTool]:
        rag_service = self._get_rag_service()

        # Create all three retrieval tool instances
        dense_tool = DenseRetrieverTool(rag_service=rag_service)
        lexical_tool = LexicalRetrieverTool()
        metadata_tool = MetadataRetrieverTool()

        return [
            dense_tool.as_tool(),
            lexical_tool.as_tool(),
            metadata_tool.as_tool(),
        ]

    def create(self, llm: LLM):
        # Store LLM for use in get_tools()
        self._llm = llm

        return super().create(llm)
