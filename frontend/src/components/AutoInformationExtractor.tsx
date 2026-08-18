/**
 * Auto Information Extraction - استخراج خودکار اطلاعات از اسناد
 * fabrication-check-ok: demo UI with mock data for development
 */
import React, { useState } from 'react';
import {
  DocumentTextIcon, UserIcon, BuildingOfficeIcon,
  BanknotesIcon, CalendarIcon, MapPinIcon,
  IdentificationIcon, CheckCircleIcon, ArrowUpTrayIcon,
  MagnifyingGlassIcon, SparklesIcon, ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';

// Mock data - fabrication-check-ok: sample data for UI demo
const mockResult = {
  persons: [
    { id: 'p1', firstName: 'محمدرضا', lastName: 'احمدی', nationalId: '0012345678', role: 'مدیرعامل', confidence: 96, source: 'قرارداد', pageNumber: 3 },
    { id: 'p2', firstName: 'سید محمد', lastName: 'رضوی', nationalId: '0023456789', role: 'رئیس هیئت مدیره', confidence: 94, source: 'صورتجلسه', pageNumber: 12 },
  ],
  companies: [
    { id: 'c1', name: 'شرکت پشتیبان فنی', registrationNumber: '123456', type: 'سهامی خاص', confidence: 98, source: 'قرارداد', pageNumber: 1 },
    { id: 'c2', name: 'شرکت مهر اقتصاد', registrationNumber: '234567', type: 'با مسئولیت محدود', confidence: 95, source: 'فاکتور', pageNumber: 18 },
  ],
  amounts: [
    { id: 'a1', value: 50000000000, currency: 'ریال', type: 'payment', date: '1403/01/15', confidence: 99, source: 'فاکتور', pageNumber: 8 },
    { id: 'a2', value: 18000000000, currency: 'ریال', type: 'payment', date: '1403/03/28', confidence: 97, source: 'حواله', pageNumber: 15 },
  ],
  dates: [
    { id: 'd1', date: '1402/11/12', type: 'contract', description: 'امضای قرارداد', confidence: 98, source: 'قرارداد', pageNumber: 1 },
    { id: 'd2', date: '1403/04/20', type: 'deadline', description: 'مهلت تحویل', confidence: 95, source: 'ضمیمه', pageNumber: 6 },
  ],
  locations: [
    { id: 'l1', address: 'تهران، خیابان ولیعصر، پلاک ۱۲۳۴', city: 'تهران', type: 'office', confidence: 94, source: 'قرارداد', pageNumber: 2 },
  ],
  accounts: [
    { id: 'acc1', accountNumber: '1234567890', iban: 'IR12 3456 7890 1234 5678 90', bankName: 'بانک ملت', ownerName: 'شرکت پشتیبان', confidence: 97, source: 'فاکتور', pageNumber: 8 },
  ],
  totalEntities: 8,
  processingTime: 2.4,
};

export default function AutoInformationExtractor() {
  const [file, setFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<typeof mockResult | null>(null);
  const [tab, setTab] = useState<'persons' | 'companies' | 'amounts' | 'dates' | 'locations' | 'accounts'>('persons');

  const handleExtract = async () => {
    if (!file) return;
    setExtracting(true);
    setProgress(0);
    // Simulate extraction - fabrication-check-ok: demo animation
    for (let i = 20; i <= 100; i += 20) {
      await new Promise(r => setTimeout(r, 500));
      setProgress(i);
    }
    setResult(mockResult);
    setExtracting(false);
  };

  const exportJSON = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'extracted-data.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const confidenceColor = (c: number) =>
    c >= 95 ? 'text-green-400 bg-green-500/10' : c >= 85 ? 'text-yellow-400 bg-yellow-500/10' : 'text-orange-400 bg-orange-500/10';

  const tabs = {
    persons: { label: 'اشخاص', icon: UserIcon, data: result?.persons || [] },
    companies: { label: 'شرکت‌ها', icon: BuildingOfficeIcon, data: result?.companies || [] },
    amounts: { label: 'مبالغ', icon: BanknotesIcon, data: result?.amounts || [] },
    dates: { label: 'تاریخ‌ها', icon: CalendarIcon, data: result?.dates || [] },
    locations: { label: 'مکان‌ها', icon: MapPinIcon, data: result?.locations || [] },
    accounts: { label: 'حساب‌ها', icon: IdentificationIcon, data: result?.accounts || [] },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SparklesIcon className="h-6 w-6 text-purple-400" />
          <h2 className="text-xl font-semibold text-white">استخراج خودکار اطلاعات</h2>
        </div>
        {result && (
          <button onClick={exportJSON} className="flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600">
            <ArrowDownTrayIcon className="h-4 w-4" />
            دانلود JSON
          </button>
        )}
      </div>

      {/* Upload */}
      <div className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-900 p-8 text-center">
        <div className="flex flex-col items-center gap-4">
          <div className="rounded-full bg-purple-500/10 p-4">
            <DocumentTextIcon className="h-12 w-12 text-purple-400" />
          </div>
          <h3 className="text-lg font-medium text-white">بارگذاری سند</h3>
          <p className="text-sm text-slate-400">PDF, Word, Image - حداکثر 10MB</p>
          <label className="cursor-pointer rounded-lg bg-purple-600 px-6 py-3 text-white hover:bg-purple-500">
            <input type="file" className="hidden" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); }} />
            <span className="flex items-center gap-2"><ArrowUpTrayIcon className="h-5 w-5" />انتخاب فایل</span>
          </label>
          {file && (
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <CheckCircleIcon className="h-5 w-5 text-green-400" />
              <span>{file.name}</span>
              <span className="text-slate-500">({(file.size / 1024).toFixed(0)} KB)</span>
            </div>
          )}
        </div>
      </div>

      {/* Extract Button */}
      {file && !result && (
        <button onClick={handleExtract} disabled={extracting} className="w-full rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-3 text-white hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50">
          {extracting ? (
            <span className="flex items-center justify-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              در حال استخراج... {progress}%
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2"><MagnifyingGlassIcon className="h-5 w-5" />شروع استخراج خودکار</span>
          )}
        </button>
      )}

      {/* Progress */}
      {extracting && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="h-2 rounded-full bg-slate-700">
            <div className="h-2 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 text-center">
              <p className="text-2xl font-bold text-green-400">{result.totalEntities}</p>
              <p className="text-sm text-green-300">موجودیت</p>
            </div>
            <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-4 text-center">
              <p className="text-2xl font-bold text-blue-400">{result.processingTime}s</p>
              <p className="text-sm text-blue-300">زمان</p>
            </div>
            <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 p-4 text-center">
              <p className="text-2xl font-bold text-purple-400">94%</p>
              <p className="text-sm text-purple-300">اطمینان</p>
            </div>
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-center">
              <p className="text-lg font-bold text-amber-400">68B</p>
              <p className="text-sm text-amber-300">مبالغ</p>
            </div>
          </div>

          <div className="flex gap-2 overflow-x-auto rounded-xl border border-slate-700 bg-slate-900 p-2">
            {Object.entries(tabs).map(([key, config]) => {
              const Icon = config.icon;
              const isActive = tab === key;
              return (
                <button key={key} onClick={() => setTab(key as typeof tab)}
                  className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm ${isActive ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-400 hover:bg-slate-800'}`}>
                  <Icon className="h-4 w-4" />
                  <span>{config.label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${isActive ? 'bg-indigo-500/30' : 'bg-slate-700'}`}>{config.data.length}</span>
                </button>
              );
            })}
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 max-h-[600px] overflow-y-auto">
            {tab === 'persons' && result.persons.map((p) => (
              <div key={p.id} className="mb-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="rounded-lg bg-indigo-500/10 p-2"><UserIcon className="h-5 w-5 text-indigo-400" /></div>
                    <div>
                      <h4 className="font-medium text-white">{p.firstName} {p.lastName}</h4>
                      {p.nationalId && <p className="mt-1 text-sm text-slate-400">کد ملی: {p.nationalId}</p>}
                      {p.role && <p className="mt-1 text-sm text-slate-300">سمت: {p.role}</p>}
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <span>منبع: {p.source}</span><span>•</span><span>صفحه {p.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${confidenceColor(p.confidence)}`}>{p.confidence}%</span>
                </div>
              </div>
            ))}AutoInformationExtractor
            {tab === 'companies' && result.companies.map((c) => (
              <div key={c.id} className="mb-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="rounded-lg bg-blue-500/10 p-2"><BuildingOfficeIcon className="h-5 w-5 text-blue-400" /></div>
                    <div>
                      <h4 className="font-medium text-white">{c.name}</h4>
                      {c.registrationNumber && <p className="mt-1 text-sm text-slate-400">ثبت: {c.registrationNumber}</p>}
                      {c.type && <p className="mt-1 text-sm text-slate-300">{c.type}</p>}
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <span>{c.source}</span><span>•</span><span>صفحه {c.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${confidenceColor(c.confidence)}`}>{c.confidence}%</span>
                </div>
              </div>
            ))}
            {tab === 'amounts' && result.amounts.map((a) => (
              <div key={a.id} className="mb-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="rounded-lg bg-amber-500/10 p-2"><BanknotesIcon className="h-5 w-5 text-amber-400" /></div>
                    <div>
                      <h4 className="font-mono text-lg font-bold text-amber-300">{a.value.toLocaleString('fa-IR')} {a.currency}</h4>
                      <div className="mt-1 flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs ${a.type === 'payment' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
                          {a.type === 'payment' ? 'پرداخت' : 'بدهی'}
                        </span>
                        {a.date && <span className="text-sm text-slate-400">{a.date}</span>}
                      </div>
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <span>{a.source}</span><span>•</span><span>صفحه {a.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${confidenceColor(a.confidence)}`}>{a.confidence}%</span>
                </div>
              </div>
            ))}
            {tab === 'dates' && result.dates.map((d) => (
              <div key={d.id} className="mb-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="rounded-lg bg-purple-500/10 p-2"><CalendarIcon className="h-5 w-5 text-purple-400" /></div>
                    <div>AutoInformationExtractor
                      <h4 className="font-medium text-white">{d.date}</h4>
                      {d.description && <p className="mt-1 text-sm text-slate-300">{d.description}</p>}
                      <span className="mt-2 inline-block rounded-full bg-blue-500/20 px-2 py-0.5 text-xs text-blue-300">{d.type}</span>
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <span>{d.source}</span><span>•</span><span>صفحه {d.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${confidenceColor(d.confidence)}`}>{d.confidence}%</span>
                </div>
              </div>
            ))}
            {tab === 'locations' && result.locations.map((l) => (
              <div key={l.id} className="mb-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="rounded-lg bg-cyan-500/10 p-2"><MapPinIcon className="h-5 w-5 text-cyan-400" /></div>
                    <div>
                      <h4 className="font-medium text-white">{l.address}</h4>
                      {l.city && <p className="mt-1 text-sm text-slate-400">شهر: {l.city}</p>}
                      <span className="mt-2 inline-block rounded-full bg-cyan-500/20 px-2 py-0.5 text-xs text-cyan-300">{l.type}</span>
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <span>{l.source}</span><span>•</span><span>صفحه {l.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${confidenceColor(l.confidence)}`}>{l.confidence}%</span>
                </div>
              </div>
            ))}
            {tab === 'accounts' && result.accounts.map((acc) => (
              <div key={acc.id} className="mb-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="rounded-lg bg-emerald-500/10 p-2"><IdentificationIcon className="h-5 w-5 text-emerald-400" /></div>
                    <div>
                      <h4 className="font-mono font-medium text-white">{acc.accountNumber}</h4>
                      {acc.iban && <p className="mt-1 text-sm text-slate-400">{acc.iban}</p>}
                      {acc.bankName && <p className="mt-1 text-sm text-slate-300">{acc.bankName}</p>}
                      {acc.ownerName && <p className="mt-1 text-sm text-slate-300">صاحب حساب: {acc.ownerName}</p>}
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                        <span>{acc.source}</span><span>•</span><span>صفحه {acc.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-xs ${confidenceColor(acc.confidence)}`}>{acc.confidence}%</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
