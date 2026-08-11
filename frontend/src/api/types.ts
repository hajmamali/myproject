/**
 * API Types and Interfaces
 */

export interface LegalSearchFilters {
  query?: string | null;
  jurisdiction?: string | null;
  caseType?: string | null;
  case_type?: string | null;
  dateRange?: {
    from: string;
    to: string;
  } | null;
  courtLevel?: string | null;
  court_level?: string | null;
  article_no?: string | null;
  law_name?: string | null;
  tags?: string[] | null;
  limit?: number | null;
  offset?: number | null;
  is_final?: boolean | null;
}

export interface LegalSearchHit {
  id: string;
  verdict_id?: string;
  title: string;
  content: string;
  chunk_text?: string;
  case_number?: string;
  court?: string;
  date?: string;
  judges?: string[];
  parties?: string[];
  case_type?: string;
  court_level?: string;
  procedure_stage?: string;
  is_final?: boolean | null;
  score?: number;
  section?: string;
  law_articles: Array<{
    article: string;
    section?: string;
    description?: string;
  }>;
  tags: string[];
  relevance_score?: number;
  verdict?: string;
  summary?: string;
  full_text_url?: string;
  metadata?: Record<string, any>;
}

export interface SearchResult {
  hits: LegalSearchHit[];
  results?: LegalSearchHit[];
  total: number;
  query: string;
  executionTime: number;
  filters?: LegalSearchFilters;
}

export interface JobStatusResponse {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'queued' | 'processing';
  progress?: number | {
    percent?: number;
    current_step?: string;
  };
  error?: string;
  result?: any;
  createdAt: string;
  updatedAt: string;
}

export interface TrainingJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  model?: string;
  datasetSize?: number;
  createdAt: string;
  completedAt?: string;
  error?: string;
}

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  version: string;
  description?: string;
  parameters?: Record<string, any>;
}

export interface VerdictRequest {
  caseId: string;
  question: string;
  context?: string;
  filters?: LegalSearchFilters;
}

export interface VerdictResponse {
  id: string;
  verdict: string;
  confidence: number;
  sources: LegalSearchHit[];
  reasoning: string;
  timestamp: string;
}
