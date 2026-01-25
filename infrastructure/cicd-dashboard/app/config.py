"""Configuration settings for CI/CD Dashboard."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite+aiosqlite:///data/cicd.db"
    github_webhook_secret: str = ""
    api_prefix: str = "/api/v1"
    debug: bool = False

    # GitHub API settings
    github_token: str = ""  # Personal Access Token for API calls
    github_app_id: int | None = None  # Alternative: GitHub App ID
    github_app_private_key: str = ""  # GitHub App private key (PEM)

    # Pipeline settings
    approval_timeout_hours: int = 24
    pipeline_timeout_hours: int = 48
    default_repo: str = "obtFusi/network-agent"


settings = Settings()
