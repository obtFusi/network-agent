"""Pydantic schemas for API request/response models."""

from app.schemas.event import (
    EventType,
    SSEEvent,
    PipelineCreatedPayload,
    PipelineUpdatedPayload,
    PipelineCompletedPayload,
    StepStartedPayload,
    StepCompletedPayload,
    StepLogPayload,
    ApprovalRequestedPayload,
    ApprovalResolvedPayload,
    HeartbeatPayload,
    ErrorPayload,
)
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineListResponse,
    PipelineStepResponse,
)
from app.schemas.webhook import (
    WebhookEventResponse,
    WebhookEventListResponse,
    WebhookEventDetailResponse,
)

__all__ = [
    # Event schemas
    "EventType",
    "SSEEvent",
    "PipelineCreatedPayload",
    "PipelineUpdatedPayload",
    "PipelineCompletedPayload",
    "StepStartedPayload",
    "StepCompletedPayload",
    "StepLogPayload",
    "ApprovalRequestedPayload",
    "ApprovalResolvedPayload",
    "HeartbeatPayload",
    "ErrorPayload",
    # Pipeline schemas
    "PipelineCreate",
    "PipelineResponse",
    "PipelineListResponse",
    "PipelineStepResponse",
    # Webhook schemas
    "WebhookEventResponse",
    "WebhookEventListResponse",
    "WebhookEventDetailResponse",
]
