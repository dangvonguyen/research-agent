"""Retrieval evaluation metrics.

This module provides standard information retrieval metrics for evaluating
retrieval quality against ground truth references.
"""

from rageval.retrieval_eval.match_strategies import MatchStrategy


class RetrievalMetrics:
    """Computes standard IR metrics using a match strategy."""

    def __init__(self, matcher: MatchStrategy):
        """Initialize metrics computer.

        Args:
            matcher: Strategy for determining relevance
        """
        self.matcher = matcher

    def has_match(self, retrieved: list[str], ground_truth: list[str]) -> bool:
        """Check if any ground truth appears in retrieved chunks.

        Args:
            retrieved: List of retrieved chunk texts
            ground_truth: List of ground truth reference texts

        Returns:
            True if at least one match found
        """
        return any(
            self.matcher.is_relevant(rt, gt)
            for gt in ground_truth
            for rt in retrieved
        )

    def compute_recall(self, retrieved: list[str], ground_truth: list[str]) -> float:
        """Compute recall: % of ground truth chunks found in retrieved.

        Args:
            retrieved: List of retrieved chunk texts
            ground_truth: List of ground truth reference texts

        Returns:
            Recall score (0.0 to 1.0)
        """
        if not ground_truth:
            return 0.0

        matched = sum(
            any(self.matcher.is_relevant(rt, gt) for rt in retrieved)
            for gt in ground_truth
        )
        return matched / len(ground_truth)

    def compute_precision(self, retrieved: list[str], ground_truth: list[str]) -> float:
        """Compute precision@K: % of retrieved chunks that match ground truth.

        Args:
            retrieved: List of retrieved chunk texts
            ground_truth: List of ground truth reference texts

        Returns:
            Precision score (0.0 to 1.0)
        """
        if not retrieved:
            return 0.0

        matched = sum(
            any(self.matcher.is_relevant(rt, gt) for gt in ground_truth)
            for rt in retrieved
        )
        return matched / len(retrieved)

    def compute_mrr(self, retrieved: list[str], ground_truth: list[str]) -> float:
        """Compute Mean Reciprocal Rank: 1/rank of first relevant chunk.

        Args:
            retrieved: List of retrieved chunk texts (order matters)
            ground_truth: List of ground truth reference texts

        Returns:
            MRR score (0.0 to 1.0)
        """
        for rank, rt in enumerate(retrieved, 1):
            if any(self.matcher.is_relevant(rt, gt) for gt in ground_truth):
                return 1.0 / rank
        return 0.0

    def compute_all(self, retrieved: list[str], ground_truth: list[str]) -> dict[str, float]:
        """Compute all metrics at once.

        Args:
            retrieved: List of retrieved chunk texts
            ground_truth: List of ground truth reference texts

        Returns:
            Dictionary with recall, precision, hit_rate, and mrr
        """
        return {
            "recall": self.compute_recall(retrieved, ground_truth),
            "precision": self.compute_precision(retrieved, ground_truth),
            "hit_rate": 1.0 if self.has_match(retrieved, ground_truth) else 0.0,
            "mrr": self.compute_mrr(retrieved, ground_truth),
        }
