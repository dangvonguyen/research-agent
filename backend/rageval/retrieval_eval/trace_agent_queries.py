"""Trace retrieval agent tool invocations to capture optimized queries.

This script:
1. Runs the retrieval agent on each query with a specific prompt variant
2. Captures which tools the agent calls and with what arguments
3. Saves tool invocations for later evaluation

Prompt Variants:
- baseline: Simple prompt, exact user query, RRF merge
- pe: Prompt-engineered with query expansion, rerank merge

Usage:
    python trace_agent_queries.py --variant baseline
    python trace_agent_queries.py --variant pe
"""

import argparse
import asyncio
import json
import logging
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
from llama_index.core.agent.workflow import ToolCall, ToolCallResult
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.ai.agents.retrieval import RetrievalAgent
from app.ai.prompts import (
    RETRIEVAL_AGENT_PROMPT_BASELINE,
    RETRIEVAL_AGENT_PROMPT_PE,
)
from app.services.llm_service import default_llm

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class PromptVariant(str, Enum):
    """Available prompt variants for A/B testing."""

    BASELINE = "baseline"
    PE = "pe"

    @property
    def prompt(self) -> str:
        """Get the prompt string for this variant."""
        if self == PromptVariant.BASELINE:
            return RETRIEVAL_AGENT_PROMPT_BASELINE
        elif self == PromptVariant.PE:
            return RETRIEVAL_AGENT_PROMPT_PE
        raise ValueError(f"Unknown variant: {self}")


@dataclass
class ToolInvocation:
    tool_name: str
    tool_id: str
    tool_kwargs: dict[str, Any]
    tool_output: Any | None = None


@dataclass
class TraceResult:
    query_id: str
    query_type: str
    user_query: str
    tool_calls: list[ToolInvocation]
    agent_output: str
    error: bool
    error_message: str | None
    ground_truth: dict[str, Any]


class AgentTracer:
    """Traces retrieval agent tool invocations."""

    def __init__(self, variant: PromptVariant, max_concurrency: int = 2):
        self.variant = variant
        self.max_concurrency = max_concurrency

        # Create agent with the specified prompt variant
        retrieval_agent_def = RetrievalAgent(system_prompt=variant.prompt)
        self.agent = retrieval_agent_def.create(llm=default_llm)

    def load_queries(self, dataset_path: str) -> list[dict[str, Any]]:
        with open(dataset_path) as f:
            return [json.loads(line.strip()) for line in f]

    async def trace_query(self, query_item: dict[str, Any]) -> TraceResult:
        """Run agent on query and trace tool invocations."""

        query_id = query_item["query"]["query_id"]
        query_text = query_item["query"]["content"]
        query_type = query_item["query"]["query_type"]

        # Track tool invocations
        tool_calls: dict[str, ToolInvocation] = {}
        agent_output = ""
        error = False
        error_message = None

        try:
            # Run agent workflow
            handler = self.agent.run(user_msg=query_text)

            async for event in handler.stream_events():
                if isinstance(event, ToolCall):
                    tool_calls[event.tool_id] = ToolInvocation(
                        tool_name=event.tool_name,
                        tool_id=event.tool_id,
                        tool_kwargs=event.tool_kwargs,
                    )

                elif isinstance(event, ToolCallResult):
                    invocation = tool_calls.get(event.tool_id)
                    if invocation:
                        tool_output = event.tool_output.raw_output
                        if isinstance(tool_output, BaseModel):
                            tool_output = tool_output.model_dump()
                        invocation.tool_output = tool_output

            # Get final output
            final_output = await handler
            agent_output = str(final_output)

        except Exception as e:
            logger.error(f"Error tracing query {query_id}: {e}")
            error = True
            error_message = str(e)

        return TraceResult(
            query_id=query_id,
            query_type=query_type,
            user_query=query_text,
            tool_calls=list(tool_calls.values()),
            agent_output=agent_output,
            error=error,
            error_message=error_message,
            ground_truth=query_item["ground_truth"],
        )

    async def trace_all_queries(
        self,
        dataset_path: str,
        output_path: str,
        start_index: int = 0,
        end_index: int | None = None,
    ) -> list[TraceResult]:
        """Trace queries and save results.

        Args:
            dataset_path: Path to JSONL dataset
            output_path: Path to save traced results
            start_index: Start index in dataset (for resuming)
            end_index: End index (exclusive), None for all remaining
        """
        all_queries = self.load_queries(dataset_path)
        queries = all_queries[start_index:end_index]

        logger.info(
            f"Tracing {len(queries)} queries (index {start_index} to {end_index or len(all_queries)})"
        )

        results: list[TraceResult] = []

        for i, query_item in enumerate(queries):
            global_idx = start_index + i
            logger.info(
                f"[{global_idx}/{len(all_queries)}] Processing query: {query_item['query']['query_id']}"
            )

            result = await self.trace_query(query_item)
            results.append(result)

            # Save incrementally (in case of crash)
            if (i + 1) % 10 == 0:
                await self.save_results(results, output_path)
                logger.info(f"Checkpoint saved at {i + 1} queries")

            await asyncio.sleep(2)  # Rate limiting

        # Final save
        await self.save_results(results, output_path)

        return results

    async def save_results(self, results: list[TraceResult], output_path: str) -> None:
        """Save traced results to JSONL file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(output_path, "w") as f:
            for r in results:
                await f.write(json.dumps(asdict(r)) + "\n")

    def generate_summary(self, results: list[TraceResult]) -> dict[str, Any]:
        """Generate summary statistics from traced executions."""

        tool_usage = defaultdict(int)
        by_query_type: dict[str, list[TraceResult]] = defaultdict(list)

        # Aggregate by query type
        for r in results:
            by_query_type[r.query_type].append(r)
            for tc in r.tool_calls:
                tool_usage[tc.tool_name] += 1

        # Compute statistics
        summary = {
            "total_queries": len(results),
            "total_tool_calls": sum(len(r.tool_calls) for r in results),
            "avg_tool_calls_per_query": sum(len(r.tool_calls) for r in results)
            / max(1, len(results)),
            "errors": sum(1 for r in results if r.error),
            "tool_usage": dict(tool_usage),
            "by_query_type": {},
        }

        # Stats by query type
        for query_type, items in by_query_type.items():
            summary["by_query_type"][query_type] = {
                "count": len(items),
                "avg_tool_calls": sum(len(r.tool_calls) for r in items) / len(items),
                "errors": sum(1 for r in items if r.error),
            }

        return summary


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Trace retrieval agent tool invocations with different prompt variants."
    )
    parser.add_argument(
        "--variant",
        type=str,
        choices=[v.value for v in PromptVariant],
        required=True,
        help="Prompt variant to use (baseline or pe)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="/home/jarvis/Workspaces/research-agent/backend/rageval/qar_generation/results/DRAGONBALL_query.jsonl",
        help="Path to the query dataset (JSONL)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/traced_queries",
        help="Output directory for traced results",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start index in dataset (for resuming)",
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=None,
        help="End index in dataset (exclusive, None for all)",
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Parse variant
    variant = PromptVariant(args.variant)

    # Build output paths with variant name
    path = "/home/jarvis/Workspaces/research-agent/backend/rageval/retrieval_eval/agent/openai_final/traced_queries"
    output_dir = Path(path)
    output_path = output_dir / f"traced_{variant.value}.jsonl"
    summary_path = output_dir / f"summary_{variant.value}.json"

    logger.info(f"Running with variant: {variant.value}")
    logger.info(f"Output: {output_path}")

    # Run tracing
    tracer = AgentTracer(variant=variant)
    traced_results = await tracer.trace_all_queries(
        dataset_path=args.dataset,
        output_path=str(output_path),
        start_index=args.start_index,
        end_index=args.end_index,
    )

    # Generate summary
    summary = tracer.generate_summary(traced_results)
    summary["variant"] = variant.value

    # Save summary
    output_dir.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(summary_path, "w") as f:
        await f.write(json.dumps(summary, indent=2))

    logger.info(f"Tracing complete. Results saved to {output_path}")
    logger.info(f"Summary: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
