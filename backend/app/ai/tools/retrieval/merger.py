"""Merger tool for combining and deduplicating retrieval results."""

import logging
from collections import defaultdict
from typing import Any

from llama_index.core.workflow import Context
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class MergerToolInput(BaseModel):
    """Input schema for MergerTool."""

    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return after merging and deduplication",
    )
    rerank_strategy: str = Field(
        default="max_score",
        description=(
            "Re-ranking strategy: 'max_score' (best score wins), "
            "'avg_score' (average across strategies)"
        ),
    )


class MergerTool(BaseTool):
    """Merge and deduplicate retrieval results with automatic normalization.

    Combines outputs from all retrieval tools, applies score normalization,
    deduplicates by chunk_id, and re-ranks results. Has return_direct=True
    to terminate agent immediately.
    """

    name = "merge_results"
    input_schema = MergerToolInput
    description = """Combine and deduplicate results from all retrieval tools.

This tool MUST be called as the FINAL step after using retrieval tools.

Features:
- Merge semantic, keyword, and metadata results
- Normalize BM25 scores to [0, 1] range
- Deduplicate by chunk_id
- Re-rank using max_score, or avg_score
- Return top_k results

Use when:
- You have completed all necessary retrieval operations
- You are ready to return final results to the user

Do NOT use when:
- Before calling any retrieval tools
- In the middle of retrieval strategy
"""

    async def arun(
        self, ctx: Context, top_k: int = 10, rerank_strategy: str = "max_score"
    ) -> ToolOutput:
        """Merge retrieval results from context store.

        Args:
            ctx: Workflow context with persisted tool results
            top_k: Maximum results to return
            rerank_strategy: Scoring strategy

        Returns:
            ToolOutput with merged results
        """
        try:
            # Retrieve persisted results (structure: {tool_name: [result1, result2, ...]})
            retrieval_results: dict[str, list[dict[str, Any]]] = await ctx.store.get(
                "retrieval_results", default={}
            )

            if not retrieval_results:
                return ToolOutput(
                    type="error-json",
                    value={
                        "error": "no_retrieval_tools_called",
                        "message": "No retrieval tools have been called",
                    },
                )

            # Collect all outputs and errors from all tool invocations
            semantic_outputs = []
            lexical_outputs = []
            metadata_outputs = []
            errors = []

            for tool_name, result_list in retrieval_results.items():
                for result in result_list:
                    output = result["output"]

                    if result["status"] == "error":
                        errors.append(
                            {
                                "error": output.get("error"),
                                "message": output.get("message"),
                            }
                        )
                        continue

                    # Collect successful outputs by tool type
                    if tool_name == "semantic_search":
                        semantic_outputs.append(output)
                    elif tool_name == "keyword_search":
                        lexical_outputs.append(output)
                    elif tool_name == "metadata_search":
                        metadata_outputs.append(output)

            # Check if all tools failed
            if not any([semantic_outputs, lexical_outputs, metadata_outputs]):
                return ToolOutput(
                    type="error-json",
                    value={
                        "error": "all_retrieval_tools_failed",
                        "message": "All retrieval tools failed to return results",
                        "errors": errors,
                    },
                )

            # Merge all outputs
            merged_result = self.merge_retrieval_outputs(
                semantic_outputs=semantic_outputs,
                lexical_outputs=lexical_outputs,
                metadata_outputs=metadata_outputs,
                top_k=top_k,
                rerank_strategy=rerank_strategy,
            )

            # Add merge operation metadata
            merged_result["merge_metadata"] = {
                "tools_used": list(retrieval_results.keys()),
                "total_calls": sum(
                    len(results) for results in retrieval_results.values()
                ),
                "rerank_strategy": rerank_strategy,
                "had_errors": bool(errors),
                "errors": errors or None,
            }

            logger.info(
                "Merged %d results from %d tool calls (strategy: %s)",
                merged_result["count"],
                merged_result["merge_metadata"]["total_calls"],
                rerank_strategy,
            )

            return ToolOutput(type="json", value=merged_result)

        except Exception as e:
            logger.exception("MergerTool failed unexpectedly: %s", str(e))
            error_data = {
                "error": "merge_retrieval_results_failed",
                "message": "Failed to merge retrieval results",
            }
            return ToolOutput(type="error-json", value=error_data)

    def as_tool(self):
        """Convert to FunctionTool with return_direct=True for immediate termination."""
        tool = super().as_tool()

        # Set return_direct in tool metadata
        tool.metadata.return_direct = True

        return tool

    @staticmethod
    def normalize_bm25_score(bm25_score: float, max_bm25: float = 10.0) -> float:
        """Normalize BM25 score to [0, 1] range.

        Args:
            bm25_score: Raw BM25 score (unbounded, typically 0-10)
            max_bm25: Expected maximum for scaling

        Returns:
            Capped normalized score in [0, 1]
        """
        return min(bm25_score / max_bm25, 1.0)

    @staticmethod
    def deduplicate_and_rerank(
        results: list[dict[str, Any]], strategy: str = "max_score"
    ) -> list[dict[str, Any]]:
        """Deduplicate by chunk_id and re-rank by strategy.

        Groups results by chunk_id, applies ranking strategy, and sorts descending.

        Args:
            results: Results with text, score, metadata, and strategy fields
            strategy: max_score (highest) | avg_score (mean)

        Returns:
            Deduplicated results sorted by score descending
        """
        if not results:
            return []

        # Group by chunk_id using defaultdict
        chunks_by_id: dict[str, list[dict]] = defaultdict(list)

        for result in results:
            chunk_id = result.get("metadata", {}).get("chunk_id")
            if not chunk_id:
                logger.warning("Result missing chunk_id, skipping")
                continue

            chunks_by_id[chunk_id].append(result)

        # Merge duplicates based on strategy
        merged_results = []

        for chunk_results in chunks_by_id.values():
            if strategy == "max_score":
                # Use result with highest score
                best_result = max(chunk_results, key=lambda x: x.get("score", 0.0))
                merged_results.append(best_result)

            elif strategy == "avg_score":
                # Average scores across all strategies
                avg_score = sum(r.get("score", 0.0) for r in chunk_results) / len(
                    chunk_results
                )
                merged = chunk_results[0].copy()
                merged["score"] = avg_score
                merged["strategies"] = [
                    r.get("strategy", "unknown") for r in chunk_results
                ]
                merged_results.append(merged)

        # Sort by score descending
        merged_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        logger.info(
            "Deduplication: %d results -> %d unique chunks",
            len(results),
            len(merged_results),
        )

        return merged_results

    @staticmethod
    def merge_retrieval_outputs(
        semantic_outputs: list[dict[str, Any]] | None = None,
        lexical_outputs: list[dict[str, Any]] | None = None,
        metadata_outputs: list[dict[str, Any]] | None = None,
        top_k: int = 10,
        rerank_strategy: str = "max_score",
    ) -> dict[str, Any]:
        """Merge outputs from multiple retrieval tool calls.

        Args:
            semantic_outputs: List of DenseRetrieverTool outputs
            lexical_outputs: List of LexicalRetrieverTool outputs
            metadata_outputs: List of MetadataRetrieverTool outputs
            top_k: Maximum results after merging
            rerank_strategy: max_score | avg_score

        Returns:
            {"count": int, "records": list, "total_before_dedup": int, "strategies_used": list}
        """
        all_results = []

        # Process all semantic outputs
        if semantic_outputs:
            for output in semantic_outputs:
                if output and output.get("records"):
                    for record in output["records"]:
                        record["strategy"] = "semantic"
                        all_results.append(record)

        # Process all lexical outputs with BM25 normalization
        if lexical_outputs:
            for output in lexical_outputs:
                if output and output.get("records"):
                    for record in output["records"]:
                        original_score = record.get("score", 0.0)
                        record["score"] = MergerTool.normalize_bm25_score(
                            original_score
                        )
                        record["original_bm25_score"] = original_score
                        record["strategy"] = "lexical"
                        all_results.append(record)

        # Process all metadata outputs (assign neutral score)
        if metadata_outputs:
            for output in metadata_outputs:
                if output and output.get("records"):
                    for record in output["records"]:
                        record["score"] = 0.5  # Neutral score for unranked results
                        record["strategy"] = "metadata"
                        all_results.append(record)

        # Deduplicate and re-rank
        merged = MergerTool.deduplicate_and_rerank(
            all_results, strategy=rerank_strategy
        )

        # Limit to top_k
        top_results = merged[:top_k]

        return {
            "count": len(top_results),
            "records": top_results,
            "total_before_dedup": len(all_results),
            "strategies_used": sorted({r.get("strategy") for r in all_results}),
        }
