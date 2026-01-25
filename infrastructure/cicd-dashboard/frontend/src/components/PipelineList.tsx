import { useEffect } from 'react';
import { PipelineCard } from './PipelineCard';
import { usePipelines } from '@/hooks/usePipelines';
import { useEventStream } from '@/hooks/useEventStream';
import type { SSEEventType } from '@/types';

export function PipelineList() {
  const { pipelines, loading, error, refetch } = usePipelines();

  // Listen for pipeline events and refetch
  const handleEvent = (type: SSEEventType) => {
    if (
      type === 'pipeline.created' ||
      type === 'pipeline.updated' ||
      type === 'pipeline.completed'
    ) {
      refetch();
    }
  };

  useEventStream({ onEvent: handleEvent });

  useEffect(() => {
    // Poll every 30 seconds as backup
    const interval = setInterval(refetch, 30000);
    return () => clearInterval(interval);
  }, [refetch]);

  if (loading && pipelines.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
        <p className="mt-4 text-gray-500">Loading pipelines...</p>
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

  if (pipelines.length === 0) {
    return (
      <div className="card card-body text-center py-12">
        <p className="text-gray-500">No pipelines yet</p>
        <p className="text-sm text-gray-400 mt-2">
          Pipelines will appear here when triggered via webhook or manual
          creation.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Pipelines</h2>
        <button onClick={refetch} className="btn btn-secondary text-sm">
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {pipelines.map((pipeline) => (
          <PipelineCard key={pipeline.id} pipeline={pipeline} />
        ))}
      </div>
    </div>
  );
}
