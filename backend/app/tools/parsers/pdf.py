import base64
import logging
import re
import time
from pathlib import Path
from typing import Optional
from uuid import UUID

import requests
import tiktoken
from markdown_it import MarkdownIt

from app.core.config import settings
from app.db.models import Paper, PaperContent

logger = logging.getLogger(__name__)


class PDFParser:
    """A parser to extract sections from PDF research papers using datalab API."""

    def __init__(self) -> None:
        self.api_key = settings.DATALAB_API_KEY
        self.api_url = settings.DATALAB_API_URL
        self.min_content_length = settings.PDF_MIN_CONTENT_LENGTH
        self.max_chunk_words = settings.PDF_MAX_CHUNK_WORDS
        if not hasattr(self, "_tokenizer"):
            self._tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")

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

        result = self._convert_pdf_to_markdown(pdf_path, max_pages)
        return result.get("markdown", "")

    def _save_images(
        self, images: dict, paper_id: UUID, output_dir: Path
    ) -> dict[str, str]:
        """
        Save images from base64-encoded data to filesystem.

        Args:
            images: Dict mapping image names to base64-encoded image data
            paper_id: UUID of the paper
            output_dir: Base directory where paper images are stored

        Returns:
            Dict mapping image names to saved file paths (relative to output_dir)
        """
        if not images:
            return {}

        # Create images directory for this paper
        images_dir = output_dir / str(paper_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = {}
        for image_name, image_data in images.items():
            try:
                # Decode base64 image data
                image_bytes = base64.b64decode(image_data)
                image_path = images_dir / image_name

                # Write image to file
                image_path.write_bytes(image_bytes)
                saved_paths[image_name] = str(image_path.relative_to(output_dir))

                logger.debug("Saved image '%s' to '%s'", image_name, image_path)
            except Exception as e:
                logger.warning(
                    "Failed to save image '%s' for paper '%s': %s",
                    image_name,
                    paper_id,
                    str(e),
                )

        return saved_paths

    def _extract_image_from_chunk(self, chunk_content: str) -> Optional[str]:
        """
        Extract image reference from a chunk if it contains one.

        Args:
            chunk_content: Markdown content of the chunk

        Returns:
            Image filename if found, None otherwise
        """
        # Pattern to match markdown images: ![](image.jpg) or ![alt](image.jpg)
        # Also matches: ![alt text](image.jpg) or ![alt text with spaces](image.jpg)
        pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
        matches = re.findall(pattern, chunk_content)

        if matches:
            # Get the last image reference (most relevant one)
            # Format: (alt_text, image_path)
            _, image_path = matches[-1]
            # Extract just the filename from the path
            image_name = Path(image_path).name
            return image_name

        return None

    def _extract_images_from_content(self, content: str) -> list[tuple[str, int]]:
        """
        Extract all image references from content with their character positions.

        Args:
            content: Markdown content

        Returns:
            List of tuples: (image_filename, character_position)
        """
        images = []
        pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
        for match in re.finditer(pattern, content):
            _, image_path = match.groups()
            image_name = Path(image_path).name
            images.append((image_name, match.start()))
        return images

    def _find_nearest_image(
        self, chunk_start: int, chunk_end: int, images: list[tuple[str, int]]
    ) -> Optional[str]:
        """
        Find the nearest image to a chunk based on character positions.

        Args:
            chunk_start: Character position where chunk starts in original content
            chunk_end: Character position where chunk ends in original content
            images: List of (image_filename, position) tuples

        Returns:
            Image filename if found nearby, None otherwise
        """
        if not images:
            return None

        # Find images before or after the chunk (within reasonable distance)
        # Consider images up to 500 characters before or after the chunk
        search_range = 500
        nearest_image = None
        min_distance = float("inf")

        for image_name, image_pos in images:
            if image_pos < chunk_start:
                # Image is before chunk
                distance = chunk_start - image_pos
                if distance < search_range and distance < min_distance:
                    min_distance = distance
                    nearest_image = image_name
            elif image_pos > chunk_end:
                # Image is after chunk
                distance = image_pos - chunk_end
                if distance < search_range and distance < min_distance:
                    min_distance = distance
                    nearest_image = image_name
            else:
                # Image is within chunk
                nearest_image = image_name
                break

        return nearest_image

    def parse_paper(
        self,
        paper: Paper,
        max_pages: Optional[int] = None,
        markdown_content: Optional[str] = None,
        pdf_conversion_result: Optional[dict] = None,
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
                pdf_conversion_result = self._convert_pdf_to_markdown(
                    paper.file_path, max_pages
                )
                markdown_content = pdf_conversion_result.get("markdown", "")
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

            # Save images if we have them from PDF conversion
            image_paths_map = {}
            if pdf_conversion_result and pdf_conversion_result.get("images"):
                images = pdf_conversion_result.get("images", {})
                # Determine output directory for images (same directory as PDF file)
                if paper.file_path:
                    pdf_dir = Path(paper.file_path).parent
                else:
                    # Fallback to a default directory
                    pdf_dir = (
                        Path(settings.UPLOAD_DIR)
                        if hasattr(settings, "UPLOAD_DIR")
                        else Path("uploads")
                    )

                image_paths_map = self._save_images(images, paper.id, pdf_dir)
                logger.info(
                    "Saved %d images for paper '%s'", len(image_paths_map), paper.id
                )

            # Save markdown to file for debugging
            if paper.file_path:
                pdf_dir = Path(paper.file_path).parent
            else:
                pdf_dir = (
                    Path(settings.UPLOAD_DIR)
                    if hasattr(settings, "UPLOAD_DIR")
                    else Path("uploads")
                )
            markdown_dir = pdf_dir / str(paper.id)
            markdown_dir.mkdir(parents=True, exist_ok=True)
            markdown_file = markdown_dir / "markdown.md"
            markdown_file.write_text(markdown_content, encoding="utf-8")
            logger.info(
                "Saved markdown to '%s' for paper '%s'", markdown_file, paper.id
            )

            # Print image names for debugging
            if pdf_conversion_result and pdf_conversion_result.get("images"):
                images = pdf_conversion_result.get("images", {})
                logger.info(
                    "Found %d images for paper '%s': %s",
                    len(images),
                    paper.id,
                    ", ".join(images.keys()),
                )
                print(f"Images found for paper {paper.id}: {', '.join(images.keys())}")

            # Parse markdown into sections
            sections = self._parse_markdown_sections(markdown_content)

            # Convert to PaperContent objects with chunking
            contents: list[PaperContent] = []
            for section_idx, (section_title, content) in enumerate(sections.items()):
                # Check if this is a reference section
                is_reference = self._is_reference_section(section_title)

                if is_reference:
                    # For reference sections, save as a single chunk
                    # Store section name and content in metadata, don't create embedding
                    word_count = len(content.split())
                    contents.append(
                        PaperContent(
                            paper_id=paper.id,
                            section_name=section_title,
                            section_index=section_idx,
                            chunk_index=0,  # Single chunk, always index 0
                            content=content,
                            token_count=word_count,
                            embedding_vector=None,  # No embedding for references
                            extra_metadata={
                                "is_reference": True,
                            },
                        )
                    )
                    logger.debug(
                        "Saved reference section '%s' as single chunk for paper '%s'",
                        section_title,
                        paper.title,
                    )
                else:
                    # For regular sections, extract image positions from original content
                    images_in_section = self._extract_images_from_content(content)
                    if images_in_section:
                        logger.debug(
                            "Found %d images in section '%s': %s",
                            len(images_in_section),
                            section_title,
                            ", ".join([img[0] for img in images_in_section]),
                        )

                    # Split content into paragraphs first to track image positions relative to paragraphs
                    paragraphs = self._split_into_paragraphs(content)

                    # Map images to paragraph indices
                    image_to_paragraph = {}
                    current_char_pos = 0
                    for para_idx, paragraph in enumerate(paragraphs):
                        para_start = content.find(paragraph, current_char_pos)
                        if para_start != -1:
                            para_end = para_start + len(paragraph)
                            # Check if any image is in this paragraph or immediately before/after
                            for img_name, img_pos in images_in_section:
                                if para_start <= img_pos < para_end:
                                    image_to_paragraph[img_name] = para_idx
                                    break
                                # Also check if image is very close (within 50 chars) before or after
                                if (
                                    abs(img_pos - para_start) < 50
                                    or abs(img_pos - para_end) < 50
                                ):
                                    image_to_paragraph[img_name] = para_idx
                                    break
                            current_char_pos = (
                                para_end
                                if para_start != -1
                                else current_char_pos + len(paragraph)
                            )

                    # Split into chunks as usual, but track which paragraphs go into each chunk
                    chunks = []
                    chunk_paragraph_ranges = []

                    # Build chunks manually while tracking paragraph indices
                    if not paragraphs:
                        chunks = []
                    else:
                        current_chunk = []
                        current_chunk_size = 0
                        current_chunk_start_para = 0

                        for para_idx, paragraph in enumerate(paragraphs):
                            paragraph_size = self._count_tokens(paragraph)

                            # If a single paragraph exceeds the limit, add it as its own chunk
                            if paragraph_size > self.max_chunk_words:
                                # Save current chunk if any
                                if current_chunk:
                                    chunks.append("\n\n".join(current_chunk))
                                    chunk_paragraph_ranges.append(
                                        (current_chunk_start_para, para_idx - 1)
                                    )
                                    current_chunk = []
                                    current_chunk_size = 0

                                # Add the large paragraph as its own chunk
                                chunks.append(paragraph)
                                chunk_paragraph_ranges.append((para_idx, para_idx))
                            else:
                                # Check if adding this paragraph would exceed the limit
                                separator_size = 2 if current_chunk else 0
                                new_size = (
                                    current_chunk_size + separator_size + paragraph_size
                                )

                                if new_size > self.max_chunk_words and current_chunk:
                                    # Current chunk is full, start a new one
                                    chunks.append("\n\n".join(current_chunk))
                                    chunk_paragraph_ranges.append(
                                        (current_chunk_start_para, para_idx - 1)
                                    )
                                    current_chunk = [paragraph]
                                    current_chunk_size = paragraph_size
                                    current_chunk_start_para = para_idx
                                else:
                                    # Add to current chunk
                                    if not current_chunk:
                                        current_chunk_start_para = para_idx
                                    current_chunk.append(paragraph)
                                    current_chunk_size = new_size

                        # Add any remaining chunk
                        if current_chunk:
                            chunks.append("\n\n".join(current_chunk))
                            chunk_paragraph_ranges.append(
                                (current_chunk_start_para, len(paragraphs) - 1)
                            )

                    # Create PaperContent for each chunk
                    for chunk_idx, chunk_content in enumerate(chunks):
                        word_count = len(chunk_content.split())

                        # First, try to extract image from chunk content directly
                        image_filename = self._extract_image_from_chunk(chunk_content)

                        # If no image in chunk, check images from paragraphs in this chunk range
                        if not image_filename and chunk_idx < len(
                            chunk_paragraph_ranges
                        ):
                            para_start, para_end = chunk_paragraph_ranges[chunk_idx]
                            # Also check one paragraph before and after (images might be on adjacent paragraphs)
                            check_start = max(0, para_start - 1)
                            check_end = min(len(paragraphs) - 1, para_end + 1)

                            for img_name, para_idx in image_to_paragraph.items():
                                if check_start <= para_idx <= check_end:
                                    image_filename = img_name
                                    logger.debug(
                                        "Found image '%s' in paragraph %d (range %d-%d) for chunk %d of section '%s'",
                                        image_filename,
                                        para_idx,
                                        check_start,
                                        check_end,
                                        chunk_idx,
                                        section_title,
                                    )
                                    break

                        extra_metadata = {}
                        if image_filename and image_filename in image_paths_map:
                            extra_metadata["image_path"] = image_paths_map[
                                image_filename
                            ]
                            logger.info(
                                "Associating image '%s' with chunk %d of section '%s' for paper '%s'",
                                image_filename,
                                chunk_idx,
                                section_title,
                                paper.id,
                            )
                            print(
                                f"Image '{image_filename}' associated with chunk {chunk_idx} in section '{section_title}'"
                            )

                        contents.append(
                            PaperContent(
                                paper_id=paper.id,
                                section_name=section_title,
                                section_index=section_idx,
                                chunk_index=chunk_idx,
                                content=chunk_content,
                                token_count=word_count,  # Using word count as approximation
                                embedding_vector=None,
                                extra_metadata=extra_metadata
                                if extra_metadata
                                else None,
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
    ) -> dict:
        """
        Convert PDF to markdown using datalab API.

        Args:
            pdf_path: Path to the PDF file
            max_pages: Maximum number of pages to process

        Returns:
            Dictionary with keys:
                - markdown: Markdown content as string
                - images: Dict mapping image names to base64-encoded image data
                - metadata: Dict with metadata
                - status: Status string
                - success: Boolean
                - error: Error message if any
                - page_count: Number of pages
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

        if not markdown_content:
            raise Exception("No markdown content found in result")

        logger.debug("Received markdown (%d characters)", len(markdown_content))

        # Preprocess markdown to fix footnote superscripts
        markdown_content = self._preprocess_footnote_sups(markdown_content)

        # Extract images from result
        images = result.get("images", {})
        metadata = result.get("metadata", {})
        page_count = result.get("page_count", 0)

        return {
            "markdown": markdown_content,
            "images": images,
            "metadata": metadata,
            "status": result.get("status", "complete"),
            "success": result.get("success", True),
            "error": result.get("error", ""),
            "page_count": page_count,
        }

    def _preprocess_footnote_sups(self, markdown_content: str) -> str:
        """
        Preprocess markdown to move footnote superscripts that appear at the start
        of a line to right after their reference.

        Detects <sup>X</sup> tags that:
        - Start at the beginning of a line (after line break)
        - Are NOT followed by a period
        - Have a matching <sup>X</sup> earlier in the text

        Moves the entire paragraph containing the second sup to right before the first sup.

        Args:
            markdown_content: The markdown content to preprocess

        Returns:
            Preprocessed markdown content
        """
        lines = markdown_content.split("\n")
        # Track which lines to skip (footnote paragraphs that will be moved)
        skip_lines = set()
        # Track insertions: (line_index, position_in_line, text_to_insert)
        insertions = []

        # First pass: identify footnote paragraphs and their target positions
        i = 0
        while i < len(lines):
            line = lines[i]

            # Check if line starts with <sup>X</sup> (after any leading whitespace)
            stripped = line.lstrip()
            sup_match = re.match(r"^<sup>(\d+)</sup>", stripped)

            if sup_match:
                sup_num = sup_match.group(1)
                # Check if NOT followed by a period (after the sup tag)
                after_sup = stripped[len(f"<sup>{sup_num}</sup>") :].lstrip()

                if not after_sup.startswith("."):
                    # This is a candidate - find the paragraph containing this sup
                    paragraph_start = i
                    paragraph_end = i + 1

                    # Collect the entire paragraph (until next blank line or end)
                    while paragraph_end < len(lines) and lines[paragraph_end].strip():
                        paragraph_end += 1

                    paragraph_lines = lines[paragraph_start:paragraph_end]
                    paragraph_text = "\n".join(paragraph_lines)

                    # Find matching sup earlier in the text (before this position)
                    # Search backwards from current position
                    found_match = False
                    for j in range(i - 1, -1, -1):
                        if f"<sup>{sup_num}</sup>" in lines[j]:
                            # Find the position right after the last occurrence of this sup
                            match_pos = lines[j].rfind(f"<sup>{sup_num}</sup>")
                            if match_pos != -1:
                                # Record insertion: add paragraph right after the matching sup
                                after_sup_pos = match_pos + len(f"<sup>{sup_num}</sup>")
                                insertions.append(
                                    (j, after_sup_pos, " " + paragraph_text)
                                )
                                found_match = True
                                break

                    if found_match:
                        # Mark these lines to skip
                        for k in range(paragraph_start, paragraph_end):
                            skip_lines.add(k)
                        i = paragraph_end
                        continue

            i += 1

        # Second pass: build result with insertions and skipping moved paragraphs
        result_lines = []
        for i, line in enumerate(lines):
            if i in skip_lines:
                continue

            # Apply any insertions for this line
            line_insertions = [(pos, text) for idx, pos, text in insertions if idx == i]
            if line_insertions:
                # Sort by position (descending) to insert from end to start
                line_insertions.sort(reverse=True)
                for pos, text in line_insertions:
                    line = line[:pos] + text + line[pos:]

            result_lines.append(line)

        return "\n".join(result_lines)

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

    def _extract_markdown_from_inline(self, inline_token) -> str:
        """
        Extract markdown syntax from an inline token, preserving images, links, and formatting.

        Args:
            inline_token: Inline token from MarkdownIt

        Returns:
            Markdown string preserving all inline elements
        """
        if not inline_token.children:
            return inline_token.content if hasattr(inline_token, "content") else ""

        parts = []
        for child in inline_token.children:
            if child.type == "text":
                parts.append(child.content if hasattr(child, "content") else "")
            elif child.type == "code_inline":
                content = child.content if hasattr(child, "content") else ""
                parts.append(f"`{content}`")
            elif child.type == "image":
                # Extract image markdown: ![alt](src)
                attrs = child.attrs if hasattr(child, "attrs") else []
                alt = ""
                src = ""
                for attr_name, attr_value in attrs:
                    if attr_name == "alt":
                        alt = attr_value
                    elif attr_name == "src":
                        src = attr_value
                parts.append(f"![{alt}]({src})")
            elif child.type == "link_open":
                # Extract link markdown: [text](href)
                attrs = child.attrs if hasattr(child, "attrs") else []
                href = ""
                for attr_name, attr_value in attrs:
                    if attr_name == "href":
                        href = attr_value
                        break
                # Find the link text in following tokens until link_close
                link_text = ""
                link_text_tokens = []
                idx = inline_token.children.index(child) + 1
                while idx < len(inline_token.children):
                    sibling = inline_token.children[idx]
                    if sibling.type == "link_close":
                        break
                    if sibling.type == "text":
                        link_text_tokens.append(
                            sibling.content if hasattr(sibling, "content") else ""
                        )
                    elif sibling.type == "code_inline":
                        # Preserve formatting inside links
                        link_text_tokens.append(
                            f"`{sibling.content if hasattr(sibling, 'content') else ''}`"
                        )
                    idx += 1
                link_text = "".join(link_text_tokens)
                parts.append(f"[{link_text}]({href})")
            elif child.type == "strong_open":
                # Extract bold text
                strong_parts = []
                idx = inline_token.children.index(child) + 1
                while idx < len(inline_token.children):
                    sibling = inline_token.children[idx]
                    if sibling.type == "strong_close":
                        break
                    if sibling.type == "text":
                        strong_parts.append(
                            sibling.content if hasattr(sibling, "content") else ""
                        )
                    idx += 1
                parts.append(f"**{''.join(strong_parts)}**")
            elif child.type == "em_open":
                # Extract italic text
                em_parts = []
                idx = inline_token.children.index(child) + 1
                while idx < len(inline_token.children):
                    sibling = inline_token.children[idx]
                    if sibling.type == "em_close":
                        break
                    if sibling.type == "text":
                        em_parts.append(
                            sibling.content if hasattr(sibling, "content") else ""
                        )
                    idx += 1
                parts.append(f"*{''.join(em_parts)}*")
            elif child.type in ["softbreak", "hardbreak"]:
                parts.append("\n")
            elif child.type in [
                "link_close",
                "strong_close",
                "em_close",
                "image_close",
            ]:
                # Skip close tokens, already handled
                pass

        return "".join(parts)

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
                    content_parts.append(
                        self._extract_markdown_from_inline(tokens[idx])
                    )
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
                                self._extract_markdown_from_inline(tokens[item_idx])
                            )
                        item_idx += 1
                    if item_parts:
                        content_parts.append("• " + " ".join(item_parts))
                idx += 1

        return " ".join(content_parts).strip()

    def _parse_markdown_sections(self, markdown_text: str) -> dict[str, str]:
        """
        Parse markdown text into sections and their content, preserving all markdown syntax.
        Uses raw markdown extraction to preserve images, tables, code blocks, etc.
        Merges short parent sections with their first child section.

        Args:
            markdown_text: The markdown content to parse

        Returns:
            Dictionary with section titles as keys and content as values (preserving markdown)
        """
        # Find all headings in the raw markdown text using regex
        # Pattern matches markdown headings: # Heading, ## Heading, etc.
        heading_pattern = r"^(#{1,6})\s+(.+)$"
        lines = markdown_text.split("\n")

        heading_positions = []  # List of (line_number, heading_level, heading_text)
        for line_num, line in enumerate(lines):
            match = re.match(heading_pattern, line)
            if match:
                heading_level = len(match.group(1))  # Number of # characters
                heading_text = match.group(2).strip()
                heading_positions.append((line_num, heading_level, heading_text))

        if not heading_positions:
            # No headings found, treat entire document as one section
            return {"": markdown_text.strip()}

        # Extract section content as raw markdown between headings
        sections_data = []
        for idx, (line_num, heading_level, heading_text) in enumerate(
            heading_positions
        ):
            # Determine section boundaries
            start_line = line_num + 1  # Content starts after heading line
            if idx + 1 < len(heading_positions):
                end_line = heading_positions[idx + 1][0]  # Until next heading
            else:
                end_line = len(lines)  # Until end of document

            # Extract raw markdown content
            section_lines = lines[start_line:end_line]
            section_content = "\n".join(section_lines).strip()

            # Extract section number if present
            section_info = self._extract_section_number(heading_text)
            if section_info:
                current_level, current_numbers, title_text = section_info
                if title_text:
                    heading_text = (
                        f"{'.'.join(map(str, current_numbers))}. {title_text}"
                    )
            else:
                current_level = heading_level
                current_numbers = None

            sections_data.append(
                {
                    "title": heading_text,
                    "content": section_content,
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

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        """
        return len(self._tokenizer.encode(text))

    def _is_reference_section(self, section_title: str) -> bool:
        """
        Check if a section is a reference/bibliography section.

        Reference sections typically start with the keyword and stand alone
        (e.g., "References", "6. References", "Bibliography").
        This avoids false positives like "Related References" or "Citations in Literature".

        Args:
            section_title: Title of the section

        Returns:
            True if this is a reference section
        """
        ref_keywords = [
            "reference",
            "references",
            "bibliography",
            "bibliographies",
            "works cited",
            "citations",
        ]
        title_lower = section_title.lower().strip()

        # Remove section numbers if present (e.g., "6. References" -> "references")
        # Pattern: optional numbers/dots at start, then whitespace, then title
        title_without_number = re.sub(
            r"^(\d+(?:\.\d+)*)\.?\s*", "", title_lower
        ).strip()

        # Check if title starts with keyword and stands alone
        for keyword in ref_keywords:
            # Exact match after removing numbers
            if title_without_number == keyword:
                return True

            # Title starts with keyword
            if title_without_number.startswith(keyword):
                # Get what comes after the keyword
                remaining = title_without_number[len(keyword) :].strip()

                # If nothing after, or only punctuation/whitespace, it's a match
                if not remaining:
                    return True

                # Allow trailing punctuation only
                if remaining in [".", ":", ";", "!", "?"]:
                    return True

                # Allow "References and Acknowledgments" type patterns but reject "References to..." or "Related References"
                if remaining.startswith((" and ", " & ", " or ")):
                    return True

        return False

    def _is_table_line(self, line: str) -> bool:
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

    def _is_image_line(self, line: str) -> bool:
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

    def _split_into_paragraphs(self, content: str) -> list[str]:
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
            is_table_line = self._is_table_line(line)
            is_image_line = self._is_image_line(line)

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

    def _split_into_chunks(self, content: str) -> list[str]:
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
        paragraphs = self._split_into_paragraphs(content)

        if not paragraphs:
            return []

        chunks = []
        current_chunk = []
        current_chunk_size = 0

        for paragraph in paragraphs:
            paragraph_size = self._count_tokens(paragraph)

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
