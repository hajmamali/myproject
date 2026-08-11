/**
 * Experiment Designer Component
 * Create and configure A/B experiments
 */

import { useState } from 'react';

interface ExperimentConfig {
  name: string;
  description: string;
  variant_a_name: string;
  variant_a_config: string;
  variant_b_name: string;
  variant_b_config: string;
  traffic_split: number;
  duration_days: number;
  success_metric: string;
  min_sample_size: number;
  statistical_significance: number;
}

export default function ExperimentDesigner() {
  const [config, setConfig] = useState<ExperimentConfig>({
    name: '',
    description: '',
    variant_a_name: 'Control',
    variant_a_config: '',
    variant_b_name: 'Treatment',
    variant_b_config: '',
    traffic_split: 50,
    duration_days: 7,
    success_metric: 'conversion_rate',
    min_sample_size: 1000,
    statistical_significance: 0.95,
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!config.name || !config.variant_a_config || !config.variant_b_config) {
      setError('لطفاً تمام فیلدهای ضروری را پر کنید');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/experiments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!response.ok) throw new Error('Failed to create experiment');
      
      const data = await response.json();
      window.location.href = `/app/studio/experiments/${data.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSaving(false);
    }
  };

  const calculateEstimatedSampleSize = () => {
    const dailyTraffic = 1000; // Estimated daily traffic
    const totalTraffic = dailyTraffic * config.duration_days;
    const variantTraffic = totalTraffic * (config.traffic_split / 100);
    
    return Math.max(config.min_sample_size, variantTraffic);
  };

  return (
    <div className="p-8 bg-slate-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">طراحی آزمایش جدید</h1>
          <p className="text-slate-400">ایجاد و پیکربندی آزمایش A/B</p>
        </div>

        {/* Form */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 space-y-6">
          {/* Basic Info */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">اطلاعات پایه</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  نام آزمایش *
                </label>
                <input
                  type="text"
                  value={config.name}
                  onChange={(e) => setConfig({ ...config, name: e.target.value })}
                  placeholder="مثال: بهبود نرخ تبدیل صفحه جستجو"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white placeholder-slate-400"
                />
              </div>
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  توضیحات
                </label>
                <textarea
                  value={config.description}
                  onChange={(e) => setConfig({ ...config, description: e.target.value })}
                  placeholder="توضیح هدف و فرضیه آزمایش..."
                  rows={3}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white placeholder-slate-400"
                />
              </div>
            </div>
          </div>

          {/* Variants */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">تنظیمات واریانت‌ها</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Variant A */}
              <div className="bg-slate-900/50 rounded-lg p-4">
                <h3 className="text-blue-400 font-medium mb-4">Variant A (Control)</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-slate-300 text-sm font-medium mb-2">
                      نام
                    </label>
                    <input
                      type="text"
                      value={config.variant_a_name}
                      onChange={(e) => setConfig({ ...config, variant_a_name: e.target.value })}
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 text-sm font-medium mb-2">
                      پیکربندی (JSON) *
                    </label>
                    <textarea
                      value={config.variant_a_config}
                      onChange={(e) => setConfig({ ...config, variant_a_config: e.target.value })}
                      placeholder='{"model": "gpt-4", "temperature": 0.7}'
                      rows={5}
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white font-mono text-sm placeholder-slate-400"
                    />
                  </div>
                </div>
              </div>

              {/* Variant B */}
              <div className="bg-slate-900/50 rounded-lg p-4">
                <h3 className="text-green-400 font-medium mb-4">Variant B (Treatment)</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-slate-300 text-sm font-medium mb-2">
                      نام
                    </label>
                    <input
                      type="text"
                      value={config.variant_b_name}
                      onChange={(e) => setConfig({ ...config, variant_b_name: e.target.value })}
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 text-sm font-medium mb-2">
                      پیکربندی (JSON) *
                    </label>
                    <textarea
                      value={config.variant_b_config}
                      onChange={(e) => setConfig({ ...config, variant_b_config: e.target.value })}
                      placeholder='{"model": "gpt-4-turbo", "temperature": 0.5}'
                      rows={5}
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white font-mono text-sm placeholder-slate-400"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Traffic & Duration */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">ترافیک و مدت زمان</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  تقسیم ترافیک برای Variant B: {config.traffic_split}%
                </label>
                <input
                  type="range"
                  min="1"
                  max="99"
                  value={config.traffic_split}
                  onChange={(e) => setConfig({ ...config, traffic_split: Number(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>Variant A: {100 - config.traffic_split}%</span>
                  <span>Variant B: {config.traffic_split}%</span>
                </div>
              </div>
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  مدت زمان (روز)
                </label>
                <input
                  type="number"
                  min="1"
                  max="90"
                  value={config.duration_days}
                  onChange={(e) => setConfig({ ...config, duration_days: Number(e.target.value) })}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
                />
              </div>
            </div>
          </div>

          {/* Success Metrics */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">معیارهای موفقیت</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  معیار موفقیت
                </label>
                <select
                  value={config.success_metric}
                  onChange={(e) => setConfig({ ...config, success_metric: e.target.value })}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
                >
                  <option value="conversion_rate">نرخ تبدیل</option>
                  <option value="click_through_rate">نرخ کلیک</option>
                  <option value="engagement_time">زمان تعامل</option>
                  <option value="satisfaction_score">امتیاز رضایت</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  حداقل نمونه
                </label>
                <input
                  type="number"
                  min="100"
                  value={config.min_sample_size}
                  onChange={(e) => setConfig({ ...config, min_sample_size: Number(e.target.value) })}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  اهمیت آماری
                </label>
                <select
                  value={config.statistical_significance}
                  onChange={(e) => setConfig({ ...config, statistical_significance: Number(e.target.value) })}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white"
                >
                  <option value={0.90}>90%</option>
                  <option value={0.95}>95%</option>
                  <option value={0.99}>99%</option>
                </select>
              </div>
            </div>
          </div>

          {/* Estimated Stats */}
          <div className="bg-slate-900/50 rounded-lg p-4">
            <h3 className="text-white font-medium mb-3">برآورد آماری</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-slate-400">مدت زمان</div>
                <div className="text-white">{config.duration_days} روز</div>
              </div>
              <div>
                <div className="text-slate-400">نمونه برآوردی</div>
                <div className="text-white">{calculateEstimatedSampleSize().toLocaleString('fa-IR')}</div>
              </div>
              <div>
                <div className="text-slate-400">اهمیت آماری</div>
                <div className="text-white">{(config.statistical_significance * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div className="text-slate-400">معیار موفقیت</div>
                <div className="text-white">{config.success_metric}</div>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
              <p className="font-medium">خطا</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-600 text-white font-medium py-3 rounded-lg transition-colors"
            >
              {saving ? 'در حال ذخیره...' : 'شروع آزمایش'}
            </button>
            <button
              onClick={() => window.location.href = '/app/studio/experiments'}
              className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg transition-colors"
            >
              انصراف
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
