/**
 * Fail-Closed Monitor Component
 * Displays fail-closed safety events and recovery actions
 */

import { useState, useEffect } from 'react';

// Types matching backend API
interface FailClosedEvent {
  id: string;
  type: string;
  reason: string;
  impact: string;
  timestamp: string;
  recovered: boolean;
}

export default function FailClosedMonitor() {
  const [events, setEvents] = useState<FailClosedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState(10);

  useEffect(() => {
    fetchFailClosedEvents();
  }, [limit]);

  const fetchFailClosedEvents = async () => {
    try {
      const response = await fetch(`/api/v1/governance/fail-closed/recent?limit=${limit}`);
      if (!response.ok) throw new Error('Failed to fetch fail-closed events');
      const data = await response.json();
      setEvents(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getEventIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'governance_violation':
        return '🛡️';
      case 'validation_failure':
        return '❌';
      case 'timeout':
        return '⏱️';
      case 'resource_exhaustion':
        return '💾';
      default:
        return '⚠️';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact.toLowerCase()) {
      case 'critical':
        return 'bg-red-900/30 border-red-700 text-red-300';
      case 'high':
        return 'bg-orange-900/30 border-orange-700 text-orange-300';
      case 'medium':
        return 'bg-yellow-900/30 border-yellow-700 text-yellow-300';
      case 'low':
        return 'bg-blue-900/30 border-blue-700 text-blue-300';
      default:
        return 'bg-slate-800 border-slate-700 text-slate-300';
    }
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">نظارت Fail-Closed</h1>
          <p className="text-slate-400">رویدادهای ایمنی fail-closed و اقدامات بازیابی</p>
        </div>

        {/* Limit Selector */}
        <div className="mb-6 flex items-center gap-4">
          <label className="text-slate-300 text-sm">تعداد رویدادها:</label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm"
          >
            <option value={5}>۵ مورد</option>
            <option value={10}>۱۰ مورد</option>
            <option value={25}>۲۵ مورد</option>
            <option value={50}>۵۰ مورد</option>
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
        ) : events.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 border border-slate-700 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h3 className="text-xl font-semibold text-white mb-2">هیچ رویداد fail-closed ثبت نشده</h3>
            <p className="text-slate-400">سیستم در حالت عادی و ایمن عمل می‌کند</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">کل رویدادها</div>
                <div className="text-2xl font-bold text-white">{events.length}</div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">بازیابی شده</div>
                <div className="text-2xl font-bold text-green-500">
                  {events.filter(e => e.recovered).length}
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">در انتظار بازیابی</div>
                <div className="text-2xl font-bold text-yellow-500">
                  {events.filter(e => !e.recovered).length}
                </div>
              </div>
            </div>

            {/* Events List */}
            <div className="space-y-3">
              {events.map((event) => (
                <div
                  key={event.id}
                  className={`p-4 rounded-lg border ${getImpactColor(event.impact)}`}
                >
                  <div className="flex items-start gap-4">
                    <div className="text-2xl">{getEventIcon(event.type)}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{event.type}</span>
                          {event.recovered ? (
                            <span className="px-2 py-0.5 bg-green-900/50 text-green-300 text-xs rounded-full">
                              بازیابی شده
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-yellow-900/50 text-yellow-300 text-xs rounded-full">
                              در انتظار
                            </span>
                          )}
                        </div>
                        <span className="text-xs opacity-70">
                          {new Date(event.timestamp).toLocaleString('fa-IR')}
                        </span>
                      </div>
                      <p className="mb-2">{event.reason}</p>
                      <div className="text-sm opacity-80">
                        <span className="font-medium">تأثیر:</span> {event.impact}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
