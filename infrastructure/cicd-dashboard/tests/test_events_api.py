"""Tests for Events API (SSE streaming endpoints)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.event_bus import event_bus


# Create transport for httpx to use ASGI app
transport = ASGITransport(app=app)


@pytest.fixture(autouse=True)
def clear_event_bus():
    """Clear event bus before each test."""
    event_bus.clear_buffer()
    yield
    event_bus.clear_buffer()


@pytest.mark.asyncio
async def test_get_event_stats():
    """Test getting event stream statistics."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/events/stats")

    assert response.status_code == 200
    data = response.json()
    assert "subscriber_count" in data
    assert "buffer_size" in data
    assert "buffer_capacity" in data
    assert data["buffer_capacity"] == 100  # Default buffer size


@pytest.mark.asyncio
async def test_get_event_stats_with_buffer():
    """Test event stats after buffering events."""
    # Add some events to buffer
    await event_bus.publish_heartbeat()
    await event_bus.publish_pipeline_updated(
        pipeline_id="test",
        status="running",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/events/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["buffer_size"] == 2


@pytest.mark.asyncio
async def test_event_stats_subscriber_count():
    """Test subscriber count in stats."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/events/stats")

    assert response.status_code == 200
    data = response.json()
    # No active subscribers in this test
    assert data["subscriber_count"] == 0


@pytest.mark.asyncio
async def test_event_buffer_capacity():
    """Test buffer capacity is correctly reported."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/events/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["buffer_capacity"] == 100  # Default


# Note: SSE streaming endpoint tests are omitted because they require
# long-running connections that don't terminate naturally.
# The EventBus tests in test_event_bus.py cover the core functionality.
# Manual testing or integration tests should verify SSE streaming works.
