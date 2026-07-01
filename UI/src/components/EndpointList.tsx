import { useMemo, useState } from 'react';
import type { Endpoint, EndpointModule, HttpMethod } from '../types/endpoint';

const METHOD_COLORS: Record<HttpMethod, string> = {
  GET: 'bg-emerald-500/15 text-emerald-400',
  POST: 'bg-blue-500/15 text-blue-400',
  PUT: 'bg-amber-500/15 text-amber-400',
  DELETE: 'bg-red-500/15 text-red-400',
  PATCH: 'bg-purple-500/15 text-purple-400',
};

interface EndpointListProps {
  module: EndpointModule | null;
  selectedEndpointId: string | null;
  onSelectEndpoint: (endpoint: Endpoint) => void;
}

export default function EndpointList({
  module,
  selectedEndpointId,
  onSelectEndpoint,
}: EndpointListProps) {
  const [search, setSearch] = useState('');

  const filteredEndpoints = useMemo(() => {
    if (!module) return [];
    if (!search.trim()) return module.endpoints;
    const q = search.toLowerCase();
    return module.endpoints.filter(
      (ep) =>
        ep.path.toLowerCase().includes(q) ||
        ep.description.toLowerCase().includes(q) ||
        ep.method.toLowerCase().includes(q)
    );
  }, [module, search]);

  if (!module) {
    return (
      <div className="flex w-64 flex-col border-r border-edge bg-surface-alt/50">
        <div className="flex flex-1 items-center justify-center px-4 text-center">
          <p className="text-xs text-txt-faint">
            Select a module from the sidebar
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-64 flex-col border-r border-edge bg-surface-alt/50">
      {/* Module header */}
      <div className="border-b border-edge px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-sm">{module.icon}</span>
          <h2 className="text-sm font-semibold text-txt">{module.name}</h2>
        </div>
        <p className="mt-0.5 text-xs text-txt-muted">{module.description}</p>
      </div>

      {/* Search endpoints */}
      <div className="border-b border-edge px-3 py-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter endpoints…"
          className="w-full rounded-md border border-edge bg-surface px-3 py-1.5 text-xs text-txt-sec placeholder-zinc-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
        />
      </div>

      {/* Endpoint list */}
      <div className="flex-1 overflow-y-auto py-1">
        {filteredEndpoints.map((ep) => (
          <button
            key={ep.id}
            onClick={() => onSelectEndpoint(ep)}
            className={`flex w-full items-center gap-2 px-3 py-2 text-left transition-colors ${
              selectedEndpointId === ep.id
                ? 'bg-indigo-500/8 text-txt'
                : 'text-txt-sec hover:bg-surface-raised/50 hover:text-txt'
            }`}
          >
            <span
              className={`inline-flex w-14 flex-shrink-0 items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${METHOD_COLORS[ep.method]}`}
            >
              {ep.method}
            </span>
            <div className="min-w-0 flex-1">
              <div className="truncate font-mono text-xs">{ep.path}</div>
              <div className="truncate text-[10px] text-txt-faint">
                {ep.description}
              </div>
            </div>
          </button>
        ))}
        {filteredEndpoints.length === 0 && (
          <div className="px-3 py-4 text-center text-xs text-txt-faint">
            No endpoints match
          </div>
        )}
      </div>
    </div>
  );
}
