/**
 * Audit Center Component
 * Displays audit events, timeline, and analytics
 */

import { useState, useEffect } from 'react';

// Types matching backend API
interface TrendData {
  timestamp: string;
  value: number;
}

interface AuditMetrics {
  totalEvents: number;
  criticalEvents: number;
  complianceRate: number;
  trends: TrendData[];
}

export default function AuditCenter() {
  const [metrics, setMetrics] = useState<AuditMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    fetchAuditMetrics();
  }, [hours]);

  const fetchAuditMetrics = async () => {
    try {
      const response = await fetch(`/api/v1/governance/audit/metrics?hours=${hours}`);
      if (!response.ok) throw new Error('Failed to fetch audit metrics');
      const data = await response.json();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getComplianceColor = (rate: number) => {
    if (rate >= 95) return 'text-green-600';
    if (rate >= 80) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">مرکز ممیزی</h1>
          <p className="text-slate-400">مشاهده و تحلیل رویدادهای ممیزی سیستم</p>
        </div>

        {/* Time Range Selector */}
        <div className="mb-6 flex items-center gap-4">
          <label className="text-slate-300 text-sm">بازه زمانی:</label>
          <select
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm"
          >
            <option value={1}>۱ ساعت</option>
            <option value={6}>۶ ساعت</option>
            <option value={24}>۲۴ ساعت</option>
            <option value={168}>۷ روز</option>
            <option value={720}>۳۰ روز</option>
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
        ) : metrics ? (
          <div className="space-y-6">
            {/* Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Total Events */}
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="text-slate-400 text-sm mb-2">کل رویدادها</div>
                <div className="text-3xl font-bold text-white">{metrics.totalEvents.toLocaleString('fa-IR')}</div>
              </div>

              {/* Critical Events */}
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="text-slate-400 text-sm mb-2">رویدادهای بحرانی</div>
                <div className={`text-3xl font-bold ${metrics.criticalEvents > 0 ? 'text-red-500' : 'text-green-500'}`}>
                  {metrics.criticalEvents.toLocaleString('fa-IR')}
                </div>
              </div>

              {/* Compliance Rate */}
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="text-slate-400 text-sm mb-2">نرخ تطابق</div>
                <div className={`text-3xl font-bold ${getComplianceColor(metrics.complianceRate)}`}>
                  {metrics.complianceRate.toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Trends Chart */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">روند رویدادها</h2>
              {metrics.trends.length > 0 ? (
                <div className="h-64 flex items-end gap-1">
                  {metrics.trends.map((trend, index) => {
                    const maxValue = Math.max(...metrics.trends.map(t => t.value));
                    const height = maxValue > 0 ? (trend.value / maxValue) * 100 : 0;
                    return (
                      <div
                        key={index}
                        className="flex-1 bg-primary-600 rounded-t transition-all hover:bg-primary-500"
                        style={{ height: `${height}%` }}
                        title={`${new Date(trend.timestamp).toLocaleString('fa-IR')}: ${trend.value}`}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <p>داده‌ای برای نمایش وجود ندارد</p>
                </div>
              )}
            </div>

            {/* Export Button */}
            <div className="flex justify-end">
              <button
                onClick={() => {
                  const dataStr = JSON.stringify(metrics, null, 2);
                  const blob = new Blob([dataStr], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `audit-metrics-${new Date().toISOString()}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                دانلود گزارش
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
