/**
 * Delay Analysis Dashboard Component
 *
 * Allows users to analyze project delays by comparing baseline and actual schedules.
 * Uses the /api/v1/mahoun/analyze-delay endpoint.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';

interface DelayAnalysisRequest {
  project_id: string;
  query?: string;
  baseline_schedule?: Record<string, any>;
  actual_schedule?: Record<string, any>;
}

interface DelayAnalysisResponse {
  success: boolean;
  project_id: string;
  delays: Record<string, any>[];
  delay_analysis: Record<string, any>;
  critical_path: Record<string, any>[];
  attribution: Record<string, any>;
  processing_time_ms: number;
}

function parseJSON<T>(str: string, fallback: T): T {
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
}

export default function DelayAnalysisDashboard() {
  const [request, setRequest] = useState<DelayAnalysisRequest>({
    project_id: 'proj-123',
    query: 'Analyze delays in construction project',
    baseline_schedule: {
      tasks: [
        { id: 'A', name: 'Design', duration: 5, start: '2024-01-01', end: '2024-01-05' },
        { id: 'B', name: 'Foundation', duration: 10, start: '2024-01-06', end: '2024-01-15', dependsOn: ['A'] },
        { id: 'C', name: 'Framing', duration: 15, start: '2024-01-16', end: '2024-01-30', dependsOn: ['B'] },
      ]
    },
    actual_schedule: {
      tasks: [
        { id: 'A', name: 'Design', duration: 7, start: '2024-01-01', end: '2024-01-07' },
        { id: 'B', name: 'Foundation', duration: 12, start: '2024-01-08', end: '2024-01-19', dependsOn: ['A'] },
        { id: 'C', name: 'Framing', duration: 20, start: '2024-01-20', end: '2024-02-08', dependsOn: ['B'] },
      ]
    }
  });

  const [response, setResponse] = useState<DelayAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setRequest(prev => {
      if (name === 'baseline_schedule' || name === 'actual_schedule') {
        return { ...prev, [name]: parseJSON(value, prev[name] ?? {}) };
      }
      return { ...prev, [name]: value };
    });
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const data = await apiClient.post<DelayAnalysisResponse>('/api/v1/mahoun/analyze-delay', request);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'تحلیل تأخیر ناموفق بود');
    } finally {
      setLoading(false);
    }
  }, [request]);

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white">تحلیل تأخیر</h1>
          <p className="mt-2 text-slate-400">مقایسه برنامه‌ریزی Baseline با برنامه Actual</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-800 rounded-xl shadow-xl border border-slate-700 p-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">شناسه پروژه</label>
              <input
                name="project_id"
                value={request.project_id}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Query (اختیاری)</label>
              <input
                name="query"
                value={request.query ?? ''}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Baseline Schedule (JSON)</label>
              <textarea
                name="baseline_schedule"
                value={JSON.stringify(request.baseline_schedule, null, 2)}
                onChange={handleChange}
                rows={8}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono resize-y"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Actual Schedule (JSON)</label>
              <textarea
                name="actual_schedule"
                value={JSON.stringify(request.actual_schedule, null, 2)}
                onChange={handleChange}
                rows={8}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono resize-y"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium rounded-lg transition-colors"
              >
                {loading ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full" />
                    در حال تحلیل...
                  </>
                ) : (
                  'تحلیل را اجرا کن'
                )}
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
            <p className="font-medium">خطا در تحلیل</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        {response && (
          <div className="mt-6">
            <h2 className="mb-4 text-xl font-bold text-white">نتایج تحلیل</h2>
            <div className="space-y-4">
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">تأخیرها</h3>
                {response.delays.length ? (
                  <ul className="space-y-2">
                    {response.delays.map((delay, idx) => (
                      <li key={idx} className="p-3 bg-slate-900/30 rounded-lg">
                        <pre className="text-xs text-slate-300 whitespace-pre-wrap">{JSON.stringify(delay, null, 2)}</pre>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-slate-400 italic">هیچ تأخیر خاصی یافت نشد.</p>
                )}
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                  <h3 className="text-lg font-semibold text-slate-200 mb-2">تحلیل تأخیر</h3>
                  <pre className="text-xs text-slate-300 whitespace-pre-wrap">{JSON.stringify(response.delay_analysis, null, 2)}</pre>
                </div>
                <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                  <h3 className="text-lg font-semibold text-slate-200 mb-2">مسیر بحرانی</h3>
                  {response.critical_path.length ? (
                    <ol className="list-decimal list-inside text-slate-300">
                      {response.critical_path.map((step, idx) => (
                        <li key={idx}>{JSON.stringify(step)}</li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-slate-400 italic">مسیر بحرانی tanımlanmadı.</p>
                  )}
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">تخصیص原因 (Attribution)</h3>
                <pre className="text-xs text-slate-300 whitespace-pre-wrap">{JSON.stringify(response.attribution, null, 2)}</pre>
              </div>

              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 text-center">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">زمان پردازش</h3>
                <p className="text-2xl font-bold text-slate-900">{response.processing_time_ms.toFixed(0)} ms</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
