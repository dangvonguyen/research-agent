"""Module for text processing, chunking, and paragraph splitting."""

import logging
import re
from collections import deque
from typing import Literal

import tiktoken

logger = logging.getLogger(__name__)


class TextProcessor:
    """Handles text splitting, chunking, and token counting."""

    def __init__(self, max_chunk_words: int):
        """
        Initialize text processor.

        Args:
            max_chunk_words: Maximum tokens per chunk
        """
        self.max_chunk_words = max_chunk_words
        if not hasattr(self, "_tokenizer"):
            self._tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        """
        return len(self._tokenizer.encode(text))

    @staticmethod
    def is_table_line(line: str) -> bool:
        """
        Check if a line is part of a markdown table.

        Args:
            line: Line to check

        Returns:
            True if line is a table line (starts with | and contains multiple |)
        """
        stripped = line.strip()
        # A table line should start with | and contain at least one more |
        # This handles both data rows and separator rows
        return stripped.startswith("|") and stripped.count("|") >= 2

    @staticmethod
    def is_image_line(line: str) -> bool:
        """
        Check if a line is just an image reference.

        Args:
            line: Line to check

        Returns:
            True if line is just an image reference (e.g., ![](image.jpg))
        """
        stripped = line.strip()
        pattern = r"^!\[([^\]]*)\]\(([^\)]+)\)\s*$"
        return bool(re.match(pattern, stripped))

    def split_into_paragraphs(self, content: str) -> list[str]:
        """
        Split content into paragraphs, preserving tables as single units.
        Image-only paragraphs are attached to the previous paragraph to ensure
        they're included in chunks.

        Args:
            content: Content to split

        Returns:
            List of paragraphs (tables are kept as single units, images attached to previous paragraph)
        """
        if not content.strip():
            return []

        lines = content.split("\n")
        paragraphs = []
        current_paragraph = []
        in_table = False

        for line in lines:
            line_stripped = line.strip()
            is_table_line = self.is_table_line(line)
            is_image_line = self.is_image_line(line)

            if is_table_line:
                # We're in a table
                if not in_table:
                    # Start of a new table - save previous paragraph if any
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                    in_table = True
                current_paragraph.append(line)
            else:
                # Not a table line
                if in_table:
                    # End of table - save it as a single paragraph
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                    in_table = False

                if line_stripped:
                    if is_image_line:
                        # Image line - attach to current paragraph if it exists,
                        # otherwise save it to attach to next paragraph
                        if current_paragraph:
                            # Attach image to current paragraph
                            current_paragraph.append(line)
                        else:
                            # No current paragraph - save to attach to next paragraph
                            # Use a temporary marker to track this
                            if not hasattr(self, "_pending_image"):
                                self._pending_image = []
                            self._pending_image.append(line)
                    else:
                        # Non-empty, non-image line
                        if hasattr(self, "_pending_image") and self._pending_image:
                            # Attach pending images to start of this paragraph
                            current_paragraph.extend(self._pending_image)
                            self._pending_image = []
                        current_paragraph.append(line)
                else:
                    # Empty line - end of paragraph
                    if current_paragraph:
                        # If we have pending images, attach them before ending
                        if hasattr(self, "_pending_image") and self._pending_image:
                            current_paragraph.extend(self._pending_image)
                            self._pending_image = []
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []

        # Add any remaining paragraph
        if current_paragraph:
            # Attach any pending images
            if hasattr(self, "_pending_image") and self._pending_image:
                current_paragraph.extend(self._pending_image)
                self._pending_image = []
            paragraphs.append("\n".join(current_paragraph))
        elif hasattr(self, "_pending_image") and self._pending_image:
            # Image at the very end with no following paragraph - include it
            paragraphs.append("\n".join(self._pending_image))
            self._pending_image = []

        # Clean up
        if hasattr(self, "_pending_image"):
            delattr(self, "_pending_image")

        return paragraphs

    def split_into_chunks(
        self, content: str, max_chunk_words: int | None = None, overlap_words: int = 0
    ) -> list[str]:
        """
        Split content into chunks by paragraph, preserving tables.

        Combines multiple paragraphs together until the token limit is exceeded.
        Tables are never split across chunks. Implements overlap by preserving
        last N tokens from previous chunk and prepending to next chunk.

        Args:
            content: Content to split into chunks
            max_chunk_words: Maximum tokens per chunk
            overlap_words: Number of overlap tokens between chunks

        Returns:
            List of chunk strings
        """
        if not content.strip():
            return []

        max_chunk_words = max_chunk_words or self.max_chunk_words

        # Split into paragraphs (tables are preserved as single units)
        paragraphs = self.split_into_paragraphs(content)

        if not paragraphs:
            return []

        # Precompute token counts
        para_tokens = [self.count_tokens(p) for p in paragraphs]

        chunks = []
        current_chunk = []
        current_chunk_size = 0

        for paragraph, para_size in zip(paragraphs, para_tokens, strict=False):
            # Paragraph too large → standalone chunk
            if para_size > max_chunk_words:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_chunk_size = 0

                chunks.append(paragraph)

                # IMPORTANT:
                # Do NOT seed overlap from this paragraph
                continue

            # Check if adding this paragraph would exceed the limit
            # Account for the "\n\n" separator between paragraphs
            separator_size = 2 if current_chunk else 0
            new_size = current_chunk_size + separator_size + para_size

            if new_size > max_chunk_words and current_chunk:
                # Finalize current chunk
                chunks.append("\n\n".join(current_chunk))

                # Extract overlap
                overlap = self._extract_overlap(current_chunk, overlap_words)

                current_chunk = [*overlap, paragraph]
                current_chunk_size = sum(self.count_tokens(p) for p in current_chunk)
            else:
                # Add to current chunk
                current_chunk.append(paragraph)
                current_chunk_size = new_size

        # Add any remaining chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        logger.debug(
            "Split content into %d chunks (max %d tokens, overlap %d tokens, paragraph-based)",
            len(chunks),
            max_chunk_words,
            overlap_words,
        )

        return chunks

    def _extract_overlap(
        self,
        paragraphs: list[str],
        overlap_words: int,
        level: Literal["word", "sentence", "paragraph"] = "sentence",
    ) -> list[str]:
        """
        Extract last N tokens worth of content for overlap.

        Walks backwards through content, collecting units until the overlap token
        limit is reached.

        Args:
            paragraphs: List of paragraphs to extract overlap from
            overlap_words: Target number of tokens for overlap
            level: Granularity level

        Returns:
            List of paragraphs reconstructed from extracted overlap content
        """
        if overlap_words == 0 or not paragraphs:
            return []

        overlap = deque()
        remaining = overlap_words

        if level == "paragraph":
            for para in reversed(paragraphs):
                size = self.count_tokens(para)
                if size <= remaining:
                    break
                overlap.appendleft(para)
                remaining -= size
            return list(overlap)

        if level == "sentence":
            # Walk paragraphs backwards, split lazily
            for para in reversed(paragraphs):
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in reversed(sentences):
                    size = self.count_tokens(sent)
                    if size > remaining:
                        return [" ".join(overlap)] if overlap else []
                    overlap.appendleft(sent)
                    remaining -= size

            # Reconstruct as single paragraph
            return [" ".join(overlap)] if overlap else []

        if level == "word":
            for para in reversed(paragraphs):
                words = para.split()
                for word in reversed(words):
                    size = self.count_tokens(word)
                    if size > remaining:
                        return [" ".join(overlap)] if overlap else []
                    overlap.appendleft(word)
                    remaining -= size

            # Reconstruct as single paragraph
            return [" ".join(overlap)] if overlap else []

        logger.warning("Unknown overlap level '%s', defaulting to sentence", level)
        return self._extract_overlap(paragraphs, overlap_words, "sentence")
