/**
 * API Client for Legal Search, Auth, and shared HTTP helpers.
 *
 * Provides single canonical HTTP client with:
 * - Authorization Bearer header injection
 * - Governance headers (X-Request-ID, X-Trace-ID)
 * - Request timeout handling via AbortController (default 30s)
 * - 401 Unauthorized interceptor & auto-logout redirect
 * - Clean typed methods (get, post, put, patch, delete)
 * - Canonical Auth & Search API methods
 */

import { LegalSearchFilters, SearchResult } from './types';
import { useAuth } from '../store/authStore';
import { useGovernanceStore } from '../store/governanceStore';

export class APIError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export const SearchAPIError = APIError;

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT) || 30000;

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, unknown>;
  timeout?: number;
  skipAuth?: boolean;
  skipGovernance?: boolean;
  skipAuthRedirect?: boolean;
  body?: BodyInit | null;
  [key: string]: unknown;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number | string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  permissions: string[];
  is_active: boolean;
  created_at: string;
}

const REQUEST_INIT_KEYS = new Set([
  'method',
  'headers',
  'body',
  'signal',
  'credentials',
  'cache',
  'mode',
  'redirect',
  'referrer',
  'referrerPolicy',
  'integrity',
  'keepalive',
  'priority',
  'duplex',
  'timeout',
  'skipAuth',
  'skipGovernance',
  'skipAuthRedirect',
  'params',
]);

function extractQueryParams(options: Record<string, unknown> = {}): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  const entries = Object.entries(options);

  for (const [key, value] of entries) {
    if (REQUEST_INIT_KEYS.has(key)) continue;
    if (key === 'params' && value && typeof value === 'object') {
      Object.assign(params, value as Record<string, unknown>);
      continue;
    }
    if (value !== undefined && value !== null && value !== '') {
      params[key] = value;
    }
  }

  if (options.params && typeof options.params === 'object') {
    Object.assign(params, options.params);
  }

  return params;
}

function withQueryString(endpoint: string, options: Record<string, unknown> = {}): string {
  const params = extractQueryParams(options);
  if (Object.keys(params).length === 0) return endpoint;

  const isFullUrl = endpoint.startsWith('http://') || endpoint.startsWith('https://');
  const url = new URL(endpoint, isFullUrl ? undefined : 'http://localhost');

  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== '') {
          url.searchParams.append(key, String(item));
        }
      }
      continue;
    }

    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }

  return isFullUrl ? url.toString() : `${url.pathname}${url.search}`;
}

function generateId(prefix = 'req_'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}${crypto.randomUUID()}`;
  }
  return `${prefix}${Math.random().toString(36).substring(2, 11)}_${Date.now().toString(36)}`;
}

export const apiClient = {
  async fetch<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const queryParams = extractQueryParams(options as Record<string, unknown>);
    const queryStringEndpoint = withQueryString(endpoint, options as Record<string, unknown>);
    const url = queryStringEndpoint.startsWith('http://') || queryStringEndpoint.startsWith('https://')
      ? queryStringEndpoint
      : `${API_BASE_URL}${queryStringEndpoint.startsWith('/') ? '' : '/'}${queryStringEndpoint}`;

    const {
      headers: rawHeaders = {},
      timeout = DEFAULT_TIMEOUT_MS,
      skipAuth = false,
      skipGovernance = false,
      skipAuthRedirect = false,
      signal: customSignal,
      ...requestOptions
    } = options;

    const sanitizedOptions = { ...requestOptions };
    for (const key of Object.keys(queryParams)) {
      delete (sanitizedOptions as Record<string, unknown>)[key];
    }
    delete (sanitizedOptions as Record<string, unknown>).params;
    delete (sanitizedOptions as Record<string, unknown>).timeout;
    delete (sanitizedOptions as Record<string, unknown>).skipAuth;
    delete (sanitizedOptions as Record<string, unknown>).skipGovernance;
    delete (sanitizedOptions as Record<string, unknown>).skipAuthRedirect;

    // Headers assembly
    const headers: Record<string, string> = {};
    if (rawHeaders) {
      if (rawHeaders instanceof Headers) {
        rawHeaders.forEach((val, key) => {
          headers[key] = val;
        });
      } else if (Array.isArray(rawHeaders)) {
        rawHeaders.forEach(([key, val]) => {
          headers[key] = val;
        });
      } else {
        Object.assign(headers, rawHeaders);
      }
    }

    const isFormData = typeof FormData !== 'undefined' && sanitizedOptions.body instanceof FormData;
    const isSearchParams = typeof URLSearchParams !== 'undefined' && sanitizedOptions.body instanceof URLSearchParams;
    if (!isFormData && !isSearchParams && !headers['Content-Type'] && !headers['content-type']) {
      headers['Content-Type'] = 'application/json';
    }

    // 1. Authorization header injection
    if (!skipAuth && !headers['Authorization'] && !headers['authorization']) {
      try {
        const authState = useAuth.getState();
        const token = authState?.accessToken || authState?.token;
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      } catch (err) {
        console.debug('Failed to get auth token:', err);
      }
    }

    // 2. Governance headers injection
    if (!skipGovernance) {
      try {
        const govState = useGovernanceStore.getState();
        const context = govState?.context || (govState as any)?.governanceContext;
        const requestId = context?.requestId || context?.request_id || generateId('req_');
        const traceId = context?.traceId || context?.trace_id || generateId('trace_');

        if (!headers['X-Request-ID'] && !headers['x-request-id']) {
          headers['X-Request-ID'] = requestId;
        }
        if (!headers['X-Trace-ID'] && !headers['x-trace-id']) {
          headers['X-Trace-ID'] = traceId;
        }
      } catch (err) {
        if (!headers['X-Request-ID']) headers['X-Request-ID'] = generateId('req_');
        if (!headers['X-Trace-ID']) headers['X-Trace-ID'] = generateId('trace_');
      }
    }

    // 3. Request timeout handling with AbortController
    const controller = new AbortController();
    let timeoutId: any = null;

    if (timeout > 0) {
      timeoutId = setTimeout(() => {
        controller.abort(new Error(`Request timed out after ${timeout}ms`));
      }, timeout);
    }

    if (customSignal) {
      customSignal.addEventListener('abort', () => {
        controller.abort(customSignal.reason);
      });
    }

    try {
      const response = await fetch(url, {
        headers,
        signal: controller.signal,
        ...sanitizedOptions,
      });

      if (!response.ok) {
        // 4. 401 Unauthorized handling
        if (response.status === 401) {
          const isLoginEndpoint = endpoint.includes('/api/v1/auth/login') || endpoint.includes('/auth/login');
          if (!isLoginEndpoint && !skipAuthRedirect) {
            try {
              useAuth.getState().logout();
            } catch (e) {
              console.error('Error during auto-logout:', e);
            }
            if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
              window.location.href = '/login';
            }
          }
        }

        const error = await response.json().catch(() => ({}));
        throw new APIError(
          response.status,
          (error as { message?: string; detail?: string }).message
            || (error as { detail?: string }).detail
            || response.statusText,
          error
        );
      }

      if (response.status === 204) {
        return null as unknown as T;
      }

      const contentType = response.headers?.get ? response.headers.get('content-type') : null;
      if (!contentType || contentType.includes('application/json')) {
        if (typeof response.json === 'function') {
          return (await response.json()) as T;
        }
      }

      if (typeof response.text === 'function') {
        return (await response.text()) as unknown as T;
      }

      return response as unknown as T;
    } catch (err) {
      if (err instanceof APIError) {
        throw err;
      }
      if ((err as Error)?.name === 'AbortError' || (err as any)?.message?.includes('timed out')) {
        throw new APIError(408, `درخواست به دلیل اتمام مهلت زمانی (${timeout}ms) لغو شد`, err);
      }
      throw new APIError(500, (err as Error)?.message || 'Network request failed', err);
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    }
  },

  async get<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.fetch<T>(endpoint, { ...options, method: 'GET' });
  },

  async post<T = unknown>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    let body: BodyInit | undefined;
    if (data instanceof FormData || data instanceof URLSearchParams || typeof data === 'string') {
      body = data;
    } else if (data !== undefined && data !== null) {
      body = JSON.stringify(data);
    }

    return this.fetch<T>(endpoint, {
      ...options,
      method: 'POST',
      body,
    });
  },

  async put<T = unknown>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    let body: BodyInit | undefined;
    if (data instanceof FormData || data instanceof URLSearchParams || typeof data === 'string') {
      body = data;
    } else if (data !== undefined && data !== null) {
      body = JSON.stringify(data);
    }

    return this.fetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      body,
    });
  },

  async patch<T = unknown>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    let body: BodyInit | undefined;
    if (data instanceof FormData || data instanceof URLSearchParams || typeof data === 'string') {
      body = data;
    } else if (data !== undefined && data !== null) {
      body = JSON.stringify(data);
    }

    return this.fetch<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body,
    });
  },

  async delete<T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.fetch<T>(endpoint, { ...options, method: 'DELETE' });
  },
};

// ============================================================================
// Canonical Auth API Functions
// ============================================================================

export async function loginAPI(usernameOrEmail: string, password: string): Promise<LoginResponse> {
  const formData = new URLSearchParams();
  formData.append('username', usernameOrEmail.trim());
  formData.append('password', password);

  return apiClient.post<LoginResponse>('/api/v1/auth/login', formData, {
    skipAuth: true,
    skipAuthRedirect: true,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
}

export async function getCurrentUserAPI(token?: string): Promise<UserResponse> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return apiClient.get<UserResponse>('/api/v1/auth/me', {
    headers,
    skipAuthRedirect: false,
  });
}

export async function refreshTokenAPI(refreshToken: string): Promise<LoginResponse> {
  return apiClient.post<LoginResponse>(
    `/api/v1/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
    null,
    {
      skipAuth: true,
      skipAuthRedirect: true,
    }
  );
}

export async function logoutAPI(token?: string): Promise<{ success: boolean; message: string }> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return apiClient.post<{ success: boolean; message: string }>('/api/v1/auth/logout', null, {
    headers,
    skipAuthRedirect: true,
  });
}

// ============================================================================
// Legal Search & Document APIs
// ============================================================================

function buildSearchPayload(filters: LegalSearchFilters) {
  const query = (filters.query || '').trim();
  const nestedFilters: Record<string, unknown> = {};

  const courtLevel = filters.courtLevel ?? filters.court_level;
  const caseType = filters.caseType ?? filters.case_type;

  if (courtLevel) nestedFilters.court_level = courtLevel;
  if (caseType) nestedFilters.case_type = caseType;
  if (filters.is_final != null) nestedFilters.is_final = filters.is_final;
  if (filters.article_no) nestedFilters.article_no = filters.article_no;
  if (filters.law_name) nestedFilters.law_name = filters.law_name;
  if (filters.tags?.length) nestedFilters.tags = filters.tags;

  return {
    query,
    limit: filters.limit ?? 10,
    enrich_with_graph: true,
    filters: Object.keys(nestedFilters).length > 0 ? nestedFilters : undefined,
  };
}

export async function searchVerdicts(filters: LegalSearchFilters): Promise<SearchResult> {
  const payload = buildSearchPayload(filters);
  const response = await apiClient.post<{
    results?: SearchResult['hits'];
    hits?: SearchResult['hits'];
    total: number;
    query: string;
  }>('/v1/search/verdicts', payload);

  const hits = response.results || response.hits || [];

  return {
    hits,
    results: hits,
    total: response.total ?? hits.length,
    query: response.query ?? payload.query,
    executionTime: 0,
    filters,
  };
}

export async function uploadDocument(file: File, metadata?: Record<string, unknown>) {
  const formData = new FormData();
  formData.append('file', file);
  if (metadata) {
    formData.append('metadata', JSON.stringify(metadata));
  }

  return apiClient.post('/api/v1/mahoun/upload-documents', formData);
}
