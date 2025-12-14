import logging

from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.rag_service import RAGService
from app.types import ToolResultOutput as ToolOutput

logger = logging.getLogger(__name__)


class DenseRetrievalInput(BaseModel):
    """Input schema for DenseRetrievalTool."""

    query: str = Field(description="The query to retrieve relevant context for")
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to retrieve (1-50)",
    )
    collection_names: list[str] | None = Field(
        default=None,
        description="Optional list of collection names to filter the retrieval",
    )


class DenseRetrievalTool(BaseTool):
    """Tool for retrieving relevant paper chunks without synthesis.

    This tool performs pure retrieval without response generation:
    - Retrieves relevant chunks via semantic search
    - Filters by similarity threshold
    - Returns raw chunks with metadata and scores
    """

    name = "semantic_search"
    description = (
        "Retrieve relevant paper chunks for a query without synthesizing a response. "
        "Use this tool when you need raw context from papers without an AI-generated answer. "
        "The tool performs semantic search and returns matching chunks with metadata "
        "(paper title, authors, venue, section name) and relevance scores. "
    )
    input_schema = DenseRetrievalInput

    def __init__(self, rag_service: RAGService):
        """Initialize DenseRetrievalTool.

        Args:
            rag_service: RAGService instance for performing retrieval
        """
        self.rag_service = rag_service

    async def arun(
        self,
        query: str,
        collection_names: list[str] | None = None,
        top_k: int = 10,
    ) -> ToolOutput:
        """Retrieve relevant chunks without synthesis.

        Args:
            query: The query to retrieve relevant context for
            top_k: Maximum number of chunks to retrieve (default: 10)
            collection_names: Optional list of collection names to filter by

        Returns:
            ToolOutput with JSON containing chunks and metadata
        """
        try:
            # Retrieve context only
            chunks = await self.rag_service.retrieve_chunks(
                query=query,
                collection_names=collection_names,
                top_k=top_k,
            )

            # Format chunks for JSON output
            formatted_chunks = [
                {
                    "text": chunk["text"],
                    "relevance_score": round(chunk["score"], 4),
                    "metadata": {
                        "paper_id": chunk["metadata"].get("paper_id", ""),
                        "paper_title": chunk["metadata"].get("paper_title", ""),
                        "authors": chunk["metadata"].get("authors", []),
                        "venue": chunk["metadata"].get("venue", ""),
                        "year": chunk["metadata"].get("year", None),
                        "section_name": chunk["metadata"].get("section_name", ""),
                        "section_index": chunk["metadata"].get("section_index", 0),
                        "chunk_index": chunk["metadata"].get("chunk_index", 0),
                        "collection_names": chunk["metadata"].get(
                            "collection_names", []
                        ),
                    },
                }
                for chunk in chunks
            ]

            # Prepare response
            response_data = {
                "query": query,
                "chunks": formatted_chunks,
                "num_chunks": len(formatted_chunks),
            }

            logger.info(
                "DenseRetrievalTool completed: %d chunks for query: %s",
                len(formatted_chunks),
                query[:100],
            )

            return ToolOutput(
                type="json",
                value=response_data,
            )

        except Exception as e:
            logger.exception("DenseRetrievalTool failed: %s", str(e))
            error_data = {
                "error": str(e),
                "query": query,
                "message": "Failed to retrieve context. Please try again.",
            }
            return ToolOutput(
                type="error-json",
                value=error_data,
            )
