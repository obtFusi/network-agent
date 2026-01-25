import { useEffect } from 'react';
import { ApprovalCard } from './ApprovalCard';
import { useApprovals } from '@/hooks/useApprovals';
import { useEventStream } from '@/hooks/useEventStream';
import type { SSEEventType } from '@/types';

export function ApprovalQueue() {
  const { approvals, loading, error, refetch, approve, reject } = useApprovals();

  // Listen for approval events and refetch
  const handleEvent = (type: SSEEventType) => {
    if (type === 'approval.requested' || type === 'approval.resolved') {
      refetch();
    }
  };

  useEventStream({ onEvent: handleEvent });

  useEffect(() => {
    // Poll every 30 seconds as backup
    const interval = setInterval(refetch, 30000);
    return () => clearInterval(interval);
  }, [refetch]);

  if (loading && approvals.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto" />
        <p className="mt-4 text-gray-500">Loading approvals...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card card-body text-center py-12">
        <p className="text-red-600">{error}</p>
        <button onClick={refetch} className="btn btn-primary mt-4">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Pending Approvals
          {approvals.length > 0 && (
            <span className="ml-2 px-2 py-1 text-sm bg-purple-100 text-purple-800 rounded-full">
              {approvals.length}
            </span>
          )}
        </h2>
        <button onClick={refetch} className="btn btn-secondary text-sm">
          Refresh
        </button>
      </div>

      {approvals.length === 0 ? (
        <div className="card card-body text-center py-12">
          <p className="text-gray-500">No pending approvals</p>
          <p className="text-sm text-gray-400 mt-2">
            Approval requests will appear here when pipelines require manual
            approval.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={approve}
              onReject={reject}
            />
          ))}
        </div>
      )}
    </div>
  );
}
