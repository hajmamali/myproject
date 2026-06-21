/**
 * Monitoring Dashboard Component
 *
 * Real-time monitoring of training jobs, system metrics, and performance analytics
 */

import { useState, useEffect } from "react";
import {
  ChartBarIcon,
  ClockIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  StopIcon,
  TrashIcon,
  EyeIcon,
} from "@heroicons/react/24/outline";
import { TrainingJob, listTrainingJobs, stopTrainingJob, deleteTrainingJob } from "../api/trainingClient";
import { getLegalMetrics, getDetailedHealth, getDashboardData, type LegalMetrics, type HealthStatus, type DashboardData } from "../api/monitoringClient";

interface MonitoringDashboardProps {
  className?: string;
}

interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  gpu_usage?: number;
  active_jobs: number;
  total_jobs: number;
  uptime: number;
}

export default function MonitoringDashboard({ className = "" }: MonitoringDashboardProps) {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<SystemMetrics>({
    cpu_usage: 0,
    memory_usage: 0,
    gpu_usage: 0,
    active_jobs: 0,
    total_jobs: 0,
    uptime: 0,
  });
  const [legalMetrics, setLegalMetrics] = useState<LegalMetrics | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);

  // Load training jobs
  useEffect(() => {
    loadJobs();
    loadMetrics();
    // Set up real-time updates
    const jobsInterval = setInterval(loadJobs, 5000); // Update every 5 seconds
    const metricsInterval = setInterval(loadMetrics, 10000); // Update every 10 seconds
    return () => {
      clearInterval(jobsInterval);
      clearInterval(metricsInterval);
    };
  }, []);

  const loadJobs = async () => {
    try {
      const response = await listTrainingJobs();
      setJobs(response.jobs);
    } catch (error) {
      console.error("Failed to load jobs:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      // Load dashboard data
      const dashboard = await getDashboardData();
      
      // Extract system metrics from dashboard
      setMetrics({
        cpu_usage: 0, // TODO: Extract from dashboard if available
        memory_usage: 0,
        gpu_usage: 0,
        active_jobs: Object.values(dashboard.components).filter(c => c.status === "running").length,
        total_jobs: Object.keys(dashboard.components).length,
        uptime: dashboard.components.orchestrator?.uptime || 0,
      });

      // Load legal metrics
      const legal = await getLegalMetrics();
      setLegalMetrics(legal);

      // Load health status
      const health = await getDetailedHealth();
      setHealthStatus(health);
    } catch (error) {
      console.error("Failed to load metrics:", error);
    }
  };

  const handleStopJob = async (jobId: string) => {
    if (confirm("آیا مطمئن هستید که می‌خواهید این کار را متوقف کنید؟")) {
      try {
        await stopTrainingJob(jobId);
        await loadJobs(); // Refresh list
      } catch (error) {
        alert("خطا در توقف کار: " + String(error));
      }
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (confirm("آیا مطمئن هستید که می‌خواهید این کار را حذف کنید؟ این عمل قابل بازگشت نیست.")) {
      try {
        await deleteTrainingJob(jobId);
        await loadJobs(); // Refresh list
        if (selectedJob?.job_id === jobId) {
          setSelectedJob(null);
        }
      } catch (error) {
        alert("خطا در حذف کار: " + String(error));
      }
    }
  };

  const getStatusColor = (status: TrainingJob["status"]) => {
    switch (status) {
      case "running": return "bg-green-100 text-green-800";
      case "pending": return "bg-yellow-100 text-yellow-800";
      case "completed": return "bg-blue-100 text-blue-800";
      case "failed": return "bg-red-100 text-red-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusIcon = (status: TrainingJob["status"]) => {
    switch (status) {
      case "running": return <PlayIcon className="h-4 w-4" />;
      case "pending": return <ClockIcon className="h-4 w-4" />;
      case "completed": return <EyeIcon className="h-4 w-4" />;
      case "failed": return <ExclamationTriangleIcon className="h-4 w-4" />;
      default: return <ClockIcon className="h-4 w-4" />;
    }
  };

  const formatDuration = (startTime: string) => {
    const start = new Date(startTime);
    const now = new Date();
    const diff = Math.floor((now.getTime() - start.getTime()) / 1000);
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${mins}m`;
  };

  return (
    <div className={`max-w-7xl mx-auto p-6 ${className}`}>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">مانیتورینگ سیستم</h1>
        <p className="text-gray-600">
          نظارت بر فرآیندهای آموزش و عملکرد سیستم
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        {/* System Metrics Cards */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <CpuChipIcon className="h-6 w-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">CPU</h3>
          </div>
          <div className="text-3xl font-bold text-blue-600 mb-2">{metrics.cpu_usage}%</div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${metrics.cpu_usage}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <ChartBarIcon className="h-6 w-6 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-900">حافظه</h3>
          </div>
          <div className="text-3xl font-bold text-green-600 mb-2">{metrics.memory_usage}%</div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${metrics.memory_usage}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <PlayIcon className="h-6 w-6 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">کارهای فعال</h3>
          </div>
          <div className="text-3xl font-bold text-purple-600 mb-2">{metrics.active_jobs}</div>
          <p className="text-sm text-gray-600">از {metrics.total_jobs} کار کل</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <ClockIcon className="h-6 w-6 text-orange-600" />
            <h3 className="text-lg font-semibold text-gray-900">Uptime</h3>
          </div>
          <div className="text-2xl font-bold text-orange-600 mb-2">
            {formatUptime(metrics.uptime)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Training Jobs List */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">کارهای آموزش</h2>
            </div>

            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {loading ? (
                <div className="p-6 text-center text-gray-500">
                  در حال بارگذاری...
                </div>
              ) : jobs.length === 0 ? (
                <div className="p-6 text-center text-gray-500">
                  هیچ کاری یافت نشد
                </div>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.job_id}
                    className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                      selectedJob?.job_id === job.job_id ? "bg-blue-50 border-r-4 border-blue-600" : ""
                    }`}
                    onClick={() => setSelectedJob(job)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                          {getStatusIcon(job.status)}
                          {job.status === "running" ? "در حال اجرا" :
                           job.status === "pending" ? "در انتظار" :
                           job.status === "completed" ? "تکمیل شده" :
                           job.status === "failed" ? "ناموفق" : job.status}
                        </span>
                        <span className="text-sm text-gray-500">
                          {job.config.model_name.split('/').pop()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {job.status === "running" && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStopJob(job.job_id);
                            }}
                            className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                            title="توقف کار"
                          >
                            <StopIcon className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteJob(job.job_id);
                          }}
                          className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                          title="حذف کار"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-sm text-gray-600">
                      <span>{job.config.training_mode.toUpperCase()}</span>
                      <span>شروع: {new Date(job.created_at).toLocaleString('fa-IR')}</span>
                    </div>

                    {job.status === "running" && job.progress && (
                      <div className="mt-2">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>پیشرفت: {job.progress.step}/{job.progress.total_steps}</span>
                          <span>Epoch {job.progress.epoch}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${(job.progress.step / job.progress.total_steps) * 100}%` }}
                          ></div>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Loss: {job.progress.loss.toFixed(4)}</span>
                          <span>LR: {job.progress.learning_rate.toExponential(2)}</span>
                        </div>
                      </div>
                    )}

                    {job.status === "running" && job.started_at && (
                      <div className="text-xs text-gray-500 mt-1">
                        مدت زمان: {formatDuration(job.started_at)}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Job Details Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 sticky top-6">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">جزئیات کار</h2>
            </div>

            {selectedJob ? (
              <div className="p-6 space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">مدل</h3>
                  <p className="text-sm text-gray-600">{selectedJob.config.model_name}</p>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">پارامترها</h3>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div>حالت: {selectedJob.config.training_mode}</div>
                    <div>Epochs: {selectedJob.config.num_train_epochs}</div>
                    <div>Batch Size: {selectedJob.config.per_device_train_batch_size}</div>
                    <div>Learning Rate: {selectedJob.config.learning_rate}</div>
                  </div>
                </div>

                {selectedJob.progress && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">پیشرفت</h3>
                    <div className="space-y-1 text-sm text-gray-600">
                      <div>Epoch: {selectedJob.progress.epoch}</div>
                      <div>Step: {selectedJob.progress.step}/{selectedJob.progress.total_steps}</div>
                      <div>Loss: {selectedJob.progress.loss.toFixed(4)}</div>
                      <div>Learning Rate: {selectedJob.progress.learning_rate.toExponential(2)}</div>
                    </div>
                  </div>
                )}

                {selectedJob.metrics && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">متریک‌ها</h3>
                    <div className="space-y-1 text-sm text-gray-600">
                      {selectedJob.metrics.train_loss && (
                        <div>Train Loss: {selectedJob.metrics.train_loss.toFixed(4)}</div>
                      )}
                      {selectedJob.metrics.eval_loss && (
                        <div>Eval Loss: {selectedJob.metrics.eval_loss.toFixed(4)}</div>
                      )}
                      {selectedJob.metrics.accuracy && (
                        <div>Accuracy: {(selectedJob.metrics.accuracy * 100).toFixed(2)}%</div>
                      )}
                      {selectedJob.metrics.perplexity && (
                        <div>Perplexity: {selectedJob.metrics.perplexity.toFixed(2)}</div>
                      )}
                    </div>
                  </div>
                )}

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">زمان‌بندی</h3>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div>ایجاد: {new Date(selectedJob.created_at).toLocaleString('fa-IR')}</div>
                    {selectedJob.started_at && (
                      <div>شروع: {new Date(selectedJob.started_at).toLocaleString('fa-IR')}</div>
                    )}
                    {selectedJob.completed_at && (
                      <div>اتمام: {new Date(selectedJob.completed_at).toLocaleString('fa-IR')}</div>
                    )}
                  </div>
                </div>

                {selectedJob.error_message && (
                  <div>
                    <h3 className="font-medium text-red-900 mb-2">خطا</h3>
                    <p className="text-sm text-red-600 bg-red-50 p-2 rounded">
                      {selectedJob.error_message}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">
                یک کار را انتخاب کنید تا جزئیات آن نمایش داده شود
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
