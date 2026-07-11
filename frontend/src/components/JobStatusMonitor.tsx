/**
 * JobStatusMonitor - Real-time Job Status Monitoring
 * 
 * Enterprise-grade job monitoring with:
 * - Automatic polling (every 2s)
 * - Progress visualization
 * - Status indicators
 * - Error handling
 * - Completion callbacks
 */

import { useState, useEffect, useCallback } from "react";
import { getJobStatus, JobStatusResponse } from "../api/mahounClient";
import {
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";

interface JobStatusMonitorProps {
  jobId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
  pollingInterval?: number;
}

export default function JobStatusMonitor({
  jobId,
  onComplete,
  onError,
  pollingInterval = 2000,
}: JobStatusMonitorProps) {
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await getJobStatus(jobId);
      setStatus(response);
      setError(null);

      // Handle completion
      if (response.status === "completed") {
        setLoading(false);
        onComplete?.();
      }

      // Handle failure
      if (response.status === "failed") {
        setLoading(false);
        const errorMsg = response.error || "Job failed";
        setError(errorMsg);
        onError?.(errorMsg);
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Failed to fetch job status";
      setError(errorMsg);
      setLoading(false);
      onError?.(errorMsg);
    }
  }, [jobId, onComplete, onError]);

  useEffect(() => {
    // Initial fetch
    fetchStatus();

    // Setup polling
    const interval = setInterval(() => {
      if (status?.status !== "completed" && status?.status !== "failed") {
        fetchStatus();
      }
    }, pollingInterval);

    return () => clearInterval(interval);
  }, [fetchStatus, pollingInterval, status?.status]);

  if (!status && loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <ArrowPathIcon className="h-4 w-4 animate-spin" />
        <span>در حال بارگذاری وضعیت...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-400">
        <XCircleIcon className="h-4 w-4" />
        <span>{error}</span>
      </div>
    );
  }

  if (!status) return null;

  const getStatusIcon = () => {
    switch (status.status) {
      case "completed":
        return <CheckCircleIcon className="h-5 w-5 text-green-400" />;
      case "failed":
        return <XCircleIcon className="h-5 w-5 text-red-400" />;
      case "processing":
        return <ArrowPathIcon className="h-5 w-5 text-primary-400 animate-spin" />;
      default:
        return <ClockIcon className="h-5 w-5 text-slate-400" />;
    }
  };

  const getStatusText = () => {
    switch (status.status) {
      case "queued":
        return "در صف انتظار";
      case "pending":
        return "در انتظار پردازش";
      case "processing":
        return "در حال پردازش";
      case "completed":
        return "تکمیل شد";
      case "failed":
        return "خطا";
      default:
        return status.status;
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case "completed":
        return "text-green-400";
      case "failed":
        return "text-red-400";
      case "processing":
        return "text-primary-400";
      default:
        return "text-slate-400";
    }
  };

  const progress = status.progress?.percent || 0;
  const currentStep = status.progress?.current_step || "";

  return (
    <div className="space-y-3">
      {/* Status header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className={`text-sm font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </span>
        </div>
        {status.status === "processing" && (
          <span className="text-xs text-slate-500">{progress}%</span>
        )}
      </div>

      {/* Progress bar */}
      {status.status === "processing" && (
        <div className="space-y-1">
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-600 transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          {currentStep && (
            <p className="text-xs text-slate-500">{currentStep}</p>
          )}
        </div>
      )}

      {/* Completion details */}
      {status.status === "completed" && status.result && (
        <div className="text-xs text-slate-400 space-y-1">
          <div className="flex justify-between">
            <span>Document ID:</span>
            <span className="font-mono text-slate-300">{status.result.doc_id}</span>
          </div>
          {status.result.node_count > 0 && (
            <div className="flex justify-between">
              <span>Graph Nodes:</span>
              <span className="text-slate-300">{status.result.node_count}</span>
            </div>
          )}
        </div>
      )}

      {/* Error details */}
      {status.status === "failed" && status.error && (
        <div className="text-xs text-red-400 bg-red-950/30 border border-red-900/50 rounded p-2">
          {status.error}
        </div>
      )}
    </div>
  );
}
