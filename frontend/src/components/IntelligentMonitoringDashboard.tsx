/**
 * Intelligent Monitoring Dashboard Component
 * ============================================
 * Comprehensive monitoring dashboard for graph integrity, model performance,
 * and system health with real-time updates and interactive visualizations.
 * 
 * Features:
 * - Graph health score with gauge visualization
 * - Active violations list with filtering
 * - Model performance leaderboard
 * - Real-time polling with configurable intervals
 * - Interactive cleanup actions
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cleanupMonitoringOrphans,
  getMonitoringGraphHealth,
  getMonitoringGraphViolations,
  getMonitoringModelLeaderboard,
  getMonitoringSystemOverview,
  type GraphHealthResponse,
  type GraphViolation,
  type ModelLeaderboardEntry,
  type SystemOverviewResponse,
} from '../api/monitoring';
import GaugeChart from './GaugeChart';
import ViolationsList from './ViolationsList';
import ModelLeaderboard from './ModelLeaderboard';

// ============================================================================
// Main Component
// ============================================================================

export default function IntelligentMonitoringDashboard() {
  const queryClient = useQueryClient();
  const [pollingInterval, setPollingInterval] = useState(5000);
  const [isPollingEnabled, setIsPollingEnabled] = useState(true);

  const graphHealthQuery = useQuery<GraphHealthResponse>({
    queryKey: ['monitoring', 'graph-health'],
    queryFn: getMonitoringGraphHealth,
    refetchInterval: isPollingEnabled ? pollingInterval : false,
    staleTime: 0,
  });

  const violationsQuery = useQuery({
    queryKey: ['monitoring', 'graph-violations'],
    queryFn: () => getMonitoringGraphViolations({ limit: 50 }),
    refetchInterval: isPollingEnabled ? pollingInterval : false,
    staleTime: 0,
  });

  const leaderboardQuery = useQuery({
    queryKey: ['monitoring', 'leaderboard'],
    queryFn: () => getMonitoringModelLeaderboard({ top_n: 10 }),
    refetchInterval: isPollingEnabled ? pollingInterval : false,
    staleTime: 0,
  });

  const overviewQuery = useQuery<SystemOverviewResponse>({
    queryKey: ['monitoring', 'system-overview'],
    queryFn: getMonitoringSystemOverview,
    refetchInterval: isPollingEnabled ? pollingInterval : false,
    staleTime: 0,
  });

  const cleanupMutation = useMutation({
    mutationFn: (mode: 'safe' | 'aggressive' | 'manual-review') => cleanupMonitoringOrphans(mode, true),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['monitoring'] });
    },
  });

  const graphHealth = graphHealthQuery.data ?? null;
  const violations = (violationsQuery.data?.violations ?? []) as GraphViolation[];
  const modelLeaderboard = (leaderboardQuery.data?.ranking ?? []) as ModelLeaderboardEntry[];
  const systemOverview = overviewQuery.data ?? null;
  const lastUpdated = overviewQuery.data?.timestamp ?? graphHealthQuery.data?.timestamp ?? null;
  const isLoading = graphHealthQuery.isLoading || violationsQuery.isLoading || leaderboardQuery.isLoading || overviewQuery.isLoading;
  const error = [graphHealthQuery.error, violationsQuery.error, leaderboardQuery.error, overviewQuery.error]
    .find(Boolean)?.message ?? null;

  const refreshAll = async () => {
    await Promise.all([
      graphHealthQuery.refetch(),
      violationsQuery.refetch(),
      leaderboardQuery.refetch(),
      overviewQuery.refetch(),
    ]);
  };

  const triggerCleanup = async (mode: 'safe' | 'aggressive' | 'manual-review') => {
    await cleanupMutation.mutateAsync(mode);
  };

  // ============================================================================
  // Loading State
  // ============================================================================

  if (isLoading && !systemOverview) {
    return (
      <div className="p-8">
        <h1 className="mb-8 text-3xl font-bold text-slate-900">مانیتورینگ هوشمند</h1>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">مانیتورینگ هوشمند</h1>
          <p className="mt-1 text-sm text-slate-500">
            سلامت گراف، عملکرد مدل‌ها و وضعیت سیستم
            {lastUpdated && ` · آخرین به‌روزرسانی ${new Date(lastUpdated).toLocaleTimeString('fa-IR')}`}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Polling Interval Selector */}
          <select
            value={pollingInterval}
            onChange={(e) => setPollingInterval(Number(e.target.value))}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600"
          >
            <option value={5000}>۵ ثانیه</option>
            <option value={10000}>۱۰ ثانیه</option>
            <option value={15000}>۱۵ ثانیه</option>
            <option value={30000}>۳۰ ثانیه</option>
          </select>
          
          {/* Polling Toggle */}
          <button
            type="button"
            onClick={() => setIsPollingEnabled(!isPollingEnabled)}
            className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
              isPollingEnabled
                ? 'border-green-300 bg-green-50 text-green-700'
                : 'border-slate-200 bg-slate-50 text-slate-600'
            }`}
          >
            {isPollingEnabled ? '⏸ توقف' : '▶ شروع'}
          </button>
          
          {/* Manual Refresh */}
          <button
            type="button"
            onClick={() => void refreshAll()}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100"
          >
            به‌روزرسانی
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">خطا</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {/* System Overview Banner */}
      {systemOverview && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <OverviewCard
            label="سلامت گراف"
            value={systemOverview.graph.health_score.toFixed(1)}
            unit="%"
            status={systemOverview.graph.status}
          />
          <OverviewCard
            label="نقض‌های فعال"
            value={systemOverview.graph.violations.total.toString()}
            unit=""
            status={systemOverview.graph.violations.critical > 0 ? 'critical' : 'healthy'}
          />
          <OverviewCard
            label="مدل‌های فعال"
            value={systemOverview.models.active.toString()}
            unit={`از ${systemOverview.models.total}`}
            status="healthy"
          />
          <OverviewCard
            label="بهترین مدل"
            value={systemOverview.models.top_performer}
            unit=""
            status="healthy"
          />
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Graph Health Gauge */}
        {graphHealth && (
          <div className="col-span-1">
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-900">سلامت گراف</h2>
              <GaugeChart
                value={graphHealth.health_score}
                label={graphHealth.status}
              />
              <div className="mt-4 space-y-2">
                {graphHealth.recommendations.map((rec, idx) => (
                  <p key={idx} className="text-sm text-slate-600">
                    • {rec}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Violations List */}
        <div className="col-span-2">
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">نقض‌های فعال</h2>
              <button
                type="button"
                onClick={() => void triggerCleanup('manual-review')}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700"
              >
                پاکسازی خودکار
              </button>
            </div>
            <ViolationsList violations={violations} />
          </div>
        </div>

        {/* Model Leaderboard */}
        <div className="col-span-3">
          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">جدول برترین مدل‌ها</h2>
            <ModelLeaderboard models={modelLeaderboard} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Helper Components
// ============================================================================

function OverviewCard({ 
  label, 
  value, 
  unit, 
  status 
}: { 
  label: string; 
  value: string; 
  unit: string; 
  status: string;
}) {
  const statusColors = {
    healthy: 'border-green-200 bg-green-50',
    degraded: 'border-yellow-200 bg-yellow-50',
    critical: 'border-red-200 bg-red-50',
  };

  const colorClass = statusColors[status as keyof typeof statusColors] || 'border-slate-200 bg-white';

  return (
    <div className={`rounded-lg border p-4 ${colorClass}`}>
      <p className="text-sm text-slate-600">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">
        {value}
        <span className="text-sm font-normal text-slate-500"> {unit}</span>
      </p>
    </div>
  );
}