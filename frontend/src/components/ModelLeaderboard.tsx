/**
 * Model Leaderboard Component
 * ============================
 * Interactive leaderboard showing model performance rankings with comparison view.
 * 
 * Features:
 * - Ranked model display with composite scores
 * - Score breakdown visualization
 * - Performance metrics comparison
 * - Sorting and filtering
 */

import { useState, useMemo } from 'react';

interface ModelMetrics {
  model_id: string;
  model_type: string;
  composite_score: number;
  score_breakdown: {
    success_rate_score: number;
    latency_score: number;
    throughput_score: number;
    reliability_score: number;
  };
  metrics: {
    total_requests: number;
    success_rate: number;
    avg_latency_ms: number;
    error_rate: number;
  };
  active: boolean;
}

interface ModelLeaderboardProps {
  models: ModelMetrics[];
  onModelSelect?: (modelId: string) => void;
}

export default function ModelLeaderboard({ models, onModelSelect }: ModelLeaderboardProps) {
  const [sortBy, setSortBy] = useState<'composite' | 'success' | 'latency' | 'throughput'>('composite');
  const [selectedModel, setSelectedModel] = useState<ModelMetrics | null>(null);
  const [showOnlyActive, setShowOnlyActive] = useState(false);

  // Sort models
  const sortedModels = useMemo(() => {
    const filtered = showOnlyActive ? models.filter(m => m.active) : models;
    
    return [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'success':
          return b.metrics.success_rate - a.metrics.success_rate;
        case 'latency':
          return a.metrics.avg_latency_ms - b.metrics.avg_latency_ms; // Lower is better
        case 'throughput':
          return b.metrics.total_requests - a.metrics.total_requests;
        case 'composite':
        default:
          return b.composite_score - a.composite_score;
      }
    });
  }, [models, sortBy, showOnlyActive]);

  const getScoreColor = (score: number): string => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRankBadge = (rank: number): string => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  if (models.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500">
        <p className="text-2xl">📊</p>
        <p className="mt-2">هیچ مدلی یافت نشد</p>
      </div>
    );
  }

  return (
    <div>
      {/* Controls */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-4">
          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="composite">امتیاز ترکیبی</option>
            <option value="success">نرخ موفقیت</option>
            <option value="latency">تأخیر</option>
            <option value="throughput">توان عملیاتی</option>
          </select>

          {/* Active Only Toggle */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showOnlyActive}
              onChange={(e) => setShowOnlyActive(e.target.checked)}
              className="rounded border-slate-300"
            />
            <span className="text-slate-700">فقط فعال‌ها</span>
          </label>
        </div>

        <div className="text-sm text-slate-500">
          {sortedModels.length} مدل
        </div>
      </div>

      {/* Leaderboard Table */}
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                رتبه
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                مدل
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                امتیاز ترکیبی
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                موفقیت
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                تأخیر (ms)
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                درخواست‌ها
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                وضعیت
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {sortedModels.map((model, index) => (
              <tr
                key={model.model_id}
                className="cursor-pointer transition-colors hover:bg-slate-50"
                onClick={() => {
                  setSelectedModel(model);
                  onModelSelect?.(model.model_id);
                }}
              >
                <td className="px-4 py-3 text-lg">
                  {getRankBadge(index + 1)}
                </td>
                <td className="px-4 py-3">
                  <div>
                    <div className="font-medium text-slate-900">{model.model_id}</div>
                    <div className="text-xs text-slate-500">{model.model_type}</div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className={`text-lg font-bold ${getScoreColor(model.composite_score)}`}>
                    {model.composite_score.toFixed(1)}
                  </div>
                  <ScoreBreakdownBar breakdown={model.score_breakdown} />
                </td>
                <td className="px-4 py-3 text-sm text-slate-900">
                  {model.metrics.success_rate.toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-sm text-slate-900">
                  {model.metrics.avg_latency_ms.toFixed(0)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-900">
                  {model.metrics.total_requests.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                    model.active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-slate-100 text-slate-700'
                  }`}>
                    {model.active ? 'فعال' : 'غیرفعال'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Model Detail Modal */}
      {selectedModel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-3xl rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">
                جزئیات مدل: {selectedModel.model_id}
              </h3>
              <button
                type="button"
                onClick={() => setSelectedModel(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {/* Composite Score */}
              <div className="rounded-lg bg-slate-50 p-4">
                <h4 className="mb-2 text-sm font-medium text-slate-600">امتیاز ترکیبی</h4>
                <div className={`text-4xl font-bold ${getScoreColor(selectedModel.composite_score)}`}>
                  {selectedModel.composite_score.toFixed(1)}
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="rounded-lg bg-slate-50 p-4">
                <h4 className="mb-2 text-sm font-medium text-slate-600">عملکرد</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">نرخ موفقیت:</span>
                    <span className="font-medium text-slate-900">{selectedModel.metrics.success_rate.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">تأخیر میانگین:</span>
                    <span className="font-medium text-slate-900">{selectedModel.metrics.avg_latency_ms.toFixed(0)} ms</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">نرخ خطا:</span>
                    <span className="font-medium text-slate-900">{selectedModel.metrics.error_rate.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">کل درخواست‌ها:</span>
                    <span className="font-medium text-slate-900">{selectedModel.metrics.total_requests.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Score Breakdown */}
              <div className="col-span-2 rounded-lg bg-slate-50 p-4">
                <h4 className="mb-3 text-sm font-medium text-slate-600">جزئیات امتیازات</h4>
                <div className="grid grid-cols-4 gap-4">
                  <ScoreCard
                    label="موفقیت (۴۰٪)"
                    score={selectedModel.score_breakdown.success_rate_score}
                  />
                  <ScoreCard
                    label="تأخیر (۳۰٪)"
                    score={selectedModel.score_breakdown.latency_score}
                  />
                  <ScoreCard
                    label="توان عملیاتی (۲۰٪)"
                    score={selectedModel.score_breakdown.throughput_score}
                  />
                  <ScoreCard
                    label="قابلیت اطمینان (۱۰٪)"
                    score={selectedModel.score_breakdown.reliability_score}
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedModel(null)}
                className="rounded-lg bg-slate-200 px-4 py-2 text-slate-700 hover:bg-slate-300"
              >
                بستن
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBreakdownBar({ breakdown }: { breakdown: ModelMetrics['score_breakdown'] }) {
  const total = breakdown.success_rate_score + breakdown.latency_score + 
                breakdown.throughput_score + breakdown.reliability_score;

  return (
    <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
      <div className="flex h-full">
        <div
          className="bg-green-500"
          style={{ width: `${(breakdown.success_rate_score / total) * 100}%` }}
          title="Success Rate"
        />
        <div
          className="bg-blue-500"
          style={{ width: `${(breakdown.latency_score / total) * 100}%` }}
          title="Latency"
        />
        <div
          className="bg-yellow-500"
          style={{ width: `${(breakdown.throughput_score / total) * 100}%` }}
          title="Throughput"
        />
        <div
          className="bg-purple-500"
          style={{ width: `${(breakdown.reliability_score / total) * 100}%` }}
          title="Reliability"
        />
      </div>
    </div>
  );
}

function ScoreCard({ label, score }: { label: string; score: number }) {
  const colorClass = score >= 70 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="rounded-lg bg-white p-3 text-center">
      <div className="text-xs text-slate-600">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${colorClass}`}>
        {score.toFixed(1)}
      </div>
    </div>
  );
}