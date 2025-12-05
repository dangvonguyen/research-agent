import logging
from enum import Enum
from typing import Any, Optional, cast

from llama_index.core import Settings
from llama_index.core.llms import LLM
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.gemini import Gemini
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENAI = "openai"


class LLMModel(BaseModel):
    # Core identification
    model_name: str = Field(..., description="Model name")
    provider: LLMProvider = Field(..., description="LLM provider type")

    # Generation parameters
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)

    # Additional provider-specific configuration
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)


class LLMFactory:
    """Factory for creating LLM instances from LLMModel configurations."""

    # Provider configuration mapping
    _PROVIDER_CONFIG = {
        LLMProvider.ANTHROPIC: {
            "llm_class": Anthropic,
            "api_key_attr": "ANTHROPIC_API_KEY",
            "provider_name": "Anthropic",
        },
        LLMProvider.GEMINI: {
            "llm_class": Gemini,
            "api_key_attr": "GEMINI_API_KEY",
            "provider_name": "Gemini",
        },
        LLMProvider.OPENAI: {
            "llm_class": OpenAI,
            "api_key_attr": "OPENAI_API_KEY",
            "provider_name": "OpenAI",
        },
    }

    @staticmethod
    def create_llm(model: LLMModel) -> LLM:
        """Create an LLM instance from a model configuration.

        Args:
            model (LLMModel): A model configuration

        Raises:
            ValueError: If the provider is not supported or the API key is not available

        Returns:
            Configured LLM instance
        """
        try:
            if model.provider not in LLMFactory._PROVIDER_CONFIG:
                raise ValueError(f"Unsupported provider: {model.provider}")

            return LLMFactory._create_llm(model)

        except Exception as e:
            logger.error(
                f"Failed to create LLM {model.model_name} ({model.provider}): {e}"
            )
            raise

    @staticmethod
    def _create_llm(model: LLMModel) -> LLM:
        """Create LLM instance."""
        config = LLMFactory._PROVIDER_CONFIG[model.provider]
        llm_class = cast(type[LLM], config["llm_class"])
        api_key_attr = cast(str, config["api_key_attr"])
        provider_name = cast(str, config["provider_name"])

        # Get API key from settings
        api_key = getattr(settings, api_key_attr, None)

        if not api_key:
            raise ValueError(
                f"{provider_name} API key is required for model {model.model_name}"
            )

        # Build base kwargs
        kwargs = {
            "model": model.model_name,
            "api_key": api_key,
            "temperature": model.temperature,
            "max_tokens": model.max_tokens,
        }

        # Add provider-specific supported parameters
        kwargs.update(model.additional_kwargs)

        return llm_class(**kwargs)


class LLMService:
    def __init__(self) -> None:
        self._default_llm = self.create_llm(
            model_name=settings.DEFAULT_LLM_MODEL,
            provider=settings.DEFAULT_LLM_PROVIDER,
        )

        Settings.llm = self._default_llm

    def create_llm(
        self, model_name: str, provider: str | LLMProvider, **kwargs: Any
    ) -> LLM:
        """Create an LLM instance from a model configuration.

        Args:
            model_name (str): Name of the model to use
            provider (str | LLMProvider): A provider name or enum
            **kwargs: Additional parameters for the model (e.g. temperature, max_tokens, etc.)

        Returns:
            Configured LLM instance
        """
        if isinstance(provider, str):
            provider = LLMProvider(provider)

        model = LLMModel(model_name=model_name, provider=provider, **kwargs)

        return LLMFactory.create_llm(model)

    def get_default_llm(self) -> LLM:
        """Get the default LLM."""
        return self._default_llm

    async def enhance_search_keywords(self, user_query: str) -> str:
        """
        Enhance user query by extracting and improving keywords for paper search.

        Args:
            user_query: The user's search query/question

        Returns:
            Enhanced keywords string optimized for paper search
        """
        try:
            llm = self.get_default_llm()
            if not llm:
                # Fallback: create a default LLM if none is set
                llm = self.create_llm(
                    model_name="gpt-3.5-turbo", provider="openai", temperature=0.3
                )
                if not llm:
                    logger.warning("No LLM available, returning original query")
                    return user_query.strip()

            prompt = f"""You are a research assistant helping to find academic papers.
Extract and enhance the key search terms from the following user query to optimize it for searching academic paper databases.

User query: "{user_query}"

Please:
1. Extract the main keywords and concepts
2. Expand with relevant synonyms and related terms
3. Remove unnecessary words
4. Format as a concise search query (3-5 key terms maximum)
5. Keep it focused on the core research topic
6. Do NOT add quotes, brackets, or any special formatting - just return the plain search terms

Return ONLY the enhanced search query as plain text, nothing else. Do not include explanations, quotes, or additional text."""

            response = await llm.acomplete(prompt)
            enhanced_query = response.text.strip()

            # Remove any quotes that the LLM might have added
            enhanced_query = enhanced_query.strip('"').strip("'").strip()

            # Fallback to original if enhancement failed or is empty
            if not enhanced_query or len(enhanced_query) < 3:
                logger.warning(
                    "LLM enhancement produced empty/invalid result, using original query"
                )
                return user_query.strip()

            logger.info(f"Enhanced query: '{user_query}' -> '{enhanced_query}'")
            return enhanced_query

        except Exception as e:
            logger.exception(f"Error enhancing search keywords: {e}")
            # Fallback to original query on error
            return user_query.strip()


# Global service instance
llm_service = LLMService()
default_llm = llm_service.get_default_llm()
