"""Metadata-based chunk retrieval tool for filtering without vector search."""

import logging

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.zilliz_service import zilliz_service
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class MetadataRetrieverInput(BaseModel):
    """Input schema for MetadataRetrieverTool."""

    metadata_filter: str = Field(
        description=(
            "Metadata filter expression using Zilliz syntax. "
            "Examples: "
            "'year == 2023', "
            "'paper_id == \"uuid-here\"', "
            "'year >= 2020 AND year <= 2023', "
            "'json_contains(collection_names, \"AI\")'"
        )
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of chunks to retrieve (1-100)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of chunks to skip for pagination",
    )
    output_fields: list[str] | None = Field(
        default=None,
        description="Optional list of specific fields to return in results",
    )


class MetadataRetrieverTool(BaseTool):
    """Tool for retrieving chunks using metadata filters only.

    This tool filters chunks by metadata fields without performing semantic similarity
    search. More efficient when you know exactly what you're looking for based on
    metadata.

    Use cases:
    - Get all chunks from a specific paper
    - Find chunks from a specific year or venue
    - Filter by author, collection, or section
    - Retrieve chunks matching complex metadata criteria
    """

    name = "metadata_search"
    description = (
        "Retrieve chunks by filtering metadata fields without semantic search. "
        "Use this when you need chunks matching specific metadata criteria "
        "(year, venue, paper_id, collection, section, etc.) without relevance ranking. "
        "More efficient than semantic search for known metadata values. "
    )
    input_schema = MetadataRetrieverInput

    async def arun(
        self,
        metadata_filter: str,
        limit: int = 10,
        offset: int = 0,
        output_fields: list[str] | None = None,
    ) -> ToolOutput:
        """Retrieve chunks using metadata filters only.

        Args:
            metadata_filter: Metadata filter expression
            limit: Maximum number of chunks to retrieve
            offset: Number of chunks to skip for pagination
            output_fields: Optional list of fields to return

        Returns:
            ToolOutput with JSON containing filtered chunks
        """
        try:
            # Default output fields if not specified
            if output_fields is None:
                output_fields = [
                    "chunk_id",
                    "paper_id",
                    "paper_title",
                    "authors",
                    "venue",
                    "year",
                    "collection_names",
                    "section_name",
                    "section_index",
                    "chunk_index",
                    "chunk_content",
                    "image_path",
                ]

            # Query using metadata filter only
            results = zilliz_service.query(
                filter=metadata_filter,
                limit=limit,
                offset=offset,
                output_fields=output_fields,
            )

            # Format chunks for output - only include requested fields
            formatted_chunks = []
            for result in results:
                metadata = {}
                for field in output_fields:
                    if field in result:
                        metadata[field] = result[field]

                chunk_data = {
                    "metadata": metadata,
                }
                formatted_chunks.append(chunk_data)

            # Prepare response
            response_data = {
                "count": len(formatted_chunks),
                "records": formatted_chunks,
            }

            logger.debug(
                "MetadataRetrieverTool: Retrieved %d chunks with filter: %s",
                len(formatted_chunks),
                metadata_filter,
            )

            return ToolOutput(type="json", value=response_data)

        except Exception as e:
            logger.exception("MetadataRetrieverTool failed: %s", str(e))
            error_data = {
                "error": str(e),
                "filter": metadata_filter,
                "message": "Failed to filter chunks by metadata. Please check your filter expression syntax.",
            }
            return ToolOutput(type="error-json", value=error_data)
