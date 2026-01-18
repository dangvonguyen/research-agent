"""Match strategies for determining retrieval relevance.

This module provides different strategies for determining if a retrieved
chunk is relevant to a ground truth reference.
"""

import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher

from app.tools.parsers.markdown_parser import MarkdownParser


class MatchStrategy(ABC):
    """Base class for match strategies."""

    @abstractmethod
    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Determine if retrieved chunk is relevant to ground truth.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if relevant, False otherwise
        """
        pass


class SubstringMatch(MatchStrategy):
    """Baseline substring matching strategy.

    Considers a chunk relevant if the ground truth appears as a substring
    in the retrieved chunk.
    """

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Check if ground truth is substring of retrieved.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if ground truth is substring of retrieved
        """
        return ground_truth.strip() in retrieved.strip()


class TokenOverlapMatch(MatchStrategy):
    """Token overlap matching strategy.

    Better for lexical retrieval. Considers a chunk relevant if there's
    sufficient token overlap between retrieved and ground truth.
    """

    def __init__(self, min_overlap: float = 0.2):
        """Initialize token overlap matcher.

        Args:
            min_overlap: Minimum overlap ratio (0.0 to 1.0)
        """
        self.min_overlap = min_overlap

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Check if token overlap exceeds threshold.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if overlap ratio >= min_overlap
        """
        r = set(retrieved.lower().split())
        g = set(ground_truth.lower().split())
        if not g:
            return False
        overlap = len(r & g) / len(g)
        return overlap >= self.min_overlap


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Applies the following normalizations:
    - Convert to lowercase
    - Normalize unicode characters (NFKC)
    - Remove punctuation
    - Collapse multiple whitespace to single space
    - Strip leading/trailing whitespace

    Args:
        text: The text to normalize

    Returns:
        Normalized text string
    """
    # Normalize unicode (e.g., convert fancy quotes to regular quotes)
    # text = unicodedata.normalize("NFKC", text)

    # Convert to lowercase
    text = text.lower()

    # Remove punctuation (keep alphanumeric and whitespace)
    text = re.sub(r"[^\w\s]", " ", text)

    # Collapse multiple whitespace to single space
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    return text.strip()


class NormalizedMatch(MatchStrategy):
    """Normalized substring matching strategy.

    Normalizes both texts before comparison:
    - Removes punctuation
    - Normalizes whitespace
    - Converts to lowercase
    - Handles unicode normalization

    This is more lenient than exact substring but more precise than token overlap.
    """

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Check if normalized ground truth is substring of normalized retrieved.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if normalized ground truth is substring of normalized retrieved
        """
        normalized_retrieved = normalize_text(retrieved)
        normalized_ground_truth = normalize_text(ground_truth)

        if not normalized_ground_truth:
            return False

        return normalized_ground_truth in normalized_retrieved


class FuzzyMatch(MatchStrategy):
    """Fuzzy matching strategy using sequence similarity.

    Uses difflib's SequenceMatcher to find the best matching subsequence.
    Good for detecting paraphrased or slightly modified text.
    """

    def __init__(self, min_ratio: float = 0.8):
        """Initialize fuzzy matcher.

        Args:
            min_ratio: Minimum similarity ratio (0.0 to 1.0)
        """
        self.min_ratio = min_ratio

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Check if fuzzy similarity exceeds threshold.

        Uses a sliding window approach to find best match within retrieved text.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if best match ratio >= min_ratio
        """
        normalized_retrieved = normalize_text(retrieved)
        normalized_ground_truth = normalize_text(ground_truth)

        if not normalized_ground_truth:
            return False

        # For short ground truths, use direct comparison
        if len(normalized_ground_truth) <= 50:
            matcher = SequenceMatcher(
                None, normalized_retrieved, normalized_ground_truth
            )
            # Find best matching block
            match = matcher.find_longest_match(
                0, len(normalized_retrieved), 0, len(normalized_ground_truth)
            )
            if match.size == 0:
                return False
            ratio = match.size / len(normalized_ground_truth)
            return ratio >= self.min_ratio

        # For longer texts, use sliding window
        window_size = len(normalized_ground_truth)
        best_ratio = 0.0

        # Slide through retrieved text
        for i in range(
            0, max(1, len(normalized_retrieved) - window_size + 1), window_size // 4
        ):
            window = normalized_retrieved[i : i + window_size + window_size // 2]
            matcher = SequenceMatcher(None, window, normalized_ground_truth)
            ratio = matcher.ratio()
            best_ratio = max(best_ratio, ratio)

            # Early exit if we find a great match
            if best_ratio >= 0.95:
                return True

        return best_ratio >= self.min_ratio


class NormalizedTokenOverlapMatch(MatchStrategy):
    """Normalized token overlap matching strategy.

    Combines normalization with token overlap for robust matching.
    Normalizes text before tokenizing and computing overlap.
    """

    def __init__(self, min_overlap: float = 0.8):
        """Initialize normalized token overlap matcher.

        Args:
            min_overlap: Minimum overlap ratio (0.0 to 1.0)
        """
        self.min_overlap = min_overlap

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Check if normalized token overlap exceeds threshold.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if overlap ratio >= min_overlap
        """
        normalized_retrieved = normalize_text(retrieved)
        normalized_ground_truth = normalize_text(ground_truth)

        r_tokens = set(normalized_retrieved.split())
        g_tokens = set(normalized_ground_truth.split())

        if not g_tokens:
            return False

        overlap = len(r_tokens & g_tokens) / len(g_tokens)
        return overlap >= self.min_overlap


class RegexAnchorMatch(MatchStrategy):
    """Regex-based anchor matching strategy.

    Uses the first N words and last N words from the ground truth as anchors
    to locate the relevant portion in the retrieved document. Then computes
    similarity between the extracted portion and the ground truth.

    This is useful when:
    - The retrieved chunk may contain the reference with slight modifications
    - Exact substring matching fails due to formatting differences
    - You need to locate content boundaries using known start/end patterns
    """

    def __init__(
        self,
        n_first_words: int = 5,
        n_last_words: int = 5,
        min_similarity: float = 0.8,
        normalize: bool = True,
    ):
        """Initialize regex anchor matcher.

        Args:
            n_first_words: Number of words from the start of ground truth to use as anchor
            n_last_words: Number of words from the end of ground truth to use as anchor
            min_similarity: Minimum similarity ratio for the extracted content (0.0 to 1.0)
            normalize: Whether to normalize text before comparison
        """
        self.n_first_words = n_first_words
        self.n_last_words = n_last_words
        self.min_similarity = min_similarity
        self.normalize = normalize

    def _get_words(self, text: str) -> list[str]:
        """Extract words from text.

        Args:
            text: Input text

        Returns:
            List of words
        """
        # Split on whitespace and filter empty strings
        return [w for w in text.split() if w]

    def _build_anchor_pattern(self, words: list[str]) -> str:
        """Build a flexible regex pattern from words.

        Creates a pattern that matches the words with flexible whitespace
        and optional punctuation between them.

        Args:
            words: List of words to build pattern from

        Returns:
            Regex pattern string
        """
        if not words:
            return ""

        # Escape special regex characters in each word
        escaped_words = [re.escape(w) for w in words]

        # Join with flexible whitespace pattern (allows any whitespace/punctuation between words)
        # \s* matches any whitespace, [^\w]* matches non-word characters (punctuation)
        pattern = r"[\s\W]*".join(escaped_words)

        return pattern

    def _extract_anchored_content(
        self, text: str, first_anchor: str, last_anchor: str
    ) -> str | None:
        """Extract content between first and last anchors.

        Args:
            text: Text to search in
            first_anchor: Regex pattern for start anchor
            last_anchor: Regex pattern for end anchor

        Returns:
            Extracted content or None if not found
        """
        # Build full pattern: first_anchor ... last_anchor
        # Use non-greedy matching (.*?) to get smallest match
        full_pattern = f"({first_anchor})(.*)({last_anchor})"

        match = re.search(full_pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Return the full match including anchors
            return match.group(0)

        return None

    def _compute_similarity_v0(self, text1: str, text2: str) -> float:
        """Compute similarity ratio between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        if self.normalize:
            text1 = normalize_text(text1)
            text2 = normalize_text(text2)

        if not text1 or not text2:
            return 0.0

        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _compute_similarity(self, retrieved: str, ground_truth: str) -> bool:
        """Check if fuzzy similarity exceeds threshold.

        Uses a sliding window approach to find best match within retrieved text.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if best match ratio >= min_ratio
        """
        self.min_ratio = 0.9
        normalized_retrieved = normalize_text(retrieved)
        normalized_ground_truth = normalize_text(ground_truth)

        if not normalized_ground_truth:
            return False

        # For short ground truths, use direct comparison
        if len(normalized_ground_truth) <= 50:
            matcher = SequenceMatcher(
                None, normalized_retrieved, normalized_ground_truth
            )
            # Find best matching block
            match = matcher.find_longest_match(
                0, len(normalized_retrieved), 0, len(normalized_ground_truth)
            )
            if match.size == 0:
                return False
            ratio = match.size / len(normalized_ground_truth)
            return ratio >= self.min_ratio

        # For longer texts, use sliding window
        window_size = len(normalized_ground_truth)
        best_ratio = 0.0

        # Slide through retrieved text
        for i in range(
            0, max(1, len(normalized_retrieved) - window_size + 1), window_size // 4
        ):
            window = normalized_retrieved[i : i + window_size + window_size // 2]
            matcher = SequenceMatcher(None, window, normalized_ground_truth)
            ratio = matcher.ratio()
            best_ratio = max(best_ratio, ratio)

            # Early exit if we find a great match
            if best_ratio >= 0.95:
                return True

        return best_ratio >= self.min_ratio

    def _compute_similarity_v2(self, retrieved: str, ground_truth: str) -> bool:
        """Check if token overlap exceeds threshold.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if overlap ratio >= min_overlap
        """
        r = set(retrieved.lower().split())
        g = set(ground_truth.lower().split())
        if not g:
            return False
        overlap = len(r & g) / len(r)
        return overlap >= self.min_similarity

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Determine if retrieved chunk is relevant using anchor-based matching.

        Strategy:
        1. Extract first N words and last N words from ground truth as anchors
        2. Use regex to find content in retrieved text bounded by these anchors
        3. Compute similarity between extracted content and ground truth
        4. Return True if similarity exceeds threshold

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if relevant, False otherwise
        """
        if not retrieved or not ground_truth:
            return False

        # Prepare text for processing
        proc_retrieved = normalize_text(retrieved)
        proc_ground_truth = normalize_text(ground_truth)

        # Extract words from ground truth
        gt_words = self._get_words(proc_ground_truth)

        if len(gt_words) < self.n_first_words + self.n_last_words:
            # Ground truth too short for anchor strategy, fall back to direct similarity
            similarity = self._compute_similarity(retrieved, ground_truth)
            return similarity >= self.min_similarity

        # Build anchor patterns
        first_words = gt_words[: self.n_first_words]
        last_words = gt_words[-self.n_last_words :]

        first_anchor = self._build_anchor_pattern(first_words)
        last_anchor = self._build_anchor_pattern(last_words)

        # Try to extract content using anchors
        extracted = self._extract_anchored_content(
            proc_retrieved, first_anchor, last_anchor
        )

        if extracted:
            # Compute similarity between extracted content and ground truth
            similarity = self._compute_similarity(extracted, ground_truth)
            print(len(extracted) if extracted else 0)
            return similarity >= self.min_similarity

        # Fallback: try matching with just first anchor or last anchor
        # This handles cases where only part of the reference is in the chunk

        # Try first anchor only
        first_match = re.search(first_anchor, proc_retrieved, re.IGNORECASE)
        if first_match:
            # Extract from first anchor to end of reasonable window
            start_pos = first_match.start()
            window_size = len(proc_ground_truth) + len(proc_ground_truth) // 2
            extracted = proc_retrieved[start_pos : start_pos + window_size]
            similarity = self._compute_similarity(extracted, ground_truth)
            if similarity >= self.min_similarity:
                print(len(extracted) if extracted else 0)
                return True

        # Try last anchor only
        last_match = re.search(last_anchor, proc_retrieved, re.IGNORECASE)
        if last_match:
            # Extract window ending at last anchor
            end_pos = last_match.end()
            window_size = len(proc_ground_truth) + len(proc_ground_truth) // 2
            start_pos = max(0, end_pos - window_size)
            extracted = proc_retrieved[start_pos:end_pos]
            similarity = self._compute_similarity(extracted, ground_truth)
            if similarity >= self.min_similarity:
                print(len(extracted) if extracted else 0)
                return True

        print(0)

        return False


class SectionSimilarityMatch(MatchStrategy):
    """Section-based similarity matching strategy using MarkdownParser.

    Splits the retrieved document into markdown sections and computes similarity
    between the ground truth reference and each section. Returns True if
    any section has sufficient similarity.

    This is useful when:
    - The document contains multiple distinct sections
    - The reference corresponds to a specific section
    - You want to avoid noise from unrelated sections affecting similarity
    """

    def __init__(
        self,
        min_similarity: float = 0.8,
        min_section_length: int = 50,
    ):
        """Initialize section similarity matcher.

        Args:
            min_similarity: Minimum similarity ratio (0.0 to 1.0)
            min_section_length: Minimum character length for a section to be considered
        """
        self.min_similarity = min_similarity
        self.min_section_length = min_section_length
        self.parser = MarkdownParser(min_content_length=min_section_length)

    def _get_sections(self, text: str) -> list[str]:
        """Split text into sections using MarkdownParser.

        Args:
            text: Text to split

        Returns:
            List of section content strings
        """
        sections_dict = self.parser.parse_markdown_sections(text)

        sections = []
        for title, content in sections_dict.items():
            # Combine title and content
            if title:
                section_text = f"{title}\n{content}"
            else:
                section_text = content

            sections.append(section_text.strip())

        return sections if sections else [text]

    def _compute_similarity_v0(self, section: str, ground_truth: str) -> float:
        """Compute similarity between a section and ground truth using sliding window.

        Args:
            section: Section text
            ground_truth: Ground truth reference text

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        normalized_section = normalize_text(section)
        normalized_gt = normalize_text(ground_truth)

        if not normalized_section or not normalized_gt:
            return 0.0

        # For short texts, use direct comparison
        if len(normalized_gt) <= 100:
            matcher = SequenceMatcher(None, normalized_section, normalized_gt)
            return matcher.ratio()

        # For longer texts, use sliding window to find best match
        window_size = len(normalized_gt)
        best_ratio = 0.0

        step = max(1, window_size // 4)
        for i in range(0, max(1, len(normalized_section) - window_size + 1), step):
            window = normalized_section[i : i + window_size + window_size // 2]
            matcher = SequenceMatcher(None, window, normalized_gt)
            ratio = matcher.ratio()
            best_ratio = max(best_ratio, ratio)

            if best_ratio >= 0.95:
                return best_ratio

        # Also check overall similarity
        overall_matcher = SequenceMatcher(None, normalized_section, normalized_gt)
        best_ratio = max(best_ratio, overall_matcher.ratio())

        return best_ratio

    def _compute_similarity(self, retrieved: str, ground_truth: str) -> bool:
        """Check if normalized token overlap exceeds threshold.

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if overlap ratio >= min_overlap
        """
        normalized_retrieved = normalize_text(retrieved)
        normalized_ground_truth = normalize_text(ground_truth)

        r_tokens = set(normalized_retrieved.split())
        g_tokens = set(normalized_ground_truth.split())

        if not g_tokens:
            return False

        overlap = len(r_tokens & g_tokens) / len(g_tokens)
        return overlap >= self.min_similarity

    def is_relevant(self, retrieved: str, ground_truth: str) -> bool:
        """Determine if retrieved chunk is relevant by checking each section.

        Strategy:
        1. Split retrieved text into markdown sections using MarkdownParser
        2. Compute similarity between each section and ground truth
        3. Return True if any section has similarity >= threshold

        Args:
            retrieved: Retrieved chunk text
            ground_truth: Ground truth reference text

        Returns:
            True if any section is relevant, False otherwise
        """
        if not retrieved or not ground_truth:
            return False

        # Get sections from retrieved text
        sections = self._get_sections(retrieved)

        count = 0

        # Check each section
        for section in sections:
            similarity = self._compute_similarity(section, ground_truth)
            if similarity >= self.min_similarity:
                # return True
                count += 1

        if count > 1:
            print(count)
        return bool(count)
