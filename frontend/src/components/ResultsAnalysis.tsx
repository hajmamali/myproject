/**
 * Results Analysis Component
 * Analyze A/B test results with statistical significance
 */

import { useState, useEffect } from 'react';

interface ExperimentResult {
  id: string;
  name: string;
  status: string;
  variant_a: string;
  variant_b: string;
  metrics: {
    impressions_a: number;
    impressions_b: number;
    conversions_a: number;
    conversions_b: number;
    conversion_rate_a: number;
    conversion_rate_b: number;
    lift: number;
    confidence_interval: [number, number];
    p_value: number;
    statistical_significance: boolean;
    winner?: 'A' | 'B' | 'inconclusive';
    power: number;
  };
  segments: {
    name: string;
    conversion_rate_a: number;
    conversion_rate_b: number;
    lift: number;
    significant: boolean;
  }[];
}

export default function ResultsAnalysis({ experimentId }: { experimentId: string }) {
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchResults();
  }, [experimentId]);

  const fetchResults = async () => {
    try {
      const response = await fetch(`/api/v1/experiments/${experimentId}/results`);
      if (!response.ok) throw new Error('Failed to fetch results');
      const data = await response.json();
      setResult(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getWinnerColor = (winner?: string) => {
    switch (winner) {
      case 'A': return 'text-blue-500';
      case 'B': return 'text-green-500';
      case 'inconclusive': return 'text-yellow-500';
      default: return 'text-slate-400';
    }
  };

  const getSignificanceColor = (significant: boolean) => {
    return significant ? 'text-green-400' : 'text-yellow-400';
  };

  const formatPercentage = (value: number) => {
    return (value * 100).toFixed(2) + '%';
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">تحلیل نتایج</h1>
          <p className="text-slate-400">تحلیل آماری نتایج آزمایش A/B</p>
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
        ) : result ? (
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">{result.name}</h2>
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    result.status === 'completed' ? 'bg-green-100 text-green-800' :
                    result.status === 'running' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {result.status}
                  </span>
                  {result.metrics.winner && (
                    <span className={`text-sm font-medium ${getWinnerColor(result.metrics.winner)}`}>
                      برنده: {result.metrics.winner}
                    </span>
                  )}
                </div>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 text-sm mb-1">Lift</div>
                  <div className={`text-2xl font-bold ${result.metrics.lift > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {result.metrics.lift > 0 ? '+' : ''}{formatPercentage(result.metrics.lift)}
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 text-sm mb-1">P-Value</div>
                  <div className="text-2xl font-bold text-white">
                    {result.metrics.p_value.toFixed(4)}
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 text-sm mb-1">Significance</div>
                  <div className={`text-2xl font-bold ${getSignificanceColor(result.metrics.statistical_significance)}`}>
                    {result.metrics.statistical_significance ? '✓' : '✗'}
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 text-sm mb-1">Power</div>
                  <div className="text-2xl font-bold text-white">
                    {formatPercentage(result.metrics.power)}
                  </div>
                </div>
              </div>
            </div>

            {/* Conversion Rates Comparison */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">مقایسه نرخ تبدیل</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Variant A */}
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-blue-400 font-medium">{result.variant_a}</span>
                    <span className="text-slate-400 text-sm">{result.metrics.impressions_a.toLocaleString('fa-IR')} impressions</span>
                  </div>
                  <div className="text-3xl font-bold text-white mb-2">
                    {formatPercentage(result.metrics.conversion_rate_a)}
                  </div>
                  <div className="text-slate-400 text-sm">
                    {result.metrics.conversions_a.toLocaleString('fa-IR')} conversions
                  </div>
                </div>

                {/* Variant B */}
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-green-400 font-medium">{result.variant_b}</span>
                    <span className="text-slate-400 text-sm">{result.metrics.impressions_b.toLocaleString('fa-IR')} impressions</span>
                  </div>
                  <div className="text-3xl font-bold text-white mb-2">
                    {formatPercentage(result.metrics.conversion_rate_b)}
                  </div>
                  <div className="text-slate-400 text-sm">
                    {result.metrics.conversions_b.toLocaleString('fa-IR')} conversions
                  </div>
                </div>
              </div>

              {/* Confidence Interval */}
              <div className="mt-6">
                <h3 className="text-white font-medium mb-3">فاصله اطمینان (95%)</h3>
                <div className="bg-slate-900 rounded-lg p-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Lower Bound:</span>
                    <span className="text-white">{formatPercentage(result.metrics.confidence_interval[0])}</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2 my-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{
                        width: `${Math.abs(result.metrics.confidence_interval[1] - result.metrics.confidence_interval[0]) * 100}%`,
                        marginLeft: `${result.metrics.confidence_interval[0] * 100}%`
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Upper Bound:</span>
                    <span className="text-white">{formatPercentage(result.metrics.confidence_interval[1])}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Segment Analysis */}
            {result.segments.length > 0 && (
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 className="text-xl font-semibold text-white mb-4">تحلیل سگمنت</h2>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-900/50">
                      <tr>
                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase">
                          سگمنت
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase">
                          Rate A
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase">
                          Rate B
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase">
                          Lift
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase">
                          Significant
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700">
                      {result.segments.map((segment, index) => (
                        <tr key={index} className="hover:bg-slate-700/50">
                          <td className="px-4 py-3 text-white">{segment.name}</td>
                          <td className="px-4 py-3 text-slate-300">{formatPercentage(segment.conversion_rate_a)}</td>
                          <td className="px-4 py-3 text-slate-300">{formatPercentage(segment.conversion_rate_b)}</td>
                          <td className={`px-4 py-3 ${segment.lift > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {segment.lift > 0 ? '+' : ''}{formatPercentage(segment.lift)}
                          </td>
                          <td className={`px-4 py-3 ${getSignificanceColor(segment.significant)}`}>
                            {segment.significant ? '✓' : '✗'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Statistical Summary */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">خلاصه آماری</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 mb-1">فرضیه صفر (H₀)</div>
                  <div className="text-white">هیچ تفاوتی بین واریانت‌ها وجود ندارد</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 mb-1">فرضیه جایگزین (H₁)</div>
                  <div className="text-white">تفاوت معناداری بین واریانت‌ها وجود دارد</div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 mb-1">نتیجه آزمون</div>
                  <div className={`text-white ${getSignificanceColor(result.metrics.statistical_significance)}`}>
                    {result.metrics.statistical_significance ? 'رد H₀' : 'ناتوانی در رد H₀'}
                  </div>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-slate-400 mb-1">قدرت آزمون</div>
                  <div className="text-white">{formatPercentage(result.metrics.power)}</div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-4">
              <button
                onClick={fetchResults}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                بروزرسانی
              </button>
              <button
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                دانلود گزارش
              </button>
              <button
                onClick={() => window.location.href = '/app/studio/experiments'}
                className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
              >
                بازگشت به لیست
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
