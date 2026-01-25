"""Pipeline and PipelineStep database models."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class PipelineStatus(str, enum.Enum):
    """Status of a pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(str, enum.Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ApprovalStatus(str, enum.Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Pipeline(Base):
    """A CI/CD pipeline execution."""

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    ref: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), default=PipelineStatus.PENDING
    )
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    steps: Mapped[list["PipelineStep"]] = relationship(
        "PipelineStep", back_populates="pipeline", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["Approval"]] = relationship(
        "Approval", back_populates="pipeline", cascade="all, delete-orphan"
    )


class PipelineStep(Base):
    """A step within a pipeline execution."""

    __tablename__ = "pipeline_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus), default=StepStatus.PENDING
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="steps")


# Import Approval here to avoid circular import
from app.models.approval import Approval  # noqa: E402, F401
