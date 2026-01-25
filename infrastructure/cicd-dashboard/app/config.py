"""Configuration settings for CI/CD Dashboard."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite+aiosqlite:///data/cicd.db"
    github_webhook_secret: str = ""
    api_prefix: str = "/api/v1"
    debug: bool = False


settings = Settings()
