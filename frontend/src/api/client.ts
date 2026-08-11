/**
 * API Client for Legal Search and Verdict Services
 */

import { LegalSearchFilters, SearchResult, VerdictRequest, VerdictResponse } from './types';

export class SearchAPIError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'SearchAPIError';
  }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = {
  async fetch(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new SearchAPIError(response.status, error.message || response.statusText, error);
    }

    return response.json();
  },

  async get(endpoint: string, options: RequestInit = {}) {
    return this.fetch(endpoint, { ...options, method: 'GET' });
  },

  async post(endpoint: string, data?: any, options: RequestInit = {}) {
    return this.fetch(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  async put(endpoint: string, data?: any, options: RequestInit = {}) {
    return this.fetch(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  async delete(endpoint: string, options: RequestInit = {}) {
    return this.fetch(endpoint, { ...options, method: 'DELETE' });
  },
};

export async function searchVerdicts(filters: LegalSearchFilters): Promise<SearchResult> {
  const params = new URLSearchParams();
  if (filters.query) params.append('query', filters.query);
  if (filters.jurisdiction) params.append('jurisdiction', filters.jurisdiction);
  if (filters.caseType) params.append('caseType', filters.caseType);
  if (filters.courtLevel) params.append('courtLevel', filters.courtLevel);
  if (filters.limit) params.append('limit', String(filters.limit));
  if (filters.offset) params.append('offset', String(filters.offset));

  return apiClient.get(`/api/search/verdicts?${params.toString()}`);
}

export async function getVerdict(verdictId: string): Promise<VerdictResponse> {
  return apiClient.get(`/api/verdicts/${verdictId}`);
}

export async function createVerdict(request: VerdictRequest): Promise<VerdictResponse> {
  return apiClient.post('/api/verdicts', request);
}

export async function uploadDocument(file: File, metadata?: Record<string, any>) {
  const formData = new FormData();
  formData.append('file', file);
  if (metadata) {
    formData.append('metadata', JSON.stringify(metadata));
  }

  const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new SearchAPIError(response.status, error.message || response.statusText, error);
  }

  return response.json();
}
