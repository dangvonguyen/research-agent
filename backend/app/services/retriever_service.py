import logging
import math

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.services.embedding_service import embedding_service
from app.services.zilliz_service import zilliz_service

logger = logging.getLogger(__name__)


class ZillizRetriever(BaseRetriever):
    """Custom LlamaIndex retriever that wraps ZillizService for paper retrieval.

    This retriever:
    - Searches Zilliz vector database via existing ZillizService
    - Returns results as LlamaIndex TextNode objects with metadata
    - Supports collection filtering and section-aware retrieval
    """

    def __init__(
        self,
        collection_names: list[str] | None = None,
        top_k: int = 10,
    ):
        """Initialize ZillizRetriever.

        Args:
            collection_names: Optional list of collection names to filter by
            top_k: Maximum number of results to return (default: 10)
        """
        super().__init__()
        self.collection_names = collection_names
        self.top_k = top_k

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """Retrieve relevant chunks asynchronously.

        Args:
            query_bundle: Query bundle containing the search query

        Returns:
            List of TextNode objects with relevance scores
        """
        query_text = query_bundle.query_str

        if not query_text or not query_text.strip():
            logger.warning("Empty query provided to retriever")
            return []

        try:
            # Generate embedding for query
            query_embedding = await embedding_service.generate_embedding(query_text)

            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []

            # Build filter expression for collection filtering
            filter_expr = None
            if self.collection_names:
                # Build JSON filter for collection_names array field
                # Format: json_contains(collection_names, '"collection_name"')
                collection_filters = [
                    f'json_contains(collection_names, \\"{name}\\")'
                    for name in self.collection_names
                ]
                filter_expr = " || ".join(collection_filters)

            # Search Zilliz
            search_results = zilliz_service.search(
                query_vector=query_embedding,
                limit=self.top_k,
                filter_expr=filter_expr,
                output_fields=[
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
                ],
            )

            # Convert to TextNode objects
            nodes_with_scores = []
            for result in search_results:
                entity = result.get("entity", {})
                distance = result.get("distance", 0.0)

                # Convert L2 distance to similarity score (inverse)
                # Lower distance = higher similarity
                # We'll normalize it to 0-1 range (1 = perfect match, 0 = no match)
                # Using exponential decay: score = exp(-distance)
                similarity_score = math.exp(-distance)

                # Extract metadata
                node_id = str(entity.get("id", entity.get("chunk_id", "")))
                paper_id = entity.get("paper_id", "")
                paper_title = entity.get("paper_title", "")
                authors = entity.get("authors", [])
                venue = entity.get("venue", "")
                year = entity.get("year", None)
                collection_names_field = entity.get("collection_names", [])
                section_name = entity.get("section_name", "")
                section_index = entity.get("section_index", 0)
                chunk_index = entity.get("chunk_index", 0)
                chunk_content = entity.get("chunk_content", "")
                image_path = entity.get("image_path", "")

                # Create TextNode with metadata
                node = TextNode(
                    id_=node_id,
                    text=chunk_content,
                    metadata={
                        "paper_id": paper_id,
                        "paper_title": paper_title,
                        "authors": authors,
                        "venue": venue,
                        "year": year,
                        "collection_names": collection_names_field,
                        "section_name": section_name,
                        "section_index": section_index,
                        "chunk_index": chunk_index,
                        "image_path": image_path,
                    },
                )

                nodes_with_scores.append(
                    NodeWithScore(node=node, score=similarity_score)
                )

            logger.info(
                "Retrieved %d chunks for query: %s",
                len(nodes_with_scores),
                query_text[:100],
            )

            return nodes_with_scores

        except Exception as e:
            logger.exception("Failed to retrieve from Zilliz: %s", str(e))
            return []

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """Synchronous retrieval (not supported)."""
        raise NotImplementedError(
            "ZillizRetriever only supports async retrieval. Use _aretrieve() instead."
        )
