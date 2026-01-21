"""Retrieval Agent - autonomous multi-strategy document retrieval."""

from datetime import UTC, datetime
from typing import Any

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import ToolCallResult
from llama_index.core.llms import LLM
from llama_index.core.memory import BaseMemory
from llama_index.core.tools import BaseTool as LlamaBaseTool
from llama_index.core.workflow import Context

from app.ai.prompt_agents import RETRIEVAL_AGENT_PROMPT
from app.ai.tools.retrieval import (
    DenseRetrieverTool,
    LexicalRetrieverTool,
    MergeTool,
)
from app.services.rag_service import RAGService
from app.services.zilliz_service import zilliz_service
from app.types import ToolResultOutput

from .base import BaseAgent


class StatefulRetrievalFunctionAgent(FunctionAgent):
    """Custom FunctionAgent that persists retrieval tool results to ctx.store.

    The state persistence is scoped to retrieval tools only and doesn't affect
    other tool types.
    """

    async def handle_tool_call_results(
        self, ctx: Context, results: list[ToolCallResult], memory: BaseMemory
    ) -> None:
        """Override to persist retrieval tool results to ctx.store.

        Intercepts tool call results, extracts retrieval tool outputs, and stores
        them in a structured format in ctx.store for later consumption by MergerTool.

        This method:
        1. Persists retrieval tool results to ctx.store["retrieval_results"]
        2. Tracks call order in ctx.store["tools_called"]
        3. Flags errors in ctx.store["has_errors"]
        4. Delegates to parent for scratchpad management

        State structure:
        ```
        retrieval_results = {
            "semantic_search": [result1, result2, ...],
            "keyword_search": [result1, ...]
        }
        ```
        """
        # Initialize state if not exists
        retrieval_results: dict[str, Any] = await ctx.store.get(
            "retrieval_results", default={}
        )
        tools_called: list[str] = await ctx.store.get("tools_called", default=[])
        has_errors: bool = await ctx.store.get("has_errors", default=False)

        for result in results:
            tool_name = result.tool_name

            # Only persist results from retrieval tools
            if tool_name not in [
                "semantic_search",
                "keyword_search",
                "metadata_search",
            ]:
                continue

            # Extract structured value from ToolOutput.raw_output (ToolResultOutput)
            raw_output: ToolResultOutput = result.tool_output.raw_output
            output_type = raw_output.type
            output_value = raw_output.value

            # Enforce contract: retrieval tool output MUST be JSON
            if not isinstance(output_value, dict):
                result_entry = {
                    "status": "error",
                    "output": {
                        "error": "invalid_tool_output",
                        "message": "Tool output must be a JSON object",
                        "received_type": type(output_value).__name__,
                    },
                    "timestamp": datetime.now(UTC).isoformat(),
                    "tool_id": result.tool_id,
                }

            else:
                # NOTE: `output_value` may already contain a structured error payload
                # Infer error status from the output type
                is_error = output_type.startswith("error")

                result_entry = {
                    "status": "error" if is_error else "success",
                    "output": output_value,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "tool_id": result.tool_id,
                }

            # Handle multiple calls to the same tool
            if tool_name not in retrieval_results:
                retrieval_results[tool_name] = []
            retrieval_results[tool_name].append(result_entry)

            # Track tool call order
            tools_called.append(tool_name)

            # Update error flag
            if is_error:
                has_errors = True

        # Persist back to context store
        await ctx.store.set("retrieval_results", retrieval_results)
        await ctx.store.set("tools_called", tools_called)
        await ctx.store.set("has_errors", has_errors)

        # Call parent implementation to handle scratchpad updates
        await super().handle_tool_call_results(ctx, results, memory)


class RetrievalAgent(BaseAgent):
    """Agent specialized in autonomous multi-strategy document retrieval.

    Intelligently orchestrates semantic, keyword, and metadata search to provide
    comprehensive, deduplicated, and re-ranked results.
    """

    def __init__(
        self,
        rag_service: RAGService | None = None,
        system_prompt: str | None = None,
        collection_names: list[str] | None = None,
    ):
        self._rag_service = rag_service
        self._llm: LLM | None = None
        self._collection_names = collection_names

    @property
    def name(self) -> str:
        return "local_search_agent"

    @property
    def description(self) -> str:
        return (
            "Autonomous retrieval tool that intelligently combines semantic search, "
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

        # Create all retrieval tool instances with collection filter
        dense_tool = DenseRetrieverTool(
            rag_service=rag_service,
            collection_names=self._collection_names,
        )
        lexical_tool = LexicalRetrieverTool(
            collection_names=self._collection_names,
        )
        merge_tool = MergeTool(zilliz_service)

        return [
            dense_tool.as_tool(),
            lexical_tool.as_tool(),
            merge_tool.as_tool(),
        ]

    def create(self, llm: LLM) -> StatefulRetrievalFunctionAgent:
        """Create a stateful retrieval agent."""
        # Store LLM for use in get_tools()
        self._llm = llm

        return StatefulRetrievalFunctionAgent(
            name=self.name,
            description=self.description,
            system_prompt=self.system_prompt,
            tools=self.get_tools(),
            tool_retriever=self.get_tool_retriever(),
            llm=llm,
            output_cls=self.output_cls,
        )
