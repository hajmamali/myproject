/**
 * Training API Client
 * Handles model training and fine-tuning API calls
 */

import { apiClient } from './client';
import { TrainingJob, ModelOption } from './types';

// Re-export types for external usage
export type { TrainingJob, ModelOption };

export async function listTrainingJobs(
  status?: string,
  limit?: number
): Promise<{ jobs: TrainingJob[]; total: number }> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (limit) params.append('limit', String(limit));

  return apiClient.get(`/api/training/jobs?${params.toString()}`);
}

export async function getTrainingJob(jobId: string): Promise<TrainingJob> {
  return apiClient.get(`/api/training/jobs/${jobId}`);
}

export async function createTrainingJob(data: {
  name: string;
  model: string;
  datasetId: string;
  hyperparameters?: Record<string, any>;
}): Promise<TrainingJob> {
  return apiClient.post('/api/training/jobs', data);
}

export async function stopTrainingJob(jobId: string): Promise<{ success: boolean }> {
  return apiClient.post(`/api/training/jobs/${jobId}/stop`);
}

export async function deleteTrainingJob(jobId: string): Promise<{ success: boolean }> {
  return apiClient.delete(`/api/training/jobs/${jobId}`);
}

export async function listAvailableModels(): Promise<ModelOption[]> {
  return apiClient.get('/api/training/models');
}

export async function getModelDetails(modelId: string): Promise<ModelOption> {
  return apiClient.get(`/api/training/models/${modelId}`);
}

export async function deployModel(jobId: string): Promise<{ deploymentId: string }> {
  return apiClient.post(`/api/training/jobs/${jobId}/deploy`);
}
