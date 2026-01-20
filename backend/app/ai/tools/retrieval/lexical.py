"""Keyword-based retrieval tool using BM25 algorithm for exact term matching."""

import logging

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.zilliz_service import zilliz_service
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class LexicalRetrievalInput(BaseModel):
    """Input schema for LexicalRetrieverTool."""

    query: str = Field(
        description="Keywords or terms to search for (e.g., 'ResNet', 'BERT', 'attention mechanism')"
    )
    top_k: int = Field(
        default=30,
        ge=20,
        le=50,
        description="Maximum number of matching chunks to retrieve (20-50)",
    )
    metadata_filter: str | None = Field(
        default=None,
        description=("Optional metadata filter expression using Zilliz syntax."),
    )


class LexicalRetrieverTool(BaseTool):
    """Retrieve document chunks using BM25 full-text search algorithm.

    Uses BM25 ranking algorithm for term-based retrieval with relevance scoring.
    Ideal for queries requiring precise keyword matching with statistical ranking.
    """

    name = "keyword_search"
    input_schema = LexicalRetrievalInput
    description = """BM25 full-text search over document chunks with relevance ranking.

Use when:
- You need to find specific keywords, method names, or technical terms
- Multi-term queries where term weighting matters
- Exact keyword matching is more important than semantic similarity

Do NOT use when:
- Broad semantic or conceptual search is sufficient
- Only metadata-based filtering is needed

Query rules:
- Use plain keywords, no operators, or special syntax
- Do not include double quotes

Metadata filtering (optional):
- Supported fields: paper_id, paper_title, authors, venue, year, section_name, section_index, chunk_index, chunk_id
- Never invent field names

Filter syntax:
- Zilliz boolean expressions
- Operators: AND / OR / NOT
- String values must use double quotes

Example:
- query: reinforcement learning, human feedback
- metadata_filter: year > 2020 AND venue == "ACL"
"""

    async def arun(
        self,
        query: str,
        top_k: int = 10,
        metadata_filter: str | None = None,
    ) -> ToolOutput:
        """Retrieve chunks using BM25 full-text search algorithm.

        Args:
            query: Keywords or terms to search for
            top_k: Maximum number of chunks to retrieve
            metadata_filter: Optional filter expression string

        Returns:
            ToolOutput with JSON containing BM25-ranked chunks and scores
        """
        try:
            # Perform BM25 search
            search_results = zilliz_service.bm25_search(
                query_text=query,
                limit=top_k,
                filter_expr=metadata_filter,
                output_fields=[
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
                ],
            )

            # Format results for output
            formatted_chunks = []
            for result in search_results:
                entity = result.get("entity", {})
                distance = result.get("distance", 0.0)

                # For BM25, higher distance = better match
                similarity_score = distance

                chunk_data = {
                    "text": entity.get("chunk_content", ""),
                    "score": round(similarity_score, 4),
                    "metadata": {
                        "chunk_id": entity.get("chunk_id", ""),
                        "paper_id": entity.get("paper_id", ""),
                        "paper_title": entity.get("paper_title", ""),
                        "authors": entity.get("authors", []),
                        "venue": entity.get("venue", ""),
                        "year": entity.get("year", None),
                        "section_name": entity.get("section_name", ""),
                        "section_index": entity.get("section_index", 0),
                        "chunk_index": entity.get("chunk_index", 0),
                    },
                }
                formatted_chunks.append(chunk_data)

            # Prepare response
            response_data = {
                "count": len(formatted_chunks),
                "records": formatted_chunks,
            }

            logger.debug(
                "LexicalRetrieverTool: %d BM25 results for query: %s",
                len(formatted_chunks),
                query,
            )

            return ToolOutput(type="json", value=response_data)

        except Exception as e:
            logger.exception("LexicalRetrieverTool error: %s", str(e))
            error_data = {
                "error": "lexical_search_error",
                "message": "An internal error occurred while performing lexical search.",
                "query": query,
            }
            return ToolOutput(type="error-json", value=error_data)
