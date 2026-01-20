"""Evaluate retrieval tools and pipelines.

This script supports two evaluation modes:

1. **Trace-based evaluation**: Evaluate tool calls from agent traces
2. **Direct pipeline evaluation**: Run tools directly (semantic → keyword → RRF)
"""

import asyncio
import json
import logging
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.ai.tools.retrieval import DenseRetrieverTool, LexicalRetrieverTool
from app.ai.tools.retrieval.merger import MergerTool
from app.services.llm_service import default_llm
from app.services.rag_service import RAGService
from rageval.retrieval_eval.match_strategies import SectionSimilarityMatch
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
        strategy = SectionSimilarityMatch(0.97)
        self.metrics = RetrievalMetrics(strategy)

    def load_traced_queries(self, trace_path: str) -> list[dict[str, Any]]:
        """
        Load agent-traced tool invocations.
        """
        res = []
        with open(trace_path) as f:
            for line in f:
                content = json.loads(line.strip())
                res.append(content)

        return res

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


# =============================================================================
# DIRECT PIPELINE EVALUATOR (No Agent - True Baseline)
# =============================================================================


@dataclass
class PipelineConfig:
    """Configuration for direct pipeline evaluation."""

    semantic_top_k: int = 30
    keyword_top_k: int = 30
    final_top_k: int = 20


class DirectPipelineEvaluator:
    """Evaluates retrieval by running tools directly without an agent.

    This serves as the true baseline:
    - Uses exact user query (no LLM modifications)
    - Fixed pipeline: semantic_search → keyword_search → RRF merge
    - Deterministic and reproducible
    """

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()

        # Initialize tools
        self.rag_service = RAGService(llm=default_llm)
        self.dense_tool = DenseRetrieverTool(rag_service=self.rag_service)
        self.lexical_tool = LexicalRetrieverTool()
        self.merger_tool = MergerTool()

        # Initialize metrics
        strategy = SectionSimilarityMatch(0.97)
        self.metrics = RetrievalMetrics(strategy)

    def load_queries(self, dataset_path: str) -> list[dict[str, Any]]:
        """Load query dataset."""
        with open(dataset_path) as f:
            return [json.loads(line.strip()) for line in f]

    async def run_pipeline(self, query: str) -> dict[str, Any]:
        """Run the retrieval pipeline on a single query.

        Pipeline: semantic_search → keyword_search → RRF merge (using MergerTool)

        Args:
            query: The user query (used as-is, no modifications)

        Returns:
            Dict with tool_calls in the same format as ToolEvaluator
        """
        tool_calls = []

        # Step 1: Semantic search
        semantic_kwargs = {
            "query": query,
            "top_k": self.config.semantic_top_k,
            "metadata_filter": None,
        }
        semantic_output = await self.dense_tool.arun(
            query=query,
            top_k=self.config.semantic_top_k,
        )
        semantic_results = (
            semantic_output.value.get("records", [])
            if semantic_output.type == "json"
            else []
        )
        tool_calls.append(
            {
                "tool_name": "semantic_search",
                "tool_id": f"call_{uuid.uuid4().hex[:24]}",
                "tool_kwargs": semantic_kwargs,
                "tool_output": {
                    "type": semantic_output.type,
                    "value": {
                        "count": len(semantic_results),
                        "records": semantic_results,
                    },
                },
            }
        )

        # Step 2: Keyword search
        keyword_kwargs = {
            "query": query,
            "top_k": self.config.keyword_top_k,
            "metadata_filter": None,
        }
        keyword_output = await self.lexical_tool.arun(
            query=query,
            top_k=self.config.keyword_top_k,
        )
        keyword_results = (
            keyword_output.value.get("records", [])
            if keyword_output.type == "json"
            else []
        )
        tool_calls.append(
            {
                "tool_name": "keyword_search",
                "tool_id": f"call_{uuid.uuid4().hex[:24]}",
                "tool_kwargs": keyword_kwargs,
                "tool_output": {
                    "type": keyword_output.type,
                    "value": {
                        "count": len(keyword_results),
                        "records": keyword_results,
                    },
                },
            }
        )

        # Step 3: RRF merge using MergerTool's logic
        # Build retrieval_results dict in the format MergerTool expects
        retrieval_results = {
            "semantic_search": [
                {"status": "success", "output": {"records": semantic_results}}
            ],
            "keyword_search": [
                {"status": "success", "output": {"records": keyword_results}}
            ],
        }

        # Use MergerTool's internal methods for RRF
        merge_kwargs = {
            "top_k": self.config.final_top_k,
            "strategy": "rrf",
            "query": query,
        }
        merged, _ = self.merger_tool._merge_results(retrieval_results, "rrf")
        final_results = self.merger_tool._apply_rrf(merged, self.config.final_top_k)
        tool_calls.append(
            {
                "tool_name": "merge_results",
                "tool_id": f"call_{uuid.uuid4().hex[:24]}",
                "tool_kwargs": merge_kwargs,
                "tool_output": {
                    "type": "json",
                    "value": {
                        "count": len(final_results),
                        "records": final_results,
                    },
                },
            }
        )

        return {
            "tool_calls": tool_calls,
            "merged_results": final_results,
        }

    async def evaluate_query(self, query_item: dict[str, Any]) -> dict[str, Any]:
        """Evaluate pipeline on a single query.

        Returns results in the same format as ToolEvaluator for consistency.
        """
        query_id = query_item["query"]["query_id"]
        query_text = query_item["query"]["content"]
        query_type = query_item["query"]["query_type"]
        ground_truth = query_item["ground_truth"]

        try:
            # Run pipeline
            pipeline_result = await self.run_pipeline(query_text)

            # Build agent_output from merged results
            merged_results = pipeline_result["merged_results"]
            agent_output = f"type='json' value={{'count': {len(merged_results)}, 'records': [...]}}"

            return {
                "query_id": query_id,
                "query_type": query_type,
                "user_query": query_text,
                "tool_calls": pipeline_result["tool_calls"],
                "agent_output": agent_output,
                "error": False,
                "error_message": None,
                "ground_truth": ground_truth,
            }

        except Exception as e:
            logger.error(f"Error evaluating query {query_id}: {e}")
            return {
                "query_id": query_id,
                "query_type": query_type,
                "user_query": query_text,
                "tool_calls": [],
                "agent_output": None,
                "error": True,
                "error_message": str(e),
                "ground_truth": ground_truth,
            }

    async def evaluate_all(
        self,
        dataset_path: str,
        start_index: int = 0,
        end_index: int | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate pipeline on all queries."""
        all_queries = self.load_queries(dataset_path)
        queries = all_queries[start_index:end_index]

        logger.info(f"Evaluating {len(queries)} queries with direct pipeline")

        results = []
        for i, query_item in enumerate(queries):
            global_idx = start_index + i
            logger.info(
                f"[{global_idx}/{len(all_queries)}] {query_item['query']['query_id']}"
            )

            result = await self.evaluate_query(query_item)
            results.append(result)

            await asyncio.sleep(0.5)  # Rate limiting

        return results

    def _evaluate_tool_call(
        self, tool_call: dict[str, Any], ground_truth: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate a single tool call against ground truth."""
        try:
            chunks = tool_call["tool_output"]["value"]["records"]
            retrieved_texts = [c.get("text") for c in chunks]
            if not retrieved_texts:
                retrieved_texts = [c["metadata"]["chunk_content"] for c in chunks]

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

    def aggregate_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate evaluation results.

        Computes metrics from tool_calls for each result, matching ToolEvaluator format.
        """
        valid_results = [r for r in results if not r.get("error")]

        if not valid_results:
            return {"error": "No valid results"}

        def _average(metrics: list[dict[str, float]], key: str) -> float:
            return sum(m[key] for m in metrics) / len(metrics) if metrics else 0.0

        # Collect metrics by tool
        by_tool: dict[str, list[MetricDict]] = defaultdict(list)
        by_tool_and_type: dict[tuple[str, str], list[MetricDict]] = defaultdict(list)

        for result in valid_results:
            query_type = result["query_type"]
            ground_truth = result["ground_truth"]

            for tool_call in result["tool_calls"]:
                eval_result = self._evaluate_tool_call(tool_call, ground_truth)
                if eval_result["error"]:
                    continue

                eval_result["metrics"]["top_k"] = tool_call["tool_kwargs"]["top_k"]
                by_tool[tool_call["tool_name"]].append(eval_result["metrics"])
                by_tool_and_type[(tool_call["tool_name"], query_type)].append(
                    eval_result["metrics"]
                )

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

        return {
            "pipeline": "direct_rrf",
            "config": {
                "semantic_top_k": self.config.semantic_top_k,
                "keyword_top_k": self.config.keyword_top_k,
                "final_top_k": self.config.final_top_k,
            },
            "total_queries": len(results),
            "valid_queries": len(valid_results),
            "errors": len(results) - len(valid_results),
            "by_tool": aggregated,
        }

    def save_results(
        self,
        results: list[dict[str, Any]],
        aggregated: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """Save evaluation results."""
        output_dir.mkdir(parents=True, exist_ok=True)

        detailed_path = output_dir / "pipeline_evaluations.jsonl"
        with open(detailed_path, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")
        logger.info(f"Saved detailed results to {detailed_path}")

        report_path = output_dir / "pipeline_report.json"
        with open(report_path, "w") as f:
            json.dump(aggregated, f, indent=2)
        logger.info(f"Saved aggregated report to {report_path}")


async def run_trace_evaluation(trace_path: str, output_dir: Path) -> None:
    """Run evaluation from agent traces."""
    logger.info(f"Running trace-based evaluation from {trace_path}")

    evaluator = ToolEvaluator()
    queries = evaluator.load_traced_queries(trace_path)
    results = await evaluator.evaluate_all_traces(queries)
    aggregated = evaluator.aggregate_results(results)
    evaluator.save_results(results, aggregated, output_dir)


async def run_pipeline_evaluation(
    dataset_path: str,
    output_dir: Path,
    config: PipelineConfig | None = None,
    start_index: int = 0,
    end_index: int | None = None,
) -> None:
    """Run direct pipeline evaluation (true baseline)."""
    logger.info(f"Running direct pipeline evaluation on {dataset_path}")

    evaluator = DirectPipelineEvaluator(config=config)
    results = await evaluator.evaluate_all(
        dataset_path=dataset_path,
        start_index=start_index,
        end_index=end_index,
    )
    aggregated = evaluator.aggregate_results(results)
    evaluator.save_results(results, aggregated, output_dir)


async def main():
    """Main entry point - runs direct pipeline baseline."""
    dataset_path = "/home/jarvis/Workspaces/research-agent/backend/rageval/qar_generation/results/DRAGONBALL_query.jsonl"
    output_dir = Path(
        "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/agent/pipeline_baseline"
    )

    pipeline = True

    if pipeline:
        config = PipelineConfig(
            semantic_top_k=30,
            keyword_top_k=30,
            final_top_k=20,
        )
        await run_pipeline_evaluation(
            dataset_path=dataset_path,
            output_dir=output_dir,
            config=config,
        )
        return

    base = "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/agent/openai_final"
    trace_path = Path(f"{base}/traced_queries/traced_pe.jsonl")
    output_dir = Path(f"{base}/eval_pe")

    await run_trace_evaluation(trace_path=trace_path, output_dir=output_dir)

    logger.info("Evaluation complete!")


if __name__ == "__main__":
    asyncio.run(main())
