/**
 * Legal Search API Client
 * ========================
 * Typed client for /v1/search endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const SEARCH_BASE = `${API_BASE_URL}/v1/search`;

// ============================================================================
// Types
// ============================================================================

export interface SearchFilters {
  court_level?: string;
  case_type?: string;
  is_final?: boolean;
  article_no?: string;
  law_name?: string;
  tags?: string[];
}

export interface VerdictSearchRequest {
  query: string;
  filters?: SearchFilters;
  limit?: number;
  enrich_with_graph?: boolean;
}

export interface VerdictHit {
  verdict_id: string;
  score: number;
  section: string;
  chunk_text: string;
  case_type?: string;
  court_level?: string;
  procedure_stage?: string;
  is_final?: boolean;
  tags: string[];
  law_articles: string[];
  extra_metadata: Record<string, any>;
}

export interface VerdictSearchResponse {
  results: VerdictHit[];
  total: number;
  query: string;
  filters_applied?: Record<string, any>;
}

export interface SearchHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  service: string;
  backends: {
    vector_store: string;
    graph: string;
  };
  message?: string;
  error?: string;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Search for legal verdicts using natural language queries
 */
export async function searchVerdicts(
  request: VerdictSearchRequest
): Promise<VerdictSearchResponse> {
  const res = await fetch(`${SEARCH_BASE}/verdicts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: request.query,
      filters: request.filters || null,
      limit: request.limit || 10,
      enrich_with_graph: request.enrich_with_graph ?? true,
    }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Search failed");
  }

  return res.json();
}

/**
 * Quick search with just query string
 */
export async function quickSearch(
  query: string,
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({ query, limit });
}

/**
 * Search with filters
 */
export async function searchWithFilters(
  query: string,
  filters: SearchFilters,
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({ query, filters, limit });
}

/**
 * Search by court level
 */
export async function searchByCourtLevel(
  query: string,
  courtLevel: string,
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({
    query,
    filters: { court_level: courtLevel },
    limit,
  });
}

/**
 * Search by case type
 */
export async function searchByCaseType(
  query: string,
  caseType: string,
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({
    query,
    filters: { case_type: caseType },
    limit,
  });
}

/**
 * Search final verdicts only
 */
export async function searchFinalVerdicts(
  query: string,
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({
    query,
    filters: { is_final: true },
    limit,
  });
}

/**
 * Search by law article
 */
export async function searchByLawArticle(
  query: string,
  articleNo: string,
  lawName?: string,
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({
    query,
    filters: {
      article_no: articleNo,
      ...(lawName && { law_name: lawName }),
    },
    limit,
  });
}

/**
 * Search by tags
 */
export async function searchByTags(
  query: string,
  tags: string[],
  limit: number = 10
): Promise<VerdictSearchResponse> {
  return searchVerdicts({
    query,
    filters: { tags },
    limit,
  });
}

/**
 * Check search service health
 */
export async function getSearchHealth(): Promise<SearchHealthResponse> {
  const res = await fetch(`${SEARCH_BASE}/health`);

  if (!res.ok) {
    throw new Error("Failed to check search health");
  }

  return res.json();
}

/**
 * Format verdict hit for display
 */
export function formatVerdictHit(hit: VerdictHit): {
  title: string;
  subtitle: string;
  content: string;
  metadata: string[];
} {
  return {
    title: hit.case_type || "رأی قضایی",
    subtitle: `${hit.court_level || "دادگاه"} - ${hit.section}`,
    content: hit.chunk_text,
    metadata: [
      ...(hit.is_final ? ["قطعی"] : []),
      ...hit.tags,
      ...hit.law_articles,
    ],
  };
}

/**
 * Group search results by court level
 */
export function groupByCourtLevel(
  results: VerdictHit[]
): Record<string, VerdictHit[]> {
  return results.reduce((acc, hit) => {
    const court = hit.court_level || "نامشخص";
    if (!acc[court]) acc[court] = [];
    acc[court].push(hit);
    return acc;
  }, {} as Record<string, VerdictHit[]>);
}

/**
 * Group search results by case type
 */
export function groupByCaseType(
  results: VerdictHit[]
): Record<string, VerdictHit[]> {
  return results.reduce((acc, hit) => {
    const caseType = hit.case_type || "نامشخص";
    if (!acc[caseType]) acc[caseType] = [];
    acc[caseType].push(hit);
    return acc;
  }, {} as Record<string, VerdictHit[]>);
}
