/**
 * Timeline Visualization Component
 *
 * Generates a timeline report based on a query and optional date range.
 * Uses the /api/v1/mahoun/generate-timeline-report endpoint.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';

interface TimelineReportRequest {
  query?: string;
  documents?: string[]; // list of document IDs
  date_range?: Record<string, any>; // { from: string, to: string } etc.
}

interface ReportResponse {
  success: boolean;
  report_id: string;
  report_type: string;
  content: string;
  markdown: string;
  download_url?: string;
  processing_time_ms: number;
}

function parseJSON<T>(str: string, fallback: T): T {
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
}

export default function TimelineVisualization() {
  const [request, setRequest] = useState<TimelineReportRequest>({
    query: 'Timeline of key events in the legal case',
    documents: ['doc-1', 'doc-2'], // example
    date_range: { from: '2024-01-01', to: '2024-12-31' }
  });

  const [response, setResponse] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setRequest(prev => {
      if (name === 'documents' || name === 'date_range') {
        return { ...prev, [name]: parseJSON(value, prev[name] ?? (name === 'documents' ? [] : {})) };
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
      const data = await apiClient.post<ReportResponse>('/api/v1/mahoun/generate-timeline-report', request);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'تولید گزارش خطی ناموفق بود');
    } finally {
      setLoading(false);
    }
  }, [request]);

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white">تصویرسازی خط زمانی</h1>
          <p className="mt-2 text-slate-400">تولید گزارش خطی بر اساس پرس‌وجو و بازه زمانی</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-800 rounded-xl shadow-xl border border-slate-700 p-6">
          <div className="space-y-4">
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
              <label className="block text-sm font-medium text-slate-300 mb-1">Document IDs (JSON array)</label>
              <textarea
                name="documents"
                value={JSON.stringify(request.documents ?? [], null, 2)}
                onChange={handleChange}
                rows={4}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono resize-y"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Date Range (JSON)</label>
              <textarea
                name="date_range"
                value={JSON.stringify(request.date_range ?? {}, null, 2)}
                onChange={handleChange}
                rows={4}
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
                    در حال تولید...
                  </>
                ) : (
                  'تولید گزارش خطی'
                )}
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-900/20 border border-red-800 rounded-lg text-red-400">
            <p className="font-medium">خطا</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}

        {response && (
          <div className="mt-6">
            <h2 className="mb-4 text-xl font-bold text-white">نتایج گزارش خطی</h2>
            <div className="space-y-4">
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">شماره گزارش</h3>
                <p className="font-mono text-slate-300">{response.report_id}</p>
              </div>

              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">نوع گزارش</h3>
                <p className="text-slate-300">{response.report_type}</p>
              </div>

              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">زمان پردازش</h3>
                <p className="text-2xl font-bold text-slate-900">{response.processing_time_ms.toFixed(0)} ms</p>
              </div>

              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h3 className="text-lg font-semibold text-slate-200 mb-2">محتوى (Markdown)</h3>
                <div className="prose prose-slate max-w-none">
                  {/* We'll render the markdown as HTML for simplicity; in a real app you might use a markdown parser */}
                  <div dangerouslySetInnerHTML={{ __marked: response.markdown }}></div>
                  {/* Since we don't have a markdown parser installed, we'll fallback to showing raw markdown in a pre tag for now */}
                  {/* In production, you'd want to use a library like remark or marked to convert markdown to HTML */}
                  <pre className="mt-4 text-xs text-slate-300 bg-slate-900/50 p-3 rounded overflow-auto whitespace-pre-wrap">{response.markdown}</pre>
                </div>
              </div>

              {response.download_url && (
                <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 text-center">
                  <a
                    href={response.download_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    دانلود گزارش
                  </a>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
