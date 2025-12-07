import logging
from uuid import UUID

from openai import OpenAI
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import Session
from app.core.config import settings
from app.db.models import Paper, PaperContent
from app.services.zilliz_service import zilliz_service

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings and storing them in Zilliz."""

    EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI embedding model
    EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small

    def __init__(self):
        """Initialize embedding service."""
        self.client: OpenAI | None = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _ensure_client(self) -> None:
        """Ensure OpenAI client is initialized."""
        if not self.client:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is not configured")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for given text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []

        try:
            self._ensure_client()
            if not self.client:
                raise ValueError("OpenAI client not available")

            # Generate embedding
            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text,
            )

            return response.data[0].embedding

        except Exception as e:
            logger.exception("Failed to generate embedding: %s", str(e))
            raise

    async def embed_paper_chunks(self, paper_id: UUID) -> None:
        """
        Generate embeddings for all chunks of a paper and store them in Zilliz.
        This includes all metadata: paper title, authors, venue, year, collection names.

        Args:
            paper_id: UUID of the paper to embed
        """
        if not settings.ZILLIZ_ENDPOINT or not settings.ZILLIZ_TOKEN:
            logger.debug(
                "Zilliz not configured, skipping embedding for paper '%s'", paper_id
            )
            return

        async with Session() as session:
            try:
                # Fetch paper with all related data
                stmt = (
                    select(Paper)
                    .options(
                        selectinload(Paper.contents), selectinload(Paper.collections)
                    )
                    .where(Paper.id == paper_id)
                )
                result = await session.execute(stmt)
                paper = result.scalar_one_or_none()

                if not paper:
                    logger.warning("Paper '%s' not found for embedding", paper_id)
                    return

                if not paper.contents or len(paper.contents) == 0:
                    logger.info("Paper '%s' has no chunks to embed", paper_id)
                    return

                # Get collection names
                collection_names = (
                    [collection.name for collection in paper.collections]
                    if paper.collections
                    else []
                )

                logger.info(
                    "Generating embeddings for %d chunks of paper '%s'",
                    len(paper.contents),
                    paper_id,
                )

                # Prepare chunks with embeddings
                chunks_with_embeddings = []

                for content in paper.contents:
                    # Skip the first section (section_index=0) as it typically contains
                    # title and author metadata, not content to embed
                    section_index = content.section_index or 0
                    if section_index == 0:
                        logger.debug(
                            "Skipping embedding for first section (metadata) '%s' of paper '%s'",
                            content.section_name,
                            paper_id,
                        )
                        continue

                    try:
                        # Generate embedding for chunk content
                        embedding = await self.generate_embedding(content.content)

                        if not embedding:
                            logger.warning(
                                "Failed to generate embedding for chunk '%s' of paper '%s'",
                                content.id,
                                paper_id,
                            )
                            continue

                        # Prepare chunk data with metadata
                        chunk_data = {
                            "chunk_id": content.id,
                            "section_name": content.section_name,
                            "section_index": content.section_index or 0,
                            "chunk_index": content.chunk_index or 0,
                            "content": content.content,
                            "embedding": embedding,
                        }

                        chunks_with_embeddings.append(chunk_data)

                        # Update embedding_vector in database
                        # Use update statement to avoid session conflicts
                        await session.execute(
                            update(PaperContent)
                            .where(PaperContent.id == content.id)
                            .values(embedding_vector=embedding)
                        )

                    except Exception as e:
                        logger.exception(
                            "Failed to generate embedding for chunk '%s': %s",
                            content.id,
                            str(e),
                        )
                        # Continue with other chunks
                        continue

                # Commit embedding vectors to database
                await session.commit()

                if not chunks_with_embeddings:
                    logger.warning("No embeddings generated for paper '%s'", paper_id)
                    return

                # Insert embeddings into Zilliz with metadata
                zilliz_service.insert_embeddings(
                    paper_id=paper_id,
                    paper_title=paper.title,
                    authors=paper.authors,
                    venue=paper.venue,
                    year=paper.year,
                    collection_names=collection_names,
                    chunks=chunks_with_embeddings,
                )

                logger.info(
                    "Successfully embedded and stored %d chunks for paper '%s' in Zilliz",
                    len(chunks_with_embeddings),
                    paper_id,
                )

            except Exception as e:
                logger.exception(
                    "Failed to embed paper chunks for paper '%s': %s",
                    paper_id,
                    str(e),
                )
                # Don't raise - this is a background task, we don't want to fail the main operation
                raise


# Create singleton instance
embedding_service = EmbeddingService()
