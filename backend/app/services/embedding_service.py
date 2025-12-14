import logging
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import Session
from app.core.config import settings
from app.db.models import Paper, PaperContent
from app.services.zilliz_service import zilliz_service

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class EmbeddingModel(BaseModel):
    """Configuration for embedding model."""

    model_name: str = Field(..., description="Embedding model name")
    provider: EmbeddingProvider = Field(..., description="Embedding provider type")
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific configuration",
    )


class ProviderConfig(Protocol):
    """Protocol for provider-specific configuration builders."""

    def get_embedding_class(self) -> type[BaseEmbedding]:
        """Return the embedding class for this provider."""
        ...

    def build_kwargs(self, model: EmbeddingModel, settings: Any) -> dict[str, Any]:
        """Build provider-specific kwargs for embedding initialization."""
        ...


class OpenAIConfig:
    """OpenAI provider configuration."""

    def get_embedding_class(self) -> type[BaseEmbedding]:
        return OpenAIEmbedding

    def build_kwargs(self, model: EmbeddingModel, settings: Any) -> dict[str, Any]:
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise ValueError(
                f"OPENAI_API_KEY is required for model '{model.model_name}'"
            )

        kwargs = {
            "model_name": model.model_name,
            "api_key": api_key,
        }

        if hasattr(settings, "EMBEDDING_DIMENSION"):
            kwargs["dimensions"] = settings.EMBEDDING_DIMENSION

        kwargs.update(model.kwargs)
        return kwargs


class GeminiConfig:
    """Gemini provider configuration."""

    def get_embedding_class(self) -> type[BaseEmbedding]:
        return GeminiEmbedding

    def build_kwargs(self, model: EmbeddingModel, settings: Any) -> dict[str, Any]:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise ValueError(
                f"GEMINI_API_KEY is required for model '{model.model_name}'"
            )

        kwargs = {
            "model_name": model.model_name,
            "api_key": api_key,
        }

        kwargs.update(model.kwargs)
        return kwargs


class OllamaConfig:
    """Ollama provider configuration."""

    def get_embedding_class(self) -> type[BaseEmbedding]:
        return OllamaEmbedding

    def build_kwargs(self, model: EmbeddingModel, settings: Any) -> dict[str, Any]:
        base_url = getattr(settings, "OLLAMA_BASE_URL", None)
        if not base_url:
            raise ValueError(
                f"OLLAMA_BASE_URL is required for model '{model.model_name}'"
            )

        kwargs = {
            "model_name": model.model_name,
            "base_url": base_url,
        }

        kwargs.update(model.kwargs)
        return kwargs


class EmbeddingFactory:
    """Factory for creating embedding instances from configurations."""

    # Provider registry - easy to extend with new providers
    _PROVIDERS: dict[EmbeddingProvider, ProviderConfig] = {
        EmbeddingProvider.OPENAI: OpenAIConfig(),
        EmbeddingProvider.GEMINI: GeminiConfig(),
        EmbeddingProvider.OLLAMA: OllamaConfig(),
    }

    @classmethod
    def create_embedding(
        cls, model: EmbeddingModel, settings: Any | None = None
    ) -> BaseEmbedding:
        """Create an embedding instance from a model configuration.

        Args:
            model: An embedding model configuration
            settings: Settings object containing API keys and URLs

        Raises:
            ValueError: If the provider is not supported or required config is missing

        Returns:
            Configured embedding instance
        """
        if settings is None:
            # Import here to avoid circular dependencies
            from app.core.config import settings as default_settings

            settings = default_settings

        provider_config = cls._PROVIDERS.get(model.provider)
        if not provider_config:
            available = ", ".join(p.value for p in cls._PROVIDERS)
            raise ValueError(
                f"Unsupported embedding provider: {model.provider}. "
                f"Available providers: {available}"
            )

        try:
            embedding_class = provider_config.get_embedding_class()
            kwargs = provider_config.build_kwargs(model, settings)
            return embedding_class(**kwargs)
        except Exception as e:
            logger.error(
                f"Failed to create embedding '{model.model_name}' "
                f"({model.provider.value}): {e}"
            )
            raise


class EmbeddingService:
    """Service for generating embeddings and storing them in Zilliz."""

    def __init__(self):
        """Initialize embedding service with default provider."""
        self.set_embedding_model(
            model_name=settings.EMBEDDING_MODEL,
            provider=settings.EMBEDDING_PROVIDER,
        )

    def set_embedding_model(
        self, model_name: str, provider: str | EmbeddingProvider, **kwargs
    ) -> None:
        """Set a custom embedding model.

        Args:
            model_name: Name of the embedding model
            provider: Embedding provider
            **kwargs: Additional model configuration
        """
        if isinstance(provider, str):
            provider = EmbeddingProvider(provider)

        model = EmbeddingModel(model_name=model_name, provider=provider, kwargs=kwargs)
        self.embedding_model = EmbeddingFactory.create_embedding(model)

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for given text using configured provider.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []

        try:
            # Generate embedding using LlamaIndex embedding model
            embedding = await self.embedding_model.aget_text_embedding(text)
            return embedding

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

                # Generate embedding for paper title (once per paper)
                title_embedding = None
                if paper.title:
                    try:
                        title_embedding = await self.generate_embedding(paper.title)
                        logger.debug(
                            "Generated title embedding for paper '%s'", paper.title
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to generate title embedding for paper '%s': %s",
                            paper.title,
                            str(e),
                        )

                # Generate embedding for paper abstract (once per paper)
                abstract_embedding = None
                if paper.abstract:
                    try:
                        abstract_embedding = await self.generate_embedding(
                            paper.abstract
                        )
                        logger.debug(
                            "Generated abstract embedding for paper '%s'", paper.title
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to generate abstract embedding for paper '%s': %s",
                            paper.title,
                            str(e),
                        )

                # Prepare chunks with embeddings
                chunks_with_embeddings = []
                reference_chunks = []  # Store reference sections separately

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

                    # Check if this is a reference section (skip embedding but store metadata)
                    is_reference = (
                        content.extra_metadata
                        and content.extra_metadata.get("is_reference", False)
                    )

                    if is_reference:
                        # For reference sections, skip embedding but store metadata
                        logger.debug(
                            "Skipping embedding for reference section '%s' of paper '%s'",
                            content.section_name,
                            paper_id,
                        )
                        # Extract image_path from extra_metadata if present
                        image_path = None
                        if (
                            content.extra_metadata
                            and "image_path" in content.extra_metadata
                        ):
                            image_path = content.extra_metadata["image_path"]

                        # Store reference chunk with metadata but no embeddings
                        reference_chunks.append(
                            {
                                "chunk_id": content.id,
                                "section_name": content.section_name,
                                "section_index": content.section_index or 0,
                                "chunk_index": content.chunk_index or 0,
                                "content": content.content,
                                "is_reference": True,
                                "image_path": image_path or "",
                            }
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

                        # Extract image_path from extra_metadata if present
                        image_path = None
                        if (
                            content.extra_metadata
                            and "image_path" in content.extra_metadata
                        ):
                            image_path = content.extra_metadata["image_path"]

                        # Prepare chunk data with metadata
                        chunk_data = {
                            "chunk_id": content.id,
                            "section_name": content.section_name,
                            "section_index": content.section_index or 0,
                            "chunk_index": content.chunk_index or 0,
                            "content": content.content,
                            "embedding": embedding,
                            "title_embedding": title_embedding
                            if title_embedding
                            else [],
                            "image_path": image_path or "",
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

                if not chunks_with_embeddings and not reference_chunks:
                    logger.warning("No chunks to process for paper '%s'", paper_id)
                    return

                # Combine all chunks (with and without embeddings)
                all_chunks = chunks_with_embeddings.copy()
                # Add reference chunks without embedding field
                all_chunks.extend(reference_chunks)

                # Insert all chunks into Zilliz (reference chunks without embedding)
                if all_chunks:
                    zilliz_service.insert_embeddings(
                        paper_id=paper_id,
                        paper_title=paper.title,
                        authors=paper.authors,
                        venue=paper.venue,
                        year=paper.year,
                        collection_names=collection_names,
                        chunks=all_chunks,
                        abstract_embedding=abstract_embedding,
                    )

                    logger.info(
                        "Successfully stored %d chunks for paper '%s' in Zilliz (%d with embeddings, %d reference sections without embeddings)",
                        len(all_chunks),
                        paper_id,
                        len(chunks_with_embeddings),
                        len(reference_chunks),
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
