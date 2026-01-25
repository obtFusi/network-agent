"""Server-Sent Events (SSE) streaming API endpoints."""

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.services.event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


async def event_generator(
    request: Request,
    pipeline_id: str | None = None,
    replay: bool = False,
) -> AsyncIterator[str]:
    """Generate SSE events for streaming.

    Args:
        request: The FastAPI request (for disconnect detection)
        pipeline_id: Optional filter for specific pipeline
        replay: Whether to replay buffered events

    Yields:
        Formatted SSE event strings
    """
    try:
        async for event in event_bus.subscribe(pipeline_id=pipeline_id, replay=replay):
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("Client disconnected, stopping event stream")
                break

            yield event.format()

    except asyncio.CancelledError:
        logger.info("Event stream cancelled")
        raise


@router.get("/stream")
async def stream_events(
    request: Request,
    pipeline_id: str | None = Query(
        None, description="Filter events for a specific pipeline"
    ),
    replay: bool = Query(False, description="Replay buffered events on connect"),
) -> StreamingResponse:
    """Stream real-time events via Server-Sent Events (SSE).

    This endpoint establishes a long-running connection that streams events
    as they occur. Events are formatted according to the SSE specification.

    **Event Types:**
    - `pipeline.created` - New pipeline created
    - `pipeline.updated` - Pipeline status changed
    - `pipeline.completed` - Pipeline finished (success/failure)
    - `step.started` - Pipeline step started
    - `step.completed` - Pipeline step finished
    - `step.log` - Log line from a step
    - `approval.requested` - Approval gate waiting
    - `approval.resolved` - Approval granted/rejected
    - `heartbeat` - Keep-alive signal (every 30s)

    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/v1/events/stream');
    eventSource.addEventListener('pipeline.updated', (e) => {
        const data = JSON.parse(e.data);
        console.log('Pipeline updated:', data);
    });
    ```

    Args:
        pipeline_id: Optional filter for a specific pipeline's events
        replay: If true, replay recent buffered events on connect

    Returns:
        StreamingResponse with SSE content type
    """
    logger.info(
        "SSE stream started (pipeline_id=%s, replay=%s)",
        pipeline_id,
        replay,
    )

    return StreamingResponse(
        event_generator(request, pipeline_id=pipeline_id, replay=replay),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/stream/{pipeline_id}")
async def stream_pipeline_events(
    request: Request,
    pipeline_id: str,
    replay: bool = Query(False, description="Replay buffered events on connect"),
) -> StreamingResponse:
    """Stream events for a specific pipeline.

    This is a convenience endpoint equivalent to `/stream?pipeline_id=<id>`.
    Only events related to the specified pipeline will be streamed.

    Args:
        pipeline_id: The pipeline ID to filter events for
        replay: If true, replay recent buffered events on connect

    Returns:
        StreamingResponse with SSE content type
    """
    logger.info(
        "SSE stream started for pipeline %s (replay=%s)",
        pipeline_id,
        replay,
    )

    return StreamingResponse(
        event_generator(request, pipeline_id=pipeline_id, replay=replay),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stats")
async def get_event_stats() -> dict:
    """Get event stream statistics.

    Returns current subscriber count and buffer status.
    Useful for monitoring and debugging.

    Returns:
        Dict with subscriber_count and buffer_size
    """
    return {
        "subscriber_count": event_bus.subscriber_count,
        "buffer_size": len(event_bus._buffer),
        "buffer_capacity": event_bus._buffer_size,
    }
