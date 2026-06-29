import { useMemo, useState } from 'react';
import type { EndpointModule } from '../types/endpoint';
import AuthenticationPanel from './AuthenticationPanel';

interface SidebarProps {
  modules: EndpointModule[];
  selectedModuleId: string | null;
  onSelectModule: (moduleId: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  token: string;
  onSaveToken: (token: string) => void;
  onClearToken: () => void;
}

export default function Sidebar({
  modules,
  selectedModuleId,
  onSelectModule,
  collapsed,
  onToggleCollapse,
  token,
  onSaveToken,
  onClearToken,
}: SidebarProps) {
  const [search, setSearch] = useState('');

  const filteredModules = useMemo(() => {
    if (!search.trim()) return modules;
    const q = search.toLowerCase();
    return modules.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q)
    );
  }, [modules, search]);

  if (collapsed) {
    return (
      <aside className="flex w-12 flex-col border-r border-edge bg-surface-alt">
        <button
          onClick={onToggleCollapse}
          className="flex h-10 items-center justify-center text-txt-muted hover:text-txt-sec transition-colors"
          title="Expand sidebar"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>
        <div className="flex flex-1 flex-col items-center gap-1 pt-2">
          {modules.map((mod) => (
            <button
              key={mod.id}
              onClick={() => onSelectModule(mod.id)}
              className={`flex h-9 w-9 items-center justify-center rounded-md text-sm transition-colors ${
                selectedModuleId === mod.id
                  ? 'bg-indigo-600/15 text-indigo-400'
                  : 'text-txt-muted hover:bg-surface-raised hover:text-txt-sec'
              }`}
              title={mod.name}
            >
              {mod.icon}
            </button>
          ))}
        </div>
      </aside>
    );
  }

  return (
    <aside className="flex w-56 flex-col border-r border-edge bg-surface-alt">
      {/* Collapse button */}
      <div className="flex items-center justify-between border-b border-edge px-3 py-2">
        <span className="text-xs font-medium text-txt-muted uppercase tracking-wider">
          Modules
        </span>
        <button
          onClick={onToggleCollapse}
          className="flex h-6 w-6 items-center justify-center rounded text-txt-muted hover:text-txt-sec transition-colors"
          title="Collapse sidebar"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Auth Panel */}
      <AuthenticationPanel
        token={token}
        onSave={onSaveToken}
        onClear={onClearToken}
      />

      {/* Search */}
      <div className="border-b border-edge px-3 py-2">
        <div className="relative">
          <svg
            className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-txt-muted"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search modules…"
            className="w-full rounded-md border border-edge bg-surface py-1.5 pl-8 pr-3 text-xs text-txt-sec placeholder-zinc-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
          />
        </div>
      </div>

      {/* Module list */}
      <nav className="flex-1 overflow-y-auto py-1">
        {filteredModules.map((mod) => (
          <button
            key={mod.id}
            onClick={() => onSelectModule(mod.id)}
            className={`flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors ${
              selectedModuleId === mod.id
                ? 'border-r-2 border-indigo-500 bg-indigo-500/8 text-indigo-400'
                : 'text-txt-sec hover:bg-surface-raised/60 hover:text-txt'
            }`}
          >
            <span className="text-sm">{mod.icon}</span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{mod.name}</div>
              <div className="truncate text-xs text-txt-faint">
                {mod.endpoints.length} endpoint{mod.endpoints.length !== 1 ? 's' : ''}
              </div>
            </div>
          </button>
        ))}
        {filteredModules.length === 0 && (
          <div className="px-3 py-4 text-center text-xs text-txt-faint">
            No modules found
          </div>
        )}
      </nav>
    </aside>
  );
}
