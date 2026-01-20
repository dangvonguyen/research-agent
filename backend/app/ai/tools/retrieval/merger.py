"""Merger tool for combining, deduplicating, and reranking retrieval results."""

import logging
from collections import defaultdict
from typing import Any, Literal

from llama_index.core.workflow import Context
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class MergerToolInput(BaseModel):
    """Input schema for MergerTool."""

    top_k: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of results to return after merging",
    )
    strategy: Literal["rrf"] = Field(
        default="rrf",
        # description=(
        #     "Merge strategy: "
        #     "'rrf' - merge semantic + keyword with Reciprocal Rank Fusion, "
        #     "'metadata' - return metadata results directly without reranking"
        # ),
    )


class MergerTool(BaseTool):
    """Merge and deduplicate retrieval results with RRF or metadata-only mode."""

    name = "merge_results"
    input_schema = MergerToolInput
    description = """FINAL MERGE STEP FOR RETRIEVAL WORKFLOWS.

This tool merges and deduplicates results from all previously executed retrieval tools.

MODES:
- rrf: Merge semantic + keyword results with Reciprocal Rank Fusion
- metadata: Return metadata search results directly (no reranking)

WHEN TO USE:
- You have completed all necessary retrieval operations
- You are ready to return the final answer to the user

IMPORTANT RULES:
- Do NOT call before retrieval tools
- This tool must be called exactly once per workflow
- Calling this tool terminates the agent immediately
"""

    async def arun(
        self,
        ctx: Context,
        top_k: int = 20,
        strategy: Literal["rrf"] = "rrf",
    ) -> ToolOutput:
        """Merge retrieval results from context store.

        Args:
            ctx: Workflow context with persisted tool results
            top_k: Maximum results to return
            strategy: Merge strategy (rrf or metadata)

        Returns:
            ToolOutput with merged results
        """
        try:
            top_k = 20
            strategy = "rrf"
            # Retrieve persisted results from context
            retrieval_results: dict[str, list[dict[str, Any]]] = await ctx.store.get(
                "retrieval_results", default={}
            )

            if not retrieval_results:
                return self._error(
                    "no_retrieval_tools_called",
                    "No retrieval tools have been called",
                )

            # Merge results based on strategy
            merged, errors = self._merge_results(retrieval_results, strategy)

            if not merged:
                return self._error(
                    "all_retrieval_tools_failed",
                    "All retrieval tools failed to return results",
                    errors=errors,
                )

            # Apply RRF ranking if strategy is rrf, otherwise just truncate
            if strategy == "rrf":
                final = self._apply_rrf(merged, top_k)
            else:
                final = merged[:top_k]

            logger.info(
                "Merged %d tools → %d results (strategy: %s)",
                len(retrieval_results),
                len(final),
                strategy,
            )

            return ToolOutput(
                type="json",
                value={"count": len(final), "records": final},
            )

        except Exception as e:
            logger.exception("MergerTool failed unexpectedly: %s", str(e))
            return self._error(
                "merge_failed",
                "Failed to merge retrieval results",
            )

    def _merge_results(
        self,
        retrieval_results: dict[str, list[dict[str, Any]]],
        strategy: Literal["rrf", "metadata"],
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """Merge and deduplicate results based on strategy.

        Args:
            retrieval_results: Dict of tool_name -> list of results
            strategy: Merge strategy (rrf or metadata)

        Returns:
            Tuple of (merged results, errors)
        """
        chunks: dict[str, dict[str, Any]] = {}
        errors: list[dict[str, str]] = []

        # Define which tools to use based on strategy
        allowed_tools = (
            {"metadata_search"}
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
                    chunk_id = record.get("metadata", {}).get("chunk_id")
                    if not chunk_id:
                        continue

                    # Deduplicate: track strategy and keep first occurrence
                    if chunk_id not in chunks:
                        chunks[chunk_id] = {
                            **record,
                            "strategy": tool_name.replace("_search", ""),
                            "strategies": [],
                        }

                    # Track which strategies found this chunk
                    chunks[chunk_id]["strategies"].append(
                        tool_name.replace("_search", "")
                    )

        logger.info(
            "Merged %d tools → %d unique chunks (strategy: %s)",
            len(retrieval_results),
            len(chunks),
            strategy,
        )

        return list(chunks.values()), errors

    def _apply_rrf(
        self, results: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Apply RRF ranking to merged results.

        Args:
            results: Merged results grouped by strategy
            top_k: Maximum results to return

        Returns:
            Top-k results ranked by RRF score
        """
        # Group results by strategy for ranking
        results_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for result in results:
            strategy = result.get("strategy", "unknown")
            results_by_strategy[strategy].append(result)

        # Compute RRF scores
        rrf_scores = self._compute_rrf_scores(results_by_strategy)

        # Attach RRF scores to results
        for result in results:
            chunk_id = result.get("metadata", {}).get("chunk_id")
            if chunk_id:
                result["rrf_score"] = rrf_scores.get(chunk_id, 0.0)

        # Sort by RRF score descending
        results.sort(key=lambda x: x.get("rrf_score", 0.0), reverse=True)

        logger.info("RRF ranking: %d results → top %d", len(results), top_k)

        return results[:top_k]

    @staticmethod
    def _compute_rrf_scores(
        results_by_strategy: dict[str, list[dict[str, Any]]], k: int = 60
    ) -> dict[str, float]:
        """Compute RRF scores for chunks across strategies.

        Args:
            results_by_strategy: Dict mapping strategy name to ranked result list
            k: RRF constant (default 60)

        Returns:
            Dict mapping chunk_id to RRF score
        """
        rrf_scores: dict[str, float] = defaultdict(float)

        for _, strategy_results in results_by_strategy.items():
            for rank, result in enumerate(strategy_results, start=1):
                chunk_id = result.get("metadata", {}).get("chunk_id")
                if not chunk_id:
                    continue

                # RRF formula: 1 / (k + rank)
                rrf_scores[chunk_id] += 1.0 / (k + rank)

        return rrf_scores

    @staticmethod
    def _error(code: str, message: str, **extra) -> ToolOutput:
        """Create error ToolOutput."""
        payload = {"error": code, "message": message}
        if extra:
            payload.update(extra)
        return ToolOutput(type="error-json", value=payload)

    def as_tool(self):
        """Convert to FunctionTool with return_direct=True."""
        tool = super().as_tool()
        tool.metadata.return_direct = True
        return tool
