import asyncio
import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.ai.prompts import SECTION_SELECTION_PROMPT, SECTION_SELECTION_PROMPT_SINGLE
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


async def get_section_names_for_papers_async(
    paper_ids: list[str],
) -> dict[str, list[str]]:
    """Get all unique section names for multiple papers in parallel.

    Args:
        paper_ids: List of paper IDs to get section names for

    Returns:
        Dictionary mapping paper_id to list of section names
    """
    # Process all papers in parallel using asyncio.to_thread for sync functions
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, get_section_names_for_paper, paper_id)
        for paper_id in paper_ids
    ]
    section_names_list = await asyncio.gather(*tasks)

    # Combine results
    result: dict[str, list[str]] = {}
    for paper_id, section_names in zip(paper_ids, section_names_list, strict=True):
        result[paper_id] = section_names

    logger.info(
        "Extracted section names for %d papers (parallel)",
        len(paper_ids),
    )

    return result


def get_section_names_for_papers(
    paper_ids: list[str],
) -> dict[str, list[str]]:
    """Get all unique section names for multiple papers (synchronous version).

    Args:
        paper_ids: List of paper IDs to get section names for

    Returns:
        Dictionary mapping paper_id to list of section names
    """
    result: dict[str, list[str]] = {}

    for paper_id in paper_ids:
        result[paper_id] = get_section_names_for_paper(paper_id)

    logger.info(
        "Extracted section names for %d papers",
        len(paper_ids),
    )

    return result


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


async def select_relevant_sections(
    section_names_by_paper: dict[str, list[str]], schema: dict[str, Any]
) -> dict[str, list[str]]:
    """Select section names that are semantically aligned with the schema requirements.

    This function uses an LLM to analyze section names and determine which sections
    are likely to contain information required by the schema. The selection is based
    solely on section titles, not content.

    Args:
        section_names_by_paper: Dictionary mapping paper_id to list of section names
        schema: Schema dict defining what information to extract (e.g., {'data': str, 'evaluation metric': str})

    Returns:
        Dictionary mapping paper_id to list of selected section names that are
        semantically aligned with the schema requirements
    """
    # Build the prompt for LLM
    schema_str = json.dumps(schema, indent=2)

    # Format section names by paper for the prompt
    sections_str = ""
    for paper_id, section_names in section_names_by_paper.items():
        sections_str += f"\nPaper ID: {paper_id}\n"
        sections_str += (
            f"Sections: {', '.join(section_names) if section_names else '(none)'}\n"
        )

    prompt = SECTION_SELECTION_PROMPT.format(
        schema_str=schema_str, sections_str=sections_str
    )

    try:
        # Use structured output: get response and validate with Pydantic model
        response = await default_llm.acomplete(prompt)
        response_text = response.text.strip()

        # Remove any markdown code blocks if present
        if response_text.startswith("```"):
            # Extract JSON from code block
            lines = response_text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        # Parse JSON and validate with Pydantic model for structured output
        parsed_data = json.loads(response_text)
        structured_response = SectionSelectionResponse(selected_sections=parsed_data)

        # Extract the structured data
        selected_sections = structured_response.selected_sections

        # Validate and ensure all paper_ids are present
        result: dict[str, list[str]] = {}
        for paper_id in section_names_by_paper:
            if paper_id in selected_sections:
                # Validate that selected sections actually exist in the original list
                available_sections = set(section_names_by_paper[paper_id])
                selected = selected_sections[paper_id]
                # Filter to only include sections that actually exist
                result[paper_id] = [s for s in selected if s in available_sections]
            else:
                # If paper_id not in response, return empty list
                result[paper_id] = []

        logger.info(
            "Selected relevant sections for %d papers using schema",
            len(result),
        )

        return result

    except Exception as e:
        logger.exception("Failed to select relevant sections: %s", str(e))
        # Fallback: return empty selections for all papers
        return {paper_id: [] for paper_id in section_names_by_paper}


async def select_relevant_sections_parallel(
    section_names_by_paper: dict[str, list[str]], schema: dict[str, Any]
) -> dict[str, list[str]]:
    """Select section names that are semantically aligned with the schema requirements for multiple papers in parallel.

    This function uses an LLM to analyze section names and determine which sections
    are likely to contain information required by the schema. The selection is based
    solely on section titles, not content. Each paper is processed in parallel.

    Args:
        section_names_by_paper: Dictionary mapping paper_id to list of section names
        schema: Schema dict defining what information to extract (e.g., {'data': str, 'evaluation metric': str})

    Returns:
        Dictionary mapping paper_id to list of selected section names that are
        semantically aligned with the schema requirements
    """
    # Process all papers in parallel
    tasks = [
        select_relevant_sections_for_paper(paper_id, section_names, schema)
        for paper_id, section_names in section_names_by_paper.items()
    ]

    selected_sections_list = await asyncio.gather(*tasks)

    # Combine results
    result: dict[str, list[str]] = {}
    for paper_id, selected_sections in zip(
        section_names_by_paper.keys(), selected_sections_list, strict=True
    ):
        result[paper_id] = selected_sections

    logger.info(
        "Selected relevant sections for %d papers using schema (parallel)",
        len(result),
    )

    return result


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
