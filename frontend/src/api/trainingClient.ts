/**
 * Training & Fine-Tuning API Client — Canonical Implementation
 *
 * Connects directly to backend routers:
 * - Fine-Tuning Jobs: /api/v1/finetuning/jobs
 * - Models: /api/v1/models (with fallback to fine-tuned / leaderboard models)
 * - Presets: /api/v1/finetuning/presets
 */

import { apiClient } from './client';

export type TrainingMode = 'full_finetune' | 'lora' | 'qlora' | 'dora' | 'adalora';
export type TrainingStatus = 'pending' | 'preparing' | 'training' | 'evaluating' | 'completed' | 'failed' | 'cancelled';

export interface TrainingConfig {
  model_name: string;
  dataset_id?: string;
  training_mode?: TrainingMode;
  epochs?: number;
  learning_rate?: number;
  batch_size?: number;
  gradient_accumulation_steps?: number;
  warmup_ratio?: number;
  lora_r?: number;
  lora_alpha?: number;
  lora_dropout?: number;
  use_gradient_checkpointing?: boolean;
  use_mixed_precision?: boolean;
  load_in_4bit?: boolean;
  load_in_8bit?: boolean;
}

export interface TrainingJob {
  id: string;
  name?: string;
  model_name: string;
  dataset_id?: string;
  training_mode?: TrainingMode;
  status: TrainingStatus;
  progress: number;
  current_step?: number;
  total_steps?: number;
  train_loss?: number;
  eval_loss?: number;
  eval_accuracy?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  model_path?: string;
  checkpoint_path?: string;
  config?: TrainingConfig;
}

export interface TrainingJobResponse {
  job: TrainingJob;
}

export interface TrainingMetrics {
  timestamp: string;
  epoch: number;
  step: number;
  train_loss: number;
  eval_loss?: number;
  eval_accuracy?: number;
  learning_rate: number;
  gpu_memory_mb?: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  size?: string;
  description?: string;
  status?: string;
}

/**
 * Start a new fine-tuning training job
 */
export async function startTrainingJob(config: TrainingConfig): Promise<TrainingJobResponse> {
  const payload = {
    model_name: config.model_name,
    training_mode: config.training_mode || 'lora',
    learning_rate: config.learning_rate ?? 0.00002,
    num_epochs: config.epochs ?? 3,
    batch_size: config.batch_size ?? 4,
    gradient_accumulation_steps: config.gradient_accumulation_steps ?? 4,
    warmup_ratio: config.warmup_ratio ?? 0.1,
    lora_r: config.lora_r ?? 8,
    lora_alpha: config.lora_alpha ?? 16,
    lora_dropout: config.lora_dropout ?? 0.05,
    use_gradient_checkpointing: config.use_gradient_checkpointing ?? true,
    use_mixed_precision: config.use_mixed_precision ?? true,
    load_in_4bit: config.load_in_4bit ?? false,
    load_in_8bit: config.load_in_8bit ?? false,
    dataset_id: config.dataset_id,
  };

  const response = await apiClient.post<any>('/api/v1/finetuning/jobs', {
    config: payload,
    dataset_config: {
      source: config.dataset_id ? 'existing' : 'feedback',
      dataset_id: config.dataset_id,
    },
    auto_deploy: false,
  });

  const job: TrainingJob = {
    id: response.job_id || response.id,
    model_name: response.model_name || config.model_name,
    status: response.status || 'pending',
    progress: response.progress ?? 0,
    created_at: response.created_at || new Date().toISOString(),
    config,
  };

  return { job };
}

/**
 * Get the status of a specific training job
 */
export async function getTrainingJobStatus(jobId: string): Promise<TrainingJob> {
  const data = await apiClient.get<any>(`/api/v1/finetuning/jobs/${jobId}`);
  return {
    id: data.job_id || data.id || jobId,
    name: data.name,
    model_name: data.model_name || data.config?.model_name || 'LegalBERT-Fa',
    status: data.status || 'pending',
    progress: data.progress ?? 0,
    current_step: data.current_step,
    total_steps: data.total_steps,
    train_loss: data.train_loss,
    eval_loss: data.eval_loss,
    eval_accuracy: data.eval_accuracy,
    created_at: data.created_at || new Date().toISOString(),
    started_at: data.started_at,
    completed_at: data.completed_at,
    error: data.error,
    model_path: data.model_path,
    checkpoint_path: data.checkpoint_path,
    config: data.config,
  };
}

/**
 * List all training jobs with optional status filter
 */
export async function listTrainingJobs(status?: TrainingStatus): Promise<TrainingJob[]> {
  try {
    const jobs = await apiClient.get<any[]>('/api/v1/finetuning/jobs', {
      params: status ? { status } : {},
    });

    if (!Array.isArray(jobs)) return [];

    return jobs.map((data) => ({
      id: data.job_id || data.id,
      name: data.name,
      model_name: data.model_name || data.config?.model_name || 'LegalBERT-Fa',
      status: data.status || 'pending',
      progress: data.progress ?? 0,
      current_step: data.current_step,
      total_steps: data.total_steps,
      train_loss: data.train_loss,
      eval_loss: data.eval_loss,
      eval_accuracy: data.eval_accuracy,
      created_at: data.created_at || new Date().toISOString(),
      started_at: data.started_at,
      completed_at: data.completed_at,
      error: data.error,
      config: data.config,
    }));
  } catch (err) {
    console.error('Failed to list training jobs:', err);
    return [];
  }
}

/**
 * Stop and cancel a running training job
 */
export async function stopTrainingJob(jobId: string): Promise<void> {
  await apiClient.delete(`/api/v1/finetuning/jobs/${jobId}`);
}

/**
 * Delete a training job
 */
export async function deleteTrainingJob(jobId: string): Promise<void> {
  await apiClient.delete(`/api/v1/finetuning/jobs/${jobId}`);
}

/**
 * Get real-time metrics for a training job
 */
export async function getTrainingJobMetrics(jobId: string): Promise<TrainingMetrics[]> {
  try {
    return await apiClient.get<TrainingMetrics[]>(`/api/v1/finetuning/jobs/${jobId}/metrics`);
  } catch (err) {
    console.error(`Failed to get metrics for job ${jobId}:`, err);
    return [];
  }
}

/**
 * Get available base and fine-tuned models from the backend
 */
export async function getAvailableModels(): Promise<{ models: ModelInfo[] }> {
  try {
    const response = await apiClient.get<any>('/api/v1/models').catch(() => null);
    if (response && Array.isArray(response.models)) {
      return response;
    }

    // Fallback to active leaderboard models
    const leaderboard = await apiClient.get<any>('/monitoring/models/leaderboard').catch(() => null);
    if (leaderboard && Array.isArray(leaderboard.ranking)) {
      const models: ModelInfo[] = leaderboard.ranking.map((m: any) => ({
        id: m.model_id,
        name: m.model_id.replace(/[-_]/g, ' '),
        provider: m.model_type || 'local',
        description: `Composite score: ${Math.round((m.composite_score || 0) * 100)}%`,
        status: m.active ? 'active' : 'inactive',
      }));
      return { models };
    }
  } catch (err) {
    console.error('Failed to fetch available models:', err);
  }

  // Canonical base legal models for MahouN
  return {
    models: [
      { id: 'dorna-llama-3-8b', name: 'Dorna LLaMA 3 (8B)', provider: 'local', size: '8B', description: 'مدل تخصصی حقوقی فارسی' },
      { id: 'maral-7b-alpha', name: 'Maral 7B Alpha', provider: 'local', size: '7B', description: 'مدل عمومی زبان فارسی' },
      { id: 'persian-legal-bert', name: 'Persian Legal BERT', provider: 'local', size: '330M', description: 'مدل طبقه‌بندی و بازیابی اسناد' },
    ],
  };
}

/**
 * Get fine-tuning parameter presets for legal tasks
 */
export async function getTrainingPresets(): Promise<TrainingConfig[]> {
  return [
    {
      model_name: 'dorna-llama-3-8b',
      training_mode: 'lora',
      epochs: 3,
      learning_rate: 0.00002,
      batch_size: 4,
      lora_r: 16,
      lora_alpha: 32,
    },
    {
      model_name: 'persian-legal-bert',
      training_mode: 'full_finetune',
      epochs: 5,
      learning_rate: 0.00005,
      batch_size: 16,
    },
  ];
}

/** @deprecated Use getAvailableModels */
export const listAvailableModels = getAvailableModels;
