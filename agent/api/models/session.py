# Session Models
"""Pydantic models for session management."""

from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Response model for session creation."""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(..., description="Session creation timestamp")


class SessionInfo(BaseModel):
    """Response model for session info."""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(..., description="Session creation timestamp")
    message_count: int = Field(..., description="Number of messages in session")


class SessionList(BaseModel):
    """Response model for listing sessions."""

    sessions: list[SessionInfo] = Field(
        default_factory=list, description="List of sessions"
    )
    total: int = Field(..., description="Total number of sessions")
