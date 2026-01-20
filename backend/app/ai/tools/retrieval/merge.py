"""Merger tool for combining, deduplicating, or reranking retrieval results."""

import logging
from typing import Any, Literal

from llama_index.core.workflow import Context
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.zilliz_service import ZillizService
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class MergeToolInput(BaseModel):
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return after merging and/or reranking",
    )
    strategy: Literal["rerank", "metadata"] = Field(
        default="rerank",
        description=(
            "Merge strategy: "
            "'rerank' - apply cross-encoder reranking for content, "
            "'metadata' - return metadata results directly without reranking"
        ),
    )
    query: str | None = Field(
        default=None,
        description=(
            "Natural language query used for cross-encoder reranking. "
            "Required when strategy='rerank'. Ignored otherwise."
        ),
    )


class MergeTool(BaseTool):
    name = "merge_results"
    input_schema = MergeToolInput
    description = """FINAL MERGE STEP FOR RETRIEVAL WORKFLOWS.

This tool merges and deduplicates results from all previously executed retrieval tools \
and optionally applies cross-encoder reranking.

MODES:
- rerank: Merge semantic + keyword results and rerank by relevance
- metadata: Return metadata search results directly (no reranking)

WHEN TO USE:
- You have completed all necessary retrieval operations
- You are ready to return the final answer to the user

IMPORTANT RULES:
- Do NOT call before retrieval tools
- This tool must be called exactly once per workflow
- Calling this tool terminates the agent immediately
"""

    def __init__(self, zilliz_service: ZillizService):
        self.zilliz_service = zilliz_service

    async def arun(
        self,
        ctx: Context,
        top_k: int = 10,
        strategy: Literal["rerank", "metadata"] = "rerank",
        query: str | None = None,
    ) -> ToolOutput:
        try:
            # Retrieve persisted results and query from context
            retrieval_results: dict[str, list[dict[str, Any]]] = await ctx.store.get(
                "retrieval_results", default={}
            )

            if not retrieval_results:
                return self._error(
                    "no_retrieval_tools_called",
                    "No retrieval tools have been called",
                )

            merged, errors = self._merge_results(retrieval_results, strategy)

            if not merged:
                return self._error(
                    "all_retrieval_tools_failed",
                    "All retrieval tools failed to return results",
                    errors=errors,
                )

            if strategy == "rerank":
                final = await self._apply_reranking(query, merged, top_k)
            else:
                final = merged[:top_k]

            return ToolOutput(
                type="json", value={"count": len(final), "records": final}
            )

        except Exception as e:
            logger.exception("MergeTool failed unexpectedly: %s", str(e))
            return self._error(
                "merge_rerank_failed",
                "Failed to merge and rerank results",
            )

    def _merge_results(
        self,
        retrieval_results: dict[str, list[dict[str, Any]]],
        strategy: Literal["rerank", "metadata"],
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        chunks: dict[str, dict[str, Any]] = {}
        errors: list[dict[str, str]] = []

        allowed_tools = (
            ("metadata_search")
            if strategy == "metadata"
            else {"semantic_search", "keyword_search"}
        )

        for tool_name, results in retrieval_results.items():
            for result in results:
                output = result.get("output", {})

                if result.get("status") == "error":
                    errors.append(
                        {
                            "error": output.get("error"),
                            "message": output.get("message"),
                        }
                    )
                    continue

                if tool_name not in allowed_tools:
                    continue

                for record in output.get("records", []):
                    chunk_id = record["metadata"].get("chunk_id")
                    if not chunk_id:
                        continue

                    chunks[chunk_id] = {
                        **record,
                        "strategy": tool_name.replace("_search", ""),
                    }

        logger.info(
            "Merged %d tools → %d unique chunks",
            len(retrieval_results),
            len(chunks),
        )

        return list(chunks.values()), errors

    async def _apply_reranking(
        self, query: str | None, results: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Apply cross-encoder reranking."""

        if not query or not results:
            return results[:top_k]

        # Extract text for reranking
        documents = [r.get("text", "") for r in results]

        reranked = await self.zilliz_service.rerank(
            query=query, documents=documents, top_k=top_k
        )

        if not reranked:
            logger.warning("Reranking failed, returning fallback results")
            return results[:top_k]

        # Map reranked indices back to original records with new scores
        out = []
        for item in reranked:
            idx = item["index"]
            if idx >= len(results):
                continue

            base = results[idx]
            out.append(
                {
                    **base,
                    "original_score": base.get("score", 0.0),
                    "score": item["score"],
                }
            )

        logger.info("Reranked %d → %d results", len(results), len(out))
        return out

    @staticmethod
    def _error(code: str, message: str, **extra) -> ToolOutput:
        payload = {"error": code, "message": message}
        if extra:
            payload.update(extra)
        return ToolOutput(type="error-json", value=payload)

    def as_tool(self):
        tool = super().as_tool()
        tool.metadata.return_direct = True
        return tool
