/**
 * API Client for MAHOUN Legal Search
 * 
 * Communicates with the FastAPI backend at /v1/search/verdicts
 */

import { VerdictSearchRequest, VerdictSearchResponse, APIError } from "./types";

/**
 * Backend API base URL
 * 
 * In development with Vite proxy, we can use relative paths.
 * For direct connection without proxy, use full URL.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Custom error class for API errors
 */
export class SearchAPIError extends Error {
  public statusCode: number;
  public detail: string;

  constructor(message: string, statusCode: number, detail: string) {
    super(message);
    this.name = "SearchAPIError";
    this.statusCode = statusCode;
    this.detail = detail;
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
 * Search for legal verdicts matching a query
 * 
 * @param payload - Search request with query, filters, and limit
 * @param signal - AbortSignal for request cancellation
 * @returns Promise resolving to search response
 * @throws SearchAPIError on API errors
 * 
 * @example
 * ```ts
 * const response = await searchVerdicts({
 *   query: "اعتراض ثالث اجرایی",
 *   filters: { is_final: true },
 *   limit: 10
 * });
 * console.log(response.results);
 * ```
 */
export async function searchVerdicts(
  payload: VerdictSearchRequest,
  signal?: AbortSignal
): Promise<VerdictSearchResponse> {
  // Clean up the payload
  const cleanedPayload: VerdictSearchRequest = {
    query: payload.query.trim(),
    filters: cleanFilters(payload.filters),
    limit: payload.limit || 10,
    enrich_with_graph: payload.enrich_with_graph ?? true,
  };

  try {
    const res = await fetch(`${API_BASE_URL}/v1/search/verdicts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(cleanedPayload),
      signal, // Add AbortSignal for cancellation
    });

    if (!res.ok) {
      // Try to parse error response
      let errorDetail = `HTTP ${res.status}`;
      try {
        const errorData: APIError = await res.json();
        errorDetail = errorData.detail || errorDetail;
      } catch {
        // Ignore JSON parse errors
      }

      throw new SearchAPIError(
        `Search request failed: ${errorDetail}`,
        res.status,
        errorDetail
      );
    }

    const data: VerdictSearchResponse = await res.json();
    return data;
    
  } catch (error) {
    if (error instanceof SearchAPIError) {
      throw error;
    }

    // Network or other errors
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new SearchAPIError(
        "خطا در اتصال به سرور. لطفاً اتصال اینترنت و وضعیت سرور را بررسی کنید.",
        0,
        "Network error"
      );
    }

    throw new SearchAPIError(
      "خطای غیرمنتظره در ارسال درخواست",
      0,
      String(error)
    );
  }
}

/**
 * Check search service health
 */
export async function checkSearchHealth(): Promise<{
  status: string;
  backends: { vector_store: string; graph: string };
}> {
  const res = await fetch(`${API_BASE_URL}/v1/search/health`, {
    method: "GET",
    headers: { "Accept": "application/json" },
  });

  if (!res.ok) {
    throw new SearchAPIError("Health check failed", res.status, "Service unavailable");
  }

  return res.json();
}

