import json
import logging
import os
from threading import local

from dotenv import load_dotenv

from .client import GeminiClient, OpenAIClient
from .exceptions import ConfigurationError, FileOperationError

load_dotenv()

logger = logging.getLogger(__name__)

# Thread-local storage for client instances
THREAD_LOCAL = local()

# Gemini model prefixes
GEMINI_PREFIXES = ("gemini-",)


def get_client(model_name: str) -> OpenAIClient | GeminiClient:
    """Get or create a thread-local client instance based on model name."""
    # Determine client type based on model name
    is_gemini = model_name.startswith(GEMINI_PREFIXES)

    # Check if we need to create a new client (different type or not initialized)
    current_client = getattr(THREAD_LOCAL, "client", None)
    current_is_gemini = isinstance(current_client, GeminiClient) if current_client else None

    if current_client is None or current_is_gemini != is_gemini:
        if is_gemini:
            THREAD_LOCAL.client = GeminiClient(model_name=model_name)
            logger.info(f"Created GeminiClient for model: {model_name}")
        else:
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            if not OPENAI_API_KEY:
                logger.error("OPENAI_API_KEY is not set.")
                raise ConfigurationError("OPENAI_API_KEY environment variable is required")

            THREAD_LOCAL.client = OpenAIClient(
                openai_api_key=OPENAI_API_KEY,
                model_name=model_name,
            )
            logger.info(f"Created OpenAIClient for model: {model_name}")

    return THREAD_LOCAL.client


def read_prompt(file_path: str) -> list[dict]:
    """Read prompts from a JSONL file."""
    prompts = []
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                prompts.append(json.loads(line))
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}")
        raise FileOperationError(f"Prompt file not found: {file_path}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in prompt file {file_path}: {e}")
        raise FileOperationError(f"Invalid JSON in prompt file: {file_path}") from e
    return prompts


def read_config_json(json_path: str) -> dict:
    """Read a JSON configuration file."""
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except json.decoder.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e} in {json_path}")
        raise FileOperationError(f"Invalid JSON in config file: {json_path}") from e
    except FileNotFoundError as e:
        logger.error(f"File not found: {json_path}")
        raise FileOperationError(f"Config file not found: {json_path}") from e


def write_config_json(json_path: str, config: dict) -> None:
    """Write configuration data to a JSON file."""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
