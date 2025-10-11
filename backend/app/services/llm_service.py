import logging
from enum import Enum
from typing import Any, Optional, Union

from llama_index.core import Settings
from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMModel(BaseModel):
    # Core identification
    model_name: str = Field(..., description="Model name")
    provider: LLMProvider = Field(..., description="LLM provider type")
    api_key: str = Field(default=None, description="API key for the provider")

    # Generation parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)

    # Additional provider-specific configuration
    additional_config: dict[str, Any] = Field(default_factory=dict)


class LLMFactory:
    """Factory for creating LLM instances from LLMModel configurations."""

    @staticmethod
    def create_llm(model: LLMModel) -> LLM:
        """
        Create an LLM instance from a model configuration.

        Args:
            model: LLMModel configuration

        Returns:
            Configured LLM instance
        """
        try:
            if model.provider == LLMProvider.OPENAI:
                return LLMFactory._create_openai_llm(model)
            elif model.provider == LLMProvider.ANTHROPIC:
                return LLMFactory._create_anthropic_llm(model)
            else:
                raise ValueError(f"Unsupported provider: {model.provider}")

        except Exception as e:
            logger.error(f"Failed to create LLM {model.name} ({model.provider}): {e}")
            raise

    @staticmethod
    def _create_openai_llm(model: LLMModel) -> OpenAI:
        """Create OpenAI LLM instance."""
        api_key = model.api_key or getattr(settings, "OPENAI_API_KEY", None)

        if not api_key:
            raise ValueError(f"OpenAI API key is required for model {model.name}")

        kwargs = {
            "model": model.model_name,
            "temperature": model.temperature,
            "api_key": api_key,
        }

        if model.max_tokens is not None:
            kwargs["max_tokens"] = model.max_tokens
        if model.frequency_penalty is not None:
            kwargs["frequency_penalty"] = model.frequency_penalty
        if model.presence_penalty is not None:
            kwargs["presence_penalty"] = model.presence_penalty

        kwargs.update(model.additional_config)

        return OpenAI(**kwargs)

    @staticmethod
    def _create_anthropic_llm(model: LLMModel) -> LLM:
        """Create Anthropic LLM instance."""
        try:
            from llama_index.llms.anthropic import Anthropic
        except ImportError as e:
            raise ValueError("Anthropic integration not installed.") from e

        api_key = model.api_key or getattr(settings, "ANTHROPIC_API_KEY", None)

        if not api_key:
            raise ValueError(f"Anthropic API key is required for model {model.name}")

        kwargs = {
            "model": model.model_name,
            "temperature": model.temperature,
            "api_key": api_key,
        }

        if model.max_tokens is not None:
            kwargs["max_tokens"] = model.max_tokens

        kwargs.update(model.additional_config)

        return Anthropic(**kwargs)


class LLMService:
    def __init__(self):
        self._current_llm: Optional[LLM] = None
        self._current_model: Optional[LLMModel] = None

    def create_llm(
        self,
        model_name: str,
        provider: Union[str, LLMProvider],
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLM:
        if isinstance(provider, str):
            provider = LLMProvider(provider)

        model = LLMModel(
            model_name=model_name,
            provider=provider,
            api_key=api_key,
            temperature=temperature,
            **kwargs,
        )

        return LLMFactory.create_llm(model)

    def set_global_llm(self, llm_or_model: LLM | LLMModel) -> LLM:
        """
        Set the global LLM for LlamaIndex.

        Args:
            llm_or_model: Either an LLM instance or LLMModel configuration

        Returns:
            The LLM instance that was set globally
        """
        if isinstance(llm_or_model, LLMModel):
            llm = LLMFactory.create_llm(llm_or_model)
            self._current_model = llm_or_model
        else:
            llm = llm_or_model
            self._current_model = None

        Settings.llm = llm
        self._current_llm = llm

        logger.info(
            f"Set global LLM: {getattr(self._current_model, 'model_name', 'Custom LLM')}"
        )
        return llm

    def get_current_llm(self) -> Optional[LLM]:
        """Get the currently set global LLM."""
        return self._current_llm

    def get_current_model(self) -> Optional[LLMModel]:
        """Get the current model configuration."""
        return self._current_model


# Global service instance
llm_service = LLMService()


# Utility functions for quick LLM creation
def create_openai_llm(
    model_name: str = "gpt-4",
    temperature: float = 0.7,
    **kwargs,
) -> LLM | None:
    """Quick utility to create an OpenAI LLM."""
    if hasattr(settings, "OPENAI_API_KEY") and not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key is not set.")
        return None

    return llm_service.create_llm(
        model_name=model_name,
        provider=LLMProvider.OPENAI,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
        **kwargs,
    )


def create_anthropic_llm(
    model_name: str = "claude-3-sonnet-20240229",
    temperature: float = 0.7,
    **kwargs,
) -> LLM | None:
    """Quick utility to create an Anthropic LLM."""
    if hasattr(settings, "ANTHROPIC_API_KEY") and not settings.ANTHROPIC_API_KEY:
        logger.warning("Anthropic API key is not set.")
        return None

    return llm_service.create_llm(
        model_name=model_name,
        provider=LLMProvider.ANTHROPIC,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=temperature,
        **kwargs,
    )


# Initialize default LLM if possible
try:
    if hasattr(settings, "OPENAI_API_KEY") and settings.OPENAI_API_KEY:
        default_llm = create_openai_llm()
        llm_service.set_global_llm(default_llm)
        logger.info("Initialized LLM service with default OpenAI model")
except Exception as e:
    logger.warning(f"Could not initialize default LLM: {e}")
