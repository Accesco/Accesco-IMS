import type { ApiError } from '../types/api';

interface ErrorStateProps {
  error: ApiError;
}

export default function ErrorState({ error }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex items-center rounded-md bg-red-500/10 px-2.5 py-0.5 text-sm font-medium text-red-400">
          {error.status || 'ERR'}
        </span>
        <span className="text-sm font-medium text-red-400">
          {error.statusText}
        </span>
        <span className="ml-auto text-xs text-txt-muted">
          {error.duration}ms
        </span>
      </div>
      <p className="text-sm text-red-300">{error.message}</p>
      {error.detail != null && (
        <pre className="mt-3 max-h-40 overflow-auto rounded-md bg-surface/50 p-3 text-xs text-txt-sec">
          {typeof error.detail === 'string'
            ? error.detail
            : JSON.stringify(error.detail, null, 2)}
        </pre>
      )}
    </div>
  );
}
