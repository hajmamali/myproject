import { useState, useEffect } from 'react';

interface Stats {
    total_verdicts: number;
    total_searches: number;
    avg_response_time_ms: number;
    system_health: 'healthy' | 'degraded' | 'down';
}

export default function StatsPanel() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchStats();
        }
    }, [isOpen]);

    const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    const fetchStats = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/system/health`);
            const data = await response.json();
            setStats({
                total_verdicts: data.total_documents || 0,
                total_searches: data.total_queries || 0,
                avg_response_time_ms: data.avg_latency_ms || 0,
                system_health: data.status === 'healthy' ? 'healthy' : 'degraded',
            });
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    };

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-2 text-sm border border-slate-600 hover:bg-slate-800 rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                آمار سیستم
            </button>

            {isOpen && (
                <div className="absolute left-0 mt-2 w-72 bg-slate-900 rounded-xl shadow-xl border border-slate-700 p-4 z-10">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="font-bold text-slate-200">آمار سیستم</h3>
                        <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-400">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {stats ? (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between p-2 bg-slate-800 rounded-lg">
                                <span className="text-sm text-slate-400">تعداد اسناد</span>
                                <span className="font-bold text-primary-600">{stats.total_verdicts.toLocaleString('fa-IR')}</span>
                            </div>
                            <div className="flex items-center justify-between p-2 bg-slate-800 rounded-lg">
                                <span className="text-sm text-slate-400">تعداد جستجوها</span>
                                <span className="font-bold text-primary-600">{stats.total_searches.toLocaleString('fa-IR')}</span>
                            </div>
                            <div className="flex items-center justify-between p-2 bg-slate-800 rounded-lg">
                                <span className="text-sm text-slate-400">میانگین زمان پاسخ</span>
                                <span className="font-bold text-primary-600">{stats.avg_response_time_ms.toFixed(0)} ms</span>
                            </div>
                            <div className="flex items-center justify-between p-2 bg-slate-800 rounded-lg">
                                <span className="text-sm text-slate-400">وضعیت سیستم</span>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${stats.system_health === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                                    }`}>
                                    {stats.system_health === 'healthy' ? '✓ سالم' : 'نیاز به بررسی'}
                                </span>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-4 text-slate-500">در حال بارگذاری...</div>
                    )}
                </div>
            )}
        </div>
    );
}
