/**
 * Training API Client
 *
 * Client for MAHOUN training and fine-tuning endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface TrainingConfig {
  model_name: string;
  training_mode: "full_finetune" | "lora" | "qlora" | "dora" | "adalora";
  quantization_mode?: "none" | "int8" | "int4" | "fp8";
  num_train_epochs: number;
  per_device_train_batch_size: number;
  per_device_eval_batch_size: number;
  gradient_accumulation_steps: number;
  learning_rate: number;
  weight_decay: number;
  warmup_ratio: number;
  max_grad_norm: number;
  dataset_name?: string;
  output_dir?: string;
  run_name?: string;
  seed?: number;
}

export interface TrainingJob {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  config: TrainingConfig;
  progress?: {
    epoch: number;
    step: number;
    total_steps: number;
    loss: number;
    learning_rate: number;
  };
  metrics?: {
    train_loss: number;
    eval_loss?: number;
    accuracy?: number;
    perplexity?: number;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface TrainingJobResponse {
  success: boolean;
  job_id: string;
  message: string;
  job: TrainingJob;
}

/**
 * Start a new training job
 */
export async function startTrainingJob(config: TrainingConfig): Promise<TrainingJobResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/training/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify(config),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to start training job");
  }

  return res.json();
}

/**
 * Get training job status
 */
export async function getTrainingJobStatus(jobId: string): Promise<TrainingJob> {
  const res = await fetch(`${API_BASE_URL}/api/v1/training/jobs/${jobId}`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to get training job status");
  }

  return res.json();
}

/**
 * List all training jobs
 */
export async function listTrainingJobs(
  status?: string,
  limit: number = 20,
  offset: number = 0
): Promise<{
  jobs: TrainingJob[];
  total: number;
  limit: number;
  offset: number;
}> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  const res = await fetch(`${API_BASE_URL}/api/v1/training/jobs?${params}`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to list training jobs");
  }

  return res.json();
}

/**
 * Stop a training job
 */
export async function stopTrainingJob(jobId: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/training/jobs/${jobId}/stop`, {
    method: "POST",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to stop training job");
  }

  return res.json();
}

/**
 * Delete a training job
 */
export async function deleteTrainingJob(jobId: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/training/jobs/${jobId}`, {
    method: "DELETE",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to delete training job");
  }

  return res.json();
}

/**
 * Get available models
 */
export async function getAvailableModels(): Promise<{
  models: Array<{
    id: string;
    name: string;
    provider: string;
    size: string;
    capabilities: string[];
    description: string;
  }>;
}> {
  const res = await fetch(`${API_BASE_URL}/api/v1/training/models`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    // If endpoint doesn't exist, return mock data
    return {
      models: [
        {
          id: "microsoft/DialoGPT-medium",
          name: "DialoGPT Medium",
          provider: "huggingface",
          size: "117M parameters",
          capabilities: ["conversational", "text-generation"],
          description: "مدل گفتگویی مبتنی بر GPT-2",
        },
        {
          id: "microsoft/Phi-2",
          name: "Phi-2",
          provider: "huggingface",
          size: "2.7B parameters",
          capabilities: ["text-generation", "reasoning", "code"],
          description: "مدل پیشرفته Microsoft",
        },
      ],
    };
  }

  return res.json();
}

/**
 * Get training presets
 */
export async function getTrainingPresets(): Promise<{
  presets: Array<{
    id: string;
    name: string;
    description: string;
    config: Partial<TrainingConfig>;
  }>;
}> {
  // Return predefined presets
  return {
    presets: [
      {
        id: "legal-chat-finetune",
        name: "فاین‌تیون چت‌بات حقوقی",
        description: "برای آموزش مدل‌های گفتگویی در زمینه حقوق",
        config: {
          training_mode: "lora",
          num_train_epochs: 3,
          per_device_train_batch_size: 4,
          learning_rate: 0.0002,
          warmup_ratio: 0.03,
        },
      },
      {
        id: "legal-classification",
        name: "طبقه‌بندی اسناد حقوقی",
        description: "برای آموزش مدل‌های طبقه‌بندی متن حقوقی",
        config: {
          training_mode: "full_finetune",
          num_train_epochs: 5,
          per_device_train_batch_size: 8,
          learning_rate: 0.0001,
          warmup_ratio: 0.1,
        },
      },
      {
        id: "legal-embedding-finetune",
        name: "فاین‌تیون embedding حقوقی",
        description: "برای بهبود مدل‌های embedding در زمینه حقوق",
        config: {
          training_mode: "qlora",
          quantization_mode: "int4",
          num_train_epochs: 2,
          per_device_train_batch_size: 16,
          learning_rate: 0.0005,
          warmup_ratio: 0.05,
        },
      },
    ],
  };
}
