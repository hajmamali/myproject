/**
 * MahouN API Client
 * Handles core business logic API calls
 */

import { apiClient } from './client';
import { JobStatusResponse } from './types';

// Re-export JobStatusResponse for external usage
export type { JobStatusResponse };

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  return apiClient.get(`/api/jobs/${jobId}`);
}

export async function cancelJob(jobId: string): Promise<{ success: boolean }> {
  return apiClient.post(`/api/jobs/${jobId}/cancel`);
}

export async function retryJob(jobId: string): Promise<JobStatusResponse> {
  return apiClient.post(`/api/jobs/${jobId}/retry`);
}

export async function listJobs(
  status?: string,
  limit?: number,
  offset?: number
): Promise<{ jobs: JobStatusResponse[]; total: number }> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (limit) params.append('limit', String(limit));
  if (offset) params.append('offset', String(offset));

  return apiClient.get(`/api/jobs?${params.toString()}`);
}

export async function getDocumentOCRStatus(docId: string): Promise<JobStatusResponse> {
  return apiClient.get(`/api/documents/${docId}/ocr-status`);
}

export async function retryDocumentOCR(docId: string): Promise<JobStatusResponse> {
  return apiClient.post(`/api/documents/${docId}/ocr-retry`);
}
