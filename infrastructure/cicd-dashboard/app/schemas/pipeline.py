"""Pydantic schemas for Pipeline API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.pipeline import ApprovalStatus, PipelineStatus, StepStatus


class PipelineStepResponse(BaseModel):
    """Response schema for a pipeline step."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    stage: str
    status: StepStatus
    requires_approval: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    logs: str | None = None
    error: str | None = None


class ApprovalResponse(BaseModel):
    """Response schema for an approval request."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    step_id: str
    status: ApprovalStatus
    requested_at: datetime
    responded_at: datetime | None = None
    responded_by: str | None = None
    comment: str | None = None


class PipelineResponse(BaseModel):
    """Response schema for a pipeline with all details."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repo: str
    ref: str
    version: str | None = None
    status: PipelineStatus
    trigger: str
    trigger_data: dict | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    steps: list[PipelineStepResponse] = []
    approvals: list[ApprovalResponse] = []


class PipelineListResponse(BaseModel):
    """Response schema for pipeline list (without steps)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repo: str
    ref: str
    version: str | None = None
    status: PipelineStatus
    trigger: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class PipelineCreate(BaseModel):
    """Request schema for creating a new pipeline."""

    repo: str
    ref: str
    version: str | None = None
    trigger: str = "manual"
    trigger_data: dict | None = None
