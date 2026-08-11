/**
 * Monitoring Dashboard Component
 *
 * Live system monitoring for the Studio. Polls real-time metrics and
 * alerts from the backend, and lists detailed component health.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from '../api/client';

interface RealtimeMetrics {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_in: number;
  network_out: number;
  active_connections: number;
  queries_per_second: number;
  cache_hit_rate: number;
}

interface HealthComponent {
  status: 'healthy' | 'warning' | 'error' | string;
  value: number;
  unit: string;
  threshold: number;
  last_updated?: string;
}

interface StudioOverview {
  health_metrics: HealthComponent[];
  alerts: AlertItem[];
  metrics: {
    total_queries_today: number;
    avg_response_time: number;
    error_rate: number;
    active_users: number;
  };
  system_info: {
    version: string;
    uptime_hours: number;
    environment: string;
  };
}

interface AlertItem {
  id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  timestamp: string;
  component: string;
  acknowledged: boolean;
}

const REFRESH_INTERVAL_MS = 5000;

function metricColor(percent: number): string {
  if (percent >= 90) return 'text-red-400';
  if (percent >= 75) return 'text-yellow-400';
  return 'text-green-400';
}

function statusSeverityClass(status: string): string {
  switch (status) {
    case 'healthy':
      return 'bg-green-100 text-green-700';
    case 'warning':
      return 'bg-yellow-100 text-yellow-700';
    case 'error':
      return 'bg-red-100 text-red-700';
    default:
      return 'bg-slate-100 text-slate-700';
  }
}

function severityClass(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'border-red-500 bg-red-900/30 text-red-300';
    case 'error':
      return 'border-red-700 bg-red-900/20 text-red-400';
    case 'warning':
      return 'border-yellow-700 bg-yellow-900/20 text-yellow-400';
    case 'info':
    default:
      return 'border-blue-700 bg-blue-900/20 text-blue-300';
  }
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('fa-IR');
  } catch {
    return iso;
  }
}

export default function MonitoringDashboard() {
  const [metrics, setMetrics] = useState<RealtimeMetrics | null>(null);
  const [overview, setOverview] = useState<StudioOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRealtime = useCallback(async () => {
    try {
      const data = (await apiClient.get('/api/v1/dashboard/studio/metrics/realtime')) as RealtimeMetrics;
      setMetrics(data);
      setLastUpdated(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در دریافت معیارهای لحظه‌ای');
    }
  }, []);

  const fetchOverview = useCallback(async () => {
    try {
      const data = (await apiClient.get('/api/v1/dashboard/studio/overview')) as StudioOverview;
      setOverview(data);
    } catch (err) {
      // Overview is best-effort; realtime metrics are the primary stream.
      console.error('Failed to load studio overview:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const acknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      await apiClient.post(`/api/v1/dashboard/studio/alerts/${alertId}/acknowledge`);
      setOverview((prev) =>
        prev
          ? {
              ...prev,
              alerts: prev.alerts.map((a) =>
                a.id === alertId ? { ...a, acknowledged: true } : a
              ),
            }
          : prev
      );
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  }, []);

  useEffect(() => {
    void fetchOverview();
    void fetchRealtime();
    intervalRef.current = setInterval(() => void fetchRealtime(), REFRESH_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchOverview, fetchRealtime]);

  if (isLoading && !metrics && !overview) {
    return (
      <div className="p-8">
        <h1 className="mb-8 text-3xl font-bold text-slate-900">مانیتورینگ</h1>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">مانیتورینگ</h1>
          <p className="mt-1 text-sm text-slate-500">
            معیارهای لحظه‌ای سیستم{lastUpdated ? ` · آخرین به‌روزرسانی ${formatTime(lastUpdated)}` : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void fetchRealtime()}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100"
        >
          به‌روزرسانی
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">خطا</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {/* Realtime metrics grid */}
      {metrics && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard label="CPU" value={`${metrics.cpu_usage.toFixed(1)}%`} tone={metricColor(metrics.cpu_usage)} />
          <MetricCard
            label="حافظه"
            value={`${metrics.memory_usage.toFixed(1)}%`}
            tone={metricColor(metrics.memory_usage)}
          />
          <MetricCard
            label="دیسک"
            value={`${metrics.disk_usage.toFixed(1)}%`}
            tone={metricColor(metrics.disk_usage)}
          />
          <MetricCard
            label="اتصالات فعال"
            value={metrics.active_connections.toLocaleString('fa-IR')}
            tone="text-blue-400"
          />
          <MetricCard
            label="درخواست در ثانیه"
            value={metrics.queries_per_second.toFixed(2)}
            tone="text-blue-400"
          />
          <MetricCard
            label="نرخ Cache Hit"
            value={`${(metrics.cache_hit_rate * 100).toFixed(1)}%`}
            tone="text-green-400"
          />
          <MetricCard
            label="شبکه (ورودی)"
            value={`${metrics.network_in.toFixed(1)} MB/s`}
            tone="text-blue-400"
          />
          <MetricCard
            label="شبکه (خروجی)"
            value={`${metrics.network_out.toFixed(1)} MB/s`}
            tone="text-blue-400"
          />
        </div>
      )}

      {/* Summary stats from overview */}
      {overview && (
        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard
            label="پرس‌وجوهای امروز"
            value={overview.metrics.total_queries_today.toLocaleString('fa-IR')}
            tone="text-slate-900"
          />
          <MetricCard
            label="میانگین زمان پاسخ"
            value={`${(overview.metrics.avg_response_time * 1000).toFixed(0)}ms`}
            tone="text-slate-900"
          />
          <MetricCard
            label="نرخ خطا"
            value={`${(overview.metrics.error_rate * 100).toFixed(2)}%`}
            tone={overview.metrics.error_rate > 0.05 ? 'text-yellow-400' : 'text-green-400'}
          />
          <MetricCard
            label="کاربران فعال"
            value={overview.metrics.active_users.toLocaleString('fa-IR')}
            tone="text-slate-900"
          />
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Component health */}
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-bold text-slate-900">سلامت اجزا</h2>
          {overview?.health_metrics.length ? (
            <ul className="space-y-3">
              {overview.health_metrics.map((hc) => (
                <li
                  key={hc.component || `${hc.status}-${hc.value}`}
                  className="flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-slate-800">
                      {hc.component}
                    </div>
                    <div className="text-xs text-slate-500">
                      آستانه: {hc.threshold.toFixed(1)} {hc.unit}
                    </div>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-3">
                    <span className="text-sm font-bold text-slate-900">
                      {hc.value.toFixed(1)} {hc.unit}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${statusSeverityClass(hc.status)}`}>
                      {hc.status}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">داده‌ای در دسترس نیست.</p>
          )}
        </div>

        {/* Alerts */}
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-bold text-slate-900">هشدارها</h2>
          {overview?.alerts.length ? (
            <ul className="space-y-3">
              {overview.alerts.map((alert) => (
                <li
                  key={alert.id}
                  className={`rounded-lg border p-3 ${severityClass(alert.severity)}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold">{alert.title}</div>
                      <div className="text-xs opacity-80">{alert.message}</div>
                      <div className="mt-1 text-xs opacity-60">
                        {alert.component} · {formatTime(alert.timestamp)}
                      </div>
                    </div>
                    {!alert.acknowledged && (
                      <button
                        type="button"
                        onClick={() => void acknowledgeAlert(alert.id)}
                        className="flex-shrink-0 rounded border border-current/40 px-2 py-1 text-xs transition-opacity hover:opacity-80"
                      >
                        تأیید
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">هیچ هشداری ثبت نشده است.</p>
          )}
        </div>
      </div>

      {overview?.system_info && (
        <div className="mt-4 rounded-lg bg-white p-4 shadow">
          <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-slate-600">
            <div>
              <span className="text-slate-500">نسخه: </span>
              <span className="font-medium text-slate-800">{overview.system_info.version}</span>
            </div>
            <div>
              <span className="text-slate-500">زمان فعالیت: </span>
              <span className="font-medium text-slate-800">
                {overview.system_info.uptime_hours.toFixed(1)} ساعت
              </span>
            </div>
            <div>
              <span className="text-slate-500">محیط: </span>
              <span className="font-medium text-slate-800">{overview.system_info.environment}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-lg bg-white p-4 shadow">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 text-xl font-bold ${tone}`}>{value}</div>
    </div>
  );
}
