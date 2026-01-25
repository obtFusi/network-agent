"""Tests for Event Bus service."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.schemas.event import EventType, SSEEvent
from app.services.event_bus import EventBus


@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    return EventBus(buffer_size=10)


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish(event_bus):
    """Test basic subscribe and publish."""
    received_events = []

    async def collect_events():
        async for event in event_bus.subscribe():
            received_events.append(event)
            if len(received_events) >= 1:
                break

    # Start subscriber in background
    subscriber_task = asyncio.create_task(collect_events())

    # Wait for subscriber to be ready
    await asyncio.sleep(0.1)

    # Publish event
    await event_bus.publish_heartbeat()

    # Wait for event to be received
    await asyncio.wait_for(subscriber_task, timeout=1.0)

    assert len(received_events) == 1
    assert received_events[0].type == EventType.HEARTBEAT


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers(event_bus):
    """Test multiple subscribers receive same events."""
    received1 = []
    received2 = []

    async def collect_events1():
        async for event in event_bus.subscribe():
            received1.append(event)
            if len(received1) >= 1:
                break

    async def collect_events2():
        async for event in event_bus.subscribe():
            received2.append(event)
            if len(received2) >= 1:
                break

    task1 = asyncio.create_task(collect_events1())
    task2 = asyncio.create_task(collect_events2())

    await asyncio.sleep(0.1)

    await event_bus.publish_heartbeat()

    await asyncio.wait_for(asyncio.gather(task1, task2), timeout=1.0)

    assert len(received1) == 1
    assert len(received2) == 1


@pytest.mark.asyncio
async def test_event_bus_pipeline_filter(event_bus):
    """Test filtering events by pipeline ID."""
    received = []
    target_pipeline = "pipeline-123"

    async def collect_events():
        async for event in event_bus.subscribe(pipeline_id=target_pipeline):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collect_events())
    await asyncio.sleep(0.1)

    # Publish events for different pipelines
    await event_bus.publish_pipeline_updated(
        pipeline_id=target_pipeline,
        status="running",
    )
    await event_bus.publish_pipeline_updated(
        pipeline_id="other-pipeline",
        status="running",
    )
    await event_bus.publish_heartbeat()  # Should pass through filter

    await asyncio.wait_for(task, timeout=1.0)

    assert len(received) == 2
    # First event should be the matching pipeline
    assert received[0].data.get("id") == target_pipeline
    # Second event should be heartbeat (always passes)
    assert received[1].type == EventType.HEARTBEAT


@pytest.mark.asyncio
async def test_event_bus_replay(event_bus):
    """Test replaying buffered events."""
    # Publish events before subscribing
    await event_bus.publish_heartbeat()
    await event_bus.publish_pipeline_updated(
        pipeline_id="test-pipeline",
        status="running",
    )

    received = []

    async def collect_events():
        async for event in event_bus.subscribe(replay=True):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collect_events())
    await asyncio.wait_for(task, timeout=1.0)

    assert len(received) == 2


@pytest.mark.asyncio
async def test_event_bus_buffer_limit(event_bus):
    """Test buffer size limit."""
    # Buffer size is 10, publish 15 events
    for i in range(15):
        await event_bus.publish(
            SSEEvent(
                type=EventType.HEARTBEAT,
                data={"index": i},
            )
        )

    # Buffer should only have last 10 events
    assert len(event_bus._buffer) == 10
    assert event_bus._buffer[0].data["index"] == 5  # First kept event


@pytest.mark.asyncio
async def test_event_bus_event_ids(event_bus):
    """Test that events get sequential IDs."""
    await event_bus.publish_heartbeat()
    await event_bus.publish_heartbeat()
    await event_bus.publish_heartbeat()

    assert event_bus._buffer[0].id == "1"
    assert event_bus._buffer[1].id == "2"
    assert event_bus._buffer[2].id == "3"


@pytest.mark.asyncio
async def test_publish_pipeline_created(event_bus):
    """Test publishing pipeline created event."""
    now = datetime.now(UTC)

    await event_bus.publish_pipeline_created(
        pipeline_id="test-id",
        repo="test/repo",
        version="1.0.0",
        status="pending",
        trigger="manual",
        created_at=now,
    )

    assert len(event_bus._buffer) == 1
    event = event_bus._buffer[0]
    assert event.type == EventType.PIPELINE_CREATED
    assert event.data["id"] == "test-id"
    assert event.data["repo"] == "test/repo"
    assert event.data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_publish_step_started(event_bus):
    """Test publishing step started event."""
    await event_bus.publish_step_started(
        pipeline_id="pipeline-1",
        step_id="step-1",
        name="lint",
        stage="validate",
    )

    event = event_bus._buffer[0]
    assert event.type == EventType.STEP_STARTED
    assert event.data["pipeline_id"] == "pipeline-1"
    assert event.data["step_id"] == "step-1"
    assert event.data["name"] == "lint"
    assert event.data["stage"] == "validate"


@pytest.mark.asyncio
async def test_publish_step_completed(event_bus):
    """Test publishing step completed event."""
    await event_bus.publish_step_completed(
        pipeline_id="pipeline-1",
        step_id="step-1",
        name="lint",
        status="completed",
        duration_seconds=45.5,
    )

    event = event_bus._buffer[0]
    assert event.type == EventType.STEP_COMPLETED
    assert event.data["status"] == "completed"
    assert event.data["duration_seconds"] == 45.5


@pytest.mark.asyncio
async def test_publish_approval_requested(event_bus):
    """Test publishing approval requested event."""
    now = datetime.now(UTC)

    await event_bus.publish_approval_requested(
        approval_id="approval-1",
        pipeline_id="pipeline-1",
        step_id="step-1",
        step_name="pr-merge",
        requested_at=now,
    )

    event = event_bus._buffer[0]
    assert event.type == EventType.APPROVAL_REQUESTED
    assert event.data["id"] == "approval-1"
    assert event.data["step_name"] == "pr-merge"


@pytest.mark.asyncio
async def test_publish_approval_resolved(event_bus):
    """Test publishing approval resolved event."""
    now = datetime.now(UTC)

    await event_bus.publish_approval_resolved(
        approval_id="approval-1",
        pipeline_id="pipeline-1",
        status="approved",
        responded_by="user1",
        responded_at=now,
    )

    event = event_bus._buffer[0]
    assert event.type == EventType.APPROVAL_RESOLVED
    assert event.data["status"] == "approved"
    assert event.data["responded_by"] == "user1"


@pytest.mark.asyncio
async def test_subscriber_count(event_bus):
    """Test subscriber count tracking."""
    assert event_bus.subscriber_count == 0

    async def subscriber1():
        async for _ in event_bus.subscribe():
            break

    async def subscriber2():
        async for _ in event_bus.subscribe():
            break

    task1 = asyncio.create_task(subscriber1())
    task2 = asyncio.create_task(subscriber2())

    await asyncio.sleep(0.1)
    assert event_bus.subscriber_count == 2

    # Publish to release subscribers
    await event_bus.publish_heartbeat()
    await asyncio.gather(task1, task2)

    # Subscribers should be cleaned up
    assert event_bus.subscriber_count == 0


def test_sse_event_format():
    """Test SSE event formatting."""
    event = SSEEvent(
        type=EventType.PIPELINE_UPDATED,
        data={"id": "test-123", "status": "running"},
        id="42",
        retry=5000,
    )

    formatted = event.format()

    assert "id: 42" in formatted
    assert "event: pipeline.updated" in formatted
    assert "data:" in formatted
    assert '"id": "test-123"' in formatted
    assert '"status": "running"' in formatted
    assert "retry: 5000" in formatted


def test_clear_buffer(event_bus):
    """Test clearing the event buffer."""
    # Add some events to buffer (synchronously via _buffer)
    event_bus._buffer.append(SSEEvent(type=EventType.HEARTBEAT, data={}, id="1"))
    event_bus._buffer.append(SSEEvent(type=EventType.HEARTBEAT, data={}, id="2"))

    assert len(event_bus._buffer) == 2

    event_bus.clear_buffer()

    assert len(event_bus._buffer) == 0
