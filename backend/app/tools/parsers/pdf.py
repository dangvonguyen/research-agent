import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests
from markdown_it import MarkdownIt

from app.core.config import settings
from app.db.models import Paper, PaperContent

logger = logging.getLogger(__name__)


class PDFParser:
    """A parser to extract sections from PDF research papers using datalab API."""

    def __init__(self) -> None:
        self.api_key = settings.DATALAB_API_KEY
        self.api_url = settings.DATALAB_API_URL
        self.min_content_length = 200  # Minimum content length for a section
        self.max_chunk_words = 500  # Maximum words per chunk
        self.chunk_overlap_words = 50  # Overlap between chunks in words

    def get_markdown_content(
        self, pdf_path: str, max_pages: Optional[int] = None
    ) -> str:
        """
        Convert PDF to markdown and return the content.
        Useful for extracting metadata before creating Paper records.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process (None for all pages)

        Returns:
            Markdown content as string
        """
        if not Path(pdf_path).exists():
            logger.error("PDF file not found: '%s'", pdf_path)
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if not self.api_key or not self.api_url:
            logger.error("Datalab API credentials not configured.")
            raise ValueError("Datalab API credentials not configured.")

        return self._convert_pdf_to_markdown(pdf_path, max_pages)

    def parse_paper(
        self,
        paper: Paper,
        max_pages: Optional[int] = None,
        markdown_content: Optional[str] = None,
    ) -> list[PaperContent]:
        """
        Parse a research paper PDF using datalab API and extract sections.

        Args:
            paper: Paper object with file_path
            max_pages: Maximum number of pages to process (None for all pages)
            markdown_content: Optional pre-converted markdown content to avoid re-parsing

        Returns:
            List of PaperContent objects with parsed sections
        """
        if not paper.file_path and not markdown_content:
            logger.warning("No PDF file provided for paper '%s'", paper.title)
            return []

        if markdown_content:
            # Use provided markdown content (already converted)
            logger.debug(
                "Using provided markdown content for paper '%s'",
                paper.title,
            )
        else:
            # Need to convert PDF to markdown
            if not Path(paper.file_path).exists():
                logger.error("PDF file not found: '%s'", paper.file_path)
                return []

            if not self.api_key or not self.api_url:
                logger.error("Datalab API credentials not configured.")
                return []

            logger.debug(
                "Parsing PDF paper '%s' with path '%s' using datalab API",
                paper.title,
                paper.file_path,
            )

            try:
                # Convert PDF to markdown using datalab API
                markdown_content = self._convert_pdf_to_markdown(
                    paper.file_path, max_pages
                )
            except Exception as e:
                logger.exception(
                    "Error converting PDF to markdown for paper '%s': %s",
                    paper.title,
                    str(e),
                )
                return []

        try:
            if not markdown_content:
                logger.warning(
                    "No markdown content available for paper '%s'", paper.title
                )
                return []

            # Parse markdown into sections
            sections = self._parse_markdown_sections(markdown_content)

            # Convert to PaperContent objects with chunking
            contents: list[PaperContent] = []
            for section_idx, (section_title, content) in enumerate(sections.items()):
                # Split section content into chunks
                chunks = self._split_into_chunks(content)

                # Create PaperContent for each chunk
                for chunk_idx, chunk_content in enumerate(chunks):
                    word_count = len(chunk_content.split())
                    contents.append(
                        PaperContent(
                            paper_id=paper.id,
                            section_name=section_title,
                            section_index=section_idx,
                            chunk_index=chunk_idx,
                            content=chunk_content,
                            token_count=word_count,  # Using word count as approximation
                            embedding_vector=None,
                        )
                    )

            logger.info(
                "Successfully parsed %d sections into %d chunks for paper '%s'",
                len(sections),
                len(contents),
                paper.title,
            )
            return contents

        except Exception as e:
            logger.exception(
                "Error parsing PDF for paper '%s': %s",
                paper.title,
                str(e),
            )
            return []

    def _convert_pdf_to_markdown(
        self, pdf_path: str, max_pages: Optional[int] = None
    ) -> str:
        """
        Convert PDF to markdown using datalab API.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process

        Returns:
            Markdown content as string
        """
        logger.debug("Uploading PDF to datalab API: %s", pdf_path)

        # Step 1: Upload PDF and request conversion
        with open(pdf_path, "rb") as f:
            files = {"file": (Path(pdf_path).name, f, "application/pdf")}

            payload = {
                "output_format": "markdown",
                "mode": "fast",
                "force_ocr": "false",
                "use_llm": "false",
            }

            if max_pages:
                payload["max_pages"] = str(max_pages)

            headers = {"X-API-Key": self.api_key}

            response = requests.post(
                self.api_url, headers=headers, data=payload, files=files
            )

        if response.status_code != 200:
            raise Exception(
                f"Error uploading PDF: {response.status_code} - {response.text}"
            )

        result = response.json()

        if not result.get("success"):
            raise Exception(
                f"API returned error: {result.get('error', 'Unknown error')}"
            )

        request_id = result.get("request_id")
        request_check_url = result.get("request_check_url")

        if not request_check_url:
            raise Exception("No request_check_url in response")

        logger.debug("Upload successful. Request ID: %s", request_id)

        # Step 2: Poll for completion
        max_attempts = 120  # Maximum 10 minutes (120 * 5 seconds)
        attempt = 0

        while attempt < max_attempts:
            check_response = requests.get(request_check_url, headers=headers)

            if check_response.status_code != 200:
                raise Exception(
                    f"Error checking status: {check_response.status_code} - {check_response.text}"
                )

            result = check_response.json()
            status = result.get("status")

            if status == "complete":
                logger.debug("Conversion completed!")
                break

            if status == "failed":
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"Conversion failed: {error_msg}")
            else:
                attempt += 1
                if attempt % 6 == 0:  # Log every 30 seconds
                    logger.debug(
                        "Still processing... (attempt %d/%d)", attempt, max_attempts
                    )
                time.sleep(5)
        else:
            raise Exception("Conversion timeout - exceeded maximum wait time")

        # Step 3: Extract markdown
        markdown_content = None

        if "markdown" in result:
            markdown_content = result["markdown"]
        elif "files" in result:
            markdown_url = result["files"].get("markdown")
            if markdown_url:
                md_response = requests.get(markdown_url)
                markdown_content = md_response.text
        elif "output" in result:
            markdown_content = result["output"]

        if not markdown_content:
            raise Exception("No markdown content found in result")

        logger.debug("Received markdown (%d characters)", len(markdown_content))
        return markdown_content

    def _extract_section_number(
        self, section_title: str
    ) -> Optional[tuple[int, tuple[int, ...], str]]:
        """
        Extract section number from title (e.g., "5.", "5.1", "5.2.3").

        Returns:
            Tuple (level, numbers, title_text) or None if not a numbered section
        """
        pattern = r"^(\d+(?:\.\d+)*)\.?\s*(.*)$"
        match = re.match(pattern, section_title.strip())
        if match:
            numbers = tuple(map(int, match.group(1).split(".")))
            return len(numbers), numbers, match.group(2).strip()
        return None

    def _is_parent_child(
        self, parent_num: tuple[int, ...], child_num: tuple[int, ...]
    ) -> bool:
        """Check if child_num is a direct child of parent_num."""
        if len(child_num) != len(parent_num) + 1:
            return False
        return child_num[:-1] == parent_num

    def _extract_text_from_inline(self, inline_token) -> str:
        """Extract text from an inline token."""
        text = ""
        for child in inline_token.children or []:
            if child.type == "text" or child.type == "code_inline":
                text += child.content
            elif child.type == "softbreak":
                text += " "
        return text

    def _extract_content_from_token(self, tokens: list, start_idx: int) -> str:
        """Extract content from a token and its children."""
        if start_idx >= len(tokens):
            return ""

        token = tokens[start_idx]
        content_parts = []

        if token.type == "paragraph_open":
            idx = start_idx + 1
            while idx < len(tokens) and tokens[idx].type != "paragraph_close":
                if tokens[idx].type == "inline":
                    content_parts.append(self._extract_text_from_inline(tokens[idx]))
                idx += 1
        elif token.type in ["bullet_list_open", "ordered_list_open"]:
            idx = start_idx + 1
            depth = 1
            while idx < len(tokens) and depth > 0:
                if tokens[idx].type in ["bullet_list_open", "ordered_list_open"]:
                    depth += 1
                elif tokens[idx].type in ["bullet_list_close", "ordered_list_close"]:
                    depth -= 1
                elif tokens[idx].type == "list_item_open":
                    item_idx = idx + 1
                    item_parts = []
                    while (
                        item_idx < len(tokens)
                        and tokens[item_idx].type != "list_item_close"
                    ):
                        if tokens[item_idx].type == "inline":
                            item_parts.append(
                                self._extract_text_from_inline(tokens[item_idx])
                            )
                        item_idx += 1
                    if item_parts:
                        content_parts.append("• " + " ".join(item_parts))
                idx += 1

        return " ".join(content_parts).strip()

    def _parse_markdown_sections(self, markdown_text: str) -> dict[str, str]:
        """
        Parse markdown text into sections and their content.
        Merges short parent sections with their first child section.

        Args:
            markdown_text: The markdown content to parse

        Returns:
            Dictionary with section titles as keys and content as values
        """
        md = MarkdownIt()
        tokens = md.parse(markdown_text)

        sections_data = []
        current_section = None
        current_content = []
        current_level = None
        current_numbers = None

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "heading_open":
                if current_section is not None and current_content:
                    sections_data.append(
                        {
                            "title": current_section,
                            "content": "\n\n".join(current_content).strip(),
                            "level": current_level,
                            "numbers": current_numbers,
                        }
                    )

                heading_level = int(token.tag[1])

                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    inline_token = tokens[i + 1]
                    heading_text = self._extract_text_from_inline(inline_token)
                    current_section = heading_text.strip()
                    current_content = []

                    section_info = self._extract_section_number(current_section)
                    if section_info:
                        current_level, current_numbers, title_text = section_info
                        if title_text:
                            current_section = (
                                f"{'.'.join(map(str, current_numbers))}. {title_text}"
                            )
                    else:
                        current_level = heading_level
                        current_numbers = None

                    i += 2
                    continue

            if current_section is not None and token.type in [
                "paragraph_open",
                "bullet_list_open",
                "ordered_list_open",
            ]:
                content = self._extract_content_from_token(tokens, i)
                if content:
                    current_content.append(content)

            i += 1

        if current_section is not None and current_content:
            sections_data.append(
                {
                    "title": current_section,
                    "content": "\n\n".join(current_content).strip(),
                    "level": current_level,
                    "numbers": current_numbers,
                }
            )

        # Second pass: merge short parent sections with first child
        sections = {}
        i = 0
        while i < len(sections_data):
            section = sections_data[i]

            if section["numbers"] and len(section["numbers"]) > 0:
                if len(section["content"]) < self.min_content_length:
                    parent_num = section["numbers"]
                    merged_content = section["content"]
                    merged_title = section["title"]

                    j = i + 1
                    while j < len(sections_data):
                        next_section = sections_data[j]
                        if next_section["numbers"] and self._is_parent_child(
                            parent_num, next_section["numbers"]
                        ):
                            merged_title = (
                                f"{section['title']} - {next_section['title']}"
                            )
                            merged_content = f"{section['content']}\n\n{next_section['content']}".strip()
                            sections[merged_title] = merged_content
                            i = j + 1
                            break
                        if (
                            next_section["numbers"]
                            and next_section["numbers"][: len(parent_num)] == parent_num
                        ) or (
                            next_section["numbers"]
                            and len(next_section["numbers"]) <= len(parent_num)
                        ):
                            break
                        j += 1
                    else:
                        sections[section["title"]] = section["content"]
                        i += 1
                        continue
                else:
                    sections[section["title"]] = section["content"]
                    i += 1
            else:
                sections[section["title"]] = section["content"]
                i += 1

        return sections

    def _count_words(self, text: str) -> int:
        """
        Count the number of words in text.

        Args:
            text: Text to count words in

        Returns:
            Number of words
        """
        return len(text.split())

    def _split_into_chunks(self, content: str) -> list[str]:
        """
        Split content into chunks with overlap.

        Each chunk will have at most max_chunk_words words, with chunk_overlap_words
        words overlapping between consecutive chunks.

        Args:
            content: Content to split into chunks

        Returns:
            List of chunk strings
        """
        if not content.strip():
            return []

        words = content.split()
        total_words = len(words)

        # If content is smaller than max_chunk_words, return as single chunk
        if total_words <= self.max_chunk_words:
            return [content]

        chunks = []
        start_idx = 0

        while start_idx < total_words:
            # Calculate end index for this chunk
            end_idx = min(start_idx + self.max_chunk_words, total_words)

            # Extract chunk
            chunk_words = words[start_idx:end_idx]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)

            # Move start index forward, accounting for overlap
            # If this is not the last chunk, move back by overlap amount
            if end_idx < total_words:
                start_idx = end_idx - self.chunk_overlap_words
            else:
                break

        logger.debug(
            "Split content into %d chunks (max %d words, %d overlap)",
            len(chunks),
            self.max_chunk_words,
            self.chunk_overlap_words,
        )

        return chunks

    def parse_specific_sections(self, paper: Paper) -> list[PaperContent]:
        """
        Parse paper and return all sections.

        Note: This method now returns all parsed sections regardless of section_type.
        The section_types parameter is kept for backward compatibility but is ignored.

        Args:
            paper: Paper object with file_path
            section_types: Ignored - kept for backward compatibility

        Returns:
            List of all PaperContent objects with parsed sections
        """
        logger.debug(
            "Parsing all sections for paper '%s'",
            paper.title,
        )

        # Parse and return all sections (no filtering by section type)
        all_contents = self.parse_paper(paper)

        logger.info(
            "Returning %d sections for paper '%s' (all sections are included)",
            len(all_contents),
            paper.title,
        )

        return all_contents
