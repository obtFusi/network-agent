"""Pydantic schemas for Server-Sent Events (SSE)."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventType(str, Enum):
    """Event types for SSE streaming."""

    # Pipeline events
    PIPELINE_CREATED = "pipeline.created"
    PIPELINE_UPDATED = "pipeline.updated"
    PIPELINE_COMPLETED = "pipeline.completed"

    # Step events
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_LOG = "step.log"

    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"

    # System events
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class PipelineCreatedPayload(BaseModel):
    """Payload for pipeline.created event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repo: str
    version: str | None
    status: str
    trigger: str
    created_at: datetime


class PipelineUpdatedPayload(BaseModel):
    """Payload for pipeline.updated event."""

    id: str
    status: str
    current_step: str | None = None


class PipelineCompletedPayload(BaseModel):
    """Payload for pipeline.completed event."""

    id: str
    status: str
    duration_seconds: float | None = None


class StepStartedPayload(BaseModel):
    """Payload for step.started event."""

    pipeline_id: str
    step_id: str
    name: str
    stage: str


class StepCompletedPayload(BaseModel):
    """Payload for step.completed event."""

    pipeline_id: str
    step_id: str
    name: str
    status: str
    duration_seconds: float | None = None
    error: str | None = None


class StepLogPayload(BaseModel):
    """Payload for step.log event."""

    pipeline_id: str
    step_id: str
    line: str
    timestamp: datetime


class ApprovalRequestedPayload(BaseModel):
    """Payload for approval.requested event."""

    id: str
    pipeline_id: str
    step_id: str
    step_name: str
    requested_at: datetime


class ApprovalResolvedPayload(BaseModel):
    """Payload for approval.resolved event."""

    id: str
    pipeline_id: str
    status: str
    responded_by: str | None
    responded_at: datetime | None


class HeartbeatPayload(BaseModel):
    """Payload for heartbeat event."""

    timestamp: datetime
    server_id: str = "cicd-dashboard"


class ErrorPayload(BaseModel):
    """Payload for error event."""

    message: str
    code: str | None = None


class SSEEvent(BaseModel):
    """Server-Sent Event wrapper."""

    type: EventType
    data: dict[str, Any]
    id: str | None = None
    retry: int | None = None

    def format(self) -> str:
        """Format event as SSE string."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.type.value}")
        # Convert data to JSON string
        import json

        lines.append(f"data: {json.dumps(self.data, default=str)}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append("")  # Empty line to end the event
        return "\n".join(lines) + "\n"
