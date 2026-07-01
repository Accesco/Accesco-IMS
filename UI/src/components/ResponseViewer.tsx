import { useState, useCallback, useMemo } from 'react';
import type { ApiResponse } from '../types/api';
import JsonEditor from './JsonEditor';
import { formatJson } from '../utils/formatJson';
import { copyToClipboard } from '../utils/copyToClipboard';

interface ResponseViewerProps {
  response: ApiResponse;
  isDark: boolean;
  onClear: () => void;
}

function getStatusColor(status: number): string {
  if (status >= 200 && status < 300) return 'bg-emerald-500/15 text-emerald-400';
  if (status >= 300 && status < 400) return 'bg-blue-500/15 text-blue-400';
  if (status >= 400 && status < 500) return 'bg-amber-500/15 text-amber-400';
  return 'bg-red-500/15 text-red-400';
}

function getDurationColor(ms: number): string {
  if (ms < 200) return 'text-emerald-400';
  if (ms < 1000) return 'text-amber-400';
  return 'text-red-400';
}

export default function ResponseViewer({
  response,
  isDark,
  onClear,
}: ResponseViewerProps) {
  const [showHeaders, setShowHeaders] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const formattedBody = useMemo(
    () => formatJson(response.data),
    [response.data]
  );

  const handleCopy = useCallback(async () => {
    const ok = await copyToClipboard(formattedBody);
    setCopyFeedback(ok ? 'Copied!' : 'Failed');
    setTimeout(() => setCopyFeedback(null), 1500);
  }, [formattedBody]);

  const headerCount = Object.keys(response.headers).length;

  return (
    <div className="flex flex-col">
      {/* Status bar */}
      <div className="flex items-center gap-3 border-b border-edge px-4 py-2.5">
        <span
          className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-bold ${getStatusColor(response.status)}`}
        >
          {response.status}
        </span>
        <span className="text-xs text-txt-sec">{response.statusText}</span>
        <span className={`ml-auto text-xs font-mono ${getDurationColor(response.duration)}`}>
          {response.duration}ms
        </span>
        <button
          onClick={handleCopy}
          className="rounded-md border border-edge px-2 py-1 text-xs text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt"
        >
          {copyFeedback ?? 'Copy'}
        </button>
        <button
          onClick={onClear}
          className="rounded-md border border-edge px-2 py-1 text-xs text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt"
        >
          Clear
        </button>
      </div>

      {/* Headers (collapsible) */}
      <div className="border-b border-edge">
        <button
          onClick={() => setShowHeaders(!showHeaders)}
          className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs text-txt-muted hover:text-txt-sec transition-colors"
        >
          <svg
            className={`h-3 w-3 transition-transform ${showHeaders ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Response Headers
          <span className="rounded-full bg-surface-raised px-1.5 text-[10px] text-txt-muted">
            {headerCount}
          </span>
        </button>
        {showHeaders && (
          <div className="border-t border-edge/50 px-4 py-2">
            <table className="w-full">
              <tbody>
                {Object.entries(response.headers).map(([key, value]) => (
                  <tr key={key} className="border-b border-edge/30 last:border-0">
                    <td className="py-1 pr-4 font-mono text-xs text-txt-sec">{key}</td>
                    <td className="py-1 font-mono text-xs text-txt-sec">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Response body */}
      <div className="flex-1 p-4">
        <div className="mb-2 text-xs font-medium text-txt-sec">Response Body</div>
        <JsonEditor
          value={formattedBody}
          onChange={() => {}}
          readOnly
          isDark={isDark}
          height="300px"
        />
      </div>
    </div>
  );
}
