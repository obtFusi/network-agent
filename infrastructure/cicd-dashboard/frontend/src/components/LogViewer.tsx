import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';

interface LogViewerProps {
  logs: string | null;
  autoScroll?: boolean;
  maxHeight?: string;
}

interface LogLine {
  content: string;
  type: 'normal' | 'error' | 'warning';
}

export function LogViewer({
  logs,
  autoScroll = true,
  maxHeight = '400px',
}: LogViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(autoScroll);

  useEffect(() => {
    if (shouldAutoScroll.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = () => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // Auto-scroll if user is near the bottom
    shouldAutoScroll.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  if (!logs) {
    return (
      <div className="bg-gray-900 rounded-lg p-4 text-gray-400 text-sm font-mono">
        No logs available
      </div>
    );
  }

  const lines = parseLogLines(logs);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="bg-gray-900 rounded-lg overflow-auto log-viewer"
      style={{ maxHeight }}
    >
      <div className="p-2">
        {lines.map((line, index) => (
          <div
            key={index}
            className={clsx(
              'log-line',
              line.type === 'error' && 'log-line-error',
              line.type === 'warning' && 'log-line-warning'
            )}
          >
            <span className="text-gray-500 select-none mr-3">
              {String(index + 1).padStart(4, ' ')}
            </span>
            <span
              className={clsx(
                line.type === 'error' && 'text-red-400',
                line.type === 'warning' && 'text-yellow-400',
                line.type === 'normal' && 'text-gray-300'
              )}
            >
              {line.content}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function parseLogLines(logs: string): LogLine[] {
  return logs.split('\n').map((content) => {
    let type: LogLine['type'] = 'normal';

    const lowerContent = content.toLowerCase();
    if (
      lowerContent.includes('error') ||
      lowerContent.includes('failed') ||
      lowerContent.includes('exception')
    ) {
      type = 'error';
    } else if (
      lowerContent.includes('warning') ||
      lowerContent.includes('warn')
    ) {
      type = 'warning';
    }

    return { content, type };
  });
}
