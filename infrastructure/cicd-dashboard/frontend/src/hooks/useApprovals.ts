import { useState, useEffect, useCallback } from 'react';
import { approvalApi } from '@/api/client';
import type { PendingApproval } from '@/types';

interface UseApprovalsResult {
  approvals: PendingApproval[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  approve: (id: string, user: string, comment?: string) => Promise<void>;
  reject: (id: string, user: string, reason?: string) => Promise<void>;
}

export function useApprovals(): UseApprovalsResult {
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApprovals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await approvalApi.listPending();
      setApprovals(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch approvals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const approve = useCallback(
    async (id: string, user: string, comment?: string) => {
      await approvalApi.approve(id, user, comment);
      await fetchApprovals();
    },
    [fetchApprovals]
  );

  const reject = useCallback(
    async (id: string, user: string, reason?: string) => {
      await approvalApi.reject(id, user, reason);
      await fetchApprovals();
    },
    [fetchApprovals]
  );

  return { approvals, loading, error, refetch: fetchApprovals, approve, reject };
}
