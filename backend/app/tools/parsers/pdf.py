"""Main PDF parser class that orchestrates PDF parsing and content extraction."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.db.models import Paper, PaperContent
from app.services.llm_service import llm_service

from .api_converter import APIConverter
from .image_handler import ImageHandler
from .markdown_parser import MarkdownParser
from .section_classifier import SectionClassifier
from .text_processor import TextProcessor

logger = logging.getLogger(__name__)


class PDFParser:
    """A parser to extract sections from PDF research papers using datalab API."""

    def __init__(self) -> None:
        """Initialize PDF parser with required components."""
        self.api_key = settings.DATALAB_API_KEY
        self.api_url = settings.DATALAB_API_URL
        self.min_content_length = settings.PDF_MIN_CONTENT_LENGTH
        self.max_chunk_words = settings.PDF_MAX_CHUNK_WORDS

        # Initialize component modules
        self.api_converter = APIConverter(self.api_key, self.api_url)
        self.markdown_parser = MarkdownParser(self.min_content_length)
        # Use default LLM for table conversion
        default_llm = llm_service.get_default_llm()
        self.text_processor = TextProcessor(self.max_chunk_words, llm=default_llm)
        self.section_classifier = SectionClassifier()

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

        result = self.api_converter.convert_pdf_to_markdown(pdf_path, max_pages)
        # Preprocess markdown to fix footnote superscripts
        markdown = result.get("markdown", "")
        markdown = self.markdown_parser.preprocess_footnote_sups(markdown)
        return markdown

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
            pdf_conversion_result: Optional full PDF conversion result with images

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
                pdf_conversion_result = self.api_converter.convert_pdf_to_markdown(
                    paper.file_path, max_pages
                )
                markdown_content = pdf_conversion_result.get("markdown", "")
                # Preprocess markdown
                markdown_content = self.markdown_parser.preprocess_footnote_sups(
                    markdown_content
                )
                pdf_conversion_result["markdown"] = markdown_content
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

                image_paths_map = ImageHandler.save_images(images, paper.id, pdf_dir)
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
            sections = self.markdown_parser.parse_markdown_sections(markdown_content)

            # Convert to PaperContent objects with chunking
            contents: list[PaperContent] = []
            for section_idx, (section_title, content) in enumerate(sections.items()):
                # Check if this is a reference section
                is_reference = self.section_classifier.is_reference_section(
                    section_title
                )

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
                    images_in_section = ImageHandler.extract_images_from_content(
                        content
                    )
                    if images_in_section:
                        logger.debug(
                            "Found %d images in section '%s': %s",
                            len(images_in_section),
                            section_title,
                            ", ".join([img[0] for img in images_in_section]),
                        )

                    # Split content into paragraphs first to track image positions relative to paragraphs
                    # Convert tables to text if LLM is available (using async method)
                    paragraphs = self._split_into_paragraphs_with_table_conversion(content)

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
                            paragraph_size = self.text_processor.count_tokens(paragraph)

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
                        image_filename = ImageHandler.extract_image_from_chunk(
                            chunk_content
                        )

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

    def _split_into_paragraphs_with_table_conversion(self, content: str) -> list[str]:
        """
        Split content into paragraphs and convert tables to text if LLM is available.
        Handles both sync and async contexts.

        Args:
            content: Content to split

        Returns:
            List of paragraphs with tables converted to text
        """
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            # We're in async context, but parse_paper is sync
            # Use the sync version for now (tables won't be converted in async context)
            logger.warning(
                "Running in async context, table conversion may not work. Using sync method."
            )
            return self.text_processor.split_into_paragraphs(content)
        except RuntimeError:
            # No event loop running, use asyncio.run to convert tables
            return asyncio.run(
                self.text_processor.split_into_paragraphs_async(content)
            )

    def parse_specific_sections(self, paper: Paper) -> list[PaperContent]:
        """
        Parse paper and return all sections.

        Note: This method now returns all parsed sections regardless of section_type.
        The section_types parameter is kept for backward compatibility but is ignored.

        Args:
            paper: Paper object with file_path

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
