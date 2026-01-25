import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { PendingApproval } from '@/types';

interface ApprovalCardProps {
  approval: PendingApproval;
  onApprove: (id: string, user: string, comment?: string) => Promise<void>;
  onReject: (id: string, user: string, reason?: string) => Promise<void>;
}

export function ApprovalCard({
  approval,
  onApprove,
  onReject,
}: ApprovalCardProps) {
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState<'approve' | 'reject' | null>(null);
  const [comment, setComment] = useState('');
  const [user, setUser] = useState('');

  const requestedAt = new Date(approval.requested_at);
  const timeAgo = getTimeAgo(requestedAt);

  const handleAction = async (action: 'approve' | 'reject') => {
    if (!user.trim()) return;

    setLoading(true);
    try {
      if (action === 'approve') {
        await onApprove(approval.id, user, comment || undefined);
      } else {
        await onReject(approval.id, user, comment || undefined);
      }
      setShowForm(null);
      setComment('');
      setUser('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-medium text-gray-900">
              {approval.step_name}
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Stage: {approval.stage}
            </p>
            <Link
              to={`/pipelines/${approval.pipeline_id}`}
              className="mt-1 text-sm text-blue-600 hover:text-blue-800"
            >
              {approval.repo} &rarr;
            </Link>
          </div>
          <div className="text-sm text-gray-500">{timeAgo}</div>
        </div>

        {showForm ? (
          <div className="mt-4 space-y-3">
            <div>
              <label htmlFor={`user-${approval.id}`} className="label">
                Your Name
              </label>
              <input
                id={`user-${approval.id}`}
                type="text"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                className="input"
                placeholder="Enter your name"
                disabled={loading}
              />
            </div>
            <div>
              <label htmlFor={`comment-${approval.id}`} className="label">
                {showForm === 'reject' ? 'Reason' : 'Comment'} (optional)
              </label>
              <textarea
                id={`comment-${approval.id}`}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="input"
                rows={2}
                placeholder={
                  showForm === 'reject'
                    ? 'Why are you rejecting?'
                    : 'Add a comment...'
                }
                disabled={loading}
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleAction(showForm)}
                disabled={loading || !user.trim()}
                className={
                  showForm === 'approve' ? 'btn btn-success' : 'btn btn-danger'
                }
              >
                {loading
                  ? 'Processing...'
                  : showForm === 'approve'
                    ? 'Confirm Approve'
                    : 'Confirm Reject'}
              </button>
              <button
                onClick={() => {
                  setShowForm(null);
                  setComment('');
                  setUser('');
                }}
                disabled={loading}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => setShowForm('approve')}
              className="btn btn-success"
            >
              Approve
            </button>
            <button
              onClick={() => setShowForm('reject')}
              className="btn btn-danger"
            >
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function getTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
