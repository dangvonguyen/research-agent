import asyncio
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.ai.tools.base import BaseTool as BaseRetriever
from app.ai.tools.retrieval.dense import DenseRetrieverTool
from app.ai.tools.retrieval.lexical import LexicalRetrieverTool
from app.services.llm_service import default_llm
from app.services.rag_service import RAGService
from rageval.retrieval_eval.match_strategies import (
    MatchStrategy,
    SectionSimilarityMatch,
)
from rageval.retrieval_eval.metrics import RetrievalMetrics

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

MetricDict = dict[str, float]


class RetrievalEvaluator:
    """Evaluates retrieval quality on dataset."""

    def __init__(
        self,
        dataset_path: str,
        retriever: BaseRetriever,
        matcher: MatchStrategy,
        top_k: int,
    ):
        """Initialize evaluator.

        Args:
            dataset_path: Path to query file
            retriever: Retrieval tool to use
            matcher: Match strategy for determining relevance
            top_k: Number of chunks to retrieve per query
        """
        self.dataset_path = Path(dataset_path)
        self.retriever = retriever
        self.metrics = RetrievalMetrics(matcher)
        self.top_k = top_k

    def load_queries(self) -> list[dict[str, Any]]:
        """
        Load queries from JSONL file.
        """
        with open(self.dataset_path) as f:
            return [json.loads(line.strip()) for line in f]

    async def retrieve(self, query: str) -> list[str]:
        tool_output = await self.retriever.arun(
            query=query,
            top_k=self.top_k,
        )

        # Extract chunks from tool output
        if tool_output.type == "json" and isinstance(tool_output.value, dict):
            records = tool_output.value.get("records", [])
            return [record["text"] for record in records]
        else:
            logger.warning(f"Unexpected tool output type: {tool_output.type}")
            return []

    async def evaluate_query(self, query_item: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single query."""

        query_id = query_item["query"]["query_id"]
        query_text = query_item["query"]["content"]
        query_type = query_item["query"]["query_type"]

        retrieved = await self.retrieve(query_text)
        ground_truth = query_item["ground_truth"].get("references", [])

        # Compute metrics
        metrics = self.metrics.compute_all(retrieved, ground_truth)

        return {
            "query_id": query_id,
            "query_type": query_type,
            "query": query_text,
            "num_retrieved": len(retrieved),
            "num_ground_truth": len(ground_truth),
            "metrics": metrics,
        }

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
        Aggregate results by query type.
        """

        def _average(metrics: list[dict[str, float]], key: str) -> float:
            return sum(m[key] for m in metrics) / len(metrics) if metrics else 0.0

        by_type: dict[str, list[dict[str, float]]] = defaultdict(list)

        for r in results:
            by_type[r["query_type"]].append(r["metrics"])

        aggregated = {}
        for query_type, metrics in by_type.items():
            aggregated[query_type] = {
                "count": len(metrics),
                "avg_recall": _average(metrics, "recall"),
                "avg_precision": _average(metrics, "precision"),
                "avg_hit_rate": _average(metrics, "hit_rate"),
                "avg_mrr": _average(metrics, "mrr"),
            }

        # Compute overall statistics
        all_metrics = [r["metrics"] for r in results]
        aggregated["OVERALL"] = {
            "count": len(all_metrics),
            "avg_recall": _average(all_metrics, "recall"),
            "avg_precision": _average(all_metrics, "precision"),
            "avg_hit_rate": _average(all_metrics, "hit_rate"),
            "avg_mrr": _average(all_metrics, "mrr"),
        }

        return aggregated

    def save_results(
        self,
        results: list[dict[str, Any]],
        aggregated: dict[str, dict[str, Any]],
        output_dir: Path,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        detailed_path = output_dir / "detailed_results.json"
        with open(detailed_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved detailed results to {detailed_path}")

        report_path = output_dir / "aggregated_report.json"
        with open(report_path, "w") as f:
            json.dump(aggregated, f, indent=2)
        logger.info(f"Saved aggregated report to {report_path}")

    async def run(self, output_dir: str) -> dict[str, Any]:
        queries = self.load_queries()

        semaphore = asyncio.Semaphore(8)

        async def _eval(q: dict[str, Any]):
            async with semaphore:
                return await self.evaluate_query(q)

        results = await asyncio.gather(*(_eval(q) for q in queries))
        aggregated = self.aggregate_results(results)

        if output_dir:
            self.save_results(results, aggregated, Path(output_dir))

        return aggregated


async def main():
    top_k = 20

    dataset_path = "/home/jarvis/Workspaces/research-agent/backend/rageval/qar_generation/results/DRAGONBALL_query.jsonl"
    output_dir = f"/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/results/k_{top_k}"

    rag_service = RAGService(llm=default_llm)

    experiments = [
        ("dense", DenseRetrieverTool(rag_service), SectionSimilarityMatch(0.97)),
        ("lexical", LexicalRetrieverTool(), SectionSimilarityMatch(0.97)),
    ]

    for name, retriever, matcher in experiments:
        logger.info(f"Evaluating {name} retriever...")
        evaluator = RetrievalEvaluator(
            dataset_path=dataset_path,
            retriever=retriever,
            matcher=matcher,
            top_k=top_k,
        )
        await evaluator.run(output_dir=f"{output_dir}/{name}")


if __name__ == "__main__":
    asyncio.run(main())
