// Pipeline types
export type PipelineStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'aborted'
  | 'waiting_approval';

export type StepStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface Pipeline {
  id: string;
  repo: string;
  ref: string;
  version: string | null;
  status: PipelineStatus;
  trigger: string;
  trigger_data: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
  steps?: PipelineStep[];
  approvals?: Approval[];
}

export interface PipelineStep {
  id: string;
  pipeline_id: string;
  name: string;
  stage: string;
  status: StepStatus;
  requires_approval: boolean;
  started_at: string | null;
  completed_at: string | null;
  logs: string | null;
  error: string | null;
}

export interface Approval {
  id: string;
  pipeline_id: string;
  step_id: string;
  status: ApprovalStatus;
  requested_at: string;
  responded_at: string | null;
  responded_by: string | null;
  comment: string | null;
}

export interface PendingApproval {
  id: string;
  pipeline_id: string;
  step_id: string;
  step_name: string;
  stage: string;
  repo: string;
  requested_at: string;
}

// SSE Event types
export type SSEEventType =
  | 'pipeline.created'
  | 'pipeline.updated'
  | 'pipeline.completed'
  | 'step.started'
  | 'step.completed'
  | 'step.log'
  | 'approval.requested'
  | 'approval.resolved'
  | 'heartbeat';

export interface SSEEvent<T = unknown> {
  type: SSEEventType;
  data: T;
  id?: string;
}

export interface PipelineUpdatedEvent {
  id: string;
  status: PipelineStatus;
  current_step: string | null;
}

export interface StepCompletedEvent {
  pipeline_id: string;
  step_id: string;
  name: string;
  status: StepStatus;
  duration_seconds: number | null;
  error: string | null;
}

export interface ApprovalRequestedEvent {
  id: string;
  pipeline_id: string;
  step_id: string;
  step_name: string;
  requested_at: string;
}

// API response types
export interface EventStats {
  subscriber_count: number;
  buffer_size: number;
  buffer_capacity: number;
}
