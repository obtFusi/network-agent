import { useState, useEffect, useCallback, useRef } from 'react';
import { createEventSource } from '@/api/client';
import type { SSEEventType } from '@/types';

interface UseEventStreamOptions {
  pipelineId?: string;
  replay?: boolean;
  onEvent?: (type: SSEEventType, data: unknown) => void;
}

interface UseEventStreamResult {
  connected: boolean;
  error: string | null;
  lastEvent: { type: SSEEventType; data: unknown } | null;
  reconnect: () => void;
}

export function useEventStream(
  options: UseEventStreamOptions = {}
): UseEventStreamResult {
  const { pipelineId, replay = false, onEvent } = options;
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEvent, setLastEvent] = useState<{
    type: SSEEventType;
    data: unknown;
  } | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = createEventSource(pipelineId, replay);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
    };

    eventSource.onerror = () => {
      setConnected(false);
      setError('Connection lost. Reconnecting...');
    };

    // Listen to all event types
    const eventTypes: SSEEventType[] = [
      'pipeline.created',
      'pipeline.updated',
      'pipeline.completed',
      'step.started',
      'step.completed',
      'step.log',
      'approval.requested',
      'approval.resolved',
      'heartbeat',
    ];

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data);
          setLastEvent({ type, data });

          if (onEventRef.current) {
            onEventRef.current(type, data);
          }
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      });
    });

    return eventSource;
  }, [pipelineId, replay]);

  useEffect(() => {
    const eventSource = connect();

    return () => {
      eventSource.close();
    };
  }, [connect]);

  const reconnect = useCallback(() => {
    connect();
  }, [connect]);

  return { connected, error, lastEvent, reconnect };
}
