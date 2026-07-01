import { Link, useLocation } from 'react-router-dom';
import EnvironmentSelector from './EnvironmentSelector';

interface HeaderProps {
  environmentId: string;
  onEnvironmentChange: (envId: string) => void;
  isDark: boolean;
  onToggleTheme: () => void;
  token: string;
  onSaveToken: (token: string) => void;
  onClearToken: () => void;
}

export default function Header({
  environmentId,
  onEnvironmentChange,
  isDark,
  onToggleTheme,
  token,
  onSaveToken,
  onClearToken,
}: HeaderProps) {
  const location = useLocation();

  return (
    <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b border-edge bg-surface-alt/95 px-6 py-2 backdrop-blur-sm">
      {/* Left: Logo + Nav + Env */}
      <div className="flex items-center gap-6">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-xs font-bold text-white">
            A
          </div>
          <span className="text-sm font-semibold text-txt tracking-tight">
            IMS API Tester
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          <Link
            to="/"
            className={`rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
              location.pathname === '/'
                ? 'bg-surface-raised text-txt'
                : 'text-txt-sec hover:text-txt'
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/settings"
            className={`rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
              location.pathname === '/settings'
                ? 'bg-surface-raised text-txt'
                : 'text-txt-sec hover:text-txt'
            }`}
          >
            Settings
          </Link>
        </nav>

        <div className="ml-4 border-l border-edge pl-6">
          <EnvironmentSelector
            currentEnvId={environmentId}
            onChange={onEnvironmentChange}
          />
        </div>
      </div>

      {/* Right: Theme */}
      <div className="flex items-center gap-4">

        <button
          onClick={onToggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-edge text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
