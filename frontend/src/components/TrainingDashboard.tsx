/**
 * Training Dashboard Component
 *
 * Advanced interface for configuring and starting model fine-tuning jobs
 */

import { useState } from "react";
import {
  PlayIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  CpuChipIcon,
  ClockIcon,
  ChartBarIcon,
} from "@heroicons/react/24/outline";
import ModelSelector, { ModelOption } from "./ModelSelector";

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

interface TrainingDashboardProps {
  onStartTraining: (config: TrainingConfig) => Promise<void>;
  isTraining?: boolean;
  className?: string;
}

const TRAINING_MODES = [
  {
    id: "lora" as const,
    name: "LoRA",
    description: "Low-Rank Adaptation - سریع و کارآمد",
    recommended: true,
  },
  {
    id: "qlora" as const,
    name: "QLoRA",
    description: "Quantized LoRA - برای مدل‌های بزرگ",
  },
  {
    id: "full_finetune" as const,
    name: "Full Fine-tune",
    description: "فاین‌تیون کامل - کند اما دقیق",
  },
  {
    id: "dora" as const,
    name: "DoRA",
    description: "Weight-Decomposed LoRA",
  },
  {
    id: "adalora" as const,
    name: "AdaLoRA",
    description: "Adaptive LoRA",
  },
];

const QUANTIZATION_MODES = [
  { id: "none" as const, name: "بدون quantization" },
  { id: "int8" as const, name: "INT8" },
  { id: "int4" as const, name: "INT4" },
  { id: "fp8" as const, name: "FP8" },
];

export default function TrainingDashboard({
  onStartTraining,
  isTraining = false,
  className = "",
}: TrainingDashboardProps) {
  const [selectedModel, setSelectedModel] = useState<ModelOption | null>(null);
  const [config, setConfig] = useState<Partial<TrainingConfig>>({
    training_mode: "lora",
    quantization_mode: "none",
    num_train_epochs: 3,
    per_device_train_batch_size: 4,
    per_device_eval_batch_size: 8,
    gradient_accumulation_steps: 4,
    learning_rate: 0.0002,
    weight_decay: 0.01,
    warmup_ratio: 0.03,
    max_grad_norm: 1.0,
    seed: 42,
  });

  const handleStartTraining = async () => {
    if (!selectedModel) {
      alert("لطفاً ابتدا یک مدل انتخاب کنید");
      return;
    }

    const fullConfig: TrainingConfig = {
      model_name: selectedModel.id,
      training_mode: config.training_mode || "lora",
      quantization_mode: config.quantization_mode,
      num_train_epochs: config.num_train_epochs || 3,
      per_device_train_batch_size: config.per_device_train_batch_size || 4,
      per_device_eval_batch_size: config.per_device_eval_batch_size || 8,
      gradient_accumulation_steps: config.gradient_accumulation_steps || 4,
      learning_rate: config.learning_rate || 0.0002,
      weight_decay: config.weight_decay || 0.01,
      warmup_ratio: config.warmup_ratio || 0.03,
      max_grad_norm: config.max_grad_norm || 1.0,
      dataset_name: config.dataset_name,
      output_dir: config.output_dir,
      run_name: config.run_name,
      seed: config.seed,
    };

    try {
      await onStartTraining(fullConfig);
    } catch (error) {
      console.error("Training failed:", error);
      alert("خطا در شروع آموزش: " + String(error));
    }
  };

  const updateConfig = (key: keyof TrainingConfig, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className={`max-w-6xl mx-auto p-6 ${className}`}>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">آموزش مدل</h1>
        <p className="text-gray-600">
          تنظیمات پیشرفته برای فاین‌تیون کردن مدل‌های هوش مصنوعی
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Model Selection */}
        <div className="lg:col-span-1">
          <ModelSelector
            selectedModel={selectedModel || undefined}
            onSelect={setSelectedModel}
            className="h-fit"
          />
        </div>

        {/* Training Configuration */}
        <div className="lg:col-span-2 space-y-6">
          {/* Training Mode */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Cog6ToothIcon className="h-6 w-6 text-blue-600" />
              <h2 className="text-lg font-semibold text-gray-900">حالت آموزش</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {TRAINING_MODES.map((mode) => (
                <label
                  key={mode.id}
                  className={`relative flex cursor-pointer rounded-lg border p-4 shadow-sm focus:outline-none ${
                    config.training_mode === mode.id
                      ? "border-blue-600 ring-2 ring-blue-600"
                      : "border-gray-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="training-mode"
                    value={mode.id}
                    checked={config.training_mode === mode.id}
                    onChange={(e) => updateConfig("training_mode", e.target.value)}
                    className="sr-only"
                  />
                  <span className="flex flex-1">
                    <span className="flex flex-col">
                      <span className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">
                          {mode.name}
                        </span>
                        {mode.recommended && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-800">
                            پیشنهادی
                          </span>
                        )}
                      </span>
                      <span className="text-sm text-gray-500 mt-1">
                        {mode.description}
                      </span>
                    </span>
                  </span>
                  <span
                    className={`absolute -inset-px rounded-lg border-2 pointer-events-none ${
                      config.training_mode === mode.id ? "border-blue-600" : "border-transparent"
                    }`}
                    aria-hidden="true"
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Quantization */}
          {(config.training_mode === "qlora" || config.training_mode === "lora") && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <CpuChipIcon className="h-6 w-6 text-purple-600" />
                <h2 className="text-lg font-semibold text-gray-900">Quantization</h2>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {QUANTIZATION_MODES.map((mode) => (
                  <label
                    key={mode.id}
                    className={`relative flex cursor-pointer rounded-lg border p-3 text-center shadow-sm focus:outline-none ${
                      config.quantization_mode === mode.id
                        ? "border-purple-600 ring-2 ring-purple-600"
                        : "border-gray-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="quantization-mode"
                      value={mode.id}
                      checked={config.quantization_mode === mode.id}
                      onChange={(e) => updateConfig("quantization_mode", e.target.value)}
                      className="sr-only"
                    />
                    <span className="text-sm font-medium text-gray-900">{mode.name}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Training Parameters */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <ChartBarIcon className="h-6 w-6 text-green-600" />
              <h2 className="text-lg font-semibold text-gray-900">پارامترهای آموزش</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  تعداد epochs
                </label>
                <input
                  type="number"
                  value={config.num_train_epochs}
                  onChange={(e) => updateConfig("num_train_epochs", parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Batch size (train)
                </label>
                <input
                  type="number"
                  value={config.per_device_train_batch_size}
                  onChange={(e) => updateConfig("per_device_train_batch_size", parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="32"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Learning rate
                </label>
                <input
                  type="number"
                  value={config.learning_rate}
                  onChange={(e) => updateConfig("learning_rate", parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  step="0.000001"
                  min="0.000001"
                  max="0.01"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Gradient accumulation steps
                </label>
                <input
                  type="number"
                  value={config.gradient_accumulation_steps}
                  onChange={(e) => updateConfig("gradient_accumulation_steps", parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="16"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Weight decay
                </label>
                <input
                  type="number"
                  value={config.weight_decay}
                  onChange={(e) => updateConfig("weight_decay", parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  step="0.001"
                  min="0"
                  max="0.1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Seed
                </label>
                <input
                  type="number"
                  value={config.seed}
                  onChange={(e) => updateConfig("seed", parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  min="0"
                  max="999999"
                />
              </div>
            </div>
          </div>

          {/* Dataset & Output */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <DocumentTextIcon className="h-6 w-6 text-orange-600" />
              <h2 className="text-lg font-semibold text-gray-900">داده‌ها و خروجی</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  نام dataset
                </label>
                <input
                  type="text"
                  value={config.dataset_name || ""}
                  onChange={(e) => updateConfig("dataset_name", e.target.value)}
                  placeholder="مثال: legal-contracts-v1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  نام run
                </label>
                <input
                  type="text"
                  value={config.run_name || ""}
                  onChange={(e) => updateConfig("run_name", e.target.value)}
                  placeholder="مثال: legal-finetune-v1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Start Training Button */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium text-gray-900">آماده شروع آموزش</h3>
                <p className="text-sm text-gray-500 mt-1">
                  پس از کلیک روی دکمه شروع، فرآیند آموزش شروع خواهد شد
                </p>
              </div>
              <button
                onClick={handleStartTraining}
                disabled={!selectedModel || isTraining}
                className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                  !selectedModel || isTraining
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500"
                }`}
              >
                {isTraining ? (
                  <>
                    <ClockIcon className="h-5 w-5 animate-spin" />
                    در حال آموزش...
                  </>
                ) : (
                  <>
                    <PlayIcon className="h-5 w-5" />
                    شروع آموزش
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
