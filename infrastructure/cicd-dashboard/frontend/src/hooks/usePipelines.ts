import { useState, useEffect, useCallback } from 'react';
import { pipelineApi } from '@/api/client';
import type { Pipeline } from '@/types';

interface UsePipelinesResult {
  pipelines: Pipeline[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function usePipelines(limit = 50): UsePipelinesResult {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPipelines = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await pipelineApi.list(limit);
      setPipelines(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipelines');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  return { pipelines, loading, error, refetch: fetchPipelines };
}

interface UsePipelineResult {
  pipeline: Pipeline | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function usePipeline(id: string | undefined): UsePipelineResult {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPipeline = useCallback(async () => {
    if (!id) {
      setPipeline(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await pipelineApi.get(id);
      setPipeline(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipeline');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPipeline();
  }, [fetchPipeline]);

  return { pipeline, loading, error, refetch: fetchPipeline };
}
