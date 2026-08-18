/**
 * Export Button Component
 */

import { LegalSearchHit } from '../api/types';

interface ExportButtonProps {
  data?: any;
  results?: LegalSearchHit[];
  query?: string;
  format?: 'csv' | 'json' | 'pdf';
}

export default function ExportButton({ data, results, query, format = 'json' }: ExportButtonProps) {
  const handleExport = () => {
    const exportData = data || results;
    if (!exportData) return;

    const content = format === 'json' ? JSON.stringify(exportData, null, 2) : String(exportData);
    const element = document.createElement('a');
    const file = new Blob([content], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `export_${query || 'data'}.${format}`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <button
      onClick={handleExport}
      disabled={!data && !results}
      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-slate-400"
    >
      Export as {format.toUpperCase()}
    </button>
  );
}
