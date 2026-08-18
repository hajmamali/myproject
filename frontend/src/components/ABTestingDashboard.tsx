/**
 * A/B Testing Dashboard Component
 */

import { useState, useEffect } from 'react';

interface Experiment {
  id: string;
  name: string;
  description: string;
  status: 'running' | 'completed' | 'paused' | 'draft';
  variant_a: string;
  variant_b: string;
  traffic_split: number;
  started_at: string;
  ended_at?: string;
  metrics: {
    impressions_a: number;
    impressions_b: number;
    conversions_a: number;
    conversions_b: number;
    conversion_rate_a: number;
    conversion_rate_b: number;
    statistical_significance: number;
    winner?: 'A' | 'B' | 'inconclusive';
  };
}

export default function ABTestingDashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'running' | 'completed' | 'paused'>('all');

  useEffect(() => {
    fetchExperiments();
  }, []);

  const fetchExperiments = async () => {
    try {
      const response = await fetch('/api/v1/experiments');
      if (!response.ok) throw new Error('Failed to fetch experiments');
      const data = await response.json();
      setExperiments(data.experiments || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-green-100 text-green-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      case 'draft': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getWinnerColor = (winner?: string) => {
    switch (winner) {
      case 'A': return 'text-blue-500';
      case 'B': return 'text-green-500';
      case 'inconclusive': return 'text-yellow-500';
      default: return 'text-slate-400';
    }
  };

  const filteredExperiments = experiments.filter(exp => 
    filter === 'all' || exp.status === filter
  );

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">آزمایش‌های A/B</h1>
          <p className="text-slate-400">مدیریت و تحلیل آزمایش‌های A/B</p>
        </div>

        {/* Filter */}
        <div className="mb-6 flex items-center gap-4">
          <label className="text-slate-300 text-sm">فیلتر وضعیت:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm"
          >
            <option value="all">همه</option>
            <option value="running">در حال اجرا</option>
            <option value="completed">تکمیل شده</option>
            <option value="paused">متوقف</option>
          </select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
            <p className="font-medium">خطا در بارگذاری داده‌ها</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        ) : filteredExperiments.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 border border-slate-700 text-center">
            <div className="text-6xl mb-4">🧪</div>
            <h3 className="text-xl font-semibold text-white mb-2">هیچ آزمایشی یافت نشد</h3>
            <p className="text-slate-400 mb-4">برای شروع، یک آزمایش جدید بسازید</p>
            <button
              onClick={() => window.location.href = '/app/studio/experiments/new'}
              className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
            >
              ساخت آزمایش جدید
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">کل آزمایش‌ها</div>
                <div className="text-2xl font-bold text-white">{experiments.length}</div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">در حال اجرا</div>
                <div className="text-2xl font-bold text-green-400">
                  {experiments.filter(e => e.status === 'running').length}
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">تکمیل شده</div>
                <div className="text-2xl font-bold text-blue-400">
                  {experiments.filter(e => e.status === 'completed').length}
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">متوقف</div>
                <div className="text-2xl font-bold text-yellow-400">
                  {experiments.filter(e => e.status === 'paused').length}
                </div>
              </div>
            </div>

            {/* Experiment List */}
            <div className="space-y-4">
              {filteredExperiments.map((experiment) => (
                <div key={experiment.id} className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-lg font-semibold text-white">{experiment.name}</h3>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${getStatusColor(experiment.status)}`}>
                          {experiment.status}
                        </span>
                      </div>
                      <p className="text-slate-400 text-sm">{experiment.description}</p>
                    </div>
                    {experiment.metrics.winner && (
                      <div className={`text-sm font-medium ${getWinnerColor(experiment.metrics.winner)}`}>
                        برنده: {experiment.metrics.winner}
                      </div>
                    )}
                  </div>

                  {/* Variants */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    {/* Variant A */}
                    <div className="bg-slate-900/50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-blue-400 font-medium">Variant A</span>
                        <span className="text-slate-400 text-sm">{experiment.variant_a}</span>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Impressions:</span>
                          <span className="text-white">{experiment.metrics.impressions_a.toLocaleString('fa-IR')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Conversions:</span>
                          <span className="text-white">{experiment.metrics.conversions_a.toLocaleString('fa-IR')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Rate:</span>
                          <span className="text-white">{(experiment.metrics.conversion_rate_a * 100).toFixed(2)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Variant B */}
                    <div className="bg-slate-900/50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-green-400 font-medium">Variant B</span>
                        <span className="text-slate-400 text-sm">{experiment.variant_b}</span>
                      </div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Impressions:</span>
                          <span className="text-white">{experiment.metrics.impressions_b.toLocaleString('fa-IR')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Conversions:</span>
                          <span className="text-white">{experiment.metrics.conversions_b.toLocaleString('fa-IR')}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Rate:</span>
                          <span className="text-white">{(experiment.metrics.conversion_rate_b * 100).toFixed(2)}%</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <span className="text-slate-400">Traffic Split: {experiment.traffic_split}%</span>
                      <span className="text-slate-400">
                        Significance: {(experiment.metrics.statistical_significance * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => window.location.href = `/app/studio/experiments/${experiment.id}`}
                        className="text-primary-400 hover:text-primary-300"
                      >
                        مشاهده جزئیات
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Create Button */}
            <div className="flex justify-end mt-6">
              <button
                onClick={() => window.location.href = '/app/studio/experiments/new'}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                + آزمایش جدید
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
