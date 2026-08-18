/**
 * Mutation Authorization Component
 * Displays mutation authorization statistics and pending requests
 */

import { useState, useEffect } from 'react';

// Types matching backend API
interface RiskDistribution {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

interface MutationAuthorization {
  pendingRequests: number;
  approvalRate: number;
  averageReviewTime: number;
  riskDistribution: RiskDistribution;
}

export default function MutationAuthorization() {
  const [data, setData] = useState<MutationAuthorization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMutationStats();
    const interval = setInterval(fetchMutationStats, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchMutationStats = async () => {
    try {
      const response = await fetch('/api/v1/governance/mutations/stats');
      if (!response.ok) throw new Error('Failed to fetch mutation stats');
      const stats = await response.json();
      setData(stats);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getApprovalRateColor = (rate: number) => {
    if (rate >= 80) return 'text-green-600';
    if (rate >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-slate-500';
    }
  };

  const totalRisks = data ? Object.values(data.riskDistribution).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">مجوز تغییرات</h1>
          <p className="text-slate-400">نظارت بر درخواست‌های تغییرات و مجوزهای اعمال شده</p>
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
        ) : data ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Pending Requests */}
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="text-slate-400 text-sm mb-2">درخواست‌های در انتظار</div>
                <div className={`text-3xl font-bold ${data.pendingRequests > 0 ? 'text-yellow-500' : 'text-green-500'}`}>
                  {data.pendingRequests.toLocaleString('fa-IR')}
                </div>
              </div>

              {/* Approval Rate */}
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="text-slate-400 text-sm mb-2">نرخ تایید</div>
                <div className={`text-3xl font-bold ${getApprovalRateColor(data.approvalRate)}`}>
                  {data.approvalRate.toFixed(1)}%
                </div>
              </div>

              {/* Average Review Time */}
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <div className="text-slate-400 text-sm mb-2">میانگین زمان بررسی</div>
                <div className="text-3xl font-bold text-white">
                  {(data.averageReviewTime / 1000).toFixed(1)}s
                </div>
              </div>
            </div>

            {/* Risk Distribution */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">توزیع ریسک</h2>
              {totalRisks > 0 ? (
                <div className="space-y-4">
                  {Object.entries(data.riskDistribution).map(([risk, count]) => {
                    const percentage = (count / totalRisks) * 100;
                    return (
                      <div key={risk}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-slate-300 capitalize">{risk}</span>
                          <span className="text-slate-400">{count} ({percentage.toFixed(1)}%)</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${getRiskColor(risk)}`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <p>هیچ درخواستی ثبت نشده</p>
                </div>
              )}
            </div>

            {/* Risk Analysis */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">تحلیل ریسک</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 text-sm mb-2">ریسک بالا و بحرانی</div>
                  <div className="text-2xl font-bold text-red-500">
                    {(data.riskDistribution.high + data.riskDistribution.critical).toLocaleString('fa-IR')}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">نیاز به بررسی فوری</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 text-sm mb-2">ریسک پایین و متوسط</div>
                  <div className="text-2xl font-bold text-green-500">
                    {(data.riskDistribution.low + data.riskDistribution.medium).toLocaleString('fa-IR')}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">می‌تواند تایید خودکار شود</div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-lg transition-colors"
              >
                مشاهده درخواست‌های در انتظار
              </button>
              <button                
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white px-6 py-3 rounded-lg transition-colors"
              >
                مشاهده الگوهای تغییرات
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
