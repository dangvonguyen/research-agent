"""Module for text processing, chunking, and paragraph splitting."""

import logging
import re

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

    def split_into_chunks(self, content: str) -> list[str]:
        """
        Split content into chunks by paragraph, preserving tables.

        Combines multiple paragraphs together until the character limit (500)
        is exceeded. Tables are never split across chunks.

        Args:
            content: Content to split into chunks

        Returns:
            List of chunk strings
        """
        if not content.strip():
            return []

        # Split into paragraphs (tables are preserved as single units)
        paragraphs = self.split_into_paragraphs(content)

        if not paragraphs:
            return []

        chunks = []
        current_chunk = []
        current_chunk_size = 0

        for paragraph in paragraphs:
            paragraph_size = self.count_tokens(paragraph)

            # If a single paragraph exceeds the limit, add it as its own chunk
            if paragraph_size > self.max_chunk_words:
                # Save current chunk if any
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_chunk_size = 0

                # Add the large paragraph as its own chunk
                chunks.append(paragraph)
            else:
                # Check if adding this paragraph would exceed the limit
                # Account for the "\n\n" separator between paragraphs
                separator_size = 2 if current_chunk else 0
                new_size = current_chunk_size + separator_size + paragraph_size

                if new_size > self.max_chunk_words and current_chunk:
                    # Current chunk is full, start a new one
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [paragraph]
                    current_chunk_size = paragraph_size
                else:
                    # Add to current chunk
                    current_chunk.append(paragraph)
                    current_chunk_size = new_size

        # Add any remaining chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        logger.debug(
            "Split content into %d chunks (max %d characters, paragraph-based)",
            len(chunks),
            self.max_chunk_words,
        )

        return chunks
