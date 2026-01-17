"""Check if generated articles contain the expected references.

This script validates that reference texts in QA data can be found
within the generated articles using various match strategies.
"""

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from rageval.retrieval_eval.match_strategies import (
    FuzzyMatch,
    MatchStrategy,
    NormalizedMatch,
    NormalizedTokenOverlapMatch,
    RegexAnchorMatch,
    SubstringMatch,
    TokenOverlapMatch,
)


@dataclass
class RefCheckResult:
    """Result of checking a single reference."""

    question_type: str
    question: str
    answer: str
    ref_text: str
    paper_title: str | None
    config_path: Path | None
    found: bool
    match_strategy: str


@dataclass
class ArticleRefReport:
    """Report for reference checking on a single article."""

    paper_title: str
    total_refs: int
    found_refs: int
    missing_refs: list[RefCheckResult]

    @property
    def match_rate(self) -> float:
        """Calculate the match rate."""
        return self.found_refs / self.total_refs if self.total_refs > 0 else 1.0


def load_article_content(config_path: Path) -> tuple[str, str]:
    """Load article content and title from config file.

    Args:
        config_path: Path to the config JSON file

    Returns:
        Tuple of (paper_title, article_content)
    """
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    paper_title = data.get("metadata", {}).get("title", "Unknown")
    article_content = data.get("document", "")

    return paper_title, article_content


def extract_qa_refs(data: dict) -> list[tuple[str, str, str, str, str | None]]:
    """Extract all references from QA data.

    Args:
        data: QA data dictionary

    Returns:
        List of (question_type, question, answer, ref_text, paper_title) tuples
    """
    refs = []

    # QA types with simple string refs
    simple_qa_types = ["qa_fact_based", "qa_multi_hop", "qa_summary"]

    for qa_type in simple_qa_types:
        qa_list = data.get(qa_type, [])
        for qa in qa_list:
            question_type = qa.get("question type", qa_type)
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            ref_list = qa.get("ref", [])

            for ref in ref_list:
                if isinstance(ref, str):
                    refs.append((question_type, question, answer, ref, None))
                elif isinstance(ref, dict):
                    # Handle dict refs with paper_title and content
                    paper_title = ref.get("paper_title")
                    content = ref.get("content", "")
                    refs.append((question_type, question, answer, content, paper_title))

    # QA types with dict refs (multi-document)
    multi_doc_types = [
        "qa_multi_document_information_integration",
        "qa_multi_document_compare",
    ]

    for qa_type in multi_doc_types:
        qa_list = data.get(qa_type, [])
        for qa in qa_list:
            question_type = qa.get("question type", qa_type)
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            ref_list = qa.get("ref", [])

            for ref in ref_list:
                if isinstance(ref, dict):
                    paper_title = ref.get("paper_title")
                    content = ref.get("content", "")
                    refs.append((question_type, question, answer, content, paper_title))
                elif isinstance(ref, str):
                    refs.append((question_type, question, answer, ref, None))

    return refs


def check_ref_in_article(
    ref_text: str,
    article_content: str,
    strategy: MatchStrategy,
) -> bool:
    """Check if a reference exists in the article content.

    Args:
        ref_text: The reference text to find
        article_content: The full article content
        strategy: The match strategy to use

    Returns:
        True if reference is found, False otherwise
    """
    return strategy.is_relevant(article_content, ref_text)


def check_single_article(
    config_path: Path,
    strategy: MatchStrategy,
    strategy_name: str,
) -> ArticleRefReport:
    """Check all references in a single article's QA data.

    Args:
        config_path: Path to the config JSON file
        strategy: The match strategy to use
        strategy_name: Name of the strategy for reporting

    Returns:
        ArticleRefReport with results
    """
    paper_title, article_content = load_article_content(config_path)

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    refs = extract_qa_refs(data)

    found_count = 0
    missing_refs = []

    for question_type, question, answer, ref_text, _ in refs:
        # Skip empty refs
        if not ref_text.strip():
            continue

        found = check_ref_in_article(ref_text, article_content, strategy)

        if found:
            found_count += 1
        else:
            missing_refs.append(
                RefCheckResult(
                    question_type=question_type,
                    question=question,
                    answer=answer,
                    ref_text=ref_text,
                    paper_title=paper_title,
                    config_path=config_path,
                    found=False,
                    match_strategy=strategy_name,
                )
            )

    total_refs = len([r for r in refs if r[3].strip()])

    return ArticleRefReport(
        paper_title=paper_title,
        total_refs=total_refs,
        found_refs=found_count,
        missing_refs=missing_refs,
    )


def check_multidoc_file(
    multidoc_path: Path,
    articles: dict[str, str],
    strategy: MatchStrategy,
    strategy_name: str,
) -> list[RefCheckResult]:
    """Check references in a multi-document QA file.

    Args:
        multidoc_path: Path to the multidoc JSON file
        articles: Dict mapping paper titles to article content
        strategy: The match strategy to use
        strategy_name: Name of the strategy for reporting

    Returns:
        List of RefCheckResults for missing references
    """
    with open(multidoc_path, encoding="utf-8") as f:
        data = json.load(f)

    refs = extract_qa_refs(data)
    results = []

    for question_type, question, answer, ref_text, paper_title in refs:
        if not ref_text.strip():
            continue

        # Find the article content for this paper
        article_content = articles.get(paper_title, "")

        if not article_content:
            # Paper not found in our articles dict
            results.append(
                RefCheckResult(
                    question_type=question_type,
                    question=question,
                    answer=answer,
                    ref_text=ref_text,
                    paper_title=paper_title,
                    config_path=multidoc_path,
                    found=False,
                    match_strategy=f"{strategy_name} (paper not found)",
                )
            )
            continue

        found = check_ref_in_article(ref_text, article_content, strategy)

        if not found:
            results.append(
                RefCheckResult(
                    question_type=question_type,
                    question=question,
                    answer=answer,
                    ref_text=ref_text,
                    paper_title=paper_title,
                    config_path=multidoc_path,
                    found=False,
                    match_strategy=strategy_name,
                )
            )

    return results


def load_all_articles(config_dir: Path) -> dict[str, str]:
    """Load all articles from config directory.

    Args:
        config_dir: Path to the config directory

    Returns:
        Dict mapping paper titles to article content
    """
    articles = {}

    for config_file in config_dir.rglob("*.json"):
        try:
            title, content = load_article_content(config_file)
            articles[title] = content
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to load {config_file}: {e}")

    return articles


def get_strategy(strategy_name: str, threshold: float = 0.8) -> MatchStrategy:
    """Get a match strategy by name.

    Args:
        strategy_name: Name of the strategy
        threshold: Threshold for strategies that require one (overlap ratio or similarity)

    Returns:
        The match strategy instance
    """
    strategies: dict[str, MatchStrategy] = {
        "substring": SubstringMatch(),
        "normalized": NormalizedMatch(),
        "token_overlap": TokenOverlapMatch(min_overlap=threshold),
        "normalized_token_overlap": NormalizedTokenOverlapMatch(min_overlap=threshold),
        "fuzzy": FuzzyMatch(min_ratio=threshold),
        "anchor": RegexAnchorMatch(9, 9, 0.8, True),
    }

    if strategy_name not in strategies:
        valid = ", ".join(strategies.keys())
        raise ValueError(f"Unknown strategy: {strategy_name}. Valid: {valid}")

    return strategies[strategy_name]


def print_report(
    single_reports: list[ArticleRefReport],
    multidoc_missing: list[RefCheckResult],
    verbose: bool = False,
) -> None:
    """Print the reference check report.

    Args:
        single_reports: Reports for single-article checks
        multidoc_missing: Missing refs from multi-doc checks
        verbose: Whether to print detailed missing refs
    """
    print("=" * 80)
    print("REFERENCE VALIDATION REPORT")
    print("=" * 80)

    # Single article stats
    print("\n## Single-Document QA Reference Checks\n")

    total_refs = sum(r.total_refs for r in single_reports)
    total_found = sum(r.found_refs for r in single_reports)
    overall_rate = total_found / total_refs if total_refs > 0 else 1.0

    print(f"{'Paper Title':<60} {'Found':<10} {'Total':<10} {'Rate':<10}")
    print("-" * 90)

    for report in sorted(single_reports, key=lambda r: r.match_rate):
        title = (
            report.paper_title[:57] + "..."
            if len(report.paper_title) > 60
            else report.paper_title
        )
        print(
            f"{title:<60} {report.found_refs:<10} {report.total_refs:<10} {report.match_rate:.2%}"
        )

    print("-" * 90)
    print(f"{'TOTAL':<60} {total_found:<10} {total_refs:<10} {overall_rate:.2%}")

    # Multi-doc stats
    if multidoc_missing:
        print("\n## Multi-Document QA Reference Checks\n")
        print(f"Missing references: {len(multidoc_missing)}")

        if verbose:
            # Group by paper title
            by_paper: dict[str | None, list[RefCheckResult]] = defaultdict(list)
            for result in multidoc_missing:
                by_paper[result.paper_title].append(result)

            for paper_title, results in by_paper.items():
                print(f"\n### {paper_title or 'Unknown Paper'}")
                for r in results:
                    print(f"  - [{r.question_type}] {r.ref_text[:100]}...")

    # Overall summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_missing = []
    for report in single_reports:
        all_missing.extend(report.missing_refs)
    all_missing.extend(multidoc_missing)

    # Group by question type
    by_type: dict[str, int] = defaultdict(int)
    for result in all_missing:
        by_type[result.question_type] += 1

    if by_type:
        print("\nMissing references by question type:")
        for qtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"  {qtype}: {count}")

    print(f"\nTotal single-doc match rate: {overall_rate:.2%}")
    print(f"Total multi-doc missing refs: {len(multidoc_missing)}")

    if verbose and all_missing:
        print("\n" + "=" * 80)
        print("DETAILED MISSING REFERENCES (grouped by paper)")
        print("=" * 80)

        # Group by paper title
        by_paper: dict[str, list[RefCheckResult]] = defaultdict(list)
        for result in all_missing:
            by_paper[result.paper_title or "Unknown"].append(result)

        for paper_title in sorted(by_paper.keys()):
            results = by_paper[paper_title]
            # Get file path from first result
            file_path = results[0].config_path if results else None
            print(f"\n### {paper_title} ({len(results)} missing)")
            if file_path:
                print(f"    File: {file_path}")
            print("-" * 70)
            for i, result in enumerate(results, 1):
                print(f"\n  [{i}] {result.question_type}")
                print(f"      Q: {result.question}")
                print(f"      A: {result.answer[:120]}...")
                print(f"      REF (not found): {result.ref_text}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check if generated articles contain expected references"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "qar_generation" / "output" / "nlp_raw",
        help="Path to the output directory containing config and qra_multidoc",
    )
    parser.add_argument(
        "--strategy",
        choices=[
            "substring",
            "normalized",
            "token_overlap",
            "normalized_token_overlap",
            "fuzzy",
            "anchor",
        ],
        default="normalized",
        help="Match strategy to use (default: normalized)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Threshold for overlap/similarity strategies (default: 0.8)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed missing references",
    )
    parser.add_argument(
        "--check-multidoc",
        action="store_true",
        help="Also check multi-document QA files",
    )

    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    config_dir = output_dir / "config" / "0"
    multidoc_dir = output_dir / "qra_multidoc"

    if not config_dir.exists():
        print(f"Error: Config directory not found: {config_dir}")
        return

    strategy = get_strategy(args.strategy, args.threshold)
    strategy_name = args.strategy

    print(f"Using strategy: {strategy_name}")
    print(f"Output directory: {output_dir}")
    print()

    # Load all articles first
    print("Loading articles...")
    articles = load_all_articles(config_dir)
    print(f"Loaded {len(articles)} articles\n")

    # Check single-article refs
    single_reports = []

    for config_file in config_dir.rglob("*.json"):
        try:
            report = check_single_article(config_file, strategy, strategy_name)
            single_reports.append(report)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to check {config_file}: {e}")

    # Check multi-doc refs if requested
    multidoc_missing = []

    if args.check_multidoc and multidoc_dir.exists():
        print("Checking multi-document QA files...")

        for multidoc_file in sorted(multidoc_dir.glob("*.json")):
            try:
                missing = check_multidoc_file(
                    multidoc_file, articles, strategy, strategy_name
                )
                multidoc_missing.extend(missing)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to check {multidoc_file}: {e}")

    # Print report
    print_report(single_reports, multidoc_missing, args.verbose)


if __name__ == "__main__":
    main()
