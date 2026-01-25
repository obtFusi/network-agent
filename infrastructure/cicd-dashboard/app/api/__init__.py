"""API routers for CI/CD Dashboard."""

from app.api.approvals import router as approvals_router
from app.api.events import router as events_router
from app.api.pipelines import router as pipelines_router
from app.api.webhooks import router as webhooks_router

__all__ = ["approvals_router", "events_router", "pipelines_router", "webhooks_router"]
