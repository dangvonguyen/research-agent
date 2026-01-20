"""Replay traced retrieval results through different merge strategies.

This script:
1. Loads traced tool calls (semantic_search + keyword_search outputs)
2. Replays results through different merge algorithms
3. Evaluates and compares performance

This allows comparing merge strategies without re-running retrieval.
"""

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.ai.tools.retrieval.merger import MergerTool
from app.services.zilliz_service import zilliz_service
from rageval.retrieval_eval.match_strategies import SectionSimilarityMatch
from rageval.retrieval_eval.metrics import RetrievalMetrics

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# =============================================================================
# MERGE STRATEGIES
# =============================================================================


class MergeStrategy(ABC):
    """Base class for merge strategies."""

    name: str

    @abstractmethod
    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Merge results from semantic and keyword search."""
        pass


class RRFStrategy(MergeStrategy):
    """Reciprocal Rank Fusion merge strategy."""

    name = "rrf"

    def __init__(self, k: int = 60):
        self.k = k
        self.merger_tool = MergerTool()

    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        # Build retrieval_results dict in MergerTool format
        retrieval_results = {
            "semantic_search": [
                {"status": "success", "output": {"records": semantic_results}}
            ],
            "keyword_search": [
                {"status": "success", "output": {"records": keyword_results}}
            ],
        }

        merged, _ = self.merger_tool._merge_results(retrieval_results, "rrf")
        return self.merger_tool._apply_rrf(merged, top_k)


class SemanticOnlyStrategy(MergeStrategy):
    """Use only semantic search results (baseline)."""

    name = "semantic_only"

    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return semantic_results[:top_k]


class KeywordOnlyStrategy(MergeStrategy):
    """Use only keyword search results (baseline)."""

    name = "keyword_only"

    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        return keyword_results[:top_k]


class SimpleUnionStrategy(MergeStrategy):
    """Simple union with deduplication, no ranking."""

    name = "simple_union"

    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        # Add semantic results first (higher priority)
        for r in semantic_results:
            chunk_id = r.get("metadata", {}).get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(r)

        # Add keyword results
        for r in keyword_results:
            chunk_id = r.get("metadata", {}).get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(r)

        return merged[:top_k]


class WeightedScoreStrategy(MergeStrategy):
    """Weighted combination of semantic and keyword scores."""

    name = "weighted_score"

    def __init__(self, semantic_weight: float = 0.7, keyword_weight: float = 0.3):
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        scores: dict[str, float] = defaultdict(float)
        chunks: dict[str, dict[str, Any]] = {}

        # Normalize and weight semantic scores
        if semantic_results:
            max_sem = max(r.get("score", 0) for r in semantic_results) or 1
            for r in semantic_results:
                chunk_id = r.get("metadata", {}).get("chunk_id")
                if chunk_id:
                    norm_score = r.get("score", 0) / max_sem
                    scores[chunk_id] += self.semantic_weight * norm_score
                    if chunk_id not in chunks:
                        chunks[chunk_id] = r

        # Normalize and weight keyword scores
        if keyword_results:
            max_kw = max(r.get("score", 0) for r in keyword_results) or 1
            for r in keyword_results:
                chunk_id = r.get("metadata", {}).get("chunk_id")
                if chunk_id:
                    norm_score = r.get("score", 0) / max_kw
                    scores[chunk_id] += self.keyword_weight * norm_score
                    if chunk_id not in chunks:
                        chunks[chunk_id] = r

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        merged = []
        for chunk_id in sorted_ids[:top_k]:
            chunk = chunks[chunk_id].copy()
            chunk["combined_score"] = scores[chunk_id]
            merged.append(chunk)

        return merged


class RerankStrategy(MergeStrategy):
    """Cross-encoder reranking using Cohere reranker."""

    name = "rerank"

    def merge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Sync wrapper for async rerank - actual work done in amerge."""
        # This will be called via amerge in async context
        raise NotImplementedError("Use amerge() for RerankStrategy")

    async def amerge(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """Merge and rerank using Cohere cross-encoder."""
        if not query:
            # Fallback to simple union if no query
            return self._simple_union(semantic_results, keyword_results, top_k)

        # Deduplicate and collect unique chunks
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        for r in semantic_results:
            chunk_id = r.get("metadata", {}).get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(r)

        for r in keyword_results:
            chunk_id = r.get("metadata", {}).get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(r)

        if not merged:
            return []

        # Extract texts for reranking
        documents = [r.get("text", "") for r in merged]

        # Call Cohere reranker
        reranked = await zilliz_service.rerank(
            query=query,
            documents=documents,
            top_k=top_k,
        )

        if not reranked:
            logger.warning("Reranking failed, falling back to simple union")
            return merged[:top_k]

        # Map reranked indices back to original records with new scores
        result = []
        for item in reranked:
            idx = item["index"]
            if idx < len(merged):
                base = merged[idx].copy()
                base["original_score"] = base.get("score", 0.0)
                base["score"] = item["score"]
                base["rerank_score"] = item["score"]
                result.append(base)

        return result

    def _simple_union(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Fallback simple union."""
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []

        for r in semantic_results:
            chunk_id = r.get("metadata", {}).get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(r)

        for r in keyword_results:
            chunk_id = r.get("metadata", {}).get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged.append(r)

        return merged[:top_k]


# =============================================================================
# REPLAY EVALUATOR
# =============================================================================


@dataclass
class ReplayConfig:
    """Configuration for replay evaluation."""

    top_k: int = 20
    strategies: list[str] | None = None  # None = all strategies


class MergeReplayEvaluator:
    """Replay traced results through different merge strategies."""

    # Available strategies
    STRATEGIES: dict[str, MergeStrategy] = {
        "rrf": RRFStrategy(),
        "semantic_only": SemanticOnlyStrategy(),
        "keyword_only": KeywordOnlyStrategy(),
        "simple_union": SimpleUnionStrategy(),
        "weighted_score": WeightedScoreStrategy(),
        "weighted_70_30": WeightedScoreStrategy(0.7, 0.3),
        "weighted_50_50": WeightedScoreStrategy(0.5, 0.5),
        "rerank": RerankStrategy(),
    }

    def __init__(self, config: ReplayConfig | None = None):
        self.config = config or ReplayConfig()

        # Select strategies
        if self.config.strategies:
            self.strategies = {
                k: v for k, v in self.STRATEGIES.items() if k in self.config.strategies
            }
        else:
            self.strategies = self.STRATEGIES

        # Initialize metrics
        match_strategy = SectionSimilarityMatch(0.97)
        self.metrics = RetrievalMetrics(match_strategy)

    def load_traces(self, trace_path: str) -> list[dict[str, Any]]:
        """Load traced tool calls."""
        traces = []
        with open(trace_path) as f:
            for line in f:
                traces.append(json.loads(line.strip()))
        return traces

    def extract_results(
        self, trace: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract semantic and keyword results that were used for merge_results.

        MergerTool collects ALL search results that occurred before the merge call,
        so we extract all semantic_search and keyword_search results up to that point.
        """
        tool_calls = trace.get("tool_calls", [])

        # # Find the index of merge_results call
        # merge_idx = None
        # for i, tc in enumerate(tool_calls):
        #     if tc.get("tool_name") == "merge_results":
        #         merge_idx = i
        #         break

        # Determine the range of tool calls to consider
        # If merge_results exists, only consider calls before it
        # Otherwise, consider all calls
        # end_idx = merge_idx if merge_idx is not None else len(tool_calls)

        # Extract ALL semantic and keyword results before merge_results
        semantic_results: list[dict[str, Any]] = []
        keyword_results: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            # tool_call = tool_calls[i]
            tool_name = tool_call.get("tool_name")
            records = self._extract_records(tool_call)

            if tool_name == "semantic_search":
                semantic_results.extend(records)
            elif tool_name == "keyword_search":
                keyword_results.extend(records)

        return semantic_results, keyword_results

    def _extract_records(self, tool_call: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract records from a tool call output."""
        output = tool_call.get("tool_output", {})

        if isinstance(output, dict):
            value = output.get("value", output)
            return value.get("records", [])

        return []

    async def evaluate_trace(self, trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Evaluate a single trace with all merge strategies."""
        query_id = trace.get("query_id")
        query_text = trace.get("user_query")
        ground_truth = trace.get("ground_truth", {})
        gt_refs = ground_truth.get("references", [])

        # Extract results
        semantic_results, keyword_results = self.extract_results(trace)

        results_by_strategy: dict[str, dict[str, Any]] = {}

        for strategy_name, strategy in self.strategies.items():
            try:
                # Apply merge strategy (async for RerankStrategy, sync for others)
                if hasattr(strategy, "amerge"):
                    merged = await strategy.amerge(
                        semantic_results=semantic_results,
                        keyword_results=keyword_results,
                        top_k=self.config.top_k,
                        query=query_text,
                    )
                else:
                    merged = strategy.merge(
                        semantic_results=semantic_results,
                        keyword_results=keyword_results,
                        top_k=self.config.top_k,
                        query=query_text,
                    )

                # Extract texts for evaluation
                retrieved_texts = [r.get("text", "") for r in merged]

                # Compute metrics
                metrics = self.metrics.compute_all(retrieved_texts, gt_refs)

                results_by_strategy[strategy_name] = {
                    "error": False,
                    "merged_count": len(merged),
                    "metrics": metrics,
                }

            except Exception as e:
                logger.error(f"Error with strategy {strategy_name} on {query_id}: {e}")
                results_by_strategy[strategy_name] = {
                    "error": True,
                    "error_message": str(e),
                    "metrics": {"recall": 0, "precision": 0, "hit_rate": 0, "mrr": 0},
                }

        return results_by_strategy

    async def evaluate_all(self, trace_path: str) -> list[dict[str, Any]]:
        """Evaluate all traces with all strategies."""
        traces = self.load_traces(trace_path)
        logger.info(
            f"Loaded {len(traces)} traces, evaluating with {len(self.strategies)} strategies"
        )

        results = []
        for i, trace in enumerate(traces):
            if (i + 1) % 20 == 0:
                logger.info(f"Processing trace {i + 1}/{len(traces)}")

            strategy_results = await self.evaluate_trace(trace)

            results.append(
                {
                    "query_id": trace.get("query_id"),
                    "query_type": trace.get("query_type"),
                    "user_query": trace.get("user_query"),
                    "strategies": strategy_results,
                }
            )

        return results

    def aggregate_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate results by strategy."""
        aggregated: dict[str, dict[str, Any]] = {}

        for strategy_name in self.strategies:
            strategy_metrics: list[dict[str, float]] = []
            by_type: dict[str, list[dict[str, float]]] = defaultdict(list)

            for r in results:
                strat_result = r["strategies"].get(strategy_name, {})
                if strat_result.get("error"):
                    continue

                metrics = strat_result.get("metrics", {})
                strategy_metrics.append(metrics)
                by_type[r["query_type"]].append(metrics)

            if not strategy_metrics:
                continue

            n = len(strategy_metrics)
            aggregated[strategy_name] = {
                "total": n,
                "avg_recall": sum(m["recall"] for m in strategy_metrics) / n,
                "avg_precision": sum(m["precision"] for m in strategy_metrics) / n,
                "avg_hit_rate": sum(m["hit_rate"] for m in strategy_metrics) / n,
                "avg_mrr": sum(m["mrr"] for m in strategy_metrics) / n,
                "by_query_type": {},
            }

            for query_type, type_metrics in by_type.items():
                m = len(type_metrics)
                aggregated[strategy_name]["by_query_type"][query_type] = {
                    "count": m,
                    "recall": sum(x["recall"] for x in type_metrics) / m,
                    "precision": sum(x["precision"] for x in type_metrics) / m,
                    "hit_rate": sum(x["hit_rate"] for x in type_metrics) / m,
                    "mrr": sum(x["mrr"] for x in type_metrics) / m,
                }

        return aggregated

    def print_comparison(self, aggregated: dict[str, Any]) -> None:
        """Print comparison table."""
        print("\n" + "=" * 80)
        print("MERGE STRATEGY COMPARISON")
        print("=" * 80)
        print(
            f"{'Strategy':<20} {'Recall':>10} {'Precision':>10} {'Hit Rate':>10} {'MRR':>10}"
        )
        print("-" * 80)

        # Sort by recall descending
        sorted_strategies = sorted(
            aggregated.items(),
            key=lambda x: x[1].get("avg_recall", 0),
            reverse=True,
        )

        for strategy_name, metrics in sorted_strategies:
            print(
                f"{strategy_name:<20} "
                f"{metrics['avg_recall']:>10.4f} "
                f"{metrics['avg_precision']:>10.4f} "
                f"{metrics['avg_hit_rate']:>10.4f} "
                f"{metrics['avg_mrr']:>10.4f}"
            )

        print("=" * 80)

    def save_results(
        self,
        results: list[dict[str, Any]],
        aggregated: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """Save results."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Detailed results
        detailed_path = output_dir / "merge_strategy_evaluations.jsonl"
        with open(detailed_path, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        logger.info(f"Saved detailed results to {detailed_path}")

        # Aggregated comparison
        report_path = output_dir / "merge_strategy_comparison.json"
        with open(report_path, "w") as f:
            json.dump(aggregated, f, indent=2)
        logger.info(f"Saved comparison report to {report_path}")


# =============================================================================
# MAIN
# =============================================================================


async def main():
    """Main entry point."""
    # Configuration
    # trace_path = "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/traced_queries/agent_tool_calls.jsonl"
    trace_path = "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/agent/openai_final/traced_queries/traced_pe.jsonl"
    output_dir = Path(
        "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/results/merge_comparison"
    )
    output_dir = Path(
        "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/agent/openai_final/traced_queries/pe_merge_comparison"
    )

    config = ReplayConfig(
        top_k=20,
        strategies=None,  # All strategies
    )

    # Run evaluation
    evaluator = MergeReplayEvaluator(config=config)
    results = await evaluator.evaluate_all(trace_path)
    aggregated = evaluator.aggregate_results(results)

    # Print and save
    evaluator.print_comparison(aggregated)
    evaluator.save_results(results, aggregated, output_dir)

    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
