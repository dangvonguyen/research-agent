"""Module for different chunking strategies for paper content."""

import logging
import re
from typing import Optional

import tiktoken

from .markdown_parser import MarkdownParser
from .text_processor import TextProcessor

logger = logging.getLogger(__name__)


class ChunkingStrategies:
    """Different chunking strategies for splitting paper content into chunks."""

    # Hard limit for all chunks across all strategies
    MAX_CHUNK_TOKENS_HARD_LIMIT = 8000

    def __init__(
        self,
        max_chunk_tokens: int = 500,
        max_section_tokens: int = 8000,
        model_name: str = "gpt-4o-mini",
    ):
        """
        Initialize chunking strategies.

        Args:
            max_chunk_tokens: Maximum tokens per chunk (for sentence and recursive strategies)
            max_section_tokens: Maximum tokens per section (for rule-based strategy)
            model_name: Model name for tiktoken tokenizer
        """
        self.max_chunk_tokens = max_chunk_tokens
        self.max_section_tokens = max_section_tokens
        self._tokenizer = tiktoken.encoding_for_model(model_name)
        self.text_processor = TextProcessor(max_chunk_tokens)
        self.markdown_parser = MarkdownParser(min_content_length=0)

    def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    @staticmethod
    def split_into_sentences(text: str) -> list[str]:
        if not text.strip():
            return []
        sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])(?=\n|$)"
        sentences = re.split(sentence_pattern, text)

        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def chunk_by_sentence(
        self, content: str, chunk_separator: str = "\n\n"
    ) -> list[str]:
        """
        Chunk content by sentences. Combines sentences until token limit is reached.

        Args:
            content: Content to chunk
            chunk_separator: Separator between sentences in a chunk

        Returns:
            List of chunk strings
        """
        if not content.strip():
            return []

        sentences = self.split_into_sentences(content)
        if not sentences:
            return [content] if content.strip() else []

        chunks = []
        current_chunk = []
        current_chunk_size = 0

        for sentence in sentences:
            sentence_size = self.count_tokens(sentence)
            separator_size = self.count_tokens(chunk_separator) if current_chunk else 0
            new_size = current_chunk_size + separator_size + sentence_size

            # If a single sentence exceeds the limit, add it as its own chunk
            if sentence_size > self.max_chunk_tokens:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(chunk_separator.join(current_chunk))
                    current_chunk = []
                    current_chunk_size = 0

                # Add the large sentence as its own chunk
                chunks.append(sentence)
            elif new_size > self.max_chunk_tokens and current_chunk:
                # Current chunk is full, start a new one
                chunks.append(chunk_separator.join(current_chunk))
                current_chunk = [sentence]
                current_chunk_size = sentence_size
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_chunk_size = new_size

        # Add any remaining chunk
        if current_chunk:
            chunks.append(chunk_separator.join(current_chunk))

        # Enforce hard limit of 8000 tokens on all chunks
        chunks = self._enforce_hard_limit(chunks)

        logger.debug(
            "Split content into %d chunks using sentence-based strategy (max %d tokens, hard limit %d)",
            len(chunks),
            self.max_chunk_tokens,
            self.MAX_CHUNK_TOKENS_HARD_LIMIT,
        )

        return chunks

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to a maximum number of tokens.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens

        Returns:
            Truncated text
        """
        tokens = self._tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        # Truncate to max_tokens and decode back
        truncated_tokens = tokens[:max_tokens]
        return self._tokenizer.decode(truncated_tokens)

    def _enforce_hard_limit(self, chunks: list[str]) -> list[str]:
        """
        Enforce hard limit of 8000 tokens on all chunks.

        Args:
            chunks: List of chunk strings

        Returns:
            List of chunks, all truncated to MAX_CHUNK_TOKENS_HARD_LIMIT if needed
        """
        truncated_chunks = []
        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk)
            if chunk_tokens > self.MAX_CHUNK_TOKENS_HARD_LIMIT:
                logger.debug(
                    "Chunk exceeds hard limit (%d tokens), truncating to %d tokens",
                    chunk_tokens,
                    self.MAX_CHUNK_TOKENS_HARD_LIMIT,
                )
                truncated_chunk = self._truncate_to_tokens(
                    chunk, self.MAX_CHUNK_TOKENS_HARD_LIMIT
                )
                truncated_chunks.append(truncated_chunk)
            else:
                truncated_chunks.append(chunk)
        return truncated_chunks

    def chunk_by_section_rule_based(
        self, markdown_content: str, max_tokens: Optional[int] = None
    ) -> list[str]:
        """
        Chunk content by sections (rule-based). Each section is one chunk,
        but sections exceeding max_tokens are truncated (redundant part removed).

        Args:
            markdown_content: Markdown content to chunk
            max_tokens: Maximum tokens per chunk (defaults to max_section_tokens)

        Returns:
            List of chunk strings
        """
        if not markdown_content.strip():
            return []

        max_tokens = max_tokens or self.max_section_tokens

        # Parse markdown into sections
        sections = self.markdown_parser.parse_markdown_sections(markdown_content)

        chunks = []
        for section_title, section_content in sections.items():
            section_tokens = self.count_tokens(section_content)

            # Skip empty sections
            if section_tokens == 0:
                continue

            if section_tokens <= max_tokens:
                # Section fits in one chunk
                chunks.append(section_content)
            else:
                # Section exceeds limit, truncate to max_tokens (remove redundant part)
                logger.debug(
                    "Section '%s' exceeds %d tokens (%d tokens), truncating to %d tokens",
                    section_title,
                    max_tokens,
                    section_tokens,
                    max_tokens,
                )
                truncated_content = self._truncate_to_tokens(
                    section_content, max_tokens
                )
                chunks.append(truncated_content)

        # Enforce hard limit of 8000 tokens on all chunks (in case max_tokens > 8000)
        chunks = self._enforce_hard_limit(chunks)

        logger.debug(
            "Split content into %d chunks using rule-based strategy (%d sections, max %d tokens per section, hard limit %d)",
            len(chunks),
            len(sections),
            max_tokens,
            self.MAX_CHUNK_TOKENS_HARD_LIMIT,
        )

        return chunks

    def chunk_by_section_recursive(
        self, markdown_content: str, max_tokens: Optional[int] = None
    ) -> list[str]:
        """
        Chunk content recursively by sections. First splits by sections,
        then for each section, uses TextProcessor.split_into_chunks() to chunk recursively.

        Args:
            markdown_content: Markdown content to chunk
            max_tokens: Maximum tokens per chunk (defaults to max_chunk_tokens)

        Returns:
            List of chunk strings
        """
        if not markdown_content.strip():
            return []

        max_tokens = max_tokens or self.max_chunk_tokens

        # Parse markdown into sections
        sections = self.markdown_parser.parse_markdown_sections(markdown_content)

        # Create a TextProcessor with the correct max_tokens
        temp_processor = TextProcessor(max_chunk_words=max_tokens)

        chunks = []
        for _section_title, section_content in sections.items():
            if not section_content.strip():
                # Empty section, skip
                continue

            # Use TextProcessor.split_into_chunks() which already implements recursive chunking
            section_chunks = temp_processor.split_into_chunks(section_content)
            chunks.extend(section_chunks)

        # Enforce hard limit of 8000 tokens on all chunks
        chunks = self._enforce_hard_limit(chunks)

        logger.debug(
            "Split content into %d chunks using recursive strategy (%d sections, max %d tokens per chunk, hard limit %d)",
            len(chunks),
            len(sections),
            max_tokens,
            self.MAX_CHUNK_TOKENS_HARD_LIMIT,
        )

        return chunks
