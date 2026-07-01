import type { HttpMethod } from '../types/endpoint';
import { getBaseUrl } from '../services/environment';
import { getStoredToken } from '../services/storage';

export function generateCurl(
  method: HttpMethod,
  path: string,
  body?: string,
  queryParams?: Record<string, string>,
  headers?: Record<string, string>
): string {
  const baseUrl = getBaseUrl();
  let url = `${baseUrl}${path}`;

  // Append query params
  if (queryParams) {
    const params = Object.entries(queryParams)
      .filter(([, v]) => v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&');
    if (params) {
      url += `?${params}`;
    }
  }

  const parts: string[] = [`curl -X ${method}`];
  parts.push(`  '${url}'`);

  // Add auth header
  const token = getStoredToken();
  if (token) {
    parts.push(`  -H 'Authorization: Bearer ${token}'`);
  }

  // Content-Type
  if (body) {
    parts.push(`  -H 'Content-Type: application/json'`);
  }

  // Custom headers
  if (headers) {
    Object.entries(headers).forEach(([k, v]) => {
      parts.push(`  -H '${k}: ${v}'`);
    });
  }

  // Body
  if (body) {
    parts.push(`  -d '${body}'`);
  }

  return parts.join(' \\\n');
}
