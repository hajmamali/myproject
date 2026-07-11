/**
 * Delay Analysis Dashboard
 * 
 * Advanced dashboard for delay analysis with:
 * - Timeline visualization
 * - Delay statistics
 * - Attribution charts
 * - Critical path display
 * - Report generation
 */

import { useState } from "react";
import { 
  ChartBarIcon, 
  ClockIcon,
  DocumentArrowDownIcon,
  PlayIcon
} from "@heroicons/react/24/outline";
import { analyzeDelay, generateDelayReport, DelayAnalysisResponse } from "../api/mahounClient";
import { toast } from "./Toast";

export default function DelayAnalysisDashboard() {
  const [projectId, setProjectId] = useState("");
  const [query, setQuery] = useState("");
  const [analysis, setAnalysis] = useState<DelayAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);

  const handleAnalyze = async () => {
    if (!projectId) return;

    setLoading(true);
    try {
      const result = await analyzeDelay({
        project_id: projectId,
        query: query || undefined,
      });
      setAnalysis(result);
      toast.success("تحلیل تأخیرات با موفقیت انجام شد");
    } catch (error: any) {
      toast.error(`خطا در تحلیل: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!analysis) return;

    setGeneratingReport(true);
    try {
      const report = await generateDelayReport({
        project_id: projectId,
        query: query || undefined,
      });
      
      // Download report
      const blob = new Blob([report.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `delay_report_${projectId}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("گزارش با موفقیت تولید و دانلود شد");
    } catch (error: any) {
      toast.error(`خطا در تولید گزارش: ${error.message}`);
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 page-enter">
      <div className="bg-slate-900 rounded-xl shadow-lg border border-slate-700 p-8">
        <h2 className="text-2xl font-bold text-slate-100 mb-6">تحلیل تأخیرات پروژه</h2>

        {/* Input Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              شناسه پروژه
            </label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="مثال: project_001"
              className="w-full px-4 py-2 border border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              سؤال یا موضوع (اختیاری)
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="مثال: تحلیل تأخیرات فاز اول"
              className="w-full px-4 py-2 border border-slate-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || !projectId}
          className="w-full md:w-auto px-6 py-3 bg-primary-700 text-white rounded-lg hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              در حال تحلیل...
            </>
          ) : (
            <>
              <PlayIcon className="h-5 w-5" />
              شروع تحلیل
            </>
          )}
        </button>

        {/* Analysis Results */}
        {analysis && (
          <div className="mt-8 space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-primary-50 rounded-lg p-4 border border-primary-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-primary-700">تعداد تأخیرات</p>
                    <p className="text-2xl font-bold text-primary-900">
                      {analysis.delay_analysis.total_delays}
                    </p>
                  </div>
                  <ClockIcon className="h-8 w-8 text-primary-600" />
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-400">مجموع روزهای تأخیر</p>
                    <p className="text-2xl font-bold text-slate-100">
                      {analysis.delay_analysis.total_delay_days}
                    </p>
                  </div>
                  <ChartBarIcon className="h-8 w-8 text-slate-400" />
                </div>
              </div>
              <div className="bg-accent-50 rounded-lg p-4 border border-accent-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-accent-700">میانگین تأخیر</p>
                    <p className="text-2xl font-bold text-accent-900">
                      {analysis.delay_analysis.average_delay.toFixed(1)} روز
                    </p>
                  </div>
                  <ChartBarIcon className="h-8 w-8 text-accent-600" />
                </div>
              </div>
            </div>

            {/* Attribution Table */}
            {Object.keys(analysis.attribution).length > 0 && (
              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-slate-100 mb-4">مسئولیت‌ها</h3>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-600">
                        <th className="text-right py-2 px-4 text-sm font-semibold text-slate-300">
                          طرف
                        </th>
                        <th className="text-right py-2 px-4 text-sm font-semibold text-slate-300">
                          تعداد تأخیر
                        </th>
                        <th className="text-right py-2 px-4 text-sm font-semibold text-slate-300">
                          مجموع روزها
                        </th>
                        <th className="text-right py-2 px-4 text-sm font-semibold text-slate-300">
                          میانگین
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(analysis.attribution).map(([party, data]: [string, any]) => (
                        <tr key={party} className="border-b border-slate-700">
                          <td className="py-3 px-4 text-sm text-slate-100">{party}</td>
                          <td className="py-3 px-4 text-sm text-slate-300">
                            {data.delay_count || 0}
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-300">
                            {data.total_delay_days || 0} روز
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-300">
                            {data.average_delay_days?.toFixed(1) || 0} روز
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Critical Path */}
            {analysis.critical_path.length > 0 && (
              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-slate-100 mb-4">مسیر بحرانی</h3>
                <div className="space-y-2">
                  {analysis.critical_path.map((item, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 p-3 bg-slate-900 rounded-lg border border-slate-700"
                    >
                      <span className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-800 rounded-full flex items-center justify-center text-sm font-semibold">
                        {item.sequence}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm text-slate-100">{item.event}</p>
                        <p className="text-xs text-slate-500">{item.date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Report Generation */}
            <div className="flex justify-end">
              <button
                onClick={handleGenerateReport}
                disabled={generatingReport}
                className="px-6 py-3 bg-primary-700 text-white rounded-lg hover:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {generatingReport ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    در حال تولید...
                  </>
                ) : (
                  <>
                    <DocumentArrowDownIcon className="h-5 w-5" />
                    تولید گزارش PDF
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
