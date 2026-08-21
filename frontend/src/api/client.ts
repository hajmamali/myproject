/**
 * API Client for Legal Search and shared HTTP helpers.
 *
 * Search uses the canonical backend contract: POST /v1/search/verdicts
 */

import { LegalSearchFilters, SearchResult } from './types';

export class SearchAPIError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'SearchAPIError';
  }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

  return params;
}

function withQueryString(endpoint: string, options: Record<string, unknown> = {}): string {
  const params = extractQueryParams(options);
  if (Object.keys(params).length === 0) return endpoint;

  const url = new URL(endpoint, 'http://localhost');

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

  return `${url.pathname}${url.search}`;
}

export const apiClient = {
  async fetch<T = unknown>(endpoint: string, options: RequestInit & Record<string, unknown> = {}): Promise<T> {
    const queryParams = extractQueryParams(options as Record<string, unknown>);
    const url = `${API_BASE_URL}${withQueryString(endpoint, options as Record<string, unknown>)}`;
    const { headers, ...requestOptions } = options as RequestInit & Record<string, unknown>;
    const sanitizedOptions = { ...requestOptions };

    for (const key of Object.keys(queryParams)) {
      delete sanitizedOptions[key];
    }

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(headers as HeadersInit | undefined),
      },
      ...sanitizedOptions,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new SearchAPIError(
        response.status,
        (error as { message?: string; detail?: string }).message
          || (error as { detail?: string }).detail
          || response.statusText,
        error
      );
    }

    return response.json() as Promise<T>;
  },

  async get<T = unknown>(endpoint: string, options: Record<string, unknown> = {}): Promise<T> {
    return this.fetch<T>(endpoint, { ...options, method: 'GET' });
  },

  async post<T = unknown>(endpoint: string, data?: unknown, options: Record<string, unknown> = {}): Promise<T> {
    return this.fetch<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  async put<T = unknown>(endpoint: string, data?: unknown, options: Record<string, unknown> = {}): Promise<T> {
    return this.fetch<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  async delete<T = unknown>(endpoint: string, options: Record<string, unknown> = {}): Promise<T> {
    return this.fetch<T>(endpoint, { ...options, method: 'DELETE' });
  },
};

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

  const response = await fetch(`${API_BASE_URL}/api/v1/mahoun/upload-documents`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new SearchAPIError(
      response.status,
      (error as { message?: string; detail?: string }).message
        || (error as { detail?: string }).detail
        || response.statusText,
      error
    );
  }

  return response.json();
}
