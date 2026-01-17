# API Config
"""Configuration for Network Agent HTTP API."""

from pydantic import BaseModel


class CORSConfig(BaseModel):
    """CORS configuration."""

    allow_origins: list[str] = ["*"]
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = False


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = "0.0.0.0"
    port: int = 8080
    cors: CORSConfig = CORSConfig()
    debug: bool = False
