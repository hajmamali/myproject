/**
 * MAHOUN Enhanced API Client
 * 
 * Production-grade API client with:
 * - Governance integration
 * - Authentication handling
 * - Error recovery
 * - Request/response interceptors
 * - Audit logging
 */

import { VerdictSearchRequest, VerdictSearchResponse, APIError } from "./types";

/**
 * Backend API base URL with environment support
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Enhanced API error class with governance context
 */
export class MahounAPIError extends Error {
  public statusCode: number;
  public detail: string;
  public requestId: string;
  public traceId: string;

  constructor(message: string, statusCode: number, detail: string, requestId?: string, traceId?: string) {
    super(message);
    this.name = "MahounAPIError";
    this.statusCode = statusCode;
    this.detail = detail;
    this.requestId = requestId || '';
    this.traceId = traceId || '';
  }
}

/**
 * Headers interface for strict typing
 */
interface RequestHeaders {
  'Content-Type'?: string;
  'Accept'?: string;
  'X-Request-ID'?: string;
  'X-Trace-ID'?: string;
  'X-Timestamp'?: string;
  'X-Governance-Context'?: string;
  'Authorization'?: string;
  [key: string]: string | undefined;
}

/**
 * Enhanced API Client Class with Governance Integration
 */
export class MahounAPIClient {
  private baseURL: string;
  private defaultHeaders: RequestHeaders;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Generate governance headers for requests
   */
  private generateGovernanceHeaders(): Record<string, string> {
    return {
      'X-Request-ID': this.generateRequestId(),
      'X-Trace-ID': this.generateTraceId(),
      'X-Timestamp': new Date().toISOString(),
    };
  }

  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return 'req_' + Math.random().toString(36).substr(2, 16) + '_' + Date.now();
  }

  /**
   * Generate unique trace ID
   */
  private generateTraceId(): string {
    return 'trace_' + Math.random().toString(36).substr(2, 16) + '_' + Date.now();
  }

  /**
   * Enhanced request method with governance and error handling
   */
  async request<T>(
    endpoint: string, 
    options: RequestInit & { 
      governanceContext?: any;
      retries?: number;
    } = {}
  ): Promise<T> {
    const { governanceContext, retries = 3, ...fetchOptions } = options;
    
    // Prepare headers - convert to plain object for fetch, filtering out undefined values
    const headers: Record<string, string> = Object.fromEntries(
      Object.entries({
        ...this.defaultHeaders,
        ...this.generateGovernanceHeaders(),
      }).filter(([_, value]) => value !== undefined) as [string, string][]
    );
    
    // Merge any custom headers from fetchOptions
    if (fetchOptions.headers) {
      const customHeaders = fetchOptions.headers as Record<string, string>;
      Object.assign(headers, customHeaders);
    }

    // Add governance context if provided
    if (governanceContext) {
      headers['X-Governance-Context'] = JSON.stringify(governanceContext);
    }

    // Add authentication token if available
    const token = this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Retry logic with error tracking
    let lastError: Error = new Error('Unknown error');

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
          ...fetchOptions,
          headers,
        });

        // Handle response
        if (!response.ok) {
          const errorData = await this.parseErrorResponse(response);
          const error = new MahounAPIError(
            errorData.message,
            response.status,
            errorData.detail,
            headers['X-Request-ID'],
            headers['X-Trace-ID']
          );
          throw error;
        }

        const data = await response.json();
        
        // Log successful request for audit
        this.logAuditEvent('api_request_success', {
          endpoint,
          method: fetchOptions.method || 'GET',
          status: response.status,
          requestId: headers['X-Request-ID'] || 'unknown',
        });

        return data;

      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on client errors (4xx)
        if (error instanceof MahounAPIError && error.statusCode < 500) {
          break;
        }

        // Wait before retry (exponential backoff)
        if (attempt < retries) {
          await this.delay(Math.pow(2, attempt) * 1000);
        }
      }
    }

    // Log failed request
    this.logAuditEvent('api_request_failed', {
      endpoint,
      method: fetchOptions.method || 'GET',
      error: lastError.message,
      requestId: headers['X-Request-ID'] || 'unknown',
    });

    throw lastError!;
  }

  /**
   * Get authentication token from store
   */
  private getAuthToken(): string | null {
    // This will be integrated with the auth store
    const authData = localStorage.getItem('mahoun-auth-store');
    if (authData) {
      try {
        const parsed = JSON.parse(authData);
        return parsed.state?.token || null;
      } catch {
        return null;
      }
    }
    return null;
  }

  /**
   * Parse error response from API
   */
  private async parseErrorResponse(response: Response): Promise<{ message: string; detail: string }> {
    try {
      const errorData: APIError = await response.json();
      return {
        message: `API Error: ${errorData.detail || response.statusText}`,
        detail: errorData.detail || `HTTP ${response.status}`,
      };
    } catch {
      return {
        message: `HTTP Error: ${response.status} ${response.statusText}`,
        detail: `HTTP ${response.status}`,
      };
    }
  }

  /**
   * Log audit events
   */
  private logAuditEvent(action: string, context: any): void {
    // This will be integrated with the governance store
    console.log('API Audit Event:', { action, context, timestamp: new Date().toISOString() });
  }

  /**
   * Delay utility for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Clean up filters by removing null/undefined/empty values
 */
function cleanFilters(
  filters: VerdictSearchRequest["filters"]
): VerdictSearchRequest["filters"] {
  if (!filters) return null;

  const cleaned: Record<string, unknown> = {};
  
  for (const [key, value] of Object.entries(filters)) {
    // Skip null, undefined, empty strings, and empty arrays
    if (value === null || value === undefined) continue;
    if (typeof value === "string" && value.trim() === "") continue;
    if (Array.isArray(value) && value.length === 0) continue;
    
    cleaned[key] = value;
  }

  return Object.keys(cleaned).length > 0 ? cleaned as VerdictSearchRequest["filters"] : null;
}

/**
 * Enhanced search verdicts function with governance
 */
export async function searchVerdicts(
  payload: VerdictSearchRequest,
  signal?: AbortSignal,
  governanceContext?: any
): Promise<VerdictSearchResponse> {
  const client = new MahounAPIClient();
  
  // Clean up the payload
  const cleanedFilters = cleanFilters(payload.filters);
  const cleanedPayload: VerdictSearchRequest = {
    query: payload.query.trim(),
    filters: cleanedFilters || undefined,
    limit: payload.limit || 10,
    enrich_with_graph: payload.enrich_with_graph ?? true,
  };

  try {
    return await client.request<VerdictSearchResponse>('/v1/search/verdicts', {
      method: 'POST',
      body: JSON.stringify(cleanedPayload),
      signal: signal ?? null,
      governanceContext: governanceContext,
    });

  } catch (error) {
    if (error instanceof MahounAPIError) {
      throw error;
    }

    // Network or other errors
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new MahounAPIError(
        "خطا در اتصال به سرور. لطفاً اتصال اینترنت و وضعیت سرور را بررسی کنید.",
        0,
        "Network error"
      );
    }

    throw new MahounAPIError(
      "خطای غیرمنتظره در ارسال درخواست",
      0,
      String(error)
    );
  }
}

/**
 * Enhanced health check with governance tracking
 */
export async function checkSearchHealth(governanceContext?: any): Promise<{
  status: string;
  backends: { vector_store: string; graph: string };
}> {
  const client = new MahounAPIClient();
  
  try {
    return await client.request('/v1/search/health', {
      method: 'GET',
      governanceContext,
    });
  } catch (error) {
    if (error instanceof MahounAPIError) {
      throw error;
    }
    throw new MahounAPIError("Health check failed", 0, "Service unavailable");
  }
}

/**
 * Create singleton API client instance
 */
export const apiClient = new MahounAPIClient();

// Legacy alias for backward compatibility
export const SearchAPIError = MahounAPIError;

