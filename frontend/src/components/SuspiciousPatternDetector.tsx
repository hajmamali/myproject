/**
 * Suspicious Financial Pattern Detector
 * 
 * تشخیص الگوهای مالی مشکوک برای بازپرس جرایم اقتصادی
 */
import React, { useState, useEffect } from 'react';
import {
  AlertTriangleIcon,
  ExclamationTriangleIcon,
  BanknotesIcon,
  ArrowRightIcon,
  ClockIcon,
  BuildingOfficeIcon,
} from '@heroicons/react/24/outline';

interface SuspiciousPattern {
  id: string;
  type: 'smurfing' | 'structuring' | 'round_tripping' | 'layering' | 'shell_company' | 'timing_anomaly';
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  description: string;
  evidence: string[];
  affectedTransactions: number;
  totalAmount: number;
  timeframe: string;
  recommendation: string;
}

const patternTypes = {
  smurfing: { name: 'تراکنش‌های خرد (Smurfing)', icon: BanknotesIcon, color: 'text-red-500' },
  structuring: { name: 'تقسیم مبالغ (Structuring)', icon: ArrowRightIcon, color: 'text-orange-500' },
  round_tripping: { name: 'چرخش وجه (Round-tripping)', icon: ArrowRightIcon, color: 'text-amber-500' },
  layering: { name: 'لایه‌بندی (Layering)', icon: BuildingOfficeIcon, color: 'text-yellow-500' },
  shell_company: { name: 'شرکت صوری', icon: BuildingOfficeIcon, color: 'text-purple-500' },
  timing_anomaly: { name: 'زمان‌بندی غیرعادی', icon: ClockIcon, color: 'text-blue-500' },
};

const samplePatterns: SuspiciousPattern[] = [
  {
    id: 'pat001',
    type: 'smurfing',
    severity: 'critical',
    confidence: 94,
    description: '۲۸ تراکنش زیر ۱۰ میلیون ریال در مدت ۳ روز',
    evidence: [
      'تراکنش‌های ۹.۹ میلیون ریالی متعدد',
      'همه از یک حساب منبع',
      'به حساب‌های مختلف در شعب مختلف',
      'در ساعات پایانی کاری بانک'
    ],
    affectedTransactions: 28,
    totalAmount: 276000000,
    timeframe: '۱۴۰۳/۰۵/۱۵ تا ۱۴۰۳/۰۵/۱۷',
    recommendation: 'بررسی فوری منابع درآمد صاحب حساب و هدف انتقالات'
  },
  {
    id: 'pat002',
    type: 'shell_company',
    severity: 'high',
    confidence: 87,
    description: 'شرکت بدون فعالیت واقعی با تراکنش‌های میلیاردی',
    evidence: [
      'شرکت ثبت شده در ۱۴۰۳/۰۱/۱۵',
      'بدون کارمند یا دفتر فیزیکی',
      '۱۸ میلیارد ریال تراکنش در ۲ ماه',
      'تمام تراکنش‌ها انتقالی (بدون درآمد عملیاتی)'
    ],
    affectedTransactions: 15,
    totalAmount: 18000000000,
    timeframe: '۱۴۰۳/۰۲/۰۱ تا ۱۴۰۳/۰۴/۰۱',
    recommendation: 'تحقیق از محل فعالیت و بررسی اسناد تأسیس'
  },
  {
    id: 'pat003',
    type: 'round_tripping',
    severity: 'medium',
    confidence: 76,
    description: 'چرخش ۵ میلیارد ریال بین ۳ شرکت وابسته',
    evidence: [
      'شرکت A → شرکت B: ۵ میلیارد',
      'شرکت B → شرکت C: ۴.۸ میلیارد',
      'شرکت C → شرکت A: ۴.۶ میلیارد',
      'سهامداران مشترک در هر ۳ شرکت'
    ],
    affectedTransactions: 3,
    totalAmount: 14400000000,
    timeframe: '۱۴۰۳/۰۳/۱۰ تا ۱۴۰۳/۰۳/۲۵',
    recommendation: 'بررسی دلایل واقعی انتقالات و مدارک توجیهی'
  },
  {
    id: 'pat004',
    type: 'timing_anomaly',
    severity: 'medium',
    confidence: 82,
    description: 'تراکنش‌های بزرگ در ساعات غیرعادی',
    evidence: [
      '۱۲ تراکنش بین ساعت ۲۳:۴۵ تا ۰۰:۱۵',
      'همگی بالای ۱ میلیارد ریال',
      'در شب‌های پنج‌شنبه (قبل از تعطیلات)',
      'بدون مجوز اضافه‌کار مدیریت'
    ],
    affectedTransactions: 12,
    totalAmount: 15600000000,
    timeframe: 'پنج‌شنبه‌های ماه گذشته',
    recommendation: 'استعلام از بانک درباره مجوز تراکنش‌های شبانه'
  },
];

export default function SuspiciousPatternDetector() {
  const [patterns, setPatterns] = useState<SuspiciousPattern[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [selectedPattern, setSelectedPattern] = useState<SuspiciousPattern | null>(null);
  const [scanProgress, setScanProgress] = useState(0);

  useEffect(() => {
    // شبیه‌سازی اسکن
    setPatterns(samplePatterns);
  }, []);

  const runScan = async () => {
    setIsScanning(true);
    setScanProgress(0);
    
    // شبیه‌سازی پیشرفت اسکن
    for (let i = 0; i <= 100; i += 10) {
      setScanProgress(i);
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    
    setPatterns(samplePatterns);
    setIsScanning(false);
  };

  const getSeverityColor = (severity: string) => {
    const colors = {
      low: 'text-green-400 bg-green-500/10 border-green-500/30',
      medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
      high: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
      critical: 'text-red-400 bg-red-500/10 border-red-500/30',
    };
    return colors[severity as keyof typeof colors];
  };

  const getSeverityText = (severity: string) => {
    const texts = {
      low: 'کم',
      medium: 'متوسط', 
      high: 'بالا',
      critical: 'بحرانی',
    };
    return texts[severity as keyof typeof texts];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ExclamationTriangleIcon className="h-6 w-6 text-red-400" />
          <h2 className="text-xl font-semibold text-white">تشخیص الگوهای مشکوک</h2>
        </div>
        
        <button
          onClick={runScan}
          disabled={isScanning}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {isScanning ? `اسکن در حال انجام... ${scanProgress}%` : 'شروع اسکن جدید'}
        </button>
      </div>

      {/* Progress Bar */}
      {isScanning && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="mb-2 flex justify-between text-sm text-slate-300">
            <span>در حال تحلیل تراکنش‌ها...</span>
            <span>{scanProgress}%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-700">
            <div 
              className="h-2 rounded-full bg-indigo-500 transition-all duration-200"
              style={{ width: `${scanProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Patterns Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {patterns.map((pattern) => {
          const PatternIcon = patternTypes[pattern.type].icon;
          return (
            <div
              key={pattern.id}
              className={`cursor-pointer rounded-xl border p-4 transition-all hover:bg-slate-800/50 ${
                selectedPattern?.id === pattern.id ? 'border-indigo-500 bg-indigo-500/5' : 'border-slate-700 bg-slate-900'
              }`}
              onClick={() => setSelectedPattern(pattern)}
            >
              {/* Pattern Header */}
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <PatternIcon className={`h-5 w-5 ${patternTypes[pattern.type].color}`} />
                  <span className="font-medium text-white">{patternTypes[pattern.type].name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded-full border px-2 py-1 text-xs font-medium ${getSeverityColor(pattern.severity)}`}>
                    {getSeverityText(pattern.severity)}
                  </span>
                  <span className="text-xs text-slate-400">{pattern.confidence}% اطمینان</span>
                </div>
              </div>

              {/* Pattern Description */}
              <p className="mb-3 text-sm text-slate-300">{pattern.description}</p>

              {/* Pattern Stats */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-slate-400">تراکنش‌ها</p>
                  <p className="font-medium text-white">{pattern.affectedTransactions}</p>
                </div>
                <div>
                  <p className="text-slate-400">مبلغ کل</p>
                  <p className="font-mono font-medium text-amber-300">
                    {pattern.totalAmount.toLocaleString('fa-IR')} ریال
                  </p>
                </div>
                <div>
                  <p className="text-slate-400">بازه زمانی</p>
                  <p className="text-xs text-slate-300">{pattern.timeframe}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Pattern Details Modal */}
      {selectedPattern && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">جزئیات الگوی مشکوک</h3>
            <button
              onClick={() => setSelectedPattern(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          <div className="space-y-4">
            {/* Evidence */}
            <div>
              <h4 className="mb-2 font-medium text-white">شواهد شناسایی شده:</h4>
              <ul className="space-y-1">
                {selectedPattern.evidence.map((evidence, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-red-400" />
                    {evidence}
                  </li>
                ))}
              </ul>
            </div>

            {/* Recommendation */}
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
              <h4 className="mb-2 font-medium text-amber-300">توصیه اقدام:</h4>
              <p className="text-sm text-amber-200">{selectedPattern.recommendation}</p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-500">
                ایجاد هشدار فوری
              </button>
              <button className="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700">
                افزودن به گزارش
              </button>
              <button className="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700">
                تحقیق بیشتر
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-center">
          <p className="text-2xl font-bold text-red-400">{patterns.filter(p => p.severity === 'critical').length}</p>
          <p className="text-sm text-red-300">بحرانی</p>
        </div>
        <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-4 text-center">
          <p className="text-2xl font-bold text-orange-400">{patterns.filter(p => p.severity === 'high').length}</p>
          <p className="text-sm text-orange-300">بالا</p>
        </div>
        <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-center">
          <p className="text-2xl font-bold text-yellow-400">{patterns.filter(p => p.severity === 'medium').length}</p>
          <p className="text-sm text-yellow-300">متوسط</p>
        </div>
        <div className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 text-center">
          <p className="text-2xl font-bold text-green-400">
            {patterns.reduce((sum, p) => sum + p.totalAmount, 0).toLocaleString('fa-IR')}
          </p>
          <p className="text-sm text-green-300">کل مبلغ مشکوک (ریال)</p>
        </div>
      </div>
    </div>
  );
}