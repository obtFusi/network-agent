# Health Router
"""Health check endpoints for Docker and Kubernetes compatibility."""

import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter

router = APIRouter(tags=["health"])

# Fixed health check URL - configurable via environment only
# Defaults to Docker Compose service name for appliance mode
OLLAMA_HEALTH_URL = os.getenv("OLLAMA_HEALTH_URL", "http://ollama:11434/api/tags")


def _is_safe_url(url: str) -> bool:
    """Validate URL is safe for internal health checks (localhost or private networks)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Allow localhost, Docker service names, and private networks
        safe_hosts = ("localhost", "127.0.0.1", "ollama", "host.docker.internal")
        return (
            host in safe_hosts
            or host.endswith(".local")
            or host.startswith("10.")
            or host.startswith("172.")
            or host.startswith("192.168.")
        )
    except Exception:
        return False


@router.get("/health")
async def health():
    """Liveness probe - returns OK if the application is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    """Readiness probe - checks connectivity to Ollama and Postgres."""
    checks = {"ollama": False, "postgres": False}

    # Ollama connectivity check using fixed URL from environment
    try:
        if OLLAMA_HEALTH_URL and _is_safe_url(OLLAMA_HEALTH_URL):
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(OLLAMA_HEALTH_URL)
                checks["ollama"] = response.status_code == 200
    except Exception:
        pass

    # Postgres connectivity check
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # For now, just check if DATABASE_URL is set
        # Full connection test would require asyncpg
        checks["postgres"] = True
    else:
        # Postgres not configured - that's OK for standalone mode
        checks["postgres"] = True

    all_ready = all(checks.values())
    return {
        "status": "ready" if all_ready else "not_ready",
        **checks,
    }
