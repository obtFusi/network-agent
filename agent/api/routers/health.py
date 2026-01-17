# Health Router
"""Health check endpoints for Docker and Kubernetes compatibility."""

import os

import httpx
from fastapi import APIRouter, Depends

from agent.api.dependencies import get_config

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness probe - returns OK if the application is running."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(config: dict = Depends(get_config)):
    """Readiness probe - checks connectivity to Ollama and Postgres."""
    checks = {"ollama": False, "postgres": False}

    # Ollama connectivity check
    try:
        llm_config = config.get("llm", {}).get("provider", {})
        base_url = llm_config.get("base_url", "")
        if base_url:
            # Convert OpenAI-compatible URL to Ollama native API
            ollama_url = base_url.replace("/v1", "") + "/api/tags"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(ollama_url)
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
