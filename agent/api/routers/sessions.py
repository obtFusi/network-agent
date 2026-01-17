# Sessions Router
"""Session management endpoints for Network Agent API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from agent.api.dependencies import get_session_store
from agent.api.models.session import SessionCreate, SessionInfo, SessionList
from agent.api.services.session_store import SessionStore

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreate, status_code=201)
async def create_session(store: SessionStore = Depends(get_session_store)):
    """Create a new agent session."""
    session_id = store.create()
    session_info = store.get(session_id)
    return SessionCreate(
        session_id=str(session_id),
        created_at=session_info.created_at,
    )


@router.get("", response_model=SessionList)
async def list_sessions(store: SessionStore = Depends(get_session_store)):
    """List all active sessions."""
    sessions = store.list_all()
    return SessionList(
        sessions=[
            SessionInfo(
                session_id=s["session_id"],
                created_at=s["created_at"],
                message_count=s["message_count"],
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: UUID, store: SessionStore = Depends(get_session_store)
):
    """Get information about a specific session."""
    session_info = store.get(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(
        session_id=str(session_id),
        created_at=session_info.created_at,
        message_count=session_info.message_count,
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID, store: SessionStore = Depends(get_session_store)
):
    """Delete a session and free its resources."""
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return None
