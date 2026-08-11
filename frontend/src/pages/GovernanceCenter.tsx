/**
 * Governance Center Page
 * The heart of MahouN - Constitutional compliance monitoring
 */

import { useState, useEffect } from 'react';
import { useGovernanceStore } from '../store/governanceStore';

// Types matching backend API
interface Issue {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  message: string;
  timestamp: string;
}

interface ConstitutionalHealth {
  status: 'healthy' | 'degraded' | 'critical';
  score: number;
  issues: Issue[];
  lastValidation: string;
}

export default function GovernanceCenter() {
  const { getContext } = useGovernanceStore();
  const currentContext = getContext();
  
  const [healthData, setHealthData] = useState<ConstitutionalHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGovernanceHealth();
    const interval = setInterval(fetchGovernanceHealth, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchGovernanceHealth = async () => {
    try {
      const response = await fetch('/api/v1/governance/health');
      if (!response.ok) throw new Error('Failed to fetch governance health');
      const data = await response.json();
      setHealthData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-50';
      case 'degraded': return 'text-yellow-600 bg-yellow-50';
      case 'critical': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Governance Center</h1>
          <p className="text-slate-400">مرکز نظارت بر تطابق قانون اساسی و ممیزی سیستم</p>
        </div>

        {/* Context Info */}
        {currentContext && (
          <div className="bg-slate-800 rounded-lg p-4 mb-6 border border-slate-700">
            <div className="flex flex-wrap gap-6 text-sm">
              <div>
                <span className="text-slate-400">Request ID:</span>
                <span className="text-slate-200 ml-2 font-mono">{currentContext.requestId}</span>
              </div>
              <div>
                <span className="text-slate-400">Trace ID:</span>
                <span className="text-slate-200 ml-2 font-mono">{currentContext.traceId}</span>
              </div>
              <div>
                <span className="text-slate-400">User ID:</span>
                <span className="text-slate-200 ml-2">{currentContext.userId}</span>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
            <p className="font-medium">خطا در بارگذاری داده‌ها</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        ) : healthData ? (
          <div className="space-y-6">
            {/* Constitutional Health Status Card */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">وضعیت قانون اساسی</h2>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(healthData.status)}`}>
                  {healthData.status.toUpperCase()}
                </span>
              </div>

              {/* Compliance Score */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-slate-300">امتیاز تطابق</span>
                  <span className={`text-3xl font-bold ${getScoreColor(healthData.score)}`}>
                    {healthData.score.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all duration-500 ${
                      healthData.score >= 90 ? 'bg-green-500' :
                      healthData.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${healthData.score}%` }}
                  />
                </div>
              </div>

              {/* Last Validation */}
              <div className="text-sm text-slate-400">
                آخرین اعتبارسنجی: {new Date(healthData.lastValidation).toLocaleString('fa-IR')}
              </div>
            </div>

            {/* Active Issues */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">مسائل فعال</h2>
                <span className="text-slate-400 text-sm">{healthData.issues.length} مورد</span>
              </div>

              {healthData.issues.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <p className="text-green-400 font-medium">✓ هیچ مسئله‌ای یافت نشد</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {healthData.issues.map((issue) => (
                    <div
                      key={issue.id}
                      className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium uppercase">{issue.severity}</span>
                            <span className="text-xs opacity-70">{issue.category}</span>
                          </div>
                          <p className="font-medium">{issue.message}</p>
                          <p className="text-xs mt-1 opacity-70">
                            {new Date(issue.timestamp).toLocaleString('fa-IR')}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                onClick={() => window.location.href = '/app/studio/governance/audit'}
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg p-4 text-left transition-colors"
              >
                <div className="text-white font-medium mb-1">مرکز ممیزی</div>
                <div className="text-slate-400 text-sm">مشاهده رویدادهای ممیزی</div>
              </button>
              <button
                onClick={() => window.location.href = '/app/studio/governance/fail-closed'}
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg p-4 text-left transition-colors"
              >
                <div className="text-white font-medium mb-1">نظارت Fail-Closed</div>
                <div className="text-slate-400 text-sm">رویدادهای ایمنی fail-closed</div>
              </button>
              <button
                onClick={() => window.location.href = '/app/studio/governance/mutations'}
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg p-4 text-left transition-colors"
              >
                <div className="text-white font-medium mb-1">مجوز تغییرات</div>
                <div className="text-slate-400 text-sm">درخواست‌های تغییرات تایید نشده</div>
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
