import { LegalSearchHit } from '../api/types';

interface ExportButtonProps {
    results: LegalSearchHit[];
    query: string;
}

export default function ExportButton({ results, query }: ExportButtonProps) {
    const exportToJSON = () => {
        const data = {
            query,
            timestamp: new Date().toISOString(),
            total_results: results.length,
            results: results.map(r => ({
                verdict_id: r.verdict_id,
                score: r.score,
                section: r.section,
                text: r.chunk_text,
                case_type: r.case_type,
                court_level: r.court_level,
                is_final: r.is_final,
                tags: r.tags,
                law_articles: r.law_articles,
            })),
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mahoun-search-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const exportToCSV = () => {
        const headers = ['شناسه', 'امتیاز', 'بخش', 'متن', 'نوع پرونده', 'دادگاه', 'قطعیت'];
        const rows = results.map(r => [
            r.verdict_id,
            r.score.toFixed(3),
            r.section,
            `"${r.chunk_text.replace(/"/g, '""')}"`,
            r.case_type || '',
            r.court_level || '',
            r.is_final ? 'قطعی' : 'غیرقطعی',
        ]);

        const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mahoun-search-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (results.length === 0) return null;

    return (
        <div className="flex gap-2">
            <button
                onClick={exportToJSON}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-600 hover:bg-slate-800 rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                JSON
            </button>
            <button
                onClick={exportToCSV}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-600 hover:bg-slate-800 rounded-lg transition-colors"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                CSV
            </button>
        </div>
    );
}

