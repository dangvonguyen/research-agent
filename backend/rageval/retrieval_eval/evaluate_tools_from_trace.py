"""Evaluate individual retrieval tools using agent-traced queries.

This script:
1. Loads agent-traced tool invocations
2. Replays each tool call directly
3. Evaluates tool performance with agent-optimized queries
4. Compares tools side-by-side

This is Level 1 (Tool-level) evaluation with realistic agent-optimized queries.
"""

import asyncio
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rageval.retrieval_eval.match_strategies import SubstringMatch
from rageval.retrieval_eval.metrics import RetrievalMetrics

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

MetricDict = dict[str, float]


class ToolEvaluator:
    """Evaluates retrieval tools using agent-traced queries."""

    def __init__(self):
        self.metrics = RetrievalMetrics(SubstringMatch())

    def load_traced_queries(self, trace_path: str) -> list[dict[str, Any]]:
        """
        Load agent-traced tool invocations.
        """
        with open(trace_path) as f:
            return [json.loads(line.strip()) for line in f]

    def evaluate_tool_call(
        self, tool_call: dict[str, Any], ground_truth: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Evaluate a single tool call.
        """
        try:
            chunks = tool_call["tool_output"]["value"]["records"]
            retrieved_texts = [c.get("text") for c in chunks]
            if not retrieved_texts:
                retrieved_texts = [c["metadata"]["chunk_content"] for c in chunks]

            # Compute metrics
            gt_refs = ground_truth.get("references", [])
            metrics = self.metrics.compute_all(retrieved_texts, gt_refs)

            return {
                "error": False,
                "num_retrieved": len(retrieved_texts),
                "metrics": metrics,
            }

        except Exception as e:
            logger.error(f"Error evaluating {tool_call['tool_name']}: {e}")
            return {
                "error": True,
                "error_message": str(e),
                "metrics": {
                    "recall": 0.0,
                    "precision": 0.0,
                    "hit_rate": 0.0,
                    "mrr": 0.0,
                },
            }

    async def evaluate_all_traces(
        self, traces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Evaluate all traced tool calls.
        """
        results = []

        for trace in traces:
            query_result = {
                "query_id": trace["query_id"],
                "query_type": trace["query_type"],
                "user_query": trace["user_query"],
                "tool_evaluations": [],
            }

            # Evaluate each tool call
            for tool_call in trace["tool_calls"]:
                eval_result = self.evaluate_tool_call(
                    tool_call=tool_call,
                    ground_truth=trace["ground_truth"],
                )

                query_result["tool_evaluations"].append(
                    {
                        "tool_name": tool_call["tool_name"],
                        "tool_kwargs": tool_call["tool_kwargs"],
                        **eval_result,
                    }
                )

            results.append(query_result)

        return results

    def _average_metrics(self, metrics: list[MetricDict]) -> MetricDict:
        n = len(metrics)
        if n == 0:
            return {"recall": 0.0, "precision": 0.0, "hit_rate": 0.0, "mrr": 0.0}

        return {
            k: sum(m[k] for m in metrics) / n
            for k in ("recall", "precision", "hit_rate", "mrr")
        }

    def aggregate_results(
        self, results: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate results by tool and query type.
        """

        def _average(metrics: list[dict[str, float]], key: str) -> float:
            return sum(m[key] for m in metrics) / len(metrics) if metrics else 0.0

        # Collect metrics by tool
        by_tool: dict[str, list[MetricDict]] = defaultdict(list)
        by_tool_and_type: dict[tuple[str, str], list[MetricDict]] = defaultdict(list)

        for result in results:
            query_type = result["query_type"]

            for t in result["tool_evaluations"]:
                if t["error"]:
                    continue

                t["metrics"]["top_k"] = t["tool_kwargs"]["top_k"]
                by_tool[t["tool_name"]].append(t["metrics"])
                by_tool_and_type[(t["tool_name"], query_type)].append(t["metrics"])

        # Compute averages by tool
        aggregated = {}
        for tool_name, metrics in by_tool.items():
            aggregated[tool_name] = {
                "total_calls": len(metrics),
                "avg_recall": _average(metrics, "recall"),
                "avg_precision": _average(metrics, "precision"),
                "avg_hit_rate": _average(metrics, "hit_rate"),
                "avg_mrr": _average(metrics, "mrr"),
                "avg_top_k": _average(metrics, "top_k"),
                "by_query_type": {},
            }

        # Compute averages by tool and query type
        for (tool_name, query_type), metrics in by_tool_and_type.items():
            aggregated[tool_name]["by_query_type"][query_type] = {
                "calls": len(metrics),
                "avg_recall": _average(metrics, "recall"),
                "avg_precision": _average(metrics, "precision"),
                "avg_hit_rate": _average(metrics, "hit_rate"),
                "avg_mrr": _average(metrics, "mrr"),
            }

        return aggregated

    def save_results(
        self,
        results: list[dict[str, Any]],
        aggregated: dict[str, dict[str, Any]],
        output_dir: Path,
    ) -> None:
        """
        Save evaluation results.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        detailed_path = output_dir / "tool_evaluations.jsonl"
        with open(detailed_path, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")
        logger.info(f"Saved detailed results to {detailed_path}")

        report_path = output_dir / "tool_comparison.json"
        with open(report_path, "w") as f:
            json.dump(aggregated, f, indent=2)
        logger.info(f"Saved aggregated report to {report_path}")


async def main():
    """Main entry point."""
    trace_path = "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/traced_queries/agent_tool_calls.jsonl"
    output_dir = Path(
        "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/tool_eval_results"
    )

    # Run evaluation
    evaluator = ToolEvaluator()
    queries = evaluator.load_traced_queries(trace_path)
    results = await evaluator.evaluate_all_traces(queries)

    # Aggregate and report
    aggregated = evaluator.aggregate_results(results)

    # Save results
    evaluator.save_results(results, aggregated, output_dir)


if __name__ == "__main__":
    asyncio.run(main())
