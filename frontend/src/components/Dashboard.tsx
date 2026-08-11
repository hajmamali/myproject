/**
 * Portal Dashboard Component
 *
 * Personal overview for the logged-in user: usage stats, recent activities,
 * and recent queries. Data is fetched live from the Portal overview API.
 */

import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api/client';

interface UsageStat {
  label: string;
  current: number;
  total: number;
  percentage: number;
  change: number;
}

interface RecentActivity {
  id: string;
  type: string; // query, upload, export
  title: string;
  description: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
  user?: string;
}

interface RecentQuery {
  id: string;
  question: string;
  timestamp: string;
  status: string;
  confidence: number;
  verdict_count: number;
}

interface PortalOverview {
  activities: RecentActivity[];
  usage_stats: UsageStat[];
  recent_queries: RecentQuery[];
  user_info: {
    total_queries: number;
    total_uploads: number;
    member_since: string;
    last_login: string;
  };
  quick_stats: {
    queries_this_week: number;
    avg_confidence: number;
    saved_searches: number;
    bookmarked_verdicts: number;
  };
}

const ACTIVITY_TYPE_LABEL: Record<string, string> = {
  query: 'پرس‌وجو',
  upload: 'بارگذاری',
  export: 'خروجی',
};

const STATUS_LABEL: Record<string, string> = {
  success: 'موفق',
  pending: 'در انتظار',
  failed: 'ناموفق',
};

function statusColor(status: string): string {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-700';
    case 'pending':
      return 'bg-yellow-100 text-yellow-700';
    case 'failed':
      return 'bg-red-100 text-red-700';
    default:
      return 'bg-slate-100 text-slate-700';
  }
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('fa-IR', {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

export default function Dashboard() {
  const [overview, setOverview] = useState<PortalOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = (await apiClient.get('/api/v1/dashboard/portal/overview')) as PortalOverview;
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'بارگذاری داشبورد ناموفق بود');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchOverview();
  }, [fetchOverview]);

  if (isLoading) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">داشبورد</h1>
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">داشبورد</h1>
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">خطا در بارگذاری داده‌ها</p>
          <p className="mt-1 text-sm">{error ?? 'داده‌ای در دسترس نیست'}</p>
        </div>
        <button
          type="button"
          onClick={() => void fetchOverview()}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
        >
          تلاش مجدد
        </button>
      </div>
    );
  }

  const { usage_stats, activities, recent_queries, user_info, quick_stats } = overview;

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">داشبورد</h1>
          <p className="mt-1 text-sm text-slate-500">خلاصه فعالیت‌ها و استفاده از سیستم</p>
        </div>
        <button
          type="button"
          onClick={() => void fetchOverview()}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100"
        >
          به‌روزرسانی
        </button>
      </div>

      {/* Usage stats */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {usage_stats.map((stat) => (
          <div key={stat.label} className="rounded-lg bg-white p-6 shadow">
            <div className="text-sm font-medium text-slate-600">{stat.label}</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {stat.current.toLocaleString('fa-IR')}
              </span>
              <span className="text-sm text-slate-400">/ {stat.total.toLocaleString('fa-IR')}</span>
            </div>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-primary-600"
                style={{ width: `${Math.min(100, stat.percentage)}%` }}
                aria-label={`درصد: ${stat.percentage.toFixed(0)}%`}
              />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs">
              <span className="text-slate-500">{stat.percentage.toFixed(0)}%</span>
              <span
                className={
                  stat.change >= 0 ? 'font-medium text-green-600' : 'font-medium text-red-600'
                }
              >
                {stat.change >= 0 ? '↑' : '↓'} {Math.abs(stat.change).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Quick stats */}
      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-lg bg-white p-4 shadow">
          <div className="text-xs text-slate-500">پرس‌وجوهای این هفته</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {quick_stats.queries_this_week.toLocaleString('fa-IR')}
          </div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <div className="text-xs text-slate-500">میانگین اطمینان</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {(quick_stats.avg_confidence * 100).toFixed(1)}%
          </div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <div className="text-xs text-slate-500">جستجوهای ذخیره شده</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {quick_stats.saved_searches.toLocaleString('fa-IR')}
          </div>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <div className="text-xs text-slate-500">آراء نشان‌شده</div>
          <div className="mt-1 text-xl font-bold text-slate-900">
            {quick_stats.bookmarked_verdicts.toLocaleString('fa-IR')}
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Recent activities */}
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-bold text-slate-900">فعالیت‌های اخیر</h2>
          <ul className="space-y-3">
            {activities.slice(0, 6).map((act) => (
              <li key={act.id} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-800">
                    {ACTIVITY_TYPE_LABEL[act.type] ?? act.type}: {act.title}
                  </div>
                  <div className="truncate text-xs text-slate-500">{act.description}</div>
                </div>
                <div className="flex flex-shrink-0 flex-col items-end gap-1">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${statusColor(act.status)}`}>
                    {STATUS_LABEL[act.status] ?? act.status}
                  </span>
                  <span className="text-xs text-slate-400">{formatDate(act.timestamp)}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Recent queries */}
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-bold text-slate-900">پرس‌وجوهای اخیر</h2>
          <ul className="space-y-3">
            {recent_queries.map((q) => (
              <li key={q.id} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-slate-800">{q.question}</div>
                  <div className="text-xs text-slate-500">
                    {q.verdict_count.toLocaleString('fa-IR')} رأی · اطمینان {(q.confidence * 100).toFixed(0)}%
                  </div>
                </div>
                <span className="flex-shrink-0 text-xs text-slate-400">{formatDate(q.timestamp)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* User info footer */}
      <div className="mt-4 rounded-lg bg-white p-4 shadow">
        <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-slate-600">
          <div>
            <span className="text-slate-500">عضو از: </span>
            <span className="font-medium text-slate-800">{user_info.member_since}</span>
          </div>
          <div>
            <span className="text-slate-500">کل پرس‌وجوها: </span>
            <span className="font-medium text-slate-800">
              {user_info.total_queries.toLocaleString('fa-IR')}
            </span>
          </div>
          <div>
            <span className="text-slate-500">کل بارگذاری‌ها: </span>
            <span className="font-medium text-slate-800">
              {user_info.total_uploads.toLocaleString('fa-IR')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
