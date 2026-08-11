/**
 * Dataset Browser Component
 * Browse and manage training datasets
 */

import { useState, useEffect } from 'react';

interface Dataset {
  dataset_id: string;
  name: string;
  source: 'feedback' | 'upload' | 'existing';
  size: number;
  created_at: string;
  avg_quality_score?: number;
  total_examples?: number;
}

export default function DatasetBrowser() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'feedback' | 'upload' | 'existing'>('all');

  useEffect(() => {
    fetchDatasets();
  }, []);

  const fetchDatasets = async () => {
    try {
      const response = await fetch('/api/v1/training-datasets/stats');
      if (!response.ok) throw new Error('Failed to fetch datasets');
      const data = await response.json();
      
      // Combine datasets from different sources
      const allDatasets: Dataset[] = [];
      
      // From training datasets API
      if (data.datasets) {
        allDatasets.push(...data.datasets);
      }
      
      // From finetuning API
      try {
        const finetuningResponse = await fetch('/api/v1/finetuning/datasets');
        if (finetuningResponse.ok) {
          const finetuningData = await finetuningResponse.json();
          if (finetuningData.datasets) {
            allDatasets.push(...finetuningData.datasets);
          }
        }
      } catch (e) {
        console.warn('Failed to fetch finetuning datasets:', e);
      }
      
      setDatasets(allDatasets);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const filteredDatasets = datasets.filter(d => 
    filter === 'all' || d.source === filter
  );

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'feedback': return 'bg-purple-100 text-purple-800';
      case 'upload': return 'bg-blue-100 text-blue-800';
      case 'existing': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'feedback': return 'فیدبک کاربران';
      case 'upload': return 'بارگذاری';
      case 'existing': return 'موجود';
      default: return source;
    }
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">مرورگر دیتاست‌ها</h1>
          <p className="text-slate-400">مشاهده و مدیریت دیتاست‌های آموزشی</p>
        </div>

        {/* Filter */}
        <div className="mb-6 flex items-center gap-4">
          <label className="text-slate-300 text-sm">فیلتر منبع:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm"
          >
            <option value="all">همه</option>
            <option value="feedback">فیدبک کاربران</option>
            <option value="upload">بارگذاری</option>
            <option value="existing">موجود</option>
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
        ) : filteredDatasets.length === 0 ? (
          <div className="bg-slate-800 rounded-lg p-8 border border-slate-700 text-center">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-white mb-2">هیچ دیتاستی یافت نشد</h3>
            <p className="text-slate-400 mb-4">برای شروع، یک دیتاست جدید بسازید</p>
            <button
              onClick={() => window.location.href = '/app/studio/datasets/upload'}
              className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
            >
              ساخت دیتاست جدید
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">کل دیتاست‌ها</div>
                <div className="text-2xl font-bold text-white">{datasets.length}</div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">فیدبک</div>
                <div className="text-2xl font-bold text-purple-400">
                  {datasets.filter(d => d.source === 'feedback').length}
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">بارگذاری</div>
                <div className="text-2xl font-bold text-blue-400">
                  {datasets.filter(d => d.source === 'upload').length}
                </div>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <div className="text-slate-400 text-sm mb-1">موجود</div>
                <div className="text-2xl font-bold text-green-400">
                  {datasets.filter(d => d.source === 'existing').length}
                </div>
              </div>
            </div>

            {/* Dataset List */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-900/50">
                  <tr>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      نام
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      منبع
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      اندازه
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      کیفیت
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      تاریخ
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      عملیات
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {filteredDatasets.map((dataset) => (
                    <tr key={dataset.dataset_id} className="hover:bg-slate-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-white">{dataset.name}</div>
                        <div className="text-xs text-slate-400 font-mono">{dataset.dataset_id}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${getSourceColor(dataset.source)}`}>
                          {getSourceLabel(dataset.source)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                        {dataset.total_examples ? dataset.total_examples.toLocaleString('fa-IR') + ' مثال' : dataset.size.toLocaleString('fa-IR')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {dataset.avg_quality_score !== undefined ? (
                          <span className={`font-medium ${
                            dataset.avg_quality_score >= 0.8 ? 'text-green-400' :
                            dataset.avg_quality_score >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {(dataset.avg_quality_score * 100).toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                        {new Date(dataset.created_at).toLocaleString('fa-IR')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => window.location.href = `/app/studio/datasets/${dataset.dataset_id}`}
                          className="text-primary-400 hover:text-primary-300"
                        >
                          مشاهده
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Upload Button */}
            <div className="flex justify-end">
              <button
                onClick={() => window.location.href = '/app/studio/datasets/upload'}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg transition-colors"
              >
                + ساخت دیتاست جدید
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
