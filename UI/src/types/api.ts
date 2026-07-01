export interface ApiResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: unknown;
  duration: number;
}

export interface ApiError {
  status: number;
  statusText: string;
  message: string;
  detail?: unknown;
  duration: number;
}

export interface RequestHistoryEntry {
  id: string;
  timestamp: number;
  method: string;
  url: string;
  status: number;
  duration: number;
  moduleName: string;
  endpointDescription: string;
}
