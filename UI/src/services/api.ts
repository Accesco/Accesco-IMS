import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getBaseUrl } from './environment';
import { getStoredToken } from './storage';

function createApiClient(): AxiosInstance {
  const client = axios.create({
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor: inject base URL and token
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Set base URL dynamically (environment may change between requests)
      config.baseURL = getBaseUrl();

      // Inject JWT token if available
      const token = getStoredToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    },
    (error) => Promise.reject(error)
  );

  return client;
}

export const apiClient = createApiClient();

export interface FormattedError {
  status: number;
  statusText: string;
  message: string;
  detail?: unknown;
}

export function formatAxiosError(error: AxiosError): FormattedError {
  if (error.response) {
    const data = error.response.data as Record<string, unknown> | undefined;
    return {
      status: error.response.status,
      statusText: error.response.statusText,
      message:
        (data?.detail as string) ??
        (data?.message as string) ??
        error.response.statusText,
      detail: data,
    };
  }

  if (error.request) {
    return {
      status: 0,
      statusText: 'Network Error',
      message: 'Could not reach the server. Is the backend running?',
    };
  }

  return {
    status: 0,
    statusText: 'Request Error',
    message: error.message,
  };
}
