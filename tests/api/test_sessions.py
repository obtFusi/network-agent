# Session Endpoint Tests
"""Tests for session management endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

from agent.api.app import create_app

# Set dummy API key for tests (LLMClient requires it even if not used)
os.environ.setdefault("LLM_API_KEY", "test-api-key-not-used")


@pytest.fixture
def test_config():
    """Config for testing (mirrors config/settings.yaml structure)."""
    return {
        "version": "test",
        "llm": {
            "provider": {
                "model": "test-model",
                "base_url": "http://localhost:11434/v1",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            "context_limit": 4096,
        },
        "agent": {
            "max_iterations": 10,
            "verbose": False,
        },
        "scan": {
            "max_hosts_discovery": 65536,
            "max_hosts_portscan": 256,
            "exclude_ips": [],
            "timeout": 120,
            "tcp_ports": "22,80,443",
        },
    }


@pytest.fixture
def test_system_prompt():
    """Minimal system prompt for testing."""
    return "You are a test agent."


@pytest.fixture
def client(test_config, test_system_prompt):
    """Create test client with lifespan context."""
    app = create_app(test_config, test_system_prompt)
    with TestClient(app) as client:
        yield client


def test_create_session(client):
    """Test creating a new session."""
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert "created_at" in data


def test_list_sessions_empty(client):
    """Test listing sessions when none exist."""
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0


def test_list_sessions_with_session(client):
    """Test listing sessions after creating one."""
    # Create a session
    client.post("/api/v1/sessions")

    # List sessions
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["sessions"]) == 1


def test_get_session(client):
    """Test getting a specific session."""
    # Create a session
    create_response = client.post("/api/v1/sessions")
    session_id = create_response.json()["session_id"]

    # Get the session
    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["message_count"] == 0


def test_get_session_not_found(client):
    """Test getting a non-existent session."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/sessions/{fake_id}")
    assert response.status_code == 404


def test_delete_session(client):
    """Test deleting a session."""
    # Create a session
    create_response = client.post("/api/v1/sessions")
    session_id = create_response.json()["session_id"]

    # Delete the session
    response = client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 404


def test_delete_session_not_found(client):
    """Test deleting a non-existent session."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/api/v1/sessions/{fake_id}")
    assert response.status_code == 404
