/**
 * Studio Dashboard - Developer/Admin View
 * 
 * Real-time system monitoring, health metrics, alerts, and quick actions.
 */

import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  Database,
  FileText,
  GitBranch,
  TrendingUp,
  Users,
  Zap,
  CheckCircle,
  XCircle,
  AlertCircle,
  Info,
} from 'lucide-react';
import { apiClient } from '../../api/client';

interface SystemHealthMetric {
  component: string;
  status: string;
  value: number;
  unit: string;
  threshold: number;
  last_updated: string;
}

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  route: string;
  requires_role: string;
}

interface AlertItem {
  id: string;
  severity: string;
  title: string;
  message: string;
  timestamp: string;
  component: string;
  acknowledged: boolean;
}

interface DashboardOverview {
  health_metrics: SystemHealthMetric[];
  quick_actions: QuickAction[];
  alerts: AlertItem[];
  metrics: {
    queries_per_hour: Array<{ timestamp: string; value: number }>;
    total_queries_today: number;
    avg_response_time: number;
    error_rate: number;
    active_users: number;
  };
  system_info: {
    version: string;
    uptime_hours: number;
    last_deployment: string;
    environment: string;
  };
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'healthy':
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case 'warning':
      return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    case 'error':
      return <XCircle className="w-5 h-5 text-red-500" />;
    default:
      return <Info className="w-5 h-5 text-gray-500" />;
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'bg-red-100 border-red-500 text-red-800';
    case 'error':
      return 'bg-red-50 border-red-400 text-red-700';
    case 'warning':
      return 'bg-yellow-50 border-yellow-400 text-yellow-700';
    case 'info':
      return 'bg-blue-50 border-blue-400 text-blue-700';
    default:
      return 'bg-gray-50 border-gray-400 text-gray-700';
  }
};

const getActionIcon = (iconName: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    graph: <GitBranch className="w-6 h-6" />,
    brain: <Brain className="w-6 h-6" />,
    'file-text': <FileText className="w-6 h-6" />,
    database: <Database className="w-6 h-6" />,
  };
  return iconMap[iconName] || <Activity className="w-6 h-6" />;
};

export default function StudioDashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtimeMetrics, setRealtimeMetrics] = useState<any>(null);

  // Load dashboard data
  useEffect(() => {
    loadDashboard();
    
    // Real-time metrics update every 5 seconds
    const interval = setInterval(() => {
      loadRealtimeMetrics();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get('/api/v1/dashboard/studio/overview') as DashboardOverview;
      setOverview(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setError('خطا در بارگذاری داشبورد');
    } finally {
      setLoading(false);
    }
  };

  const loadRealtimeMetrics = async () => {
    try {
      const data = await apiClient.get('/api/v1/dashboard/studio/metrics/realtime');
      setRealtimeMetrics(data);
    } catch (err) {
      console.error('Failed to load realtime metrics:', err);
    }
  };

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await apiClient.post(`/api/v1/dashboard/studio/alerts/${alertId}/acknowledge`);
      // Reload dashboard to update alert status
      loadDashboard();
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">در حال بارگذاری داشبورد...</p>
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-800 font-bold mb-2">خطا در بارگذاری</p>
          <p className="text-gray-600">{error || 'داده‌های داشبورد یافت نشد'}</p>
          <button
            onClick={loadDashboard}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            تلاش مجدد
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6" dir="rtl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">داشبورد توسعه‌دهنده</h1>
        <p className="text-gray-600">
          نسخه {overview.system_info.version} • محیط {overview.system_info.environment} • آپتایم:{' '}
          {Math.floor(overview.system_info.uptime_hours)} ساعت
        </p>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {overview.health_metrics.map((metric) => (
          <div key={metric.component} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              {getStatusIcon(metric.status)}
              <span className="text-sm text-gray-500">{metric.component}</span>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">
              {metric.value.toFixed(1)}{metric.unit}
            </div>
            <div className="text-sm text-gray-600">
              آستانه: {metric.threshold}{metric.unit}
            </div>
          </div>
        ))}
      </div>

      {/* Real-time Metrics */}
      {realtimeMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <Activity className="w-5 h-5 text-blue-500" />
              <span className="text-xs text-gray-500">CPU</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {realtimeMetrics.cpu_usage.toFixed(1)}%
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <Database className="w-5 h-5 text-green-500" />
              <span className="text-xs text-gray-500">حافظه</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {realtimeMetrics.memory_usage.toFixed(1)}%
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-5 h-5 text-purple-500" />
              <span className="text-xs text-gray-500">QPS</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {realtimeMetrics.queries_per_second.toFixed(1)}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <Users className="w-5 h-5 text-orange-500" />
              <span className="text-xs text-gray-500">اتصالات</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {realtimeMetrics.active_connections}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              <span className="text-xs text-gray-500">Cache Hit</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {(realtimeMetrics.cache_hit_rate * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">دسترسی سریع</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {overview.quick_actions.map((action) => (
            <button
              key={action.id}
              onClick={() => (window.location.href = action.route)}
              className="bg-white rounded-lg shadow p-6 text-right hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center mb-3">
                {getActionIcon(action.icon)}
                <span className="mr-3 font-bold text-gray-900">{action.title}</span>
              </div>
              <p className="text-sm text-gray-600">{action.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Alerts & Stats Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Alerts */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <AlertTriangle className="w-6 h-6 ml-2 text-yellow-500" />
            هشدارهای اخیر
          </h2>
          <div className="space-y-3">
            {overview.alerts.length === 0 ? (
              <p className="text-gray-500 text-center py-4">هشداری وجود ندارد</p>
            ) : (
              overview.alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`border-r-4 rounded p-4 ${getSeverityColor(alert.severity)}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-bold mb-1">{alert.title}</h3>
                      <p className="text-sm mb-2">{alert.message}</p>
                      <div className="flex items-center text-xs">
                        <span className="ml-3">{alert.component}</span>
                        <span>{new Date(alert.timestamp).toLocaleString('fa-IR')}</span>
                      </div>
                    </div>
                    {!alert.acknowledged && (
                      <button
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="text-xs px-2 py-1 bg-white rounded hover:bg-gray-100 mr-2"
                      >
                        تأیید
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Key Metrics */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
            <TrendingUp className="w-6 h-6 ml-2 text-blue-500" />
            آمار کلیدی
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">کل پرس‌وجوهای امروز</span>
              <span className="text-2xl font-bold text-blue-600">
                {overview.metrics.total_queries_today.toLocaleString()}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">متوسط زمان پاسخ</span>
              <span className="text-2xl font-bold text-green-600">
                {overview.metrics.avg_response_time.toFixed(3)}s
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">نرخ خطا</span>
              <span className="text-2xl font-bold text-red-600">
                {(overview.metrics.error_rate * 100).toFixed(2)}%
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">کاربران فعال</span>
              <span className="text-2xl font-bold text-purple-600">
                {overview.metrics.active_users}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
