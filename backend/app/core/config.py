import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # Database settings
    MONGODB_URI: str
    MONGODB_NAME: str


# Load settings from environment
settings = Settings()  # type: ignore
logger.info("Settings loaded for project: %s", settings.PROJECT_NAME)
logger.debug(
    "API settings: API_V1_STR=%s, DEBUG=%s",
    settings.API_V1_STR, settings.DEBUG,
)
logger.debug(
    "MongoDB settings: database=%s, URI=%s",
    settings.MONGODB_NAME, settings.MONGODB_URI,
)
