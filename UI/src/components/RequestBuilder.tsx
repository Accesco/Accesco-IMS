import { useState, useMemo, useCallback, useEffect } from 'react';
import type { Endpoint, HttpMethod } from '../types/endpoint';
import JsonEditor from './JsonEditor';
import { validateJson } from '../utils/validateJson';
import { formatJson } from '../utils/formatJson';
import { copyToClipboard } from '../utils/copyToClipboard';
import { generateCurl } from '../utils/generateCurl';
import { getBaseUrl } from '../services/environment';

const METHOD_COLORS: Record<HttpMethod, string> = {
  GET: 'bg-emerald-500 text-white',
  POST: 'bg-blue-500 text-white',
  PUT: 'bg-amber-500 text-white',
  DELETE: 'bg-red-500 text-white',
  PATCH: 'bg-purple-500 text-white',
};

interface RequestBuilderProps {
  endpoint: Endpoint;
  isDark: boolean;
  loading: boolean;
  onSend: (
    method: HttpMethod,
    url: string,
    body?: unknown,
    queryParams?: Record<string, string>
  ) => void;
}

export default function RequestBuilder({
  endpoint,
  isDark,
  loading,
  onSend,
}: RequestBuilderProps) {
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});
  const [bodyText, setBodyText] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'body' | 'params' | 'headers'>('body');

  const hasBody = ['POST', 'PUT', 'PATCH'].includes(endpoint.method);
  const hasPathParams = (endpoint.pathParams?.length ?? 0) > 0;
  const hasQueryParams = (endpoint.queryParams?.length ?? 0) > 0;

  // Reset state when endpoint changes
  useEffect(() => {
    const initialPath: Record<string, string> = {};
    endpoint.pathParams?.forEach((p) => {
      initialPath[p.name] = p.defaultValue ?? '';
    });
    setPathParams(initialPath);

    const initialQuery: Record<string, string> = {};
    endpoint.queryParams?.forEach((p) => {
      initialQuery[p.name] = p.defaultValue ?? '';
    });
    setQueryParams(initialQuery);

    if (endpoint.sampleBody) {
      setBodyText(formatJson(endpoint.sampleBody));
    } else {
      setBodyText('');
    }

    setJsonError(null);

    // Auto-select the right tab
    if (hasBody) {
      setActiveTab('body');
    } else if (hasPathParams || hasQueryParams) {
      setActiveTab('params');
    } else {
      setActiveTab('body');
    }
  }, [endpoint.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Build resolved URL
  const resolvedUrl = useMemo(() => {
    let url = endpoint.path;
    Object.entries(pathParams).forEach(([key, value]) => {
      url = url.replace(`:${key}`, value || `:${key}`);
    });
    return url;
  }, [endpoint.path, pathParams]);

  const fullUrl = useMemo(() => {
    const base = getBaseUrl();
    let url = `${base}${resolvedUrl}`;
    const params = Object.entries(queryParams)
      .filter(([, v]) => v !== '')
      .map(([k, v]) => `${k}=${v}`)
      .join('&');
    if (params) url += `?${params}`;
    return url;
  }, [resolvedUrl, queryParams]);

  // Validate body on change
  useEffect(() => {
    if (!hasBody || !bodyText.trim()) {
      setJsonError(null);
      return;
    }
    const result = validateJson(bodyText);
    setJsonError(result.valid ? null : result.error ?? 'Invalid JSON');
  }, [bodyText, hasBody]);

  const handleSend = useCallback(() => {
    if (loading) return;

    let parsedBody: unknown = undefined;
    if (hasBody && bodyText.trim()) {
      const result = validateJson(bodyText);
      if (!result.valid) {
        setJsonError(result.error ?? 'Invalid JSON');
        return;
      }
      parsedBody = result.parsed;
    }

    onSend(endpoint.method, resolvedUrl, parsedBody, queryParams);
  }, [loading, hasBody, bodyText, endpoint.method, resolvedUrl, queryParams, onSend]);

  const handleCopyCurl = useCallback(async () => {
    const curl = generateCurl(endpoint.method, resolvedUrl, bodyText.trim() || undefined, queryParams);
    const ok = await copyToClipboard(curl);
    setCopyFeedback(ok ? 'Copied!' : 'Failed');
    setTimeout(() => setCopyFeedback(null), 1500);
  }, [endpoint.method, resolvedUrl, bodyText, queryParams]);

  const handleReset = useCallback(() => {
    const initialPath: Record<string, string> = {};
    endpoint.pathParams?.forEach((p) => {
      initialPath[p.name] = p.defaultValue ?? '';
    });
    setPathParams(initialPath);

    const initialQuery: Record<string, string> = {};
    endpoint.queryParams?.forEach((p) => {
      initialQuery[p.name] = p.defaultValue ?? '';
    });
    setQueryParams(initialQuery);

    if (endpoint.sampleBody) {
      setBodyText(formatJson(endpoint.sampleBody));
    } else {
      setBodyText('');
    }
    setJsonError(null);
  }, [endpoint]);

  const handleFormat = useCallback(() => {
    if (!bodyText.trim()) return;
    const result = validateJson(bodyText);
    if (result.valid && result.parsed !== undefined) {
      setBodyText(formatJson(result.parsed));
    }
  }, [bodyText]);

  return (
    <div className="flex flex-col">
      {/* Method + URL bar */}
      <div className="flex items-center gap-2 border-b border-edge px-4 py-3">
        <span
          className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-bold ${METHOD_COLORS[endpoint.method]}`}
        >
          {endpoint.method}
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate font-mono text-sm text-txt" title={fullUrl}>
            {fullUrl}
          </div>
          <div className="text-xs text-txt-muted">{endpoint.description}</div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyCurl}
            className="rounded-md border border-edge px-2.5 py-1.5 text-xs text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt"
            title="Copy as cURL"
          >
            {copyFeedback ?? 'cURL'}
          </button>
          <button
            onClick={handleReset}
            className="rounded-md border border-edge px-2.5 py-1.5 text-xs text-txt-sec transition-colors hover:border-zinc-600 hover:text-txt"
          >
            Reset
          </button>
          <button
            onClick={handleSend}
            disabled={loading || !!jsonError}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Sending…
              </>
            ) : (
              <>
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
                Send
              </>
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-edge">
        {hasBody && (
          <button
            onClick={() => setActiveTab('body')}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === 'body'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-txt-muted hover:text-txt-sec'
            }`}
          >
            Body
            {jsonError && <span className="ml-1 text-red-400">●</span>}
          </button>
        )}
        {(hasPathParams || hasQueryParams) && (
          <button
            onClick={() => setActiveTab('params')}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === 'params'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-txt-muted hover:text-txt-sec'
            }`}
          >
            Parameters
            {(hasPathParams || hasQueryParams) && (
              <span className="ml-1 rounded-full bg-surface-elevated px-1.5 text-[10px] text-txt-sec">
                {(endpoint.pathParams?.length ?? 0) + (endpoint.queryParams?.length ?? 0)}
              </span>
            )}
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Body tab */}
        {activeTab === 'body' && hasBody && (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-medium text-txt-sec">Request Body (JSON)</span>
              <button
                onClick={handleFormat}
                className="text-xs text-txt-muted hover:text-txt-sec transition-colors"
              >
                Format
              </button>
            </div>
            <JsonEditor
              value={bodyText}
              onChange={setBodyText}
              isDark={isDark}
              height="220px"
            />
            {jsonError && (
              <div className="mt-2 rounded-md bg-red-500/10 px-3 py-1.5 text-xs text-red-400">
                {jsonError}
              </div>
            )}
          </div>
        )}

        {activeTab === 'body' && !hasBody && (
          <div className="py-8 text-center text-xs text-txt-faint">
            This endpoint does not accept a request body.
          </div>
        )}

        {/* Params tab */}
        {activeTab === 'params' && (
          <div className="space-y-4">
            {hasPathParams && (
              <div>
                <h4 className="mb-2 text-xs font-medium text-txt-sec uppercase tracking-wider">
                  Path Parameters
                </h4>
                <div className="space-y-2">
                  {endpoint.pathParams!.map((param) => (
                    <div key={param.name} className="flex items-center gap-2">
                      <label className="w-32 flex-shrink-0 font-mono text-xs text-txt-sec">
                        :{param.name}
                        {param.required && <span className="text-red-400">*</span>}
                      </label>
                      <input
                        type={param.type === 'number' ? 'number' : 'text'}
                        value={pathParams[param.name] ?? ''}
                        onChange={(e) =>
                          setPathParams((prev) => ({
                            ...prev,
                            [param.name]: e.target.value,
                          }))
                        }
                        placeholder={param.description ?? param.name}
                        className="flex-1 rounded-md border border-edge bg-surface px-3 py-1.5 font-mono text-xs text-txt-sec placeholder-zinc-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {hasQueryParams && (
              <div>
                <h4 className="mb-2 text-xs font-medium text-txt-sec uppercase tracking-wider">
                  Query Parameters
                </h4>
                <div className="space-y-2">
                  {endpoint.queryParams!.map((param) => (
                    <div key={param.name} className="flex items-center gap-2">
                      <label className="w-32 flex-shrink-0 font-mono text-xs text-txt-sec">
                        {param.name}
                        {param.required && <span className="text-red-400">*</span>}
                      </label>
                      <input
                        type={param.type === 'number' ? 'number' : 'text'}
                        value={queryParams[param.name] ?? ''}
                        onChange={(e) =>
                          setQueryParams((prev) => ({
                            ...prev,
                            [param.name]: e.target.value,
                          }))
                        }
                        placeholder={param.description ?? param.name}
                        className="flex-1 rounded-md border border-edge bg-surface px-3 py-1.5 font-mono text-xs text-txt-sec placeholder-zinc-600 outline-none transition-colors focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
