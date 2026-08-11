/**
 * Dataset Engineering Center - Simplified
 */
import { useQuery } from '@tanstack/react-query';

interface DataSource {
  id: string;
  name: string;
  type: 'upload' | 'api' | 'database' | 'crawl' | 'external';
  status: 'active' | 'paused' | 'error' | 'processing' | 'completed' | 'draft';
}

interface Dataset {
  id: string;
  name: string;
  description: string;
  version: string;
  status: 'draft' | 'processing' | 'ready' | 'error' | 'deprecated';
  recordCount: number;
  metadata: {
    qualityScore: number;
  };
}

const MOCK_DATA_SOURCES: DataSource[] = [
  { id: 'src-001', name: 'Legal API', type: 'api', status: 'active' },
];

const MOCK_DATASETS: Dataset[] = [
  { id: 'ds-001', name: 'Legal Dataset v1', description: 'Legal cases', version: '1.0', status: 'ready', recordCount: 1000, metadata: { qualityScore: 0.95 } },
];

async function fetchDataSources(): Promise<DataSource[]> {
  return MOCK_DATA_SOURCES;
}

async function fetchDatasets(): Promise<Dataset[]> {
  return MOCK_DATASETS;
}

export default function DatasetEngineering() {
  const { isLoading: sourcesLoading } = useQuery({
    queryKey: ['data-sources'],
    queryFn: fetchDataSources,
  });

  const { isLoading: datasetsLoading } = useQuery({
    queryKey: ['datasets'],
    queryFn: fetchDatasets,
  });

  if (sourcesLoading || datasetsLoading) {
    return <div className="min-h-screen bg-slate-950 p-6">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">مهندسی دیتاست</h1>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h2 className="text-lg text-white">به زودی...</h2>
        <p className="text-slate-400 text-sm">صبر کنید، در حال تکمیل هستیم...</p>
      </div>
    </div>
  );
}
