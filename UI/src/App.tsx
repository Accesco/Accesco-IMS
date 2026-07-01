import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import { useTheme } from './hooks/useTheme';
import {
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  getStoredEnvironment,
  setStoredEnvironment,
} from './services/storage';
import { DEFAULT_ENVIRONMENT_ID } from './config/environments';
import { useState, useCallback } from 'react';

export default function App() {
  const { isDark, toggleTheme } = useTheme();
  const [token, setToken] = useState(() => getStoredToken() ?? '');
  const [environmentId, setEnvironmentId] = useState(
    () => getStoredEnvironment() ?? DEFAULT_ENVIRONMENT_ID
  );

  const handleSaveToken = useCallback((newToken: string) => {
    setStoredToken(newToken);
    setToken(newToken);
  }, []);

  const handleClearToken = useCallback(() => {
    clearStoredToken();
    setToken('');
  }, []);

  const handleEnvironmentChange = useCallback((envId: string) => {
    setStoredEnvironment(envId);
    setEnvironmentId(envId);
  }, []);

  return (
    <BrowserRouter>
      <div className="flex h-screen flex-col bg-surface text-txt">
        <Header
          environmentId={environmentId}
          onEnvironmentChange={handleEnvironmentChange}
          isDark={isDark}
          onToggleTheme={toggleTheme}
          token={token}
          onSaveToken={handleSaveToken}
          onClearToken={handleClearToken}
        />
        <Routes>
          <Route
            path="/"
            element={
              <Dashboard
                token={token}
                onSaveToken={handleSaveToken}
                onClearToken={handleClearToken}
                isDark={isDark}
              />
            }
          />
          <Route
            path="/settings"
            element={
              <Settings
                environmentId={environmentId}
                onEnvironmentChange={handleEnvironmentChange}
                token={token}
                onSaveToken={handleSaveToken}
                onClearToken={handleClearToken}
              />
            }
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
