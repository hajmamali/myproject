import { apiClient } from './client';

export interface GraphHealthResponse {
  health_score: number;
  status: 'healthy' | 'degraded' | 'critical';
  timestamp: string;
  validation_results?: Record<string, unknown>;
  component_scores: {
    orphaned_nodes: number;
    circular_refs: number;
    hash_integrity: number;
    temporal_consistency: number;
    anomalies: number;
  };
  recommendations: string[];
}

export interface GraphViolation {
  id: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  entity_id: string;
  entity_label: string;
  message: string;
  detected_at: string;
  remediation?: string;
  affected_downstream?: string[];
  metadata?: Record<string, unknown>;
}

export interface GraphViolationsResponse {
  total: number;
  returned: number;
  offset: number;
  violations: GraphViolation[];
}

export interface ModelLeaderboardEntry {
  rank?: number;
  model_id: string;
  model_type: string;
  composite_score: number;
  score_breakdown: {
    success_rate_score: number;
    latency_score: number;
    throughput_score: number;
    reliability_score: number;
  };
  metrics: {
    total_requests: number;
    success_rate: number;
    avg_latency_ms: number;
    error_rate: number;
  };
  active: boolean;
}

export interface ModelLeaderboardResponse {
  timestamp: string;
  ranking: ModelLeaderboardEntry[];
  total_models: number;
}

export interface SystemOverviewResponse {
  timestamp: string;
  graph: {
    health_score: number;
    status: string;
    violations: {
      total: number;
      critical: number;
      high: number;
    };
  };
  models: {
    total: number;
    active: number;
    avg_success_rate: number;
    avg_latency_ms: number;
    top_performer: string;
  };
  system: {
    uptime_seconds: number;
    version: string;
  };
}

export interface CleanupResult {
  mode: string;
  dry_run: boolean;
  summary: {
    candidates_found: number;
    nodes_processed: number;
    nodes_deleted: number;
    errors_count: number;
  };
  candidates: Array<{
    node_id: string;
    label: string;
    classification: string;
    action: string;
    reason: string;
  }>;
  execution_time_ms: number;
  recommendations: string[];
}

export function getMonitoringGraphHealth() {
  return apiClient.get<GraphHealthResponse>('/monitoring/graph/health', { run_validation: true, parallel: true });
}

export function getMonitoringGraphViolations(params?: { severity?: string; violation_type?: string; limit?: number; offset?: number }) {
  return apiClient.get<GraphViolationsResponse>('/monitoring/graph/violations', params ?? {});
}

export function getMonitoringModelPerformance(params?: { model_id?: string; time_window?: number }) {
  return apiClient.get<Record<string, unknown>>('/monitoring/models/performance', params ?? {});
}

export function getMonitoringModelLeaderboard(params?: { top_n?: number; model_type?: string }) {
  return apiClient.get<ModelLeaderboardResponse>('/monitoring/models/leaderboard', params ?? {});
}

export function getMonitoringSystemOverview() {
  return apiClient.get<SystemOverviewResponse>('/monitoring/system/overview');
}

export function cleanupMonitoringOrphans(mode: 'safe' | 'aggressive' | 'manual-review', dry_run = true) {
  return apiClient.post<CleanupResult>('/monitoring/maintenance/cleanup-orphans', undefined, { mode, dry_run });
}
