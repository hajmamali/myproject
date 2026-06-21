/**
 * A/B Testing & Experiments API Client
 * =====================================
 * Typed client for /api/v1/experiments endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const EXPERIMENTS_BASE = `${API_BASE_URL}/api/v1/experiments`;

// ============================================================================
// Types
// ============================================================================

export interface ExperimentRequest {
  name: string;
  variants: string[];
  traffic_split: number[];
  metrics: string[];
  metadata?: Record<string, any>;
}

export interface Experiment {
  experiment_id: string;
  name: string;
  variants: string[];
  traffic_split: number[];
  status: "created" | "running" | "completed" | "stopped";
  samples?: number;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface ExperimentResults {
  experiment_id: string;
  status: string;
  results: {
    [variant: string]: {
      samples: number;
      accuracy: number;
      latency_p95: number;
      [metric: string]: number;
    };
  };
  statistical_significance: {
    [metric: string]: {
      p_value: number;
      significant: boolean;
    };
  };
  recommendation: "PROMOTE" | "REJECT" | "CONTINUE";
}

export interface ExperimentListResponse {
  experiments: Experiment[];
  total: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Create a new A/B test experiment
 */
export async function createExperiment(
  request: ExperimentRequest
): Promise<Experiment> {
  const res = await fetch(EXPERIMENTS_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to create experiment");
  }

  return res.json();
}

/**
 * List all experiments
 */
export async function listExperiments(
  status?: string,
  limit: number = 10
): Promise<ExperimentListResponse> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  params.append("limit", limit.toString());

  const res = await fetch(`${EXPERIMENTS_BASE}?${params}`);

  if (!res.ok) {
    throw new Error("Failed to fetch experiments");
  }

  return res.json();
}

/**
 * Stop a running experiment
 */
export async function stopExperiment(
  experimentId: string
): Promise<{
  experiment_id: string;
  status: string;
  stopped_at: string;
}> {
  const res = await fetch(`${EXPERIMENTS_BASE}/${experimentId}/stop`, {
    method: "POST",
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to stop experiment");
  }

  return res.json();
}

/**
 * Get experiment results
 */
export async function getExperimentResults(
  experimentId: string
): Promise<ExperimentResults> {
  const res = await fetch(`${EXPERIMENTS_BASE}/${experimentId}/results`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to fetch experiment results");
  }

  return res.json();
}

/**
 * Calculate winner from experiment results
 */
export function calculateWinner(
  results: ExperimentResults,
  metric: string = "accuracy"
): string | null {
  const variants = Object.entries(results.results);
  if (variants.length === 0) return null;

  const winner = variants.reduce((best, [name, data]) => {
    const bestValue = best[1][metric] || 0;
    const currentValue = data[metric] || 0;
    return currentValue > bestValue ? [name, data] : best;
  });

  return winner[0];
}

/**
 * Check if experiment has statistical significance
 */
export function hasStatisticalSignificance(
  results: ExperimentResults,
  metric: string,
  threshold: number = 0.05
): boolean {
  const sig = results.statistical_significance[metric];
  return sig ? sig.p_value < threshold : false;
}
