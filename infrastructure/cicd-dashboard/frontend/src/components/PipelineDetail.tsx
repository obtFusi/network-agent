import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { StatusBadge } from './StatusBadge';
import { LogViewer } from './LogViewer';
import { pipelineApi } from '@/api/client';
import { useEventStream } from '@/hooks/useEventStream';
import { clsx } from 'clsx';
import type { Pipeline, PipelineStep, SSEEventType } from '@/types';

export function PipelineDetail() {
  const { id } = useParams<{ id: string }>();
  const [pipeline, setPipeline] = useState<Pipeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStep, setSelectedStep] = useState<PipelineStep | null>(null);

  const fetchPipeline = useCallback(async () => {
    if (!id) return;

    try {
      setError(null);
      const data = await pipelineApi.get(id);
      setPipeline(data);

      // Auto-select first step with logs or running step
      if (data.steps && data.steps.length > 0 && !selectedStep) {
        const runningStep = data.steps.find((s) => s.status === 'running');
        const stepWithLogs = data.steps.find((s) => s.logs);
        setSelectedStep(runningStep || stepWithLogs || data.steps[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch pipeline');
    } finally {
      setLoading(false);
    }
  }, [id, selectedStep]);

  useEffect(() => {
    fetchPipeline();
  }, [fetchPipeline]);

  // Listen for pipeline-specific events
  const handleEvent = useCallback(
    (type: SSEEventType) => {
      if (
        type === 'pipeline.updated' ||
        type === 'pipeline.completed' ||
        type === 'step.started' ||
        type === 'step.completed' ||
        type === 'step.log'
      ) {
        fetchPipeline();
      }
    },
    [fetchPipeline]
  );

  useEventStream({ pipelineId: id, onEvent: handleEvent });

  const handleAbort = async () => {
    if (!pipeline) return;
    try {
      await pipelineApi.abort(pipeline.id);
      fetchPipeline();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to abort pipeline');
    }
  };

  const handleRetry = async (stepId: string) => {
    if (!pipeline) return;
    try {
      await pipelineApi.retry(pipeline.id, stepId);
      fetchPipeline();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry step');
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
        <p className="mt-4 text-gray-500">Loading pipeline...</p>
      </div>
    );
  }

  if (error || !pipeline) {
    return (
      <div className="card card-body text-center py-12">
        <p className="text-red-600">{error || 'Pipeline not found'}</p>
        <Link to="/" className="btn btn-primary mt-4">
          Back to Pipelines
        </Link>
      </div>
    );
  }

  const createdAt = new Date(pipeline.created_at);

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/"
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block"
        >
          &larr; Back to Pipelines
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{pipeline.repo}</h1>
            <p className="mt-1 text-gray-500">
              {pipeline.ref}
              {pipeline.version && ` • v${pipeline.version}`}
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Started {createdAt.toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={pipeline.status} size="lg" />
            {(pipeline.status === 'running' ||
              pipeline.status === 'waiting_approval') && (
              <button onClick={handleAbort} className="btn btn-danger text-sm">
                Abort
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Steps and Logs */}
      <div className="grid grid-cols-12 gap-6">
        {/* Steps List */}
        <div className="col-span-4">
          <div className="card">
            <div className="card-header">
              <h3 className="font-medium text-gray-900">Steps</h3>
            </div>
            <div className="divide-y divide-gray-200">
              {pipeline.steps?.map((step) => (
                <button
                  key={step.id}
                  onClick={() => setSelectedStep(step)}
                  className={clsx(
                    'w-full text-left p-4 hover:bg-gray-50 transition-colors',
                    selectedStep?.id === step.id && 'bg-blue-50'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900 truncate">
                        {step.name}
                      </p>
                      <p className="text-sm text-gray-500">{step.stage}</p>
                    </div>
                    <StatusBadge status={step.status} size="sm" />
                  </div>
                  {step.requires_approval && (
                    <p className="mt-1 text-xs text-purple-600">
                      Requires approval
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Step Detail / Logs */}
        <div className="col-span-8">
          {selectedStep ? (
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-gray-900">
                    {selectedStep.name}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    Stage: {selectedStep.stage}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={selectedStep.status} />
                  {selectedStep.status === 'failed' && (
                    <button
                      onClick={() => handleRetry(selectedStep.id)}
                      className="btn btn-primary text-sm"
                    >
                      Retry
                    </button>
                  )}
                </div>
              </div>
              <div className="card-body">
                {selectedStep.error && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm font-medium text-red-800">Error</p>
                    <p className="text-sm text-red-700 mt-1">
                      {selectedStep.error}
                    </p>
                  </div>
                )}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Logs
                  </h4>
                  <LogViewer
                    logs={selectedStep.logs}
                    autoScroll={selectedStep.status === 'running'}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="card card-body text-center py-12">
              <p className="text-gray-500">Select a step to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
