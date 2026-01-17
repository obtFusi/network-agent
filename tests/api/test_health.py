# Health Endpoint Tests
"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient

from agent.api.app import create_app


@pytest.fixture
def test_config():
    """Minimal config for testing."""
    return {
        "version": "test",
        "llm": {
            "provider": {
                "model": "test-model",
                "base_url": "http://localhost:11434/v1",
            }
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


def test_health_endpoint(client):
    """Test /health returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint(client):
    """Test /ready returns status with checks."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama" in data
    assert "postgres" in data


def test_request_id_header(client):
    """Test that X-Request-ID header is returned."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers


def test_response_time_header(client):
    """Test that X-Response-Time header is returned."""
    response = client.get("/health")
    assert "X-Response-Time" in response.headers
    assert "ms" in response.headers["X-Response-Time"]
