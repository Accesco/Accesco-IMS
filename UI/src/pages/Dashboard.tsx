import { useState, useCallback, useMemo } from 'react';
import { endpointModules } from '../config/endpoints';
import type { Endpoint, EndpointModule, HttpMethod } from '../types/endpoint';
import Sidebar from '../components/Sidebar';
import EndpointList from '../components/EndpointList';
import RequestBuilder from '../components/RequestBuilder';
import ResponseViewer from '../components/ResponseViewer';
import LoadingState from '../components/LoadingState';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import { useApiRequest } from '../hooks/useApiRequest';
import { getSidebarCollapsed, setSidebarCollapsed } from '../services/storage';

interface DashboardProps {
  token: string;
  onSaveToken: (token: string) => void;
  onClearToken: () => void;
  isDark: boolean;
}

export default function Dashboard({
  token,
  onSaveToken,
  onClearToken,
  isDark,
}: DashboardProps) {
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [selectedEndpoint, setSelectedEndpoint] = useState<Endpoint | null>(null);
  const [collapsed, setCollapsed] = useState(getSidebarCollapsed);

  const { response, error, loading, sendRequest, clearResponse } = useApiRequest();

  const selectedModule: EndpointModule | null = useMemo(
    () => endpointModules.find((m) => m.id === selectedModuleId) ?? null,
    [selectedModuleId]
  );

  const handleSelectModule = useCallback((moduleId: string) => {
    setSelectedModuleId(moduleId);
    setSelectedEndpoint(null);
    clearResponse();
  }, [clearResponse]);

  const handleSelectEndpoint = useCallback(
    (endpoint: Endpoint) => {
      setSelectedEndpoint(endpoint);
      clearResponse();
    },
    [clearResponse]
  );

  const handleToggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      setSidebarCollapsed(next);
      return next;
    });
  }, []);

  const handleSend = useCallback(
    (
      method: HttpMethod,
      url: string,
      body?: unknown,
      queryParams?: Record<string, string>
    ) => {
      sendRequest(
        method,
        url,
        body,
        queryParams,
        selectedModule?.name,
        selectedEndpoint?.description
      );
    },
    [sendRequest, selectedModule, selectedEndpoint]
  );

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        modules={endpointModules}
        selectedModuleId={selectedModuleId}
        onSelectModule={handleSelectModule}
        collapsed={collapsed}
        onToggleCollapse={handleToggleCollapse}
        token={token}
        onSaveToken={onSaveToken}
        onClearToken={onClearToken}
      />

      {/* Endpoint List */}
      <EndpointList
        module={selectedModule}
        selectedEndpointId={selectedEndpoint?.id ?? null}
        onSelectEndpoint={handleSelectEndpoint}
      />

      {/* Workspace */}
      <main className="flex flex-1 flex-col overflow-hidden bg-surface">
        {!selectedEndpoint ? (
          <div className="flex flex-1 items-center justify-center">
            <EmptyState />
          </div>
        ) : (
          <div className="flex flex-1 flex-col overflow-y-auto">
            {/* Request Builder */}
            <div className="border-b border-edge">
              <RequestBuilder
                endpoint={selectedEndpoint}
                isDark={isDark}
                loading={loading}
                onSend={handleSend}
              />
            </div>

            {/* Response Area */}
            <div className="flex-1">
              {loading && <LoadingState />}
              {error && !loading && (
                <div className="p-4">
                  <ErrorState error={error} />
                </div>
              )}
              {response && !loading && (
                <ResponseViewer
                  response={response}
                  isDark={isDark}
                  onClear={clearResponse}
                />
              )}
              {!loading && !response && !error && (
                <div className="flex flex-1 items-center justify-center py-16">
                  <EmptyState
                    title="Ready to send"
                    message="Configure your request above and click Send to execute."
                    icon="🚀"
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
