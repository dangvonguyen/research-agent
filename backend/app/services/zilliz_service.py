import logging
from typing import Any
from uuid import UUID

from pymilvus import DataType, MilvusClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class ZillizService:
    """Service for managing Zilliz vector database operations."""

    def __init__(self):
        """Initialize Zilliz service."""
        self.endpoint = settings.ZILLIZ_ENDPOINT
        self.token = settings.ZILLIZ_TOKEN
        self.collection_name = settings.ZILLIZ_COLLECTION_NAME
        self.vector_dimension = settings.ZILLIZ_VECTOR_DIMENSION
        self.client: MilvusClient | None = None
        self._collection_created = False

    def connect(self) -> None:
        """
        Connect to Zilliz vector database.
        """
        if not self.endpoint or not self.token:
            logger.warning(
                "Zilliz endpoint or token not configured. Vector database features will be disabled."
            )
            return

        try:
            # Connect using MilvusClient (works with Zilliz Cloud)
            # For Zilliz Cloud, endpoint should be in format: https://xxx.zillizcloud.com
            self.client = MilvusClient(
                uri=self.endpoint,
                token=self.token,
            )

            logger.info("Successfully connected to Zilliz vector database")
        except Exception as e:
            logger.exception("Failed to connect to Zilliz: %s", str(e))
            raise

    def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if not self.client:
            self.connect()

    def create_collection(self) -> None:
        """
        Create collection in Zilliz if it doesn't exist (one-time operation).
        Collection schema includes:
        - chunk_content_embedding: Vector embedding for chunk text content
        - paper_title_embedding: Vector embedding for paper title
        - abstract_embedding: Vector embedding for paper abstract
        - Metadata fields: chunk_id, paper_id, paper_title, authors, venue, year,
          collection_names, section_name, section_index, chunk_index, chunk_content
        """
        if self._collection_created:
            return

        if not self.endpoint or not self.token:
            logger.warning("Zilliz not configured, skipping collection creation")
            return

        try:
            self._ensure_connected()
            if not self.client:
                return

            # Check if collection already exists
            if self.client.has_collection(self.collection_name):
                logger.info("Collection '%s' already exists", self.collection_name)
                # Verify that abstract_embedding field exists in the schema
                try:
                    collection_info = self.client.describe_collection(
                        self.collection_name
                    )
                    schema_fields = collection_info.get("fields", [])
                    has_abstract_embedding = any(
                        field.get("name") == "abstract_embedding"
                        for field in schema_fields
                    )
                    if not has_abstract_embedding:
                        logger.warning(
                            "Collection '%s' exists but does not have 'abstract_embedding' field in schema. "
                            "The field will be stored as a dynamic field. To use it as a proper schema field, "
                            "please drop and recreate the collection.",
                            self.collection_name,
                        )
                except Exception as e:
                    logger.warning(
                        "Could not verify schema for collection '%s': %s",
                        self.collection_name,
                        str(e),
                    )
                self._collection_created = True
                return

            # Define schema using MilvusClient's schema definition
            schema = self.client.create_schema(
                auto_id=False,
                enable_dynamic_field=True,
            )

            # Add fields to schema
            schema.add_field(
                field_name="chunk_id",
                datatype=DataType.VARCHAR,
                is_primary=True,
                max_length=255,
            )
            schema.add_field(
                field_name="paper_id", datatype=DataType.VARCHAR, max_length=255
            )
            schema.add_field(
                field_name="paper_title", datatype=DataType.VARCHAR, max_length=512
            )
            schema.add_field(field_name="authors", datatype=DataType.JSON)
            schema.add_field(
                field_name="venue", datatype=DataType.VARCHAR, max_length=255
            )
            schema.add_field(field_name="year", datatype=DataType.INT64)
            schema.add_field(field_name="collection_names", datatype=DataType.JSON)
            schema.add_field(
                field_name="section_name", datatype=DataType.VARCHAR, max_length=255
            )
            schema.add_field(field_name="section_index", datatype=DataType.INT64)
            schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
            schema.add_field(
                field_name="chunk_content", datatype=DataType.VARCHAR, max_length=65535
            )
            schema.add_field(
                field_name="chunk_content_embedding",
                datatype=DataType.FLOAT_VECTOR,
                dim=self.vector_dimension,
            )
            schema.add_field(
                field_name="paper_title_embedding",
                datatype=DataType.FLOAT_VECTOR,
                dim=self.vector_dimension,
            )
            schema.add_field(
                field_name="abstract_embedding",
                datatype=DataType.FLOAT_VECTOR,
                dim=self.vector_dimension,
            )
            schema.add_field(field_name="chunk_references", datatype=DataType.JSON)
            schema.add_field(
                field_name="image_path", datatype=DataType.VARCHAR, max_length=512
            )

            # Create collection with schema
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                description="Collection for storing paper content chunks with chunk_content_embedding, paper_title_embedding, and abstract_embedding vectors, plus metadata fields",
            )

            # Create index on embedding fields for similarity search
            index_params = self.client.prepare_index_params()
            index_params.add_index(
                field_name="chunk_content_embedding",
                index_type="IVF_FLAT",
                metric_type="L2",
                params={"nlist": 1024},
            )
            index_params.add_index(
                field_name="paper_title_embedding",
                index_type="IVF_FLAT",
                metric_type="L2",
                params={"nlist": 1024},
            )
            index_params.add_index(
                field_name="abstract_embedding",
                index_type="IVF_FLAT",
                metric_type="L2",
                params={"nlist": 1024},
            )
            self.client.create_index(
                collection_name=self.collection_name,
                index_params=index_params,
            )

            # Verify collection was created successfully
            if not self.client.has_collection(self.collection_name):
                raise RuntimeError(
                    f"Failed to create collection '{self.collection_name}' - collection does not exist after creation"
                )

            logger.info(
                "Successfully created collection '%s' with schema (including abstract_embedding)",
                self.collection_name,
            )
            self._collection_created = True

        except Exception as e:
            logger.exception(
                "Failed to create collection '%s': %s",
                self.collection_name,
                str(e),
            )
            raise

    def _ensure_collection(self) -> None:
        """Ensure collection exists."""
        if not self._collection_created:
            self.create_collection()
        else:
            # Double-check that collection actually exists
            # (it might have been deleted externally)
            try:
                self._ensure_connected()
                if self.client and not self.client.has_collection(self.collection_name):
                    logger.warning(
                        "Collection '%s' was expected to exist but doesn't. Recreating...",
                        self.collection_name,
                    )
                    self._collection_created = False
                    self.create_collection()
            except Exception as e:
                logger.warning(
                    "Could not verify collection existence, attempting to create: %s",
                    str(e),
                )
                self._collection_created = False
                self.create_collection()

    def insert_embeddings(
        self,
        paper_id: UUID,
        paper_title: str,
        authors: list[str] | None,
        venue: str | None,
        year: int | None,
        collection_names: list[str],
        chunks: list[dict[str, Any]],
        abstract_embedding: list[float] | None = None,
    ) -> None:
        """
        Insert paper chunks with embeddings and metadata into Zilliz.

        Args:
            paper_id: UUID of the paper
            paper_title: Title of the paper
            authors: List of authors
            venue: Venue name
            year: Publication year
            collection_names: List of collection names
            chunks: List of chunk dictionaries with keys:
                - chunk_id: UUID of the chunk
                - section_name: Name of the section
                - section_index: Index of the section
                - chunk_index: Index of the chunk
                - chunk_content: Text content of the chunk
                - chunk_content_embedding: Vector embedding for chunk text content (list of floats)
                - paper_title_embedding: Vector embedding for paper title (list of floats)
            abstract_embedding: Optional vector embedding for paper abstract (list of floats)
        """
        if not self.endpoint or not self.token:
            logger.debug("Zilliz not configured, skipping embedding insertion")
            return

        try:
            self._ensure_connected()
            if not self.client:
                logger.warning(
                    "Zilliz client not available, skipping embedding insertion"
                )
                return

            self._ensure_collection()

            # Verify collection exists one more time before insertion
            if not self.client.has_collection(self.collection_name):
                logger.error(
                    "Collection '%s' does not exist and could not be created. Aborting insertion.",
                    self.collection_name,
                )
                raise ValueError(
                    f"Collection '{self.collection_name}' does not exist in Zilliz"
                )

            # Prepare data for insertion
            data = []

            paper_id_str = str(paper_id)

            for chunk in chunks:
                chunk_data = {
                    "chunk_id": str(chunk["chunk_id"]),
                    "paper_id": paper_id_str,
                    "paper_title": paper_title,
                    "authors": authors if authors else [],
                    "venue": venue if venue else "",
                    "year": year if year else 0,
                    "collection_names": collection_names,
                    "section_name": chunk["section_name"],
                    "section_index": chunk.get("section_index", 0),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "chunk_content": chunk["content"],
                }
                # Check if this is a reference chunk (has no embeddings)
                is_reference = chunk.get("is_reference", False)

                # Add abstract embedding (same for all chunks from the same paper)
                if abstract_embedding:
                    chunk_data["abstract_embedding"] = abstract_embedding
                else:
                    # Use zero vector if abstract embedding is missing
                    chunk_data["abstract_embedding"] = [0.0] * self.vector_dimension

                if is_reference:
                    # Reference chunks have no embeddings at all - use zero vectors
                    chunk_data["chunk_content_embedding"] = [
                        0.0
                    ] * self.vector_dimension
                    chunk_data["paper_title_embedding"] = [0.0] * self.vector_dimension
                else:
                    # Regular chunks have both embeddings
                    if chunk.get("embedding"):
                        chunk_data["chunk_content_embedding"] = chunk["embedding"]
                    else:
                        # Use zero vector if content embedding is missing
                        chunk_data["chunk_content_embedding"] = [
                            0.0
                        ] * self.vector_dimension

                    # Add paper title embedding (should always be present for regular chunks)
                    if chunk.get("title_embedding"):
                        chunk_data["paper_title_embedding"] = chunk["title_embedding"]
                    else:
                        # Use zero vector if title embedding is missing
                        chunk_data["paper_title_embedding"] = [
                            0.0
                        ] * self.vector_dimension

                # Add chunk_references if present (list of reference content strings matched to this chunk)
                chunk_data["chunk_references"] = chunk.get("chunk_references", [])

                # Add image_path if present
                image_path = chunk.get("image_path", "")
                chunk_data["image_path"] = image_path if image_path else ""

                data.append(chunk_data)

            # Insert data using MilvusClient
            self.client.insert(
                collection_name=self.collection_name,
                data=data,
            )

            logger.info(
                "Successfully inserted %d chunks for paper '%s' into Zilliz",
                len(chunks),
                paper_id,
            )

        except Exception as e:
            logger.exception(
                "Failed to insert embeddings for paper '%s': %s",
                paper_id,
                str(e),
            )
            raise

    def delete_paper_chunks(self, paper_id: UUID) -> None:
        """
        Delete all chunks for a specific paper from Zilliz.

        Args:
            paper_id: UUID of the paper
        """
        if not self.endpoint or not self.token:
            logger.debug("Zilliz not configured, skipping chunk deletion")
            return

        try:
            self._ensure_connected()
            if not self.client:
                logger.warning("Zilliz client not available, skipping chunk deletion")
                return

            self._ensure_collection()

            # Delete chunks by paper_id
            self.client.delete(
                collection_name=self.collection_name,
                filter=f'paper_id == "{paper_id}"',
            )

            logger.info(
                "Successfully deleted chunks for paper '%s' from Zilliz", paper_id
            )

        except Exception as e:
            logger.exception(
                "Failed to delete chunks for paper '%s': %s",
                paper_id,
                str(e),
            )

    def query(
        self,
        filter: str,
        limit: int = 10,
        offset: int = 0,
        output_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query chunks using metadata filters only. More efficient than search() when
        you only need to filter by metadata.

        Args:
            filter: Filter expression (e.g., 'paper_id == "uuid"')
            limit: Maximum number of results to return
            offset: Number of results to skip
            output_fields: Optional list of fields to return in results

        Returns:
            List of query results with metadata
        """
        if not self.endpoint or not self.token:
            logger.warning("Zilliz not configured, returning empty query results")
            return []

        try:
            self._ensure_connected()
            if not self.client:
                logger.warning(
                    "Zilliz client not available, returning empty query results"
                )
                return []

            self._ensure_collection()

            # Default output fields
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

            # Perform query using MilvusClient
            results = self.client.query(
                collection_name=self.collection_name,
                filter=filter,
                output_fields=output_fields,
                limit=limit,
                offset=offset,
            )

            return results

        except Exception as e:
            logger.exception("Failed to query Zilliz: %s", str(e))
            return []

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filter_expr: str | None = None,
        output_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar chunks using vector similarity on chunk_content_embedding field.

        Args:
            query_vector: Query embedding vector to search against chunk_content_embedding
            limit: Maximum number of results to return
            filter_expr: Optional filter expression (e.g., 'year == 2023')
            output_fields: Optional list of fields to return in results

        Returns:
            List of search results with metadata
        """
        if not self.endpoint or not self.token:
            logger.warning("Zilliz not configured, returning empty search results")
            return []

        try:
            self._ensure_connected()
            if not self.client:
                logger.warning(
                    "Zilliz client not available, returning empty search results"
                )
                return []

            self._ensure_collection()

            # Default output fields
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

            # Search parameters
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10},
            }

            # Perform search using MilvusClient
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=limit,
                search_params=search_params,
                filter=filter_expr,
                output_fields=output_fields,
                anns_field="chunk_content_embedding",
            )

            # Format results
            formatted_results = []
            if results and len(results) > 0:
                for hit in results[0]:
                    formatted_results.append(
                        {
                            "id": hit.get("id"),
                            "distance": hit.get("distance"),
                            "entity": hit,
                        }
                    )

            return formatted_results

        except Exception as e:
            logger.exception("Failed to search in Zilliz: %s", str(e))
            return []


# Create singleton instance
zilliz_service = ZillizService()
