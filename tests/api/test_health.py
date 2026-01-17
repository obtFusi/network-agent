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


class TestIsSafeUrl:
    """Tests for URL validation in health checks."""

    def test_localhost_is_safe(self):
        """Test localhost URLs are considered safe."""
        from agent.api.routers.health import _is_safe_url

        assert _is_safe_url("http://localhost:11434/api/tags") is True
        assert _is_safe_url("http://127.0.0.1:11434/api/tags") is True

    def test_docker_services_are_safe(self):
        """Test Docker service names are considered safe."""
        from agent.api.routers.health import _is_safe_url

        assert _is_safe_url("http://ollama:11434/api/tags") is True
        assert _is_safe_url("http://host.docker.internal:11434") is True

    def test_private_networks_are_safe(self):
        """Test private network IPs are considered safe."""
        from agent.api.routers.health import _is_safe_url

        assert _is_safe_url("http://10.0.0.1:11434/api/tags") is True
        assert _is_safe_url("http://172.16.0.1:11434/api/tags") is True
        assert _is_safe_url("http://192.168.1.100:11434/api/tags") is True

    def test_external_urls_are_unsafe(self):
        """Test external URLs are rejected."""
        from agent.api.routers.health import _is_safe_url

        assert _is_safe_url("http://example.com/api") is False
        assert _is_safe_url("http://api.openai.com/v1") is False
        assert _is_safe_url("http://evil.attacker.com") is False

    def test_invalid_urls_are_unsafe(self):
        """Test invalid URLs are rejected."""
        from agent.api.routers.health import _is_safe_url

        assert _is_safe_url("") is False
        assert _is_safe_url("not-a-url") is False
