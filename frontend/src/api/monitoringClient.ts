/**
 * Monitoring & Metrics API Client
 * ================================
 * Typed client for monitoring and metrics endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ============================================================================
// Types
// ============================================================================

export interface LegalMetrics {
  total_queries: number;
  queries_per_second: number;
  avg_duration_seconds: number;
  p50_latency: number;
  p95_latency: number;
  p99_latency: number;
  error_rate: number;
  sla_compliance_rate: number;
  queries_by_court: Record<string, number>;
  queries_by_domain: Record<string, number>;
  cache_hit_rate: number;
  avg_authority_score: number;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  uptime_seconds: number;
  components: {
    [key: string]: {
      status: string;
      message?: string;
    };
  };
  sla_compliance: {
    current: number;
    target: number;
  };
}

export interface SystemMetrics {
  component: string;
  metric: string;
  window_seconds: number;
  metrics: Record<string, any>;
  timestamp: string;
}

export interface DashboardData {
  timestamp: string;
  components: {
    [key: string]: {
      status: string;
      uptime?: number;
      loss?: number;
      total_pulls?: number;
      buffer_size?: number;
    };
  };
  alerts: {
    total: number;
    critical: number;
    high: number;
    medium: number;
  };
  performance: {
    accuracy: number;
    latency_p95: number;
    throughput: number;
  };
}

export interface FeedbackStats {
  total_feedback: number;
  avg_satisfaction: number;
  avg_accuracy: number;
  feedback_rate: number;
  high_quality_count?: number;
}

// ============================================================================
// Monitoring API Functions
// ============================================================================

/**
 * Get Prometheus metrics in text format
 */
export async function getPrometheusMetrics(): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/metrics/prometheus`);

  if (!res.ok) {
    throw new Error("Failed to fetch Prometheus metrics");
  }

  return res.text();
}

/**
 * Get legal-specific metrics and comprehensive statistics
 */
export async function getLegalMetrics(): Promise<LegalMetrics> {
  const res = await fetch(`${API_BASE_URL}/metrics/legal`);

  if (!res.ok) {
    throw new Error("Failed to fetch legal metrics");
  }

  return res.json();
}

/**
 * Get detailed health check with comprehensive system status
 */
export async function getDetailedHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health/detailed`);

  if (!res.ok) {
    throw new Error("Failed to fetch health status");
  }

  return res.json();
}

/**
 * Reset all monitoring metrics (development only)
 */
export async function resetMetrics(): Promise<{
  status: string;
  message: string;
  timestamp: string;
}> {
  const res = await fetch(`${API_BASE_URL}/metrics/reset`, {
    method: "POST",
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.message || "Failed to reset metrics");
  }

  return res.json();
}

/**
 * Get system metrics from the collector
 */
export async function getSystemMetrics(
  component?: string,
  metric?: string,
  window: number = 3600
): Promise<SystemMetrics> {
  const params = new URLSearchParams();
  if (component) params.append("component", component);
  if (metric) params.append("metric", metric);
  params.append("window", window.toString());

  const res = await fetch(`${API_BASE_URL}/api/v1/metrics?${params}`);

  if (!res.ok) {
    throw new Error("Failed to fetch system metrics");
  }

  return res.json();
}

/**
 * Get dashboard data with all components
 */
export async function getDashboardData(): Promise<DashboardData> {
  const res = await fetch(`${API_BASE_URL}/api/v1/metrics/dashboard`);

  if (!res.ok) {
    throw new Error("Failed to fetch dashboard data");
  }

  return res.json();
}

/**
 * Get feedback statistics
 */
export async function getFeedbackStats(): Promise<FeedbackStats> {
  const res = await fetch(`${API_BASE_URL}/api/v1/feedback/stats`);

  if (!res.ok) {
    throw new Error("Failed to fetch feedback stats");
  }

  return res.json();
}

/**
 * Parse Prometheus metrics text format to structured data
 */
export function parsePrometheusMetrics(text: string): Record<string, number> {
  const metrics: Record<string, number> = {};
  const lines = text.split("\n");

  for (const line of lines) {
    // Skip comments and empty lines
    if (line.startsWith("#") || !line.trim()) continue;

    // Parse metric line: metric_name{labels} value
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+([0-9.eE+-]+)/);
    if (match) {
      const [, name, value] = match;
      metrics[name] = parseFloat(value);
    }
  }

  return metrics;
}

/**
 * Calculate system health percentage from components
 */
export function calculateHealthPercentage(
  components: Record<string, { status: string }>
): number {
  const total = Object.keys(components).length;
  if (total === 0) return 0;

  const healthy = Object.values(components).filter(
    (c) => c.status === "healthy" || c.status === "ok"
  ).length;

  return Math.round((healthy / total) * 100);
}
