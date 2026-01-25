"""Approval database model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.pipeline import ApprovalStatus, Base, utcnow


class Approval(Base):
    """An approval request for a pipeline step."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id"), nullable=False
    )
    step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipeline_steps.id"), nullable=False
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="approvals")
    step: Mapped["PipelineStep"] = relationship("PipelineStep")


# Forward reference for type hints
from app.models.pipeline import Pipeline, PipelineStep  # noqa: E402, F401
