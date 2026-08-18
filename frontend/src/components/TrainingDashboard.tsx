/**
 * Training Dashboard Component
 *
 * A form to configure and start a training job.
 * Receives an onStartTraining callback to handle the actual API call.
 * Accepts an isTraining prop to show loading state.
 */

import { useState, useEffect } from 'react';
import { listAvailableModels } from '../api/trainingClient';

interface ModelOption {
  id: string;
  name: string;
  provider: string;
  version: string;
}

interface TrainingConfig {
  model_name: string;
  training_mode: string; // 'lora' | 'qlora' | 'full'
  num_train_epochs: number;
  batch_size: number;
  learning_rate: number;
  dataset_name: string;
  run_name: string;
  quantization?: 'INT8' | 'INT4' | null;
}

export interface TrainingDashboardProps {
  onStartTraining: (config: TrainingConfig) => void;
  isTraining?: boolean;
}

export default function TrainingDashboard({ onStartTraining, isTraining = false }: TrainingDashboardProps) {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    model_id: '',
    training_mode: 'lora' as 'lora' | 'qlora' | 'full',
    epochs: 3,
    batch_size: 4,
    learning_rate: 2e-5,
    dataset_name: '',
    run_name: '',
    quantization: null as 'INT8' | 'INT4' | null,
  });

  // Fetch available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoadingModels(true);
        setError(null);
        const modelList = await listAvailableModels();
        setModels(
          (modelList.models ?? []).map((model) => ({
            id: model.id,
            name: model.name,
            provider: model.provider,
            version: model.size || '',
          }))
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : 'بارگذاری مدل‌ها ناموفق بود');
      } finally {
        setIsLoadingModels(false);
      }
    };

    void fetchModels();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => {
      if (type === 'checkbox') {
        return { ...prev, [name]: checked };
      }
      if (name === 'epochs' || name === 'batch_size') {
        return { ...prev, [name]: parseInt(value, 10) };
      }
      if (name === 'learning_rate') {
        return { ...prev, [name]: parseFloat(value) };
      }
      return { ...prev, [name]: value };
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.model_id) {
      setError('لطفاً یک مدل را انتخاب کنید');
      return;
    }
    if (!form.dataset_name) {
      setError('لطفاً نام dataset را وارد کنید');
      return;
    }
    if (!form.run_name) {
      setError('لطفاً نام اجرا را وارد کنید');
      return;
    }

    const selectedModel = models.find(m => m.id === form.model_id);
    if (!selectedModel) {
      setError('مدل انتخاب شده نامعتبر است');
      return;
    }

    const config: TrainingConfig = {
      model_name: selectedModel.id,
      training_mode: form.training_mode,
      num_train_epochs: form.epochs,
      batch_size: form.batch_size,
      learning_rate: form.learning_rate,
      dataset_name: form.dataset_name,
      run_name: form.run_name,
      quantization: form.quantization,
    };

    onStartTraining(config);
  };

  if (isLoadingModels && models.length === 0) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">آموزش مدل</h1>
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">آموزش مدل</h1>
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">خطا</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
        <button
          type="button"
          onClick={async () => {
            setError(null);
            setIsLoadingModels(true);
            try {
              const modelList = await listAvailableModels();
              setModels(modelList.jobs ?? []);
            } catch (e) {
              setError(e instanceof Error ? e.message : 'خطا در بارگذاری');
            } finally {
              setIsLoadingModels(false);
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
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white">آموزش مدل</h1>
          <p className="mt-2 text-slate-400">پیکربندی و شروع یک کار‌آموزش جدید</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-800 rounded-xl shadow-xl border border-slate-700 p-6">
          <div className="space-y-5">
            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-300">
                انتخاب مدل
              </label>
              <select
                value={form.model_id}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">یک مدل را انتخاب کنید</option>
                {models.map(model => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.provider} {model.version})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-300">
                حالت آموزش
              </label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="training_mode"
                    value="lora"
                    checked={form.training_mode === 'lora'}
                    onChange={e => setForm(prev => ({ ...prev, training_mode: e.target.value as 'lora' | 'qlora' | 'full' }))}
                    className="h-4 w-4 text-primary-600"
                  />
                  LoRA
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="training_mode"
                    value="qlora"
                    checked={form.training_mode === 'qlora'}
                    onChange={e => setForm(prev => ({ ...prev, training_mode: e.target.value as 'lora' | 'qlora' | 'full' }))}
                    className="h-4 w-4 text-primary-600"
                  />
                  QLoRA
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="training_mode"
                    value="full"
                    checked={form.training_mode === 'full'}
                    onChange={e => setForm(prev => ({ ...prev, training_mode: e.target.value as 'lora' | 'qlora' | 'full' }))}
                    className="h-4 w-4 text-primary-600"
                  />
                  Full Fine-tune
                </label>
              </div>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-300">
                پارامترهای آموزش
              </label>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-slate-400">تعداد epochs</label>
                  <input
                    name="epochs"
                    type="number"
                    min={1}
                    max={100}
                    value={form.epochs}
                    onChange={handleChange}
                    className="w-full px-2 py-1 bg-slate-900 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-slate-400">Batch size (train)</label>
                  <input
                    name="batch_size"
                    type="number"
                    min={1}
                    max={128}
                    value={form.batch_size}
                    onChange={handleChange}
                    className="w-full px-2 py-1 bg-slate-900 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-slate-400">Learning rate</label>
                  <input
                    name="learning_rate"
                    type="number"
                    min={0}
                    max={1}
                    step={0.00001}
                    value={form.learning_rate}
                    onChange={handleChange}
                    className="w-full px-2 py-1 bg-slate-900 border border-slate-600 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>

            {/* Quantization options - only show when QLoRA is selected */}
            {form.training_mode === 'qlora' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-300">
                    کمیتیزاسیون
                  </label>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="quantization"
                        value="INT8"
                        checked={form.quantization === 'INT8'}
                        onChange={e => setForm(prev => ({ ...prev, quantization: e.target.value as 'INT8' | 'INT4' | null }))}
                        className="h-4 w-4 text-primary-600"
                      />
                      INT8
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="quantization"
                        value="INT4"
                        checked={form.quantization === 'INT4'}
                        onChange={e => setForm(prev => ({ ...prev, quantization: e.target.value as 'INT8' | 'INT4' | null }))}
                        className="h-4 w-4 text-primary-600"
                      />
                      INT4
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="quantization"
                        value=""
                        checked={form.quantization === null}
                        onChange={e => setForm(prev => ({ ...prev, quantization: null as 'INT8' | 'INT4' | null }))}
                        className="h-4 w-4 text-primary-600"
                      />
                      なし
                    </label>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-300">
                نام dataset
              </label>
              <input
                name="dataset_name"
                value={form.dataset_name}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="نام dataset را وارد کنید..."
                required
              />
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-300">
                نام اجرا
              </label>
              <input
                name="run_name"
                value={form.run_name}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="نام اجرا را وارد کنید..."
                required
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isTraining}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors"
              >
                {isTraining ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full" />
                    در حال آموزش...
                  </>
                ) : (
                  'شروع آموزش'
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
