# API Dependencies
"""FastAPI dependency injection for Network Agent API."""

from fastapi import Request

from agent.api.services.session_store import SessionStore


def get_config(request: Request) -> dict:
    """Get application config from request state."""
    return request.app.state.config


def get_session_store(request: Request) -> SessionStore:
    """Get session store from request state."""
    return request.app.state.session_store
