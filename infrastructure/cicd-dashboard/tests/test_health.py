"""Tests for health check endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test that health endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
