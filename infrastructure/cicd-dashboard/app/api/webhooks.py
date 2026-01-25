"""GitHub webhook API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import WebhookEvent
from app.schemas import WebhookEventDetailResponse, WebhookEventListResponse
from app.services.webhook_handler import WebhookHandler, verify_github_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Type alias for database dependency
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/github", status_code=200)
async def receive_github_webhook(
    request: Request,
    db: DB,
    x_github_event: Annotated[str, Header()],
    x_github_delivery: Annotated[str, Header()],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
):
    """Receive and process GitHub webhook events.

    This endpoint validates the webhook signature, stores the event,
    and processes it to potentially create a new pipeline.

    Returns 200 OK immediately to acknowledge receipt (GitHub best practice).
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if secret is configured
    if settings.github_webhook_secret:
        if not x_hub_signature_256:
            logger.warning("Missing signature header from %s", x_github_delivery)
            raise HTTPException(status_code=401, detail="Missing signature")

        if not verify_github_signature(
            body, x_hub_signature_256, settings.github_webhook_secret
        ):
            logger.warning("Invalid signature for delivery %s", x_github_delivery)
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract repository info
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name", "unknown/unknown")
    action = payload.get("action")

    logger.info(
        "Received webhook: event=%s action=%s repo=%s delivery=%s",
        x_github_event,
        action,
        repo_full_name,
        x_github_delivery,
    )

    # Initialize handler
    handler = WebhookHandler(db)

    # Check for duplicate
    if await handler.is_duplicate(x_github_delivery):
        logger.info("Ignoring duplicate delivery %s", x_github_delivery)
        return {"status": "ignored", "reason": "duplicate"}

    # Store event
    event = await handler.store_event(
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        action=action,
        repo=repo_full_name,
        payload=payload,
    )

    # Process event (may create pipeline)
    pipeline = await handler.process_event(event)

    return {
        "status": "processed",
        "event_id": event.id,
        "pipeline_id": pipeline.id if pipeline else None,
    }


@router.get("/events", response_model=list[WebhookEventListResponse])
async def list_webhook_events(db: DB, limit: int = 50, offset: int = 0):
    """List webhook events for debugging."""
    result = await db.execute(
        select(WebhookEvent)
        .order_by(WebhookEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/events/{event_id}", response_model=WebhookEventDetailResponse)
async def get_webhook_event(event_id: str, db: DB):
    """Get webhook event details including full payload."""
    result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event
