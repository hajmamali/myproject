/**
 * Model Registry Center
 * Complete model management interface
 */

import { useState } from 'react';
import {
  CommandLineIcon,
  PlusIcon,
  RocketLaunchIcon,
} from '@heroicons/react/24/outline';

interface Model {
  id: string;
  name: string;
  version: string;
  status: 'ready' | 'deployed' | 'training' | 'error';
  modelType: string;
  provider: string;
  size: number;
  parameters: number;
  evaluationScore: number;
}

const MOCK_MODELS: Model[] = [
  {
    id: 'model-001',
    name: 'Persian-Legal-7B',
    version: 'v2.1.0',
    status: 'deployed',
    modelType: 'Transformer',
    provider: 'Local',
    size: 14000,
    parameters: 7400000000,
    evaluationScore: 0.87,
  },
  {
    id: 'model-002',
    name: 'Persian-Embedding',
    version: 'v1.2.0',
    status: 'ready',
    modelType: 'Embedding',
    provider: 'Local',
    size: 280,
    parameters: 33000000,
    evaluationScore: 0.92,
  },
];

function formatModelSize(mb: number): string {
  return mb < 1024 ? `${mb} MB` : `${(mb / 1024).toFixed(1)} GB`;
}

function formatParameters(num: number): string {
  return num >= 1000000000 ? `${(num / 1000000000).toFixed(1)}B` :
         num >= 1000000 ? `${(num / 1000000).toFixed(1)}M` :
         `${num}`;
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'deployed': return 'bg-green-500/20 text-green-400';
    case 'ready': return 'bg-blue-500/20 text-blue-400';
    case 'training': return 'bg-yellow-500/20 text-yellow-400';
    default: return 'bg-red-500/20 text-red-400';
  }
}

export default function ModelRegistry() {
  const [models] = useState<Model[]>(MOCK_MODELS);
  const [isCreating, setIsCreating] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold bg-gradient-to-l from-indigo-400 to-cyan-400 bg-clip-text text-transparent flex items-center gap-2">
          <CommandLineIcon className="h-6 w-6 text-indigo-400" />
          Model Registry
        </h1>
        <p className="text-sm text-slate-400 mt-1">مدیریت مدل‌های هوش مصنوعی</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <p className="text-xs text-slate-500 mb-1">کل مدل‌ها</p>
          <p className="text-2xl font-bold text-white">{models.length}</p>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <p className="text-xs text-slate-500 mb-1">مدل‌های آماده</p>
          <p className="text-2xl font-bold text-green-400">
            {models.filter(m => m.status === 'ready' || m.status === 'deployed').length}
          </p>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <p className="text-xs text-slate-500 mb-1">میانگین امتیاز</p>
          <p className="text-2xl font-bold text-white">
            {Math.round(models.reduce((sum, m) => sum + m.evaluationScore, 0) / models.length * 100)}%
          </p>
        </div>
      </div>

      {/* Models Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-6 border-b border-slate-800/60 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">لیست مدل‌ها</h2>
          <button
            onClick={() => setIsCreating(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600/20 text-indigo-300 border border-indigo-600/30 rounded-lg hover:bg-indigo-600/30 transition-all font-semibold text-sm"
          >
            <PlusIcon className="h-4 w-4" />
            ثبت مدل جدید
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-right">
            <thead className="bg-slate-900/40">
              <tr>
                <th className="py-4 px-6 text-slate-500">نام</th>
                <th className="py-4 px-6 text-slate-500">نسخه</th>
                <th className="py-4 px-6 text-slate-500">نوع</th>
                <th className="py-4 px-6 text-slate-500">وضعیت</th>
                <th className="py-4 px-6 text-slate-500">اندازه</th>
                <th className="py-4 px-6 text-slate-500">پارامترها</th>
                <th className="py-4 px-6 text-slate-500">امتیاز</th>
                <th className="py-4 px-6 text-slate-500">عملیات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {models.map(model => (
                <tr key={model.id} className="hover:bg-slate-800/60 transition-colors">
                  <td className="py-4 px-6 text-white font-semibold">{model.name}</td>
                  <td className="py-4 px-6 text-slate-400">{model.version}</td>
                  <td className="py-4 px-6 text-slate-400">{model.modelType}</td>
                  <td className="py-4 px-6">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${getStatusColor(model.status)}`}>
                      {model.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-slate-400">{formatModelSize(model.size)}</td>
                  <td className="py-4 px-6 text-slate-400">{formatParameters(model.parameters)}</td>
                  <td className="py-4 px-6 text-white font-bold">{Math.round(model.evaluationScore * 100)}%</td>
                  <td className="py-4 px-6">
                    {model.status === 'ready' && (
                      <button className="px-3 py-1 bg-green-600/20 text-green-300 rounded-lg hover:bg-green-600/30 transition-colors font-semibold text-xs flex items-center gap-1">
                        <RocketLaunchIcon className="h-3.5 w-3.5" />
                        Deploy
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Model Modal */}
      {isCreating && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 p-6 max-w-md w-full">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <PlusIcon className="h-6 w-6 text-indigo-400" />
              ثبت مدل جدید
            </h2>
            <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); setIsCreating(false); }}>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">نام مدل</label>
                <input
                  type="text"
                  placeholder="Persian-Legal-7B"
                  className="w-full px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/60"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">نوع</label>
                  <select className="w-full px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-lg text-white focus:outline-none focus:border-indigo-500/60">
                    <option>Transformer</option>
                    <option>Embedding</option>
                    <option>Reranker</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Provider</label>
                  <select className="w-full px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-lg text-white focus:outline-none focus:border-indigo-500/60">
                    <option>Local</option>
                    <option>HuggingFace</option>
                    <option>OpenAI</option>
                  </select>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <button type="button" onClick={() => setIsCreating(false)} className="px-4 py-2 bg-slate-700/20 text-slate-300 border border-slate-600/30 rounded-lg hover:bg-slate-700/30 transition-all font-semibold text-sm">
                  انصراف
                </button>
                <button type="submit" className="px-4 py-2 bg-indigo-600/20 text-indigo-300 border border-indigo-600/30 rounded-lg hover:bg-indigo-600/30 transition-all font-semibold text-sm flex items-center gap-2">
                  <PlusIcon className="h-4 w-4" />
                  ثبت مدل
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
