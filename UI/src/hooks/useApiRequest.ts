import { useState, useCallback } from 'react';
import { apiClient, formatAxiosError } from '../services/api';
import type { ApiResponse, ApiError, RequestHistoryEntry } from '../types/api';
import type { HttpMethod } from '../types/endpoint';
import { AxiosError } from 'axios';

const MAX_HISTORY = 50;
const HISTORY_KEY = 'ims-api-tester:request-history';

function loadHistory(): RequestHistoryEntry[] {
  try {
    const data = localStorage.getItem(HISTORY_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: RequestHistoryEntry[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, MAX_HISTORY)));
  } catch {
    // ignore
  }
}

export function useApiRequest() {
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<RequestHistoryEntry[]>(loadHistory);

  const sendRequest = useCallback(
    async (
      method: HttpMethod,
      url: string,
      body?: unknown,
      queryParams?: Record<string, string>,
      moduleName?: string,
      endpointDescription?: string
    ) => {
      setLoading(true);
      setError(null);
      setResponse(null);

      const startTime = performance.now();

      // Build query string
      const params: Record<string, string> = {};
      if (queryParams) {
        Object.entries(queryParams).forEach(([k, v]) => {
          if (v !== '') params[k] = v;
        });
      }

      try {
        const res = await apiClient.request({
          method: method.toLowerCase(),
          url,
          data: ['POST', 'PUT', 'PATCH'].includes(method) ? body : undefined,
          params: Object.keys(params).length > 0 ? params : undefined,
        });

        const duration = Math.round(performance.now() - startTime);

        // Extract headers as plain object
        const headers: Record<string, string> = {};
        if (res.headers) {
          Object.entries(res.headers).forEach(([k, v]) => {
            if (typeof v === 'string') headers[k] = v;
          });
        }

        const apiResponse: ApiResponse = {
          status: res.status,
          statusText: res.statusText,
          headers,
          data: res.data,
          duration,
        };

        setResponse(apiResponse);

        // Save to history
        const entry: RequestHistoryEntry = {
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          method,
          url,
          status: res.status,
          duration,
          moduleName: moduleName ?? '',
          endpointDescription: endpointDescription ?? '',
        };
        setHistory((prev) => {
          const next = [entry, ...prev].slice(0, MAX_HISTORY);
          saveHistory(next);
          return next;
        });

        return apiResponse;
      } catch (err) {
        const duration = Math.round(performance.now() - startTime);

        if (err instanceof AxiosError) {
          const formatted = formatAxiosError(err);
          const apiError: ApiError = { ...formatted, duration };
          setError(apiError);

          // Save to history even on error
          const entry: RequestHistoryEntry = {
            id: crypto.randomUUID(),
            timestamp: Date.now(),
            method,
            url,
            status: formatted.status,
            duration,
            moduleName: moduleName ?? '',
            endpointDescription: endpointDescription ?? '',
          };
          setHistory((prev) => {
            const next = [entry, ...prev].slice(0, MAX_HISTORY);
            saveHistory(next);
            return next;
          });

          return null;
        }

        const apiError: ApiError = {
          status: 0,
          statusText: 'Unknown Error',
          message: err instanceof Error ? err.message : 'An unknown error occurred',
          duration,
        };
        setError(apiError);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearResponse = useCallback(() => {
    setResponse(null);
    setError(null);
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
  }, []);

  return {
    response,
    error,
    loading,
    history,
    sendRequest,
    clearResponse,
    clearHistory,
  };
}
