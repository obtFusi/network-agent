"""API routers for CI/CD Dashboard."""

from app.api.webhooks import router as webhooks_router

__all__ = ["webhooks_router"]
