import type {
  Pipeline,
  PendingApproval,
  Approval,
  EventStats,
} from '@/types';

const API_BASE = '/api/v1';

// Generic fetch wrapper with error handling
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// Pipeline API
export const pipelineApi = {
  list: (limit = 50, offset = 0): Promise<Pipeline[]> =>
    fetchApi(`/pipelines?limit=${limit}&offset=${offset}`),

  get: (id: string): Promise<Pipeline> =>
    fetchApi(`/pipelines/${id}`),

  create: (data: {
    repo: string;
    ref: string;
    version?: string;
    trigger?: string;
    trigger_data?: Record<string, unknown>;
  }): Promise<Pipeline> =>
    fetchApi('/pipelines', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  start: (id: string): Promise<Pipeline> =>
    fetchApi(`/pipelines/${id}/start`, { method: 'POST' }),

  abort: (id: string): Promise<Pipeline> =>
    fetchApi(`/pipelines/${id}/abort`, { method: 'POST' }),

  retry: (pipelineId: string, stepId: string): Promise<unknown> =>
    fetchApi(`/pipelines/${pipelineId}/retry/${stepId}`, { method: 'POST' }),

  listRunning: (): Promise<Pipeline[]> =>
    fetchApi('/pipelines/running'),
};

// Approval API
export const approvalApi = {
  listPending: (): Promise<PendingApproval[]> =>
    fetchApi('/approvals/pending'),

  get: (id: string): Promise<Approval> =>
    fetchApi(`/approvals/${id}`),

  approve: (id: string, user: string, comment?: string): Promise<Approval> =>
    fetchApi(`/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ user, comment }),
    }),

  reject: (id: string, user: string, reason?: string): Promise<Approval> =>
    fetchApi(`/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ user, reason }),
    }),
};

// Events API
export const eventsApi = {
  getStats: (): Promise<EventStats> =>
    fetchApi('/events/stats'),
};

// SSE Client
export function createEventSource(
  pipelineId?: string,
  replay = false
): EventSource {
  let url = `${API_BASE}/events/stream`;
  const params = new URLSearchParams();

  if (pipelineId) {
    params.set('pipeline_id', pipelineId);
  }
  if (replay) {
    params.set('replay', 'true');
  }

  const queryString = params.toString();
  if (queryString) {
    url += `?${queryString}`;
  }

  return new EventSource(url);
}
