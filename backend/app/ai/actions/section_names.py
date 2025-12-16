import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.ai.prompts import SECTION_SELECTION_PROMPT_SINGLE
from app.services.llm_service import default_llm
from app.services.zilliz_service import zilliz_service

logger = logging.getLogger(__name__)


class SectionSelectionResponse(BaseModel):
    """Structured output model for section selection."""

    selected_sections: dict[str, list[str]] = Field(
        description="Dictionary mapping paper_id to list of selected section names"
    )


def get_section_names_for_paper(paper_id: str) -> list[str]:
    """Get all unique section names for a single paper.

    Args:
        paper_id: The paper ID to get section names for

    Returns:
        List of unique section names for the paper, sorted alphabetically
    """
    try:
        # Query Zilliz for all chunks of this paper
        # Use a filter expression to get chunks by paper_id
        filter_expr = f'paper_id == "{paper_id}"'

        # Query directly using filter expression (no need for dummy vector)
        query_results = zilliz_service.query(
            filter=filter_expr,
            output_fields=["paper_id", "section_name"],
            limit=10000,  # Large limit to get all chunks
        )

        # Extract unique section names
        section_names_set = set()
        for result_item in query_results:
            section_name = result_item.get("section_name", "")
            if section_name:  # Only add non-empty section names
                section_names_set.add(section_name)

        # Convert to sorted list for consistent output
        section_names = sorted(section_names_set)

        logger.debug(
            "Extracted %d section names for paper_id: %s",
            len(section_names),
            paper_id,
        )

        return section_names

    except Exception as e:
        logger.warning(
            "Failed to extract sections for paper_id %s: %s", paper_id, str(e)
        )
        return []


async def select_relevant_sections_for_paper(
    paper_id: str,
    section_names: list[str],
    schema: dict[str, Any],
) -> list[str]:
    """Select section names that are semantically aligned with the schema requirements for a single paper.

    This function uses an LLM to analyze section names and determine which sections
    are likely to contain information required by the schema. The selection is based
    solely on section titles, not content.

    Args:
        paper_id: Paper ID
        section_names: List of section names for this paper
        schema: Schema dict defining what information to extract (e.g., {'data': str, 'evaluation metric': str})

    Returns:
        List of selected section names that are semantically aligned with the schema requirements
    """
    if not section_names:
        logger.warning("No sections available for paper_id: %s", paper_id)
        return []

    # Build the prompt for LLM
    schema_str = json.dumps(schema, indent=2)
    sections_str = ", ".join(section_names) if section_names else "(none)"

    prompt = SECTION_SELECTION_PROMPT_SINGLE.format(
        schema_str=schema_str,
        paper_id=paper_id,
        sections_str=sections_str,
    )

    try:
        # Use structured output: get response and parse JSON array
        llm_start_time = time.perf_counter()
        logger.debug(
            "[Paper %s] LLM call (select sections) started at %.3f",
            paper_id,
            llm_start_time,
        )

        response = await default_llm.acomplete(prompt)

        llm_end_time = time.perf_counter()
        llm_duration = llm_end_time - llm_start_time
        logger.info(
            "[Paper %s] LLM call (select sections) completed in %.3f seconds",
            paper_id,
            llm_duration,
        )

        response_text = response.text.strip()

        # Remove any markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = lines[1:]  # Remove first line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last line
            response_text = "\n".join(lines).strip()

        # Parse JSON array
        selected_sections = json.loads(response_text)

        # Validate that selected sections actually exist in the original list
        available_sections = set(section_names)
        if isinstance(selected_sections, list):
            # Filter to only include sections that actually exist
            result = [s for s in selected_sections if s in available_sections]
        else:
            logger.warning(
                "Invalid response format for paper_id %s: expected list, got %s",
                paper_id,
                type(selected_sections),
            )
            result = []

        logger.debug(
            "Selected %d relevant sections for paper_id: %s",
            len(result),
            paper_id,
        )

        return result

    except Exception as e:
        logger.warning(
            "Failed to select relevant sections for paper_id %s: %s",
            paper_id,
            str(e),
        )
        return []


def get_paper_content_from_sections(paper_id: str, section_names: list[str]) -> str:
    """Get paper content from selected sections, ordered by section_index and chunk_index.

    Args:
        paper_id: The paper ID to get content for
        section_names: List of section names to include

    Returns:
        Joined paper content from the selected sections, ordered correctly
    """
    if not section_names:
        return ""

    try:
        # Build filter expression for paper_id and section names
        # Format: paper_id == "xxx" && (section_name == "Section1" || section_name == "Section2")
        section_filters = " || ".join(
            [f'section_name == "{section}"' for section in section_names]
        )
        filter_expr = f'paper_id == "{paper_id}" && ({section_filters})'

        # Query Zilliz for chunks matching the filter
        query_results = zilliz_service.query(
            filter=filter_expr,
            output_fields=[
                "section_name",
                "section_index",
                "chunk_index",
                "chunk_content",
            ],
            limit=10000,  # Large limit to get all chunks
        )

        # Sort by section_index first, then chunk_index
        sorted_chunks = sorted(
            query_results,
            key=lambda x: (
                x.get("section_index", 0),
                x.get("chunk_index", 0),
            ),
        )

        # Join chunk contents
        paper_content_parts = []
        for chunk in sorted_chunks:
            content = chunk.get("chunk_content", "")
            if content:
                paper_content_parts.append(content)

        paper_content = "\n\n".join(paper_content_parts)

        logger.debug(
            "Extracted %d chunks from %d sections for paper_id: %s",
            len(sorted_chunks),
            len(section_names),
            paper_id,
        )

        return paper_content

    except Exception as e:
        logger.warning(
            "Failed to extract content for paper_id %s: %s", paper_id, str(e)
        )
        return ""
