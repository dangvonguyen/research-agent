import logging
from typing import Any
from uuid import UUID

from llama_index.core import get_response_synthesizer
from llama_index.core.llms import LLM
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine

from app.services.retriever_service import ZillizRetriever
from app.types import CitationMetadata, RAGSearchResult

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG (Retrieval-Augmented Generation) operations.

    Responsibilities:
    - Indexing: Papers, chunks, metadata (handled by existing services)
    - Retrieval: Semantic search via ZillizRetriever
    - Synthesis: Response generation with citations
    """

    def __init__(self, llm: LLM):
        """Initialize RAGService.

        Args:
            llm: Language model for response synthesis
            similarity_cutoff: Minimum similarity score threshold (default: 0.7)
        """
        self.llm = llm

    def create_query_engine(
        self,
        top_k: int = 10,
        similarity_cutoff: float = 0.7,
        collection_names: list[str] | None = None,
    ) -> RetrieverQueryEngine:
        """Create a query engine with retriever and response synthesizer.

        Args:
            collection_names: Optional list of collection names to filter by
            top_k: Maximum number of chunks to retrieve (default: 10)

        Returns:
            Configured RetrieverQueryEngine
        """
        # Create retriever
        retriever = ZillizRetriever(
            collection_names=collection_names,
            top_k=top_k,
        )

        # Create postprocessor to filter low-relevance results
        similarity_postprocessor = SimilarityPostprocessor(
            similarity_cutoff=similarity_cutoff
        )

        # Create response synthesizer
        response_synthesizer = get_response_synthesizer(
            llm=self.llm,
            response_mode="compact",  # Compact mode for efficient synthesis
        )

        # Create query engine
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
            node_postprocessors=[similarity_postprocessor],
        )

        return query_engine

    async def run_rag_query(
        self,
        query: str,
        top_k: int = 10,
        similarity_cutoff: float = 0.7,
        collection_names: list[str] | None = None,
    ) -> RAGSearchResult:
        """Perform full RAG search: retrieval + synthesis with citations.

        Args:
            query: Search query
            collection_names: Optional list of collection names to filter by
            top_k: Maximum number of chunks to retrieve (default: 10)

        Returns:
            RAGSearchResult with synthesized response and citations
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to run_rag_query")
            return RAGSearchResult(
                query=query,
                response="No query provided",
                citations=[],
                source_nodes=[],
            )

        try:
            # Create query engine
            query_engine = self.create_query_engine(
                top_k=top_k,
                similarity_cutoff=similarity_cutoff,
                collection_names=collection_names,
            )

            # Execute query
            response = await query_engine.aquery(query)

            # Extract citations from source nodes
            citations = []
            source_nodes_data = []

            if response.source_nodes:
                for node_with_score in response.source_nodes:
                    node = node_with_score.node
                    score = node_with_score.score or 0.0

                    # Extract metadata
                    metadata = node.metadata or {}
                    paper_id_str = metadata.get("paper_id", "")

                    # Convert paper_id to UUID if valid
                    try:
                        paper_id = UUID(paper_id_str) if paper_id_str else None
                    except (ValueError, AttributeError):
                        paper_id = None

                    if not paper_id:
                        logger.warning("Invalid or missing paper_id in node metadata")
                        continue

                    # Create citation
                    citation = CitationMetadata(
                        paper_id=paper_id,
                        title=metadata.get("paper_title", ""),
                        authors=metadata.get("authors", []),
                        venue=metadata.get("venue", ""),
                        year=metadata.get("year", None),
                        section_name=metadata.get("section_name", ""),
                        chunk_content=node.text,
                        relevance_score=score,
                    )
                    citations.append(citation)

                    # Store source node data
                    source_nodes_data.append(
                        {
                            "text": node.text,
                            "score": score,
                            "metadata": metadata,
                        }
                    )

            logger.info(
                "RAG search completed: %d citations for query: %s",
                len(citations),
                query[:100],
            )

            return RAGSearchResult(
                query=query,
                response=str(response),
                citations=citations,
                source_nodes=source_nodes_data,
            )

        except Exception as e:
            logger.exception("Failed to perform RAG search: %s", str(e))
            return RAGSearchResult(
                query=query,
                response=f"Error performing search: {e!s}",
                citations=[],
                source_nodes=[],
            )

    async def retrieve_chunks(
        self,
        query: str,
        top_k: int = 10,
        collection_names: list[str] | None = None,
        metadata_filters: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant chunks without synthesis.

        Args:
            query: Search query (can be empty string if only filtering by metadata)
            collection_names: Optional list of collection names to filter by
            top_k: Maximum number of chunks to retrieve (default: 10)
            metadata_filters: Optional filter expression string (e.g., 'year == 2023')

        Returns:
            List of retrieved chunks with metadata
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to retrieve_context_only")
            return []

        try:
            # Create retriever
            retriever = ZillizRetriever(
                top_k=top_k,
                collection_names=collection_names,
                metadata_filters=metadata_filters,
            )

            # Retrieve chunks
            nodes_with_scores = await retriever.aretrieve(query)

            # Apply similarity filter
            # filtered_nodes = [
            #     nws
            #     for nws in nodes_with_scores
            #     if (nws.score or 0.0) >= self.similarity_cutoff
            # ]
            filtered_nodes = list(nodes_with_scores)

            # Convert to dictionary format
            chunks = []
            for node_with_score in filtered_nodes:
                node = node_with_score.node
                score = node_with_score.score or 0.0

                chunks.append(
                    {
                        "text": node.text,
                        "score": score,
                        "metadata": node.metadata or {},
                    }
                )

            logger.info(
                "Retrieved %d chunks for query for rag: %s",
                len(chunks),
                query[:100],
            )

            return chunks

        except Exception as e:
            logger.exception("Failed to retrieve context: %s", str(e))
            return []
