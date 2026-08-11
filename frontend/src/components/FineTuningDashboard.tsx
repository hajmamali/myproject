/**
 * Fine-Tuning Dashboard Component
 *
 * Lists fine-tuning jobs and allows creating new ones.
 * Uses the /api/v1/finetuning/jobs endpoint for listing and creation.
 * Fetches available models from /api/v1/training/models.
 */

import { useState, useEffect, useCallback } from 'react';
import { listTrainingJobs, listAvailableModels } from '../api/trainingClient';
import { apiClient } from '../api/client';

interface FineTuningJob {
  job_id: string;
  job_name: string;
  description?: string;
  status: string;
  config: {
    model_name: string;
    training_mode: string;
    learning_rate: number;
    num_epochs: number;
    batch_size: number;
    // ... other fields
  };
  dataset: {
    source: string;
    dataset_id?: string;
  };
  created_at: string;
  completed_at?: string;
}

interface ModelOption {
  id: string;
  name: string;
  provider: string;
  version: string;
}

function parseJSON<T>(str: string, fallback: T): T {
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
}

export default function FineTuningDashboard() {
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    job_name: '',
    description: '',
    model_id: '',
    epochs: 3,
    batch_size: 4,
    learning_rate: 2e-5,
    // We'll hardcode other config for simplicity
  });

  // Fetch available models and initial job list
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch models
        const modelList = await listAvailableModels();
        setModels(modelList.jobs ?? []); // Note: listAvailableModels returns { jobs: ModelOption[], total: number }

        // Fetch fine-tuning jobs
        const jobList = await apiClient.get('/api/v1/finetuning/jobs');
        setJobs(jobList.jobs ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'خطا در بارگذاری');
      } finally {
        setIsLoading(false);
      }
    };

    void fetchData();
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setForm(prev => {
      if (type === 'checkbox') {
        return { ...prev, [name]: e.target.checked };
      }
      if (name === 'epochs' || name === 'batch_size') {
        return { ...prev, [name]: parseInt(value, 10) };
      }
      if (name === 'learning_rate') {
        return { ...prev, [name]: parseFloat(value) };
      }
      return { ...prev, [name]: value };
    });
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      // Build the config with hardcoded defaults for simplicity
      const config = {
        model_name: form.model_id,
        training_mode: 'lora', // hardcode
        learning_rate: form.learning_rate,
        num_epochs: form.epochs,
        batch_size: form.batch_size,
        gradient_accumulation_steps: 4,
        warmup_ratio: 0.1,
        lora_r: 8,
        lora_alpha: 16,
        lora_dropout: 0.05,
        use_gradient_checkpointing: true,
        use_mixed_precision: true,
        max_grad_norm: 1.0,
        load_in_4bit: false,
        load_in_8bit: false,
      };

      const dataset = {
        source: 'existing',
        dataset_id: 'default', // In a real app, you'd have a dataset selector
      };

      const response = await apiClient.post(`/api/v1/finetuning/jobs`, {
        job_name: form.job_name,
        description: form.description,
        config,
        dataset,
        auto_deploy: false,
        deployment_strategy: 'shadow',
      });

      // Refetch jobs to include the new one
      const jobList = await apiClient.get('/api/v1/finetuning/jobs');
      setJobs(jobList.jobs ?? []);

      // Reset form
      setForm(prev => ({ ...prev, job_name: '', description: '' }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ایجاد پروژه فاین‌تیونینگ ناموفق بود');
    } finally {
      setIsLoading(false);
    }
  }, [form]);

  if (isLoading && jobs.length === 0 && models.length === 0) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">فاین‌تیونینگ</h1>
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">فاین‌تیونینگ</h1>
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">خطا در بارگذاری داده‌ها</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
        <button
          type="button"
          onClick={async () => {
            setIsLoading(true);
            setError(null);
            try {
              const modelList = await listAvailableModels();
              setModels(modelList.jobs ?? []);
              const jobList = await apiClient.get('/api/v1/finetuning/jobs');
              setJobs(jobList.jobs ?? []);
            } catch (e) {
              setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
            } finally {
              setIsLoading(false);
            }
          }}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
        >
          تلاش مجدد
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white">فاین‌تیونینگ</h1>
          <p className="mt-2 text-slate-400">ایجاد و مدیریت پروژه‌های فاین‌تیونینگ مدل</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Job List */}
          <div className="bg-slate-800 rounded-xl shadow-xl border border-slate-700">
            <div className="p-6">
              <h2 className="mb-4 text-xl font-bold text-white">프로젝트 목록</h2>
              {jobs.length ? (
                <ul className="divide-y divide-slate-700">
                  {jobs.map(job => (
                    <li key={job.job_id} className="py-4 flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-medium text-slate-100">{job.job_name}</h3>
                        <p className="text-sm text-slate-400 truncate">{job.description || 'بدون توضیح'}</p>
                        <div className="mt-2 flex items-center gap-3 text-xs">
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium {
                            job.status === 'completed' ? 'bg-green-100 text-green-800' :
                            job.status === 'failed' ? 'bg-red-100 text-red-800' :
                            job.status === 'running' ? 'bg-blue-100 text-blue-800' :
                            'bg-slate-100 text-slate-700'
                          }">
                            {job.status}
                          </span>
                          <span className="text-slate-500">· {new Date(job.created_at).toLocaleString('fa-IR')}</span>
                        </div>
                      </div>
                      <div className="text-right text-slate-400">
                        <button
                          onClick={() => {
                            // In a real app, you'd navigate to a job detail page
                            alert('Job detail not implemented yet');
                          }}
                          className="underline hover:text-white"
                        >
                          مشاهده
                        </button>
                      </div>
                    >
                  ))}
                </ul>
              ) : (
                <p className="text-slate-400 text-center py-8">هیچ پروژه‌ای یافت نشد.</p>
              )}
            </div>
          </div>

          {/* Create Job Form */}
          <div className="bg-slate-800 rounded-xl shadow-xl border border-slate-700">
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <h2 className="mb-4 text-xl font-bold text-white">ایجاد پروژه جدید</h2>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">
                  نام پروژه
                </label>
                <input
                  name="job_name"
                  value={form.job_name}
                  onChange={handleChange}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">
                  توضیح (اختیاری)
                </label>
                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
                />
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">
                  مدل
                </label>
                <select
                  name="model_id"
                  value={form.model_id}
                  onChange={handleChange}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Select a model</option>
                  {models.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider} {model.version})
                    >
                  ))}
                </select>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-slate-300">
                    Epochs
                  </label>
                  <input
                    name="epochs"
                    type="number"
                    min={1}
                    max={100}
                    value={form.epochs}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div className="space-y-3">
                  <label className="block text-sm font-medium text-slate-300">
                    Batch Size
                  </label>
                  <input
                    name="batch_size"
                    type="number"
                    min={1}
                    max={128}
                    value={form.batch_size}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div className="space-y-3">
                  <label className="block text-sm font-medium text-slate-300">
                    Learning Rate
                  </label>
                  <input
                    name="learning_rate"
                    type="number"
                    min={0}
                    max={1}
                    step={0.00001}
                    value={form.learning_rate}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isLoading || !form.job_name || !form.model_id}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors"
                >
                  {isLoading ? (
                    <>
                      <div className="animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full" />
                      در حال ایجاد...
                    </>
                  ) : (
                    'ایجاد پروژه'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
