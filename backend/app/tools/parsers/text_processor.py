"""Module for text processing, chunking, and paragraph splitting."""

import logging
import re
from typing import Optional
from typing import Optional

import tiktoken
from llama_index.core.llms import LLM
from llama_index.core.llms import LLM

logger = logging.getLogger(__name__)


class TextProcessor:
    """Handles text splitting, chunking, and token counting."""

    TABLE_TO_TEXT_PROMPT = """You are given a table in Markdown format, including its caption.

Your task is to produce a coherent natural-language description that describes the information presented in the table.

Rules:
- Use only the information explicitly contained in the table.
- Do not add interpretations, background knowledge, or external details.
- Do not mention anything that cannot be directly inferred from the table entries.

Example:
Table 1: PPL and WER figures for the dev and tsr-HE/CO(MMON) sets with 4-gram model and TLM.
|     |        | dev | tsr-HE | tsr-CO |
|-----|--------|-----|--------|--------|
| PPL | 4-gram | 117 | 117    | 106    |
|     | TLM    | 54  | 54     | 55     |
| WER | 4-gram | 7.8 | 7.2    | 9.5    |
|     | TLM    | 5.8 | 5.3    | 7.3    |

Description:
The table reports perplexity (PPL) and word error rate (WER) results for the dev, tsr-HE, and tsr-CO datasets using two language models: a 4-gram model and a TLM. For PPL, the 4-gram model yields values of 117 on both dev and tsr-HE, and 106 on tsr-CO, while the TLM achieves lower PPL values of 54 on dev and tsr-HE, and 55 on tsr-CO. For WER, the 4-gram model records error rates of 7.8 on dev, 7.2 on tsr-HE, and 9.5 on tsr-CO, whereas the TLM reduces WER to 5.8, 5.3, and 7.3 on the respective datasets.

Table:
{table}
"""

    def __init__(self, max_chunk_words: int, llm: Optional[LLM] = None):
        """
        Initialize text processor.

        Args:
            max_chunk_words: Maximum tokens per chunk
            llm: Optional LLM instance for converting tables to text
            llm: Optional LLM instance for converting tables to text
        """
        self.max_chunk_words = max_chunk_words
        self.llm = llm
        self.llm = llm
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

    @staticmethod
    def is_table_title_line(line: str) -> bool:
        """
        Check if a line is a table title (Table + number).

        Args:
            line: Line to check

        Returns:
            True if line matches pattern "Table" followed by number and colon
        """
        stripped = line.strip()
        # Pattern: "Table" followed by optional space, number, colon, and description
        pattern = r"^Table\s+\d+\s*:.*"
        return bool(re.match(pattern, stripped, re.IGNORECASE))

    @staticmethod
    def is_table_paragraph(paragraph: str) -> bool:
        """
        Check if a paragraph is a markdown table.

        Args:
            paragraph: Paragraph text to check

        Returns:
            True if paragraph is a markdown table
        """
        lines = paragraph.strip().split("\n")
        if not lines:
            return False

        # A table should have at least one table line
        table_line_count = sum(1 for line in lines if TextProcessor.is_table_line(line))
        return table_line_count > 0

    async def convert_table_to_text(self, table_markdown: str) -> str:
        """
        Convert a markdown table to natural language text using LLM.

        Args:
            table_markdown: Markdown table content (may include table title)

        Returns:
            Natural language description of the table, or original table if LLM is not available
        """
        if not self.llm:
            logger.warning(
                "No LLM available for table conversion, returning original table"
            )
            return table_markdown

        try:
            # Extract table title if present (usually at beginning or end)
            lines = table_markdown.strip().split("\n")
            table_title = None
            table_content_lines = []

            # Check if first line is a table title
            if lines and self.is_table_title_line(lines[0]):
                table_title = lines[0].strip()
                table_content_lines = [
                    line for line in lines[1:] if self.is_table_line(line)
                ]
            # Check if last line is a table title
            elif lines and self.is_table_title_line(lines[-1]):
                table_title = lines[-1].strip()
                table_content_lines = [
                    line for line in lines[:-1] if self.is_table_line(line)
                ]
            else:
                # No title found, collect all table lines
                table_content_lines = [
                    line for line in lines if self.is_table_line(line)
                ]

            # Reconstruct table content with title at the beginning
            if table_title:
                table_content = "\n".join([table_title, *table_content_lines])
            else:
                table_content = (
                    "\n".join(table_content_lines)
                    if table_content_lines
                    else table_markdown
                )

            prompt = self.TABLE_TO_TEXT_PROMPT.format(table=table_content)
            response = await self.llm.acomplete(prompt)

            if response and hasattr(response, "text"):
                description = response.text.strip()
                logger.debug(
                    "Successfully converted table to text (length: %d)",
                    len(description),
                )
                return description
            else:
                logger.warning(
                    "Empty response from LLM for table conversion, returning original table"
                )
                return table_markdown
        except Exception as e:
            logger.exception("Error converting table to text: %s", str(e))
            return table_markdown

    async def split_into_paragraphs_async(
        self, content: str, convert_tables: bool = False
    ) -> list[str]:
        """
        Split content into paragraphs, converting tables to natural language text if LLM is available.
        Image-only paragraphs are attached to the previous paragraph to ensure
        they're included in chunks.

        Args:
            content: Content to split
            convert_tables: Whether to convert tables to text

        Returns:
            List of paragraphs (tables converted to text if LLM available, images attached to previous paragraph)
        """
        paragraphs = self.split_into_paragraphs(content)

        # Convert tables to text if LLM is available
        if self.llm:
            converted_paragraphs = []
            for paragraph in paragraphs:
                if self.is_table_paragraph(paragraph) and convert_tables:
                    converted = await self.convert_table_to_text(paragraph)
                    converted_paragraphs.append(converted)
                else:
                    converted_paragraphs.append(paragraph)
            return converted_paragraphs

        return paragraphs

    def split_into_paragraphs(self, content: str) -> list[str]:
        """
        Split content into paragraphs, preserving tables as single units.
        Image-only paragraphs are attached to the previous paragraph to ensure
        they're included in chunks.
        Table titles (Table + number) are captured along with tables.

        Args:
            content: Content to split

        Returns:
            List of paragraphs (tables are kept as single units with titles, images attached to previous paragraph)
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
            is_table_title = self.is_table_title_line(line)

            if is_table_line:
                # We're in a table
                if not in_table:
                    # Start of a new table
                    # First save current non-table paragraph
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []

                    # Check if the last paragraph in paragraphs ends with a table title
                    if paragraphs and len(paragraphs) > 0:
                        last_para_lines = paragraphs[-1].split("\n")
                        if last_para_lines and self.is_table_title_line(
                            last_para_lines[-1]
                        ):
                            # Extract table title from last paragraph
                            table_title = last_para_lines.pop()
                            # Update or remove the last paragraph
                            if last_para_lines:
                                paragraphs[-1] = "\n".join(last_para_lines)
                            else:
                                paragraphs.pop()
                            # Add table title to current paragraph (which will be the table)
                            current_paragraph.append(table_title)
                    in_table = True
                current_paragraph.append(line)
            else:
                # Not a table line
                if in_table:
                    # End of table
                    # Check if current line is a table title (title after table)
                    if is_table_title:
                        # Add table title to table
                        current_paragraph.append(line)
                        # Save table with title
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                        in_table = False
                        continue
                    # Save table as a single paragraph
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

    async def split_into_chunks_async(
        self, content: str, convert_tables: bool = False
    ) -> list[str]:
        """
        Split content into chunks by paragraph, converting tables to text if LLM is available.

        Combines multiple paragraphs together until the character limit (500)
        is exceeded. Tables are never split across chunks.

        Args:
            content: Content to split into chunks

        Returns:
            List of chunk strings
        """
        if not content.strip():
            return []

        # Split into paragraphs (tables converted to text if LLM available)
        paragraphs = await self.split_into_paragraphs_async(content, convert_tables)

        return self._create_chunks_from_paragraphs(paragraphs)

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

        return self._create_chunks_from_paragraphs(paragraphs)

    def _create_chunks_from_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """
        Create chunks from paragraphs based on token limits.

        Args:
            paragraphs: List of paragraphs

        Returns:
            List of chunk strings
        """

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
            "Split content into %d chunks (max %d tokens, paragraph-based)",
            len(chunks),
            self.max_chunk_words,
        )

        return chunks
