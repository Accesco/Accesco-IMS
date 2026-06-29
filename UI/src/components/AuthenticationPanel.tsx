import { useState } from 'react';

interface AuthenticationPanelProps {
  token: string;
  onSave: (token: string) => void;
  onClear: () => void;
}

export default function AuthenticationPanel({
  token,
  onSave,
  onClear,
}: AuthenticationPanelProps) {
  const [inputValue, setInputValue] = useState(token);
  const [isExpanded, setIsExpanded] = useState(!token);

  const hasToken = token.length > 0;
  const isDirty = inputValue !== token;

  return (
    <div className="border-b border-edge px-3 py-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs">🔑</span>
          <span className="text-xs font-medium text-txt-sec uppercase tracking-wider">
            Auth Token
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasToken && (
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" title="Token set" />
          )}
          <svg
            className={`h-3 w-3 text-txt-muted transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Paste your JWT token here…"
            rows={3}
            className="w-full resize-none rounded-md border border-edge bg-surface px-3 py-2 font-mono text-xs text-txt-sec placeholder-zinc-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
          />
          <div className="flex gap-2">
            <button
              onClick={() => onSave(inputValue.trim())}
              disabled={!isDirty || !inputValue.trim()}
              className="flex-1 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Save
            </button>
            <button
              onClick={() => {
                setInputValue('');
                onClear();
              }}
              disabled={!hasToken && !inputValue}
              className="rounded-md border border-edge px-3 py-1.5 text-xs font-medium text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt-sec disabled:cursor-not-allowed disabled:opacity-40"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
