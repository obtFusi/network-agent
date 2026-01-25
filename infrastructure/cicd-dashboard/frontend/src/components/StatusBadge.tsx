import { clsx } from 'clsx';
import type { PipelineStatus, StepStatus, ApprovalStatus } from '@/types';

type Status = PipelineStatus | StepStatus | ApprovalStatus;

interface StatusBadgeProps {
  status: Status;
  size?: 'sm' | 'md' | 'lg';
}

const statusConfig: Record<
  Status,
  { label: string; color: string; animate?: boolean }
> = {
  pending: { label: 'Pending', color: 'bg-gray-100 text-gray-800' },
  running: {
    label: 'Running',
    color: 'bg-blue-100 text-blue-800',
    animate: true,
  },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-800' },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-800' },
  aborted: { label: 'Aborted', color: 'bg-orange-100 text-orange-800' },
  waiting_approval: {
    label: 'Waiting',
    color: 'bg-purple-100 text-purple-800',
    animate: true,
  },
  skipped: { label: 'Skipped', color: 'bg-gray-100 text-gray-600' },
  approved: { label: 'Approved', color: 'bg-green-100 text-green-800' },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-800' },
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status] || {
    label: status,
    color: 'bg-gray-100 text-gray-800',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        config.color,
        sizeClasses[size],
        config.animate && 'status-running'
      )}
    >
      {config.animate && (
        <span className="w-2 h-2 mr-1.5 rounded-full bg-current opacity-75" />
      )}
      {config.label}
    </span>
  );
}
