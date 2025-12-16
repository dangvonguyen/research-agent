import asyncio
import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.ai.actions.section_names import (
    get_paper_content_from_sections,
    get_section_names_for_paper,
    select_relevant_sections_for_paper,
)
from app.ai.prompts import STRUCTURED_EXTRACTION_PROMPT
from app.ai.tools.base import BaseTool
from app.services.llm_service import default_llm
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class StructuredExtractorInput(BaseModel):
    """Input schema for StructuredExtractorTool."""

    paper_ids: list[str] = Field(
        description="List of paper IDs to extract section names from"
    )
    extraction_schema: dict[str, Any] = Field(
        description=(
            "Schema defining what information to extract from papers. "
            "Example: {'data': str, 'evaluation metric': str}. "
            "This represents the parts of papers the user wants to know about."
        )
    )


class StructuredExtractorTool(BaseTool):
    """Tool for extracting structured information from papers based on a schema.

    This tool extracts structured information from papers by:
    1. Getting section names for each paper
    2. Selecting relevant sections based on the schema
    3. Retrieving content from selected sections
    4. Using LLM to extract structured data matching the schema
    """

    name = "structured_extractor"
    description = (
        "Extract structured information from papers based on a schema. "
        "Takes a list of paper IDs and a schema (dict) representing what information "
        "to extract. Returns extracted structured data for each paper matching the schema. "
        "Use this tool when you need to extract specific types of information from papers "
        "(e.g., data, evaluation metrics, methods, results)."
    )
    input_schema = StructuredExtractorInput

    def __init__(self):
        """Initialize StructuredExtractorTool."""
        pass

    async def _process_single_paper(
        self,
        paper_id: str,
        extraction_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a single paper through all steps sequentially.

        This function handles the complete flow for one paper:
        1. Get section names
        2. Select relevant sections
        3. Get paper content from selected sections
        4. Extract structured data using LLM

        Args:
            paper_id: Paper ID to process
            extraction_schema: Schema defining what information to extract

        Returns:
            Dictionary with paper_id as key and extracted data as value
        """
        try:
            logger.info("[Paper %s] Starting processing...", paper_id)

            # Step 1: Get section names for this paper
            loop = asyncio.get_event_loop()
            section_names = await loop.run_in_executor(
                None, get_section_names_for_paper, paper_id
            )
            logger.debug(
                "Retrieved %d section names for paper_id: %s",
                len(section_names),
                paper_id,
            )

            if not section_names:
                logger.warning("No sections found for paper_id: %s", paper_id)
                return {paper_id: {}}

            # Step 2: Select relevant sections based on schema
            step2_start_time = time.perf_counter()
            selected_sections = await select_relevant_sections_for_paper(
                paper_id, section_names, extraction_schema
            )
            step2_duration = time.perf_counter() - step2_start_time
            logger.info(
                "[Paper %s] Step 2 (select sections) took %.3f seconds",
                paper_id,
                step2_duration,
            )
            logger.debug(
                "Selected %d relevant sections for paper_id: %s",
                len(selected_sections),
                paper_id,
            )

            if not selected_sections:
                logger.warning(
                    "No relevant sections selected for paper_id: %s", paper_id
                )
                return {paper_id: {}}

            # Step 3: Get paper content from selected sections
            paper_content = await loop.run_in_executor(
                None, get_paper_content_from_sections, paper_id, selected_sections
            )

            if not paper_content:
                logger.warning(
                    "No content found for paper_id: %s with sections: %s",
                    paper_id,
                    selected_sections,
                )
                return {paper_id: {}}

            logger.debug(
                "[Paper %s] Retrieved %d characters of content",
                paper_id,
                len(paper_content),
            )

            # Step 4: Use LLM to extract structured data
            try:
                schema_str = json.dumps(extraction_schema, indent=2)
                prompt = STRUCTURED_EXTRACTION_PROMPT.format(
                    schema_str=schema_str, paper_content=paper_content
                )

                # Measure LLM call time
                llm_start_time = time.perf_counter()
                logger.info(
                    "[Paper %s] LLM call started at %.3f", paper_id, llm_start_time
                )

                response = await default_llm.acomplete(prompt)

                llm_end_time = time.perf_counter()
                llm_duration = llm_end_time - llm_start_time
                logger.info(
                    "[Paper %s] LLM call completed in %.3f seconds",
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

                # Parse JSON response
                extracted_data = json.loads(response_text)
                logger.debug("Extracted structured data for paper_id: %s", paper_id)
                logger.debug(
                    "[Paper %s] Extracted data: %s",
                    paper_id,
                    json.dumps(extracted_data, indent=2),
                )

                return {paper_id: extracted_data}

            except Exception as e:
                logger.warning(
                    "Failed to extract structured data for paper_id %s: %s",
                    paper_id,
                    str(e),
                )
                return {paper_id: {}}

        except Exception as e:
            logger.exception("Failed to process paper_id %s: %s", paper_id, str(e))
            return {paper_id: {}}

    async def _extract_paper_data(
        self,
        paper_id: str,
        selected_sections: list[str],
        extraction_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract structured data for a single paper.

        Args:
            paper_id: Paper ID to extract information from
            selected_sections: List of selected section names for this paper
            extraction_schema: Schema defining what information to extract

        Returns:
            Dictionary with paper_id as key and extracted data as value
        """
        if not selected_sections:
            logger.warning("No relevant sections selected for paper_id: %s", paper_id)
            return {paper_id: {}}

        # Get paper content from selected sections
        paper_content = get_paper_content_from_sections(paper_id, selected_sections)

        if not paper_content:
            logger.warning(
                "No content found for paper_id: %s with sections: %s",
                paper_id,
                selected_sections,
            )
            return {paper_id: {}}

        # Use LLM to extract structured data
        try:
            schema_str = json.dumps(extraction_schema, indent=2)
            prompt = STRUCTURED_EXTRACTION_PROMPT.format(
                schema_str=schema_str, paper_content=paper_content
            )

            response = await default_llm.acomplete(prompt)
            response_text = response.text.strip()

            # Remove any markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                lines = lines[1:]  # Remove first line
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # Remove last line
                response_text = "\n".join(lines).strip()

            # Parse JSON response
            extracted_data = json.loads(response_text)
            logger.debug("Extracted structured data for paper_id: %s", paper_id)
            return {paper_id: extracted_data}

        except Exception as e:
            logger.warning(
                "Failed to extract structured data for paper_id %s: %s",
                paper_id,
                str(e),
            )
            return {paper_id: {}}

    async def arun(
        self,
        paper_ids: list[str],
        extraction_schema: dict[str, Any],
    ) -> ToolOutput:
        """Extract structured information from papers based on schema.

        Each paper is processed as an independent parallel task that runs:
        1. Get section names
        2. Select relevant sections
        3. Get paper content
        4. Extract structured data

        Args:
            paper_ids: List of paper IDs to extract information from
            extraction_schema: Schema defining what information to extract (e.g., {'data': str, 'evaluation_metric': str})

        Returns:
            ToolOutput with JSON containing extracted structured data for each paper
        """
        try:
            logger.info("Starting processing for %d papers in parallel", len(paper_ids))
            logger.debug(
                "Extraction schema: %s", json.dumps(extraction_schema, indent=2)
            )

            # Create a parallel task for each paper_id
            # Each task will run: get_section_names -> select_sections -> get_content -> extract_data
            tasks = [
                self._process_single_paper(paper_id, extraction_schema)
                for paper_id in paper_ids
            ]

            # Process all papers in parallel
            main_start_time = time.perf_counter()
            logger.info("[Main] Started parallel processing at %.3f", main_start_time)

            results = await asyncio.gather(*tasks)

            main_end_time = time.perf_counter()
            main_duration = main_end_time - main_start_time
            logger.info(
                "[Main] Completed parallel processing in %.3f seconds",
                main_duration,
            )

            # Combine results: each result is {paper_id: extracted_data}
            extracted_data_by_paper: dict[str, dict[str, Any]] = {}
            for result in results:
                paper_id = next(iter(result.keys()))
                extracted_data_by_paper.update(result)
                logger.debug("Completed processing for paper_id: %s", paper_id)

            logger.debug(
                "Extracted data by paper: %s",
                json.dumps(extracted_data_by_paper, indent=2),
            )

            logger.info(
                "StructuredExtractorTool completed: processed %d papers",
                len(paper_ids),
            )

            # Prepare response - format: {paper_id: {extracted_data}}
            response_data = {
                "paper_ids": paper_ids,
                "schema": extraction_schema,
                "extracted_data": extracted_data_by_paper,
            }
            logger.debug("Response data: %s", json.dumps(response_data, indent=2))

            return ToolOutput(
                type="json",
                value=response_data,
            )

        except Exception as e:
            logger.exception("StructuredExtractorTool failed: %s", str(e))
            error_data = {
                "error": str(e),
                "paper_ids": paper_ids,
                "schema": extraction_schema,
                "message": "Failed to extract structured information. Please try again.",
            }
            return ToolOutput(
                type="error-json",
                value=error_data,
            )
