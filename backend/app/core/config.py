import logging
from typing import Annotated, Any, Optional

from pydantic import AnyUrl, BeforeValidator, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.logging import sanitize_db_uri

logger = logging.getLogger(__name__)


def parse_cors(value: Any) -> list[str] | str:
    """
    Parse CORS origins from string or list.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",")]
    raise ValueError(value)


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_ignore_empty=True,
        extra="ignore",
    )

    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Research Agent API"
    DEBUG: bool

    # CORS settings
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore
    @property
    def all_cors_origins(self) -> list[str]:
        """Get normalized list of CORS origins."""
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    # Postgres settings
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def POSTGRES_URI(self) -> str:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        ).encoded_string()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def POSTGRES_URI_SAFE(self) -> str:
        return sanitize_db_uri(self.POSTGRES_URI)

    # Datalab API settings for PDF parsing
    DATALAB_API_KEY: Optional[str] = None
    DATALAB_API_URL: Optional[str] = None

    # PDF parsing settings
    PDF_MIN_CONTENT_LENGTH: int  # Minimum content length for a section
    PDF_MAX_CHUNK_WORDS: int  # Maximum words per chunk
    PDF_CHUNK_OVERLAP_WORDS: int  # Overlap between chunks in words

    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB

    # LLM settings
    DEFAULT_LLM_MODEL: str = "models/gemini-2.5-flash"
    DEFAULT_LLM_PROVIDER: str = "gemini"
    TIMEOUT: Optional[float] = None
    MAX_TOKENS: Optional[int] = None

    # Embedding settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_DIMENSION: int | None = None

    # LLM Provider API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Zilliz vector database settings
    ZILLIZ_ENDPOINT: Optional[str] = None
    ZILLIZ_TOKEN: Optional[str] = None
    ZILLIZ_COLLECTION_NAME: str = "paper_chunks"
    ZILLIZ_VECTOR_DIMENSION: int = 1536


# Load settings from environment
settings = Settings()  # type: ignore
logger.info("Settings loaded for project: %s", settings.PROJECT_NAME)
logger.debug(
    "API settings: API_V1_STR=%s, DEBUG=%s",
    settings.API_V1_STR,
    settings.DEBUG,
)
logger.debug(
    "Postgres settings: database=%s, URI=%s",
    settings.POSTGRES_DB,
    settings.POSTGRES_URI_SAFE,
)
