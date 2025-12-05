import logging
import re
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class ResearchPaperMetadata(BaseModel):
    """Structured metadata extracted from research paper markdown."""

    title: str | None = Field(None, description="Paper title")
    authors: list[str] | None = Field(None, description="List of author names")
    abstract: str | None = Field(None, description="Paper abstract")
    year: int | None = Field(None, description="Publication year (4-digit)")
    venue: str | None = Field(None, description="Conference or journal name")


class PaperService:
    """Service for paper-related operations."""

    def _extract_abstract_from_markdown(self, markdown_content: str) -> str | None:
        """
        Extract abstract content from markdown by finding headings that include 'abstract'.
        Returns all content under the abstract heading until the next heading.

        Args:
            markdown_content: Full markdown content from PDF

        Returns:
            Abstract text or None if not found
        """
        lines = markdown_content.split("\n")
        abstract_start_idx = None

        # Find heading that includes "abstract" (case-insensitive)
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            # Check if it's a markdown heading (starts with #)
            if line_stripped.startswith("#"):
                heading_text = re.sub(r"^#+\s*", "", line_stripped).strip()
                if "abstract" in heading_text.lower():
                    abstract_start_idx = i
                    break

        if abstract_start_idx is None:
            return None

        # Collect all content under the abstract heading until next heading
        abstract_lines = []
        for i in range(abstract_start_idx + 1, len(lines)):
            line = lines[i].strip()

            # Stop if we hit another heading
            if line.startswith("#"):
                break

            # Skip empty lines at the start
            if not abstract_lines and not line:
                continue

            abstract_lines.append(line)

        # Join and clean up the abstract
        abstract_text = " ".join(abstract_lines).strip()
        return abstract_text if abstract_text else None

    def extract_metadata_from_markdown(self, markdown_content: str) -> dict[str, Any]:
        """
        Extract title, authors, abstract, year, and venue from markdown content using LLM structured outputs.

        Args:
            markdown_content: Markdown content from PDF conversion

        Returns:
            Dictionary with extracted metadata (title, authors, abstract, year, venue)
            Fields will be None if not found (no fabrication)
        """
        if not markdown_content or not markdown_content.strip():
            logger.warning("Empty markdown content provided")
            return {
                "title": None,
                "authors": None,
                "abstract": None,
                "year": None,
                "venue": None,
            }

        # First, extract abstract separately from full markdown (can be anywhere)
        abstract = self._extract_abstract_from_markdown(markdown_content)

        # For LLM processing, use first 2000 characters to focus on metadata (title, authors, year, venue)
        # Abstract is already extracted separately
        content_for_llm = (
            markdown_content[:2000]
            if len(markdown_content) > 2000
            else markdown_content
        )

        try:
            # Initialize OpenAI client
            if not hasattr(settings, "OPENAI_API_KEY") or not settings.OPENAI_API_KEY:
                logger.error("OpenAI API key is not configured")
                return {
                    "title": None,
                    "authors": None,
                    "abstract": abstract,
                    "year": None,
                    "venue": None,
                }

            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Use structured outputs to extract metadata
            response = client.responses.parse(
                model="gpt-4o-2024-08-06",
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert at structured data extraction from research papers. "
                            "Extract metadata from the provided markdown text. "
                            "Only extract information that is explicitly present in the text. "
                            "Do not fabricate or infer any information. "
                            "If a field is not found, set it to null. "
                            "For authors, extract all author names as a list. "
                            "For year, extract only the 4-digit publication year if present. "
                            "For venue, extract the conference or journal name if mentioned."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Extract metadata from this research paper markdown:\n\n{content_for_llm}",
                    },
                ],
                text_format=ResearchPaperMetadata,
            )

            # Get parsed output
            metadata = response.output_parsed

            # Combine LLM-extracted metadata with separately extracted abstract
            result = {
                "title": metadata.title,
                "authors": metadata.authors,
                "abstract": abstract
                or metadata.abstract,  # Use separately extracted abstract if available
                "year": metadata.year,
                "venue": metadata.venue,
            }

            logger.info(
                "Extracted metadata: title=%s, authors=%s, year=%s, venue=%s, abstract_length=%d",
                result["title"],
                len(result["authors"]) if result["authors"] else 0,
                result["year"],
                result["venue"],
                len(result["abstract"]) if result["abstract"] else 0,
            )

            return result

        except Exception as e:
            logger.exception(
                "Failed to extract metadata using LLM: %s. Falling back to abstract extraction only.",
                str(e),
            )
            # Fallback: return only abstract if LLM fails
            return {
                "title": None,
                "authors": None,
                "abstract": abstract,
                "year": None,
                "venue": None,
            }


# Create singleton instance
paper_service = PaperService()
