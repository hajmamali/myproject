/**
 * Fine-Tuning API Client
 * ======================
 * Typed client for /api/v1/finetuning endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const FINETUNING_BASE = `${API_BASE_URL}/api/v1/finetuning`;

// ============================================================================
// Types
// ============================================================================

export type TrainingStatus = 
  | "pending" 
  | "preparing" 
  | "training" 
  | "evaluating" 
  | "completed" 
  | "failed" 
  | "cancelled";

export type TrainingMode = 
  | "full_finetune" 
  | "lora" 
  | "qlora" 
  | "dora" 
  | "adalora";

export type DatasetSource = "feedback" | "upload" | "existing";

export interface FineTuningConfig {
  model_name: string;
  training_mode: TrainingMode;
  learning_rate: number;
  num_epochs: number;
  batch_size: number;
  gradient_accumulation_steps: number;
  warmup_ratio: number;
  lora_r: number;
  lora_alpha: number;
  lora_dropout: number;
  use_gradient_checkpointing: boolean;
  use_mixed_precision: boolean;
  max_grad_norm: number;
  load_in_4bit: boolean;
  load_in_8bit: boolean;
}

export interface DatasetConfig {
  source: DatasetSource;
  dataset_id?: string;
  feedback_start_date?: string;
  feedback_end_date?: string;
  min_rating?: number;
  train_ratio: number;
  eval_ratio: number;
  test_ratio: number;
}

export interface FineTuningJob {
  job_id: string;
  job_name: string;
  description?: string;
  status: TrainingStatus;
  config: FineTuningConfig;
  dataset: DatasetConfig;
  current_epoch: number;
  total_epochs: number;
  current_step: number;
  total_steps: number;
  progress_percentage: number;
  train_loss?: number;
  eval_loss?: number;
  eval_accuracy?: number;
  learning_rate?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  gpu_memory_used?: number;
  estimated_time_remaining?: number;
  model_path?: string;
  checkpoint_path?: string;
  logs_path?: string;
}

export interface TrainingMetrics {
  timestamp: string;
  epoch: number;
  step: number;
  train_loss: number;
  eval_loss?: number;
  eval_accuracy?: number;
  eval_perplexity?: number;
  learning_rate: number;
  gpu_memory_mb?: number;
  samples_per_second?: number;
}

export interface FineTuningRequest {
  job_name: string;
  description?: string;
  config: Partial<FineTuningConfig>;
  dataset: Partial<DatasetConfig>;
  auto_deploy?: boolean;
  deployment_strategy?: string;
}

export interface DeploymentRequest {
  job_id: string;
  strategy?: string;
  traffic_percentage?: number;
  rollback_on_error?: boolean;
}

export interface Dataset {
  dataset_id: string;
  name: string;
  source: DatasetSource;
  size: number;
  created_at: string;
}

export interface LogsResponse {
  job_id: string;
  lines: string[];
  total_lines: number;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Create and start a new fine-tuning job
 */
export async function createFineTuningJob(
  request: FineTuningRequest
): Promise<FineTuningJob> {
  const res = await fetch(`${FINETUNING_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to create fine-tuning job");
  }

  return res.json();
}

/**
 * List all fine-tuning jobs
 */
export async function listFineTuningJobs(
  status?: TrainingStatus,
  limit: number = 50
): Promise<FineTuningJob[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  params.append("limit", limit.toString());

  const res = await fetch(`${FINETUNING_BASE}/jobs?${params}`);

  if (!res.ok) {
    throw new Error("Failed to fetch fine-tuning jobs");
  }

  return res.json();
}

/**
 * Get detailed information about a specific job
 */
export async function getFineTuningJob(jobId: string): Promise<FineTuningJob> {
  const res = await fetch(`${FINETUNING_BASE}/jobs/${jobId}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || `Job ${jobId} not found`);
  }

  return res.json();
}

/**
 * Cancel a running fine-tuning job
 */
export async function cancelFineTuningJob(
  jobId: string
): Promise<{ status: string; job_id: string }> {
  const res = await fetch(`${FINETUNING_BASE}/jobs/${jobId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to cancel job");
  }

  return res.json();
}

/**
 * Get training metrics for a job
 */
export async function getTrainingMetrics(
  jobId: string,
  limit: number = 100
): Promise<TrainingMetrics[]> {
  const params = new URLSearchParams();
  params.append("limit", limit.toString());

  const res = await fetch(`${FINETUNING_BASE}/jobs/${jobId}/metrics?${params}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to fetch metrics");
  }

  return res.json();
}

/**
 * Get training logs for a job
 */
export async function getTrainingLogs(
  jobId: string,
  lines: number = 100
): Promise<LogsResponse> {
  const params = new URLSearchParams();
  params.append("lines", lines.toString());

  const res = await fetch(`${FINETUNING_BASE}/jobs/${jobId}/logs?${params}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to fetch logs");
  }

  return res.json();
}

/**
 * Deploy a fine-tuned model to production
 */
export async function deployFineTunedModel(
  deployment: DeploymentRequest
): Promise<{
  status: string;
  job_id: string;
  strategy: string;
  traffic_percentage: number;
  model_path: string;
  deployed_at: string;
}> {
  const res = await fetch(
    `${FINETUNING_BASE}/jobs/${deployment.job_id}/deploy`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(deployment),
    }
  );

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to deploy model");
  }

  return res.json();
}

/**
 * List available datasets for fine-tuning
 */
export async function listDatasets(): Promise<{
  datasets: Dataset[];
  total: number;
}> {
  const res = await fetch(`${FINETUNING_BASE}/datasets`);

  if (!res.ok) {
    throw new Error("Failed to fetch datasets");
  }

  return res.json();
}

/**
 * Create a training dataset from user feedback
 */
export async function createDatasetFromFeedback(
  startDate?: string,
  endDate?: string,
  minRating: number = 4.0
): Promise<{
  dataset_id: string;
  name: string;
  source: string;
  size: number;
  avg_quality_score: number;
  splits: {
    train: number;
    eval: number;
    test: number;
  };
  start_date?: string;
  end_date?: string;
  min_rating: number;
  created_at: string;
  files: Record<string, string>;
}> {
  const params = new URLSearchParams();
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  params.append("min_rating", minRating.toString());

  const res = await fetch(
    `${FINETUNING_BASE}/datasets/from-feedback?${params}`,
    {
      method: "POST",
    }
  );

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to create dataset from feedback");
  }

  return res.json();
}
