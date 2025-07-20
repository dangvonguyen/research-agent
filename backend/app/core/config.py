from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_ignore_empty=True,
        extra="ignore",
    )

    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Research Agent API"
    DEBUG: bool


settings = Settings()  # type: ignore
