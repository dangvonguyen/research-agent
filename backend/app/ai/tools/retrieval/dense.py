"""Vector-based retrieval tool to find relevant context with relevance ranking."""

import logging

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.rag_service import RAGService
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class DenseRetrieverInput(BaseModel):
    """Input schema for DenseRetrieverTool."""

    query: str = Field(description="The query to retrieve relevant context for")
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to retrieve (1-50)",
    )
    metadata_filter: str | None = Field(
        default=None,
        description=("Optional metadata filter expression using Zilliz syntax."),
    )


class DenseRetrieverTool(BaseTool):
    """Retrieve document chunks using semantic search.

    Performs vector-based retrieval with relevance ranking. Intended for queries
    where semantic similarity is required to find relevant context.

    Typical use cases:
    - Find semantically similar passages across papers or collections
    - Support question answering, summarization, or analysis workflows
    - Combine semantic search with optional metadata or collection filters

    Not recommended when:
    - Exact-match or strictly structured filtering is required
    - The query is best expressed as known metadata constraints
    """

    name = "semantic_search"
    input_schema = DenseRetrieverInput
    description = """Semantic vector search over document chunks with relevance ranking.

Use when:
- The query requires semantic similarity (QA, summarization, finding related passages)
- Keywords alone are insufficient
- You need ranked contextual chunks with metadata

Do NOT use when:
- You only need exact-match or purely metadata-based filtering

Metadata filtering (optional):
- Supported fields: paper_id, paper_title, authors, venue, year, section_name, section_index, chunk_index, chunk_id
- Never invent field names

Filter syntax:
- Zilliz boolean expressions
- Operators: AND / OR / NOT
- String values must use double quotes

Example:
year > 2020 AND venue == "ACL"
"""

    def __init__(self, rag_service: RAGService):
        """Initialize DenseRetrieverTool.

        Args:
            rag_service: RAGService instance for performing retrieval
        """
        self.rag_service = rag_service

    async def arun(
        self,
        query: str,
        top_k: int = 10,
        metadata_filter: str | None = None,
    ) -> ToolOutput:
        """Retrieve relevant chunks without synthesis.

        Args:
            query: The query to retrieve relevant context for
            top_k: Maximum number of chunks to retrieve (default: 10)
            metadata_filter: Optional filter expression string (e.g., 'year == 2023')

        Returns:
            ToolOutput with JSON containing chunks and metadata
        """
        try:
            # Retrieve context only
            chunks = await self.rag_service.retrieve_chunks(
                query=query,
                top_k=top_k,
                metadata_filter=metadata_filter,
            )

            # Format chunks for JSON output
            formatted_chunks = [
                {
                    "text": chunk["text"],
                    "score": round(chunk["score"], 4),
                    "metadata": {
                        "chunk_id": chunk["metadata"].get("chunk_id", ""),
                        "paper_id": chunk["metadata"].get("paper_id", ""),
                        "paper_title": chunk["metadata"].get("paper_title", ""),
                        "authors": chunk["metadata"].get("authors", []),
                        "venue": chunk["metadata"].get("venue", ""),
                        "year": chunk["metadata"].get("year", None),
                        "section_name": chunk["metadata"].get("section_name", ""),
                        "section_index": chunk["metadata"].get("section_index", 0),
                        "chunk_index": chunk["metadata"].get("chunk_index", 0),
                    },
                }
                for chunk in chunks
            ]

            # Prepare response
            response_data = {
                "count": len(formatted_chunks),
                "records": formatted_chunks,
            }

            logger.debug(
                "DenseRetrieverTool completed: %d chunks for query: %s",
                len(formatted_chunks),
                query,
            )

            return ToolOutput(type="json", value=response_data)

        except Exception as e:
            logger.exception("DenseRetrieverTool failed: %s", str(e))
            error_data = {
                "error": "semantic_search_error",
                "message": "An internal error occurred while performing semantic search.",
                "query": query,
            }
            return ToolOutput(type="error-json", value=error_data)
