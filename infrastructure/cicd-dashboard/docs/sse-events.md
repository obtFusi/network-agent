# Server-Sent Events (SSE) API

Real-time event streaming for the CI/CD Dashboard.

## Overview

The SSE endpoint allows clients to receive real-time updates about pipeline execution, step progress, and approval requests without polling.

## Endpoints

### `GET /api/v1/events/stream`

Main SSE streaming endpoint.

**Query Parameters:**
- `pipeline_id` (optional): Filter events for a specific pipeline
- `replay` (optional): If true, replay buffered events on connect

**Headers:**
```
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### `GET /api/v1/events/stream/{pipeline_id}`

Convenience endpoint for pipeline-specific events.

### `GET /api/v1/events/stats`

Get current event stream statistics.

**Response:**
```json
{
  "subscriber_count": 3,
  "buffer_size": 42,
  "buffer_capacity": 100
}
```

## Event Types

| Event | Payload | Description |
|-------|---------|-------------|
| `pipeline.created` | `{id, repo, version, status, trigger, created_at}` | New pipeline created |
| `pipeline.updated` | `{id, status, current_step}` | Pipeline status changed |
| `pipeline.completed` | `{id, status, duration_seconds}` | Pipeline finished |
| `step.started` | `{pipeline_id, step_id, name, stage}` | Step execution started |
| `step.completed` | `{pipeline_id, step_id, name, status, duration_seconds, error}` | Step finished |
| `step.log` | `{pipeline_id, step_id, line, timestamp}` | Log line from step |
| `approval.requested` | `{id, pipeline_id, step_id, step_name, requested_at}` | Approval needed |
| `approval.resolved` | `{id, pipeline_id, status, responded_by, responded_at}` | Approval granted/rejected |
| `heartbeat` | `{timestamp, server_id}` | Keep-alive signal (every 30s) |

## Usage Examples

### JavaScript (Browser)

```javascript
const eventSource = new EventSource('/api/v1/events/stream');

// Listen to all events
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', event.type, data);
};

// Listen to specific event types
eventSource.addEventListener('pipeline.updated', (event) => {
  const data = JSON.parse(event.data);
  updatePipelineUI(data.id, data.status);
});

eventSource.addEventListener('approval.requested', (event) => {
  const data = JSON.parse(event.data);
  showApprovalNotification(data);
});

// Handle errors
eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Browser automatically reconnects
};
```

### Filter by Pipeline

```javascript
const pipelineId = 'abc-123';
const eventSource = new EventSource(
  `/api/v1/events/stream?pipeline_id=${pipelineId}`
);
```

### Replay Buffered Events

```javascript
// Get events that occurred before connecting
const eventSource = new EventSource('/api/v1/events/stream?replay=true');
```

### Python Client

```python
import httpx

async def stream_events():
    async with httpx.AsyncClient() as client:
        async with client.stream('GET', 'http://localhost:8000/api/v1/events/stream') as response:
            async for line in response.aiter_lines():
                if line.startswith('data:'):
                    data = json.loads(line[5:])
                    print(f"Event: {data}")
```

## Event Bus Architecture

The event bus uses an in-memory pub/sub pattern:

```
┌─────────────────┐     ┌─────────────────┐
│ PipelineExecutor│────▶│    EventBus     │
└─────────────────┘     │  (In-Memory)    │
                        │                 │
┌─────────────────┐     │  ┌───────────┐  │     ┌───────────┐
│ ApprovalService │────▶│  │  Buffer   │  │────▶│ Subscriber│
└─────────────────┘     │  │ (100 max) │  │     └───────────┘
                        │  └───────────┘  │     ┌───────────┐
                        │                 │────▶│ Subscriber│
                        └─────────────────┘     └───────────┘
```

Features:
- **Multiple subscribers**: All connected clients receive all events
- **Pipeline filtering**: Clients can filter for specific pipeline events
- **Event buffering**: Last 100 events are buffered for replay
- **Heartbeat**: 30-second keep-alive signals
- **Auto-cleanup**: Disconnected subscribers are removed automatically

## Configuration

The event bus uses sensible defaults:

| Setting | Default | Description |
|---------|---------|-------------|
| Buffer size | 100 | Number of events to keep for replay |
| Heartbeat interval | 30s | Keep-alive signal frequency |
