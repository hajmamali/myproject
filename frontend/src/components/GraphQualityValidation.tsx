/**
 * Graph Quality Validation Component
 * Validates knowledge graph quality, integrity, and completeness
 */

import { useState, useEffect } from 'react';

interface QualityMetric {
  name: string;
  value: number;
  threshold: number;
  status: 'pass' | 'fail' | 'warning';
}

interface IntegrityIssue {
  id: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  affected_nodes: string[];
  affected_edges: string[];
}

interface CompletenessReport {
  overall_score: number;
  node_coverage: number;
  edge_coverage: number;
  property_coverage: number;
  missing_nodes: string[];
  missing_edges: string[];
  missing_properties: Record<string, string[]>;
}

export default function GraphQualityValidation() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [qualityMetrics, setQualityMetrics] = useState<QualityMetric[]>([]);
  const [integrityIssues, setIntegrityIssues] = useState<IntegrityIssue[]>([]);
  const [completenessReport, setCompletenessReport] = useState<CompletenessReport | null>(null);

  useEffect(() => {
    fetchQualityData();
  }, []);

  const fetchQualityData = async () => {
    try {
      // Fetch quality metrics
      const qualityResponse = await fetch('/api/v1/graph/quality/metrics');
      if (qualityResponse.ok) {
        const qualityData = await qualityResponse.json();
        setQualityMetrics(qualityData.metrics || []);
      }

      // Fetch integrity issues
      const integrityResponse = await fetch('/api/v1/graph/integrity/issues');
      if (integrityResponse.ok) {
        const integrityData = await integrityResponse.json();
        setIntegrityIssues(integrityData.issues || []);
      }

      // Fetch completeness report
      const completenessResponse = await fetch('/api/v1/graph/completeness/report');
      if (completenessResponse.ok) {
        const completenessData = await completenessResponse.json();
        setCompletenessReport(completenessData);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return 'bg-green-100 text-green-800 border-green-200';
      case 'fail': return 'bg-red-100 text-red-800 border-red-200';
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-900/30 border-red-700 text-red-300';
      case 'high': return 'bg-orange-900/30 border-orange-700 text-orange-300';
      case 'medium': return 'bg-yellow-900/30 border-yellow-700 text-yellow-300';
      case 'low': return 'bg-blue-900/30 border-blue-700 text-blue-300';
      default: return 'bg-slate-800 border-slate-700 text-slate-300';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 70) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">اعتبارسنجی کیفیت گراف</h1>
          <p className="text-slate-400">بررسی کیفیت، یکپارچگی و کامل بودن گراف دانش</p>
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
        ) : (
          <div className="space-y-6">
            {/* Quality Metrics */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <h2 className="text-xl font-semibold text-white mb-4">معیارهای کیفیت</h2>
              <div className="space-y-3">
                {qualityMetrics.map((metric) => (
                  <div key={metric.name} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                    <div className="flex-1">
                      <div className="text-white font-medium">{metric.name}</div>
                      <div className="text-slate-400 text-sm">آستانه: {metric.threshold}</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className={`text-2xl font-bold ${getScoreColor(metric.value)}`}>
                          {metric.value.toFixed(1)}%
                        </div>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(metric.status)}`}>
                        {metric.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Completeness Report */}
            {completenessReport && (
              <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h2 className="text-xl font-semibold text-white mb-4">گزارش کامل بودن</h2>
                
                {/* Overall Score */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-slate-300">امتیاز کلی</span>
                    <span className={`text-3xl font-bold ${getScoreColor(completenessReport.overall_score)}`}>
                      {completenessReport.overall_score.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all ${
                        completenessReport.overall_score >= 90 ? 'bg-green-500' :
                        completenessReport.overall_score >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${completenessReport.overall_score}%` }}
                    />
                  </div>
                </div>

                {/* Coverage Breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-slate-400 text-sm mb-1">پوشش گره‌ها</div>
                    <div className={`text-2xl font-bold ${getScoreColor(completenessReport.node_coverage)}`}>
                      {completenessReport.node_coverage.toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-slate-400 text-sm mb-1">پوشش یال‌ها</div>
                    <div className={`text-2xl font-bold ${getScoreColor(completenessReport.edge_coverage)}`}>
                      {completenessReport.edge_coverage.toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <div className="text-slate-400 text-sm mb-1">پوشش ویژگی‌ها</div>
                    <div className={`text-2xl font-bold ${getScoreColor(completenessReport.property_coverage)}`}>
                      {completenessReport.property_coverage.toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Missing Items */}
                <div className="space-y-4">
                  {completenessReport.missing_nodes.length > 0 && (
                    <div>
                      <h3 className="text-white font-medium mb-2">گره‌های گمشده</h3>
                      <div className="bg-slate-900 rounded-lg p-3">
                        <div className="text-slate-400 text-sm space-y-1">
                          {completenessReport.missing_nodes.map((node, index) => (
                            <div key={index} className="font-mono">{node}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {completenessReport.missing_edges.length > 0 && (
                    <div>
                      <h3 className="text-white font-medium mb-2">یال‌های گمشده</h33>
                      <div className="bg-slate-900 rounded-lg p-3">
                        <div className="text-slate-400 text-sm space-y-1">
                          {completenessReport.missing_edges.map((edge, index) => (
                            <div key={index} className="font-mono">{edge}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {Object.keys(completenessReport.missing_properties).length > 0 && (
                    <div>
                      <h3 className="text-white font-medium mb-2">ویژگی‌های گمشده</h3>
                      <div className="bg-slate-900 rounded-lg p-3">
                        {Object.entries(completenessReport.missing_properties).map(([node, props]) => (
                          <div key={node} className="mb-2">
                            <div className="text-slate-300 text-sm font-medium mb-1">{node}</div>
                            <div className="text-slate-400 text-xs space-y-1">
                              {props.map((prop, index) => (
                                <div key={index} className="font-mono">{prop}</div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Integrity Issues */}
            <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white">مسائل یکپارچگی</h2>
                <span className="text-slate-400 text-sm">{integrityIssues.length} مورد</span>
              </div>

              {integrityIssues.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <p className="text-green-400 font-medium">✓ هیچ مسئله‌ای یافت نشد</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {integrityIssues.map((issue) => (
                    <div
                      key={issue.id}
                      className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium uppercase">{issue.type}</span>
                            <span className="text-xs opacity-70">{issue.severity}</span>
                          </div>
                          <p className="font-medium">{issue.description}</p>
                        </div>
                      </div>
                      
                      {(issue.affected_nodes.length > 0 || issue.affected_edges.length > 0) && (
                        <div className="mt-3 text-sm">
                          {issue.affected_nodes.length > 0 && (
                            <div className="mb-1">
                              <span className="opacity-70">گره‌ها: </span>
                              <span className="font-mono">{issue.affected_nodes.join(', ')}</span>
                            </div>
                          )}
                          {issue.affected_edges.length > 0 && (
                            <div>
                              <span className="opacity-70">یال‌ها: </span>
                              <span className="font-mono">{issue.affected_edges.join(', ')}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-4">
              <button
                onClick={fetchQualityData}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                بروزرسانی
              </button>
              <button
                className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                دانلود گزارش
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
