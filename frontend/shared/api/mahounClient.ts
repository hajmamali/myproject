/**
 * MAHOUN API Client
 * 
 * Client for MAHOUN-specific endpoints:
 * - Document upload
 * - Delay analysis
 * - Claim generation
 * - Contract Q&A
 * - Report generation
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const MAHOUN_BASE = `${API_BASE_URL}/api/v1/mahoun`;

export interface DocumentUploadResponse {
  success: boolean;
  document_id: string;
  doc_type: string;
  normalized: any;
  indexed: boolean;
  processing_time_ms: number;
}

export interface DelayAnalysisRequest {
  project_id: string;
  query?: string;
  baseline_schedule?: any;
  actual_schedule?: any;
}

export interface DelayAnalysisResponse {
  success: boolean;
  project_id: string;
  delays: Array<{
    description: string;
    delay_days: number;
    source: string;
    type: string;
  }>;
  delay_analysis: {
    total_delays: number;
    total_delay_days: number;
    average_delay: number;
  };
  critical_path: Array<{
    event: string;
    date: string;
    sequence: number;
  }>;
  attribution: Record<string, any>;
  processing_time_ms: number;
}

export interface ClaimGenerationRequest {
  claim_type: string;
  facts: string;
  legal_basis?: string;
  parties?: Record<string, string>;
}

export interface ClaimGenerationResponse {
  success: boolean;
  claim_id: string;
  claim_content: string;
  markdown: string;
  citations: Array<{
    doc_id: string;
    clause: string;
    citation_text: string;
  }>;
  processing_time_ms: number;
}

export interface ContractQueryRequest {
  query: string;
  clause_number?: string;
  contract_id?: string;
  top_k?: number;
}

export interface ContractQueryResponse {
  success: boolean;
  answer: string;
  confidence: number;
  verified: boolean;
  citations: Array<{
    doc_id: string;
    clause: string;
    citation_text: string;
  }>;
  clauses: Array<{
    clause_number: string;
    doc_id: string;
    citation_text: string;
  }>;
  processing_time_ms: number;
}

export interface ReportResponse {
  success: boolean;
  report_id: string;
  report_type: string;
  content: string;
  markdown: string;
  download_url?: string;
  processing_time_ms: number;
}

/**
 * Upload document
 */
export async function uploadDocument(
  file: File,
  docType: string,
  metadata?: any,
  index: boolean = true
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (docType) formData.append("doc_type", docType);
  if (metadata) formData.append("metadata", JSON.stringify(metadata));
  formData.append("index", String(index));

  const res = await fetch(`${MAHOUN_BASE}/upload-documents`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Upload failed");
  }

  return res.json();
}

/**
 * Analyze delays
 */
export async function analyzeDelay(
  request: DelayAnalysisRequest
): Promise<DelayAnalysisResponse> {
  const res = await fetch(`${MAHOUN_BASE}/analyze-delay`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Analysis failed");
  }

  return res.json();
}

/**
 * Generate claim
 */
export async function generateClaim(
  request: ClaimGenerationRequest
): Promise<ClaimGenerationResponse> {
  const res = await fetch(`${MAHOUN_BASE}/generate-claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Claim generation failed");
  }

  return res.json();
}

/**
 * Ask contract question
 */
export async function askContract(
  request: ContractQueryRequest
): Promise<ContractQueryResponse> {
  const res = await fetch(`${MAHOUN_BASE}/ask-contract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Query failed");
  }

  return res.json();
}

/**
 * Generate delay report
 */
export async function generateDelayReport(
  request: DelayAnalysisRequest
): Promise<ReportResponse> {
  const res = await fetch(`${MAHOUN_BASE}/generate-delay-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Report generation failed");
  }

  return res.json();
}

/**
 * Generate timeline report
 */
export async function generateTimelineReport(
  query?: string,
  documents?: string[],
  dateRange?: any
): Promise<ReportResponse> {
  const res = await fetch(`${MAHOUN_BASE}/generate-timeline-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, documents, date_range: dateRange }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Report generation failed");
  }

  return res.json();
}

/**
 * Get report by ID
 */
export async function getReport(
  reportId: string,
  format: "json" | "markdown" | "text" = "json"
): Promise<any> {
  const res = await fetch(`${MAHOUN_BASE}/reports/${reportId}?format=${format}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Report not found");
  }

  return res.json();
}

/**
 * List all reports
 */
export async function listReports(): Promise<{
  reports: Array<{
    report_id: string;
    report_type: string;
    generated_at: string;
  }>;
  total: number;
}> {
  const res = await fetch(`${MAHOUN_BASE}/reports`);

  if (!res.ok) {
    throw new Error("Failed to list reports");
  }

  return res.json();
}


// ============================================================================
// Phase 6: Async Job Management API
// ============================================================================

export interface JobProgressInfo {
  current_step: string;
  percent: number;
  sub_steps?: Record<string, boolean>;
}

export interface JobSubmissionResponse {
  job_id: string;
  status: "queued" | "pending" | "processing" | "completed" | "failed";
  submitted_at: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: "queued" | "pending" | "processing" | "completed" | "failed";
  progress?: JobProgressInfo;
  result?: {
    doc_id: string;
    vector_status: string;
    graph_status: string;
    sync_status: string;
    node_count: number;
  };
  error?: string;
  retry_count: number;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
}

export interface JobListResponse {
  jobs: JobStatusResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface DLQItem {
  job_id: string;
  file_name: string;
  failed_at: string;
  error_type: "OOM" | "CorruptedFile" | "ParseError" | "Timeout" | "Unknown";
  error_message: string;
  retry_count: number;
  can_retry: boolean;
  original_metadata?: Record<string, any>;
}

export interface DLQListResponse {
  items: DLQItem[];
  total: number;
}

export interface DLQRetryResponse {
  success: boolean;
  new_job_id?: string;
  message: string;
}

const INGEST_BASE = `${API_BASE_URL}/api/v1/ingest`;
const TRAINING_DATASETS_BASE = `${API_BASE_URL}/api/v1/training-datasets`;

/**
 * Submit document for async ingestion (Phase 6)
 * 
 * Returns immediately with job_id. Client should poll /jobs/{job_id} for status.
 */
export async function submitIngestionJob(
  file: File,
  docType: string = "contract",
  metadata?: Record<string, any>
): Promise<JobSubmissionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);
  if (metadata) {
    formData.append("metadata", JSON.stringify(metadata));
  }

  const res = await fetch(`${INGEST_BASE}/submit`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Job submission failed");
  }

  return res.json();
}

export async function submitDatasetGenerationJob(
  file: File,
  domain: string = "general",
  qaStrategy: string = "hybrid",
  minQuality: number = 0.7,
  enableGroundedness: boolean = true
): Promise<any> { // Returns JobStatus from training-datasets API
  const formData = new FormData();
  formData.append("file", file);
  formData.append("domain", domain);
  formData.append("qa_strategy", qaStrategy);
  formData.append("min_quality_score", minQuality.toString());
  formData.append("enable_groundedness_check", enableGroundedness.toString());
  formData.append("output_format", "jsonl");

  const res = await fetch(`${TRAINING_DATASETS_BASE}/from-document/async`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Dataset generation submission failed");
  }

  return res.json();
}

/**
 * Get dataset job status
 */
export async function getDatasetJobStatus(jobId: string): Promise<any> {
  const res = await fetch(`${TRAINING_DATASETS_BASE}/jobs/${jobId}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to get dataset job status");
  }

  return res.json();
}

/**
 * Get job status (for polling)
 */
export async function getJobStatus(
  jobId: string
): Promise<JobStatusResponse> {
  const res = await fetch(`${INGEST_BASE}/jobs/${jobId}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to get job status");
  }

  return res.json();
}

/**
 * List all ingestion jobs
 */
export async function listJobs(
  statusFilter?: string,
  limit: number = 20,
  offset: number = 0
): Promise<JobListResponse> {
  const params = new URLSearchParams();
  if (statusFilter) params.append("status_filter", statusFilter);
  params.append("limit", limit.toString());
  params.append("offset", offset.toString());

  const res = await fetch(`${INGEST_BASE}/jobs?${params}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to list jobs");
  }

  return res.json();
}

/**
 * List Dead Letter Queue items
 */
export async function listDLQItems(): Promise<DLQListResponse> {
  const res = await fetch(`${INGEST_BASE}/dlq`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to list DLQ items");
  }

  return res.json();
}

/**
 * Get specific DLQ item details
 */
export async function getDLQItem(jobId: string): Promise<DLQItem> {
  const res = await fetch(`${INGEST_BASE}/dlq/${jobId}`);

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to get DLQ item");
  }

  return res.json();
}

/**
 * Retry a failed job from DLQ
 */
export async function retryDLQJob(jobId: string): Promise<DLQRetryResponse> {
  const res = await fetch(`${INGEST_BASE}/dlq/${jobId}/retry`, {
    method: "POST",
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to retry DLQ job");
  }

  return res.json();
}

/**
 * Delete DLQ item
 */
export async function deleteDLQItem(jobId: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${INGEST_BASE}/dlq/${jobId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to delete DLQ item");
  }

  return res.json();
}

