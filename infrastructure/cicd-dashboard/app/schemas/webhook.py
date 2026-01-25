"""Pydantic schemas for Webhook API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WebhookEventResponse(BaseModel):
    """Response schema for a webhook event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    github_delivery_id: str
    event_type: str
    action: str | None = None
    repo: str
    processed: bool
    processed_at: datetime | None = None
    pipeline_id: str | None = None
    error: str | None = None
    created_at: datetime


class WebhookEventListResponse(BaseModel):
    """Response schema for webhook event list (without payload)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    github_delivery_id: str
    event_type: str
    action: str | None = None
    repo: str
    processed: bool
    pipeline_id: str | None = None
    created_at: datetime


class WebhookEventDetailResponse(WebhookEventResponse):
    """Response schema for webhook event with full payload."""

    payload: dict
