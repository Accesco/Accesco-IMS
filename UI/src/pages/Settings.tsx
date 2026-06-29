import { useState, useMemo } from 'react';
import { environments } from '../config/environments';
import type { RequestHistoryEntry } from '../types/api';

interface SettingsProps {
  environmentId: string;
  onEnvironmentChange: (envId: string) => void;
  token: string;
  onSaveToken: (token: string) => void;
  onClearToken: () => void;
}

function loadHistory(): RequestHistoryEntry[] {
  try {
    const data = localStorage.getItem('ims-api-tester:request-history');
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

const METHOD_BADGE: Record<string, string> = {
  GET: 'bg-emerald-500/15 text-emerald-400',
  POST: 'bg-blue-500/15 text-blue-400',
  PUT: 'bg-amber-500/15 text-amber-400',
  DELETE: 'bg-red-500/15 text-red-400',
  PATCH: 'bg-purple-500/15 text-purple-400',
};

export default function Settings({
  environmentId,
  onEnvironmentChange,
  token,
  onSaveToken,
  onClearToken,
}: SettingsProps) {
  const [tokenInput, setTokenInput] = useState(token);
  const history = useMemo(loadHistory, []);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="mb-8 text-xl font-semibold text-txt">Settings</h1>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2 mb-8">
        {/* Environment */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-txt-sec uppercase tracking-wider">
            Environment
          </h2>
          <div className="flex h-full flex-col rounded-lg border border-edge bg-surface-alt p-4">
            <div className="space-y-3">
              {environments.map((env) => (
                <label
                  key={env.id}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border px-4 py-3 transition-colors ${
                    environmentId === env.id
                      ? 'border-indigo-500/50 bg-indigo-500/5'
                      : 'border-edge hover:border-edge'
                  }`}
                >
                  <input
                    type="radio"
                    name="environment"
                    value={env.id}
                    checked={environmentId === env.id}
                    onChange={() => onEnvironmentChange(env.id)}
                    className="accent-indigo-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-txt">{env.name}</div>
                    <div className="font-mono text-xs text-txt-muted">{env.baseUrl}</div>
                    <div className="text-xs text-txt-faint">{env.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </section>

        {/* JWT Token */}
        <section>
          <h2 className="mb-3 text-sm font-semibold text-txt-sec uppercase tracking-wider">
            JWT Token
          </h2>
          <div className="flex h-full flex-col rounded-lg border border-edge bg-surface-alt p-4">
            <textarea
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Paste your JWT token here…"
              rows={4}
              className="mb-3 w-full flex-1 resize-none rounded-md border border-edge bg-surface px-3 py-2 font-mono text-xs text-txt-sec placeholder-zinc-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            />
            <div className="flex gap-2 mt-auto">
              <button
                onClick={() => onSaveToken(tokenInput.trim())}
                disabled={tokenInput.trim() === token}
                className="rounded-md bg-indigo-600 px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Save Token
              </button>
              <button
                onClick={() => {
                  setTokenInput('');
                  onClearToken();
                }}
                disabled={!token && !tokenInput}
                className="rounded-md border border-edge px-4 py-1.5 text-xs font-medium text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt-sec disabled:cursor-not-allowed disabled:opacity-40"
              >
                Clear Token
              </button>
            </div>
            {token && (
              <div className="mt-3 flex items-center gap-2 text-xs text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Token is set ({token.length} chars)
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Request History */}
      <section>
        <h2 className="mb-3 text-sm font-semibold text-txt-sec uppercase tracking-wider">
          Request History
        </h2>
        <div className="rounded-lg border border-edge bg-surface-alt">
          {history.length === 0 ? (
            <div className="px-4 py-8 text-center text-xs text-txt-faint">
              No requests yet. Start testing from the Dashboard.
            </div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {history.slice(0, 20).map((entry) => (
                <div key={entry.id} className="flex items-center gap-3 px-4 py-2.5">
                  <span
                    className={`inline-flex w-14 flex-shrink-0 items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      METHOD_BADGE[entry.method] ?? 'bg-surface-elevated text-txt-sec'
                    }`}
                  >
                    {entry.method}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-mono text-xs text-txt-sec">{entry.url}</div>
                    <div className="text-[10px] text-txt-faint">
                      {entry.endpointDescription} • {entry.moduleName}
                    </div>
                  </div>
                  <span
                    className={`text-xs font-mono ${
                      entry.status >= 200 && entry.status < 300
                        ? 'text-emerald-400'
                        : entry.status >= 400
                        ? 'text-red-400'
                        : 'text-txt-sec'
                    }`}
                  >
                    {entry.status}
                  </span>
                  <span className="text-xs text-txt-faint font-mono">{entry.duration}ms</span>
                  <span className="text-[10px] text-txt-faint">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
