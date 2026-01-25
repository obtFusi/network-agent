"""Event bus for Server-Sent Events (SSE) pub/sub."""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from app.schemas.event import (
    ApprovalRequestedPayload,
    ApprovalResolvedPayload,
    EventType,
    HeartbeatPayload,
    PipelineCompletedPayload,
    PipelineCreatedPayload,
    PipelineUpdatedPayload,
    SSEEvent,
    StepCompletedPayload,
    StepLogPayload,
    StepStartedPayload,
)

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory event bus with async pub/sub for SSE.

    Features:
    - Multiple subscribers can receive events
    - Per-pipeline filtering for log streams
    - Heartbeat mechanism to keep connections alive
    - Event buffering for late-joining subscribers
    """

    def __init__(self, buffer_size: int = 100):
        """Initialize the event bus.

        Args:
            buffer_size: Number of events to buffer for replay
        """
        self._subscribers: dict[str, asyncio.Queue[SSEEvent]] = {}
        self._buffer: list[SSEEvent] = []
        self._buffer_size = buffer_size
        self._lock = asyncio.Lock()
        self._event_counter = 0

    async def subscribe(
        self,
        pipeline_id: str | None = None,
        replay: bool = False,
    ) -> AsyncIterator[SSEEvent]:
        """Subscribe to events.

        Args:
            pipeline_id: Optional filter for specific pipeline events
            replay: Whether to replay buffered events

        Yields:
            SSEEvent objects as they arrive
        """
        subscriber_id = str(uuid.uuid4())
        queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        async with self._lock:
            self._subscribers[subscriber_id] = queue
            logger.info(
                "Subscriber %s connected (pipeline_filter=%s, replay=%s)",
                subscriber_id,
                pipeline_id,
                replay,
            )

            # Replay buffered events if requested
            if replay:
                for event in self._buffer:
                    if self._matches_filter(event, pipeline_id):
                        await queue.put(event)

        try:
            while True:
                event = await queue.get()
                if self._matches_filter(event, pipeline_id):
                    yield event
        finally:
            async with self._lock:
                self._subscribers.pop(subscriber_id, None)
                logger.info("Subscriber %s disconnected", subscriber_id)

    def _matches_filter(self, event: SSEEvent, pipeline_id: str | None) -> bool:
        """Check if event matches the pipeline filter.

        Args:
            event: The event to check
            pipeline_id: Optional pipeline ID to filter by

        Returns:
            True if event matches filter or no filter is set
        """
        if pipeline_id is None:
            return True

        # System events always pass through
        if event.type in (EventType.HEARTBEAT, EventType.ERROR):
            return True

        # Check for pipeline_id in event data
        return (
            event.data.get("pipeline_id") == pipeline_id
            or event.data.get("id") == pipeline_id
        )

    async def publish(self, event: SSEEvent) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        async with self._lock:
            # Assign event ID
            self._event_counter += 1
            event.id = str(self._event_counter)

            # Add to buffer
            self._buffer.append(event)
            if len(self._buffer) > self._buffer_size:
                self._buffer.pop(0)

            # Distribute to all subscribers
            for subscriber_id, queue in self._subscribers.items():
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(
                        "Queue full for subscriber %s, dropping event", subscriber_id
                    )

        logger.debug("Published event %s (id=%s)", event.type.value, event.id)

    async def publish_pipeline_created(
        self,
        pipeline_id: str,
        repo: str,
        version: str | None,
        status: str,
        trigger: str,
        created_at: datetime,
    ) -> None:
        """Publish a pipeline.created event."""
        payload = PipelineCreatedPayload(
            id=pipeline_id,
            repo=repo,
            version=version,
            status=status,
            trigger=trigger,
            created_at=created_at,
        )
        await self.publish(
            SSEEvent(type=EventType.PIPELINE_CREATED, data=payload.model_dump())
        )

    async def publish_pipeline_updated(
        self,
        pipeline_id: str,
        status: str,
        current_step: str | None = None,
    ) -> None:
        """Publish a pipeline.updated event."""
        payload = PipelineUpdatedPayload(
            id=pipeline_id,
            status=status,
            current_step=current_step,
        )
        await self.publish(
            SSEEvent(type=EventType.PIPELINE_UPDATED, data=payload.model_dump())
        )

    async def publish_pipeline_completed(
        self,
        pipeline_id: str,
        status: str,
        duration_seconds: float | None = None,
    ) -> None:
        """Publish a pipeline.completed event."""
        payload = PipelineCompletedPayload(
            id=pipeline_id,
            status=status,
            duration_seconds=duration_seconds,
        )
        await self.publish(
            SSEEvent(type=EventType.PIPELINE_COMPLETED, data=payload.model_dump())
        )

    async def publish_step_started(
        self,
        pipeline_id: str,
        step_id: str,
        name: str,
        stage: str,
    ) -> None:
        """Publish a step.started event."""
        payload = StepStartedPayload(
            pipeline_id=pipeline_id,
            step_id=step_id,
            name=name,
            stage=stage,
        )
        await self.publish(
            SSEEvent(type=EventType.STEP_STARTED, data=payload.model_dump())
        )

    async def publish_step_completed(
        self,
        pipeline_id: str,
        step_id: str,
        name: str,
        status: str,
        duration_seconds: float | None = None,
        error: str | None = None,
    ) -> None:
        """Publish a step.completed event."""
        payload = StepCompletedPayload(
            pipeline_id=pipeline_id,
            step_id=step_id,
            name=name,
            status=status,
            duration_seconds=duration_seconds,
            error=error,
        )
        await self.publish(
            SSEEvent(type=EventType.STEP_COMPLETED, data=payload.model_dump())
        )

    async def publish_step_log(
        self,
        pipeline_id: str,
        step_id: str,
        line: str,
    ) -> None:
        """Publish a step.log event."""
        payload = StepLogPayload(
            pipeline_id=pipeline_id,
            step_id=step_id,
            line=line,
            timestamp=datetime.now(UTC),
        )
        await self.publish(SSEEvent(type=EventType.STEP_LOG, data=payload.model_dump()))

    async def publish_approval_requested(
        self,
        approval_id: str,
        pipeline_id: str,
        step_id: str,
        step_name: str,
        requested_at: datetime,
    ) -> None:
        """Publish an approval.requested event."""
        payload = ApprovalRequestedPayload(
            id=approval_id,
            pipeline_id=pipeline_id,
            step_id=step_id,
            step_name=step_name,
            requested_at=requested_at,
        )
        await self.publish(
            SSEEvent(type=EventType.APPROVAL_REQUESTED, data=payload.model_dump())
        )

    async def publish_approval_resolved(
        self,
        approval_id: str,
        pipeline_id: str,
        status: str,
        responded_by: str | None,
        responded_at: datetime | None,
    ) -> None:
        """Publish an approval.resolved event."""
        payload = ApprovalResolvedPayload(
            id=approval_id,
            pipeline_id=pipeline_id,
            status=status,
            responded_by=responded_by,
            responded_at=responded_at,
        )
        await self.publish(
            SSEEvent(type=EventType.APPROVAL_RESOLVED, data=payload.model_dump())
        )

    async def publish_heartbeat(self) -> None:
        """Publish a heartbeat event."""
        payload = HeartbeatPayload(timestamp=datetime.now(UTC))
        await self.publish(
            SSEEvent(type=EventType.HEARTBEAT, data=payload.model_dump())
        )

    @property
    def subscriber_count(self) -> int:
        """Return the number of active subscribers."""
        return len(self._subscribers)

    def clear_buffer(self) -> None:
        """Clear the event buffer."""
        self._buffer.clear()


# Global event bus instance
event_bus = EventBus()


async def heartbeat_task(interval: float = 30.0) -> None:
    """Background task to send periodic heartbeats.

    Args:
        interval: Seconds between heartbeats (default 30s)
    """
    while True:
        await asyncio.sleep(interval)
        if event_bus.subscriber_count > 0:
            await event_bus.publish_heartbeat()
            logger.debug("Heartbeat sent to %d subscribers", event_bus.subscriber_count)
