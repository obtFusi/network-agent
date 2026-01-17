# Session Store
"""Thread-safe in-memory session management for Network Agent."""

import threading
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from agent.core import NetworkAgent


class SessionInfo:
    """Container for session data including the agent instance."""

    def __init__(self, agent: NetworkAgent):
        self.agent = agent
        self.created_at = datetime.now(timezone.utc)

    @property
    def message_count(self) -> int:
        """Number of user messages in the session (excluding system prompt)."""
        return len(self.agent.messages) - 1


class SessionStore:
    """Thread-safe store for managing agent sessions."""

    def __init__(self, config: dict, system_prompt: str):
        self._sessions: dict[UUID, SessionInfo] = {}
        self._lock = threading.Lock()
        self._config = config
        self._system_prompt = system_prompt

    def create(self) -> UUID:
        """Create a new session with a fresh agent instance."""
        session_id = uuid4()
        agent = NetworkAgent(self._config, self._system_prompt)
        with self._lock:
            self._sessions[session_id] = SessionInfo(agent)
        return session_id

    def get(self, session_id: UUID) -> Optional[SessionInfo]:
        """Get session info by ID, returns None if not found."""
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: UUID) -> bool:
        """Delete a session, returns True if deleted, False if not found."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def list_all(self) -> list[dict]:
        """List all sessions with metadata."""
        with self._lock:
            return [
                {
                    "session_id": str(sid),
                    "created_at": info.created_at,
                    "message_count": info.message_count,
                }
                for sid, info in self._sessions.items()
            ]

    def clear_all(self) -> int:
        """Clear all sessions, returns count of cleared sessions."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count
