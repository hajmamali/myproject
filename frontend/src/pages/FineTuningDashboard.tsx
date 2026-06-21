/**
 * Fine-Tuning Dashboard
 * =====================
 * Complete UI for managing model fine-tuning jobs
 * 
 * Features:
 * - Create new fine-tuning jobs
 * - Monitor training progress
 * - View metrics and logs
 * - Deploy models
 */

import React, { useState, useEffect } from 'react';
import {
  PlayIcon,
  ArrowPathIcon,
  CloudArrowUpIcon,
  ChartBarIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  listFineTuningJobs,
  getFineTuningJob,
  createFineTuningJob,
  cancelFineTuningJob,
  getTrainingMetrics,
  getTrainingLogs,
  deployFineTunedModel,
  type FineTuningJob,
  type TrainingMetrics,
  type FineTuningRequest,
} from '../api/finetuningClient';

// =============================================================================
// Main Component
// =============================================================================

export const FineTuningDashboard: React.FC = () => {
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<FineTuningJob | null>(null);
  const [metrics, setMetrics] = useState<TrainingMetrics[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Fetch jobs
  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  // Fetch metrics when job selected
  useEffect(() => {
    if (selectedJob) {
      fetchMetrics(selectedJob.job_id);
      fetchLogs(selectedJob.job_id);
    }
  }, [selectedJob]);

  const fetchJobs = async () => {
    try {
      const data = await listFineTuningJobs();
      setJobs(data);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    }
  };

  const fetchMetrics = async (jobId: string) => {
    try {
      const data = await getTrainingMetrics(jobId);
      setMetrics(data);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  const fetchLogs = async (jobId: string) => {
    try {
      const data = await getTrainingLogs(jobId);
      setLogs(data.lines || []);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'training':
      case 'preparing':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-4 w-4" />;
      case 'failed':
        return <XCircleIcon className="h-4 w-4" />;
      case 'training':
        return <ChartBarIcon className="h-4 w-4" />;
      default:
        return <ExclamationTriangleIcon className="h-4 w-4" />;
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Fine-Tuning Dashboard</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setCreateDialogOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <PlayIcon className="h-5 w-5" />
            New Fine-Tuning Job
          </button>
          <button
            onClick={fetchJobs}
            className="p-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <ArrowPathIcon className="h-5 w-5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600 mb-1">Total Jobs</p>
          <p className="text-3xl font-bold text-gray-900">{jobs.length}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600 mb-1">Running</p>
          <p className="text-3xl font-bold text-blue-600">
            {jobs.filter(j => j.status === 'training').length}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600 mb-1">Completed</p>
          <p className="text-3xl font-bold text-green-600">
            {jobs.filter(j => j.status === 'completed').length}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <p className="text-sm text-gray-600 mb-1">Failed</p>
          <p className="text-3xl font-bold text-red-600">
            {jobs.filter(j => j.status === 'failed').length}
          </p>
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Fine-Tuning Jobs</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Job Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Model
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Progress
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Loss
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {jobs.map((job) => (
                  <tr
                    key={job.job_id}
                    onClick={() => setSelectedJob(job)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{job.job_name}</div>
                      {job.description && (
                        <div className="text-sm text-gray-500">{job.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {job.config.model_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                        {getStatusIcon(job.status)}
                        {job.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-full bg-gray-200 rounded-full h-2 mr-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${job.progress_percentage}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600 min-w-[3rem]">
                          {Math.round(job.progress_percentage)}%
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Epoch {job.current_epoch}/{job.total_epochs}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {job.train_loss ? job.train_loss.toFixed(4) : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Selected Job Details */}
      {selectedJob && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Metrics Chart */}
          <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Training Metrics - {selectedJob.job_name}
            </h2>
            <div className="h-64 flex items-center justify-center text-gray-500">
              {metrics.length > 0 ? (
                <div className="w-full">
                  <p className="text-sm mb-2">Latest metrics:</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-600">Train Loss</p>
                      <p className="text-2xl font-bold">{metrics[metrics.length - 1].train_loss.toFixed(4)}</p>
                    </div>
                    {metrics[metrics.length - 1].eval_loss !== undefined && (
                      <div>
                        <p className="text-xs text-gray-600">Eval Loss</p>
                        <p className="text-2xl font-bold">{metrics[metrics.length - 1].eval_loss!.toFixed(4)}</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                'No metrics available yet'
              )}
            </div>
          </div>

          {/* Job Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Job Information</h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600">Job ID</p>
                <p className="text-sm font-mono text-gray-900">{selectedJob.job_id.substring(0, 8)}...</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Training Mode</p>
                <p className="text-sm text-gray-900">{selectedJob.config.training_mode}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Learning Rate</p>
                <p className="text-sm text-gray-900">{selectedJob.config.learning_rate}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Batch Size</p>
                <p className="text-sm text-gray-900">{selectedJob.config.batch_size}</p>
              </div>
              {selectedJob.eval_accuracy && (
                <div>
                  <p className="text-sm text-gray-600">Eval Accuracy</p>
                  <p className="text-sm text-gray-900">{(selectedJob.eval_accuracy * 100).toFixed(2)}%</p>
                </div>
              )}
              {selectedJob.status === 'completed' && (
                <button 
                  onClick={async () => {
                    try {
                      await deployFineTunedModel({
                        job_id: selectedJob.job_id,
                        strategy: 'shadow',
                        traffic_percentage: 0,
                      });
                      alert('مدل با موفقیت deploy شد');
                    } catch (error) {
                      alert('خطا در deploy مدل: ' + String(error));
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors mt-4"
                >
                  <CloudArrowUpIcon className="h-5 w-5" />
                  Deploy Model
                </button>
              )}
            </div>
          </div>

          {/* Logs */}
          <div className="lg:col-span-3 bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Training Logs</h2>
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm max-h-64 overflow-y-auto">
              {logs.map((log, index) => (
                <div key={index} className="mb-1">{log}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Create Job Dialog */}
      {createDialogOpen && (
        <CreateJobDialog
          onClose={() => setCreateDialogOpen(false)}
          onSuccess={() => {
            setCreateDialogOpen(false);
            fetchJobs();
          }}
        />
      )}
    </div>
  );
};

// =============================================================================
// Create Job Dialog
// =============================================================================

interface CreateJobDialogProps {
  onClose: () => void;
  onSuccess: () => void;
}

const CreateJobDialog: React.FC<CreateJobDialogProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    job_name: '',
    description: '',
    model_name: 'gpt2',
    training_mode: 'lora',
    learning_rate: 0.00002,
    num_epochs: 3,
    batch_size: 4,
    dataset_source: 'feedback',
  });

  const handleSubmit = async () => {
    try {
      const request: FineTuningRequest = {
        job_name: formData.job_name,
        description: formData.description,
        config: {
          model_name: formData.model_name,
          training_mode: formData.training_mode as any,
          learning_rate: formData.learning_rate,
          num_epochs: formData.num_epochs,
          batch_size: formData.batch_size,
        },
        dataset: {
          source: formData.dataset_source as any,
        },
      };

      await createFineTuningJob(request);
      onSuccess();
    } catch (error) {
      console.error('Failed to create job:', error);
      alert('خطا در ایجاد job: ' + String(error));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Create Fine-Tuning Job</h2>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Job Name</label>
            <input
              type="text"
              value={formData.job_name}
              onChange={(e) => setFormData({ ...formData, job_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter job name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base Model</label>
            <select
              value={formData.model_name}
              onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="gpt2">GPT-2</option>
              <option value="gpt2-medium">GPT-2 Medium</option>
              <option value="llama-2-7b">Llama 2 7B</option>
              <option value="mistral-7b">Mistral 7B</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Training Mode</label>
            <select
              value={formData.training_mode}
              onChange={(e) => setFormData({ ...formData, training_mode: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="lora">LoRA</option>
              <option value="qlora">QLoRA</option>
              <option value="full_finetune">Full Fine-tune</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Learning Rate</label>
              <input
                type="number"
                step="0.00001"
                value={formData.learning_rate}
                onChange={(e) => setFormData({ ...formData, learning_rate: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Epochs</label>
              <input
                type="number"
                value={formData.num_epochs}
                onChange={(e) => setFormData({ ...formData, num_epochs: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Start Training
          </button>
        </div>
      </div>
    </div>
  );
};

export default FineTuningDashboard;
