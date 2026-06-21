/**
 * A/B Testing Dashboard Component
 *
 * Create and manage A/B experiments between different AI models
 */

import { useState, useEffect } from "react";
import {
  BeakerIcon,
  PlusIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
} from "@heroicons/react/24/outline";
import { ModelOption } from "./ModelSelector";
import {
  listExperiments,
  createExperiment,
  stopExperiment,
  getExperimentResults,
  calculateWinner,
  type Experiment,
  type ExperimentResults,
} from "../api/experimentsClient";

interface ABTestingDashboardProps {
  className?: string;
}

interface ABExperiment {
  id: string;
  name: string;
  description: string;
  status: "draft" | "running" | "completed" | "stopped";
  variants: Array<{
    model: ModelOption;
    traffic_percentage: number;
    metrics: {
      accuracy: number;
      latency: number;
      cost: number;
      sample_size: number;
    };
  }>;
  winner?: string | null;
  confidence_level?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export default function ABTestingDashboard({ className = "" }: ABTestingDashboardProps) {
  const [experiments, setExperiments] = useState<ABExperiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<ABExperiment | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [newExperiment, setNewExperiment] = useState({
    name: "",
    description: "",
    variants: [] as ModelOption[],
  });

  // Load experiments from API
  useEffect(() => {
    loadExperiments();
    const interval = setInterval(loadExperiments, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadExperiments = async () => {
    try {
      const response = await listExperiments();
      // Convert API experiments to ABExperiment format
      const converted: ABExperiment[] = response.experiments.map(exp => ({
        id: exp.experiment_id,
        name: exp.name,
        description: "",
        status: exp.status as any,
        variants: exp.variants.map((variant, idx) => ({
          model: {
            id: variant,
            name: variant,
            provider: "local" as const,
            size: "Unknown",
            capabilities: [],
            description: "",
          },
          traffic_percentage: exp.traffic_split[idx] || 0,
          metrics: {
            accuracy: 0,
            latency: 0,
            cost: 0,
            sample_size: exp.samples || 0,
          },
        })),
        created_at: exp.created_at,
        started_at: exp.started_at,
        completed_at: exp.stopped_at,
      }));
      setExperiments(converted);
    } catch (error) {
      console.error("Failed to load experiments:", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: ABExperiment["status"]) => {
    switch (status) {
      case "running": return "bg-green-100 text-green-800";
      case "completed": return "bg-blue-100 text-blue-800";
      case "stopped": return "bg-red-100 text-red-800";
      case "draft": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusText = (status: ABExperiment["status"]) => {
    switch (status) {
      case "running": return "در حال اجرا";
      case "completed": return "تکمیل شده";
      case "stopped": return "متوقف شده";
      case "draft": return "پیش‌نویس";
      default: return status;
    }
  };

  const calculateWinner = (variants: ABExperiment["variants"]) => {
    if (variants.length === 0) return null;

    // Simple winner calculation based on accuracy
    const winner = variants.reduce((best, current) =>
      current.metrics.accuracy > best.metrics.accuracy ? current : best
    );

    return winner.model.id;
  };

  const handleCreateExperiment = async () => {
    if (!newExperiment.name.trim() || newExperiment.variants.length < 2) {
      alert("لطفاً نام آزمایش و حداقل دو مدل را انتخاب کنید");
      return;
    }

    try {
      await createExperiment({
        name: newExperiment.name,
        variants: newExperiment.variants.map(v => v.id),
        traffic_split: newExperiment.variants.map(() => Math.floor(100 / newExperiment.variants.length)),
        metrics: ["accuracy", "latency"],
        metadata: { description: newExperiment.description },
      });

      await loadExperiments();
      setNewExperiment({ name: "", description: "", variants: [] });
      setShowCreateForm(false);
    } catch (error) {
      alert("خطا در ایجاد آزمایش: " + String(error));
    }
  };

  const handleStartExperiment = async (experimentId: string) => {
    // API doesn't have start endpoint, experiments start automatically
    alert("آزمایش به صورت خودکار شروع می‌شود");
  };

  const handleStopExperiment = async (experimentId: string) => {
    try {
      await stopExperiment(experimentId);
      await loadExperiments();
    } catch (error) {
      alert("خطا در توقف آزمایش: " + String(error));
    }
  };

  const handleCompleteExperiment = async (experimentId: string) => {
    try {
      const results = await getExperimentResults(experimentId);
      const winner = calculateWinner(results);
      
      setExperiments(experiments.map(exp => {
        if (exp.id === experimentId) {
          return {
            ...exp,
            status: "completed" as const,
            winner,
            completed_at: new Date().toISOString(),
          };
        }
        return exp;
      }));
    } catch (error) {
      alert("خطا در تکمیل آزمایش: " + String(error));
    }
  };

  return (
    <div className={`max-w-7xl mx-auto p-6 ${className}`}>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">آزمایش‌های A/B</h1>
        <p className="text-gray-600">
          مقایسه عملکرد مدل‌های مختلف هوش مصنوعی
        </p>
      </div>

      {/* Create Experiment Button */}
      <div className="mb-6">
        <button
          onClick={() => setShowCreateForm(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          ایجاد آزمایش جدید
        </button>
      </div>

      {/* Create Experiment Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">ایجاد آزمایش جدید</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                نام آزمایش
              </label>
              <input
                type="text"
                value={newExperiment.name}
                onChange={(e) => setNewExperiment(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="مثال: مقایسه DialoGPT vs GPT-3.5"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                توضیحات
              </label>
              <textarea
                value={newExperiment.description}
                onChange={(e) => setNewExperiment(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={3}
                placeholder="توضیحات آزمایش..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                مدل‌ها (حداقل دو مدل انتخاب کنید)
              </label>
              <div className="text-sm text-gray-500 mb-3">
                مدل‌های انتخاب شده: {newExperiment.variants.length}
              </div>
              {/* TODO: Add model selector component */}
              <div className="text-sm text-gray-600">
                در نسخه بعدی، کامپوننت انتخاب مدل اضافه خواهد شد
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCreateExperiment}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                ایجاد آزمایش
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 transition-colors"
              >
                انصراف
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Experiments List */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            {experiments.map((experiment) => (
              <div
                key={experiment.id}
                className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 cursor-pointer transition-colors ${
                  selectedExperiment?.id === experiment.id ? "border-blue-500 bg-blue-50" : "hover:bg-gray-50"
                }`}
                onClick={() => setSelectedExperiment(experiment)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                      {experiment.name}
                    </h3>
                    <p className="text-gray-600 text-sm mb-3">
                      {experiment.description}
                    </p>

                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(experiment.status)}`}>
                        <BeakerIcon className="h-3 w-3" />
                        {getStatusText(experiment.status)}
                      </span>

                      <span>
                        {experiment.variants.length} مدل
                      </span>

                      {experiment.winner && (
                        <span className="text-green-600 font-medium">
                          برنده: {experiment.variants.find(v => v.model.id === experiment.winner)?.model.name}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    {experiment.status === "draft" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartExperiment(experiment.id);
                        }}
                        className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors"
                      >
                        شروع
                      </button>
                    )}

                    {experiment.status === "running" && (
                      <>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCompleteExperiment(experiment.id);
                          }}
                          className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors"
                        >
                          تکمیل
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStopExperiment(experiment.id);
                          }}
                          className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
                        >
                          توقف
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Variants Preview */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {experiment.variants.map((variant, _index) => (
                    <div key={variant.model.id} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900">
                          {variant.model.name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {variant.traffic_percentage}%
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div>Accuracy: {(variant.metrics.accuracy * 100).toFixed(1)}%</div>
                        <div>Latency: {variant.metrics.latency}ms</div>
                        <div>Cost: ${variant.metrics.cost.toFixed(4)}</div>
                        <div>Samples: {variant.metrics.sample_size}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {experiment.confidence_level && (
                  <div className="mt-3 text-sm text-gray-600">
                    Confidence Level: {(experiment.confidence_level * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Experiment Details Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 sticky top-6">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">جزئیات آزمایش</h2>
            </div>

            {selectedExperiment ? (
              <div className="p-6 space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">نام آزمایش</h3>
                  <p className="text-sm text-gray-600">{selectedExperiment.name}</p>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">توضیحات</h3>
                  <p className="text-sm text-gray-600">{selectedExperiment.description}</p>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">وضعیت</h3>
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedExperiment.status)}`}>
                    <BeakerIcon className="h-3 w-3" />
                    {getStatusText(selectedExperiment.status)}
                  </span>
                </div>

                {selectedExperiment.winner && (
                  <div>
                    <h3 className="font-medium text-green-900 mb-2">برنده آزمایش</h3>
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <p className="text-sm text-green-800 font-medium">
                        {selectedExperiment.variants.find(v => v.model.id === selectedExperiment.winner)?.model.name}
                      </p>
                      <p className="text-xs text-green-600 mt-1">
                        بر اساس معیار accuracy
                      </p>
                    </div>
                  </div>
                )}

                {/* Statistical Comparison */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">مقایسه آماری</h3>
                  <div className="space-y-3">
                    {selectedExperiment.variants.map((variant, _index) => {
                      const isWinner = selectedExperiment.winner === variant.model.id;
                      return (
                        <div key={variant.model.id} className={`border rounded-lg p-3 ${isWinner ? 'border-green-300 bg-green-50' : 'border-gray-200'}`}>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-gray-900">
                              {variant.model.name}
                            </span>
                            {isWinner && (
                              <ArrowTrendingUpIcon className="h-4 w-4 text-green-600" />
                            )}
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="flex items-center gap-1">
                              <ChartBarIcon className="h-3 w-3 text-blue-600" />
                              <span>Accuracy: {(variant.metrics.accuracy * 100).toFixed(1)}%</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <ClockIcon className="h-3 w-3 text-yellow-600" />
                              <span>Latency: {variant.metrics.latency}ms</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <h3 className="font-medium text-gray-900 mb-2">زمان‌بندی</h3>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div>ایجاد: {new Date(selectedExperiment.created_at).toLocaleString('fa-IR')}</div>
                    {selectedExperiment.started_at && (
                      <div>شروع: {new Date(selectedExperiment.started_at).toLocaleString('fa-IR')}</div>
                    )}
                    {selectedExperiment.completed_at && (
                      <div>اتمام: {new Date(selectedExperiment.completed_at).toLocaleString('fa-IR')}</div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">
                یک آزمایش را انتخاب کنید تا جزئیات آن نمایش داده شود
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
