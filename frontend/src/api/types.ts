/**
 * TypeScript interfaces for MAHOUN Legal Search API
 * 
 * These match the backend Pydantic models in:
 * - services/search/legal_search_service.py
 * - api/routers/search.py
 */

/**
 * Search filters for narrowing verdict results
 */
export interface LegalSearchFilters {
  /** Court level, e.g., "دادگاه تجدیدنظر استان" */
  court_level?: string | null;
  
  /** Type of case, e.g., "اعتراض ثالث اجرایی / رفع توقیف" */
  case_type?: string | null;
  
  /** Whether the verdict is final (قطعی) */
  is_final?: boolean | null;
  
  /** Law article number to filter by, e.g., "348" */
  article_no?: string | null;
  
  /** Name of law to filter by, e.g., "قانون آیین دادرسی مدنی" */
  law_name?: string | null;
  
  /** Tags to filter by */
  tags?: string[] | null;
}

/**
 * A single search hit representing a relevant verdict chunk
 */
export interface LegalSearchHit {
  /** Unique identifier of the verdict */
  verdict_id: string;
  
  /** Relevance score (0-1, higher is better) */
  score: number;
  
  /** Section of the verdict this chunk is from */
  section: string;
  
  /** The text content of the chunk */
  chunk_text: string;
  
  /** Type of case */
  case_type?: string | null;
  
  /** Court level */
  court_level?: string | null;
  
  /** Procedure stage */
  procedure_stage?: string | null;
  
  /** Whether final verdict */
  is_final?: boolean | null;
  
  /** Associated tags */
  tags: string[];
  
  /** Referenced law articles */
  law_articles: string[];
  
  /** Additional metadata */
  extra_metadata?: Record<string, unknown>;
}

/**
 * Request payload for verdict search
 */
export interface VerdictSearchRequest {
  /** Natural language search query */
  query: string;
  
  /** Optional filters to narrow results */
  filters?: LegalSearchFilters | null;
  
  /** Maximum number of results to return (default: 10) */
  limit?: number;
  
  /** Whether to enrich results with graph data */
  enrich_with_graph?: boolean;
}

/**
 * Response from verdict search endpoint
 */
export interface VerdictSearchResponse {
  /** List of search results */
  results: LegalSearchHit[];
  
  /** Total number of results returned */
  total: number;
  
  /** Original search query */
  query: string;
  
  /** Filters that were applied */
  filters_applied?: Record<string, unknown> | null;
}

/**
 * Error response structure
 */
export interface APIError {
  detail: string;
  status_code?: number;
}

/**
 * Training configuration for model fine-tuning
 */
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

/**
 * Training job status and progress
 */
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

/**
 * Model information for selection
 */
export interface ModelOption {
  id: string;
  name: string;
  provider: "huggingface" | "openai" | "anthropic" | "local";
  size: string;
  capabilities: string[];
  description: string;
  recommended?: boolean;
}

/**
 * Training preset configuration
 */
export interface TrainingPreset {
  id: string;
  name: string;
  description: string;
  config: Partial<TrainingConfig>;
}

