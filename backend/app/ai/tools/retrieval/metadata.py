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
        description=("Metadata filter expression using Zilliz syntax.")
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
    """Retrieve document chunks using metadata-only filtering.

    This tool performs structured retrieval using metadata fields and does NOT
    use vector similarity or relevance ranking. Results are returned in storage
    order and are best suited for exact-match or constrained queries.

    Typical use cases:
    - Retrieve all chunks belonging to a specific paper or document
    - Filter content by year, venue, author, or section
    - Fetch sections or ranges of chunks using pagination
    - Apply complex boolean metadata expressions supported by Zilliz

    Not recommended when:
    - The query is semantic or exploratory in nature
    - Relevance ranking or similarity scoring is required
    """

    name = "metadata_search"
    input_schema = MetadataRetrieverInput
    description = """Structured metadata-only retrieval over document chunks. No semantic search and no relevance ranking; results follow storage order.

Use when:
- You know exact metadata constraints (paper, year, venue, section)
- You need deterministic or paginated access to chunks
- You want efficient filtering without vector similarity

Do NOT use when:
- The query is semantic or exploratory
- Relevance ranking or similarity scoring is needed

Metadata filtering:
- Supported fields: paper_id, paper_title, authors, venue, year, section_name, section_index, chunk_index, chunk_id
- Do not invent field names.

Filter syntax:
- Zilliz boolean expressions
- Operators: AND / OR / NOT
- String values must use double quotes

Example:
paper_id == "abc123" AND section_name == "Methods"
"""

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
                "error": "metadata_search_error",
                "message": "Failed to filter chunks by metadata. Please check your filter expression syntax.",
                "filter": metadata_filter,
            }
            return ToolOutput(type="error-json", value=error_data)
