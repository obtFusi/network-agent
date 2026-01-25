"""WebhookEvent database model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.pipeline import Base, utcnow


class WebhookEvent(Base):
    """A GitHub webhook event received by the dashboard."""

    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    github_delivery_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pipeline_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pipelines.id"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    # Relationships
    pipeline: Mapped["Pipeline | None"] = relationship("Pipeline")


# Forward reference for type hints
from app.models.pipeline import Pipeline  # noqa: E402, F401
