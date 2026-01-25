import { Link } from 'react-router-dom';
import { StatusBadge } from './StatusBadge';
import type { Pipeline } from '@/types';

interface PipelineCardProps {
  pipeline: Pipeline;
}

export function PipelineCard({ pipeline }: PipelineCardProps) {
  const createdAt = new Date(pipeline.created_at);
  const timeAgo = getTimeAgo(createdAt);

  return (
    <Link
      to={`/pipelines/${pipeline.id}`}
      className="card block hover:shadow-md transition-shadow"
    >
      <div className="card-body">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-medium text-gray-900 truncate">
              {pipeline.repo}
            </h3>
            <p className="mt-1 text-sm text-gray-500 truncate">
              {pipeline.ref} {pipeline.version && `• v${pipeline.version}`}
            </p>
          </div>
          <StatusBadge status={pipeline.status} />
        </div>

        <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
          <span className="flex items-center gap-1">
            <TriggerIcon trigger={pipeline.trigger} />
            {pipeline.trigger}
          </span>
          <span>{timeAgo}</span>
          <span className="font-mono text-xs">
            {pipeline.id.slice(0, 8)}
          </span>
        </div>
      </div>
    </Link>
  );
}

function TriggerIcon({ trigger }: { trigger: string }) {
  switch (trigger) {
    case 'webhook':
      return <WebhookIcon />;
    case 'manual':
      return <ManualIcon />;
    default:
      return null;
  }
}

function WebhookIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

function ManualIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  );
}

function getTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
