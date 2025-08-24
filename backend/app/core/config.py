import logging
from typing import Annotated, Any

from pydantic import AnyUrl, BeforeValidator, MongoDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.logging import sanitize_mongodb_uri

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

    # Database settings
    MONGODB_SERVER: str
    MONGODB_PORT: int
    MONGODB_ROOT_USERNAME: str | None = None
    MONGODB_ROOT_PASSWORD: str | None = None
    MONGODB_DATABASE: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MONGODB_URI(self) -> str:
        query = (
            "authSource=admin"
            if self.MONGODB_ROOT_USERNAME is not None
            and self.MONGODB_ROOT_PASSWORD is not None
            else None
        )
        return MongoDsn.build(
            scheme="mongodb",
            username=self.MONGODB_ROOT_USERNAME,
            password=self.MONGODB_ROOT_PASSWORD,
            host=self.MONGODB_SERVER,
            port=self.MONGODB_PORT,
            path=self.MONGODB_DATABASE,
            query=query,
        ).encoded_string()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def MONGODB_URI_SAFE(self) -> str:
        return sanitize_mongodb_uri(self.MONGODB_URI)


# Load settings from environment
settings = Settings()  # type: ignore
logger.info("Settings loaded for project: %s", settings.PROJECT_NAME)
logger.debug(
    "API settings: API_V1_STR=%s, DEBUG=%s",
    settings.API_V1_STR, settings.DEBUG,
)
logger.debug(
    "MongoDB settings: database=%s, URI=%s",
    settings.MONGODB_DATABASE, settings.MONGODB_URI_SAFE,
)
