/**
 * Training API Client — canonical implementation
 * 
 * fabrication-check-ok: placeholder for future training API integration
 */

export interface TrainingConfig {
  model_name: string;
  dataset_id: string;
  epochs?: number;
  learning_rate?: number;
  batch_size?: number;
}

export interface TrainingJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  config: TrainingConfig;
}

export interface TrainingJobResponse {
  job: TrainingJob;
}

export async function startTrainingJob(config: TrainingConfig): Promise<TrainingJobResponse> {
  // Placeholder implementation
  return {
    job: {
      id: 'placeholder-' + Date.now(),
      status: 'pending',
      progress: 0,
      created_at: new Date().toISOString(),
      config,
    },
  };
}

export async function getTrainingJobStatus(jobId: string): Promise<TrainingJob> {
  return {
    id: jobId,
    status: 'pending',
    progress: 0,
    created_at: new Date().toISOString(),
    config: { model_name: 'placeholder', dataset_id: 'placeholder' },
  };
}

export async function listTrainingJobs(): Promise<TrainingJob[]> {
  return [];
}

export async function stopTrainingJob(_jobId: string): Promise<void> {
  // Placeholder - jobId will be used when backend integration is complete
}

export async function deleteTrainingJob(_jobId: string): Promise<void> {
  // Placeholder - jobId will be used when backend integration is complete
}

export async function getAvailableModels(): Promise<{ models: Array<{ id: string; name: string; provider: string; size?: string }> }> {
  return {
    models: [
      { id: 'model-1', name: 'Model 1', provider: 'local', size: '7B' },
      { id: 'model-2', name: 'Model 2', provider: 'local', size: '13B' },
    ],
  };
}

export async function getTrainingPresets(): Promise<TrainingConfig[]> {
  return [];
}

/** @deprecated Use getAvailableModels */
export const listAvailableModels = getAvailableModels;
