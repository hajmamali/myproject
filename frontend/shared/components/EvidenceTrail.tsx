/**
 * Evidence Trail Visualization
 * ============================
 * 
 * Displays the complete evidence trail for AI responses.
 * Shows retrieval sources, graph context, and verification chain.
 * 
 * Constitutional Authority: mahoun/constitutional/constitution/CONSTITUTION.md
 */

import { useState } from 'react';
import { 
  DocumentTextIcon,
  ChartBarIcon,
  LinkIcon,
  ChevronDownIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

export interface EvidenceSource {
  id: string;
  text: string;
  score: number;
  metadata: {
    source: string;
    category: string;
    verdict_id?: string;
    court_level?: string;
    case_type?: string;
  };
}

export interface GraphContext {
  related_articles: Array<{
    number: string;
    law_name: string;
    relevance: number;
  }>;
  related_verdicts: Array<{
    id: string;
    case_type: string;
    relevance: number;
  }>;
  legal_concepts: string[];
}

export interface VerificationStep {
  step: string;
  status: 'pending' | 'verified' | 'failed';
  timestamp: string;
  details?: string;
}

export interface EvidenceTrail {
  sources: EvidenceSource[];
  graph_context?: GraphContext;
  verification_chain: VerificationStep[];
  total_evidence: number;
  confidence_score: number;
  processing_time_ms: number;
}

interface EvidenceTrailProps {
  trail: EvidenceTrail;
  compact?: boolean;
}

export default function EvidenceTrail({ trail, compact = false }: EvidenceTrailProps) {
  const [isExpanded, setIsExpanded] = useState(!compact);
  const [selectedSource, setSelectedSource] = useState<EvidenceSource | null>(null);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400 bg-green-500/10';
    if (score >= 0.6) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-red-400 bg-red-500/10';
  };

  const getVerificationStatus = (status: VerificationStep['status']) => {
    switch (status) {
      case 'verified':
        return <CheckCircleIcon className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <XCircleIcon className="w-4 h-4 text-red-400" />;
      case 'pending':
        return <ClockIcon className="w-4 h-4 text-yellow-400 animate-pulse" />;
    }
  };

  if (compact) {
    return (
      <div className="bg-slate-900/50 rounded-lg border border-slate-700 p-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-between w-full"
        >
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <DocumentTextIcon className="w-4 h-4" />
            <span>شواهد ({trail.total_evidence})</span>
            <span className={`px-2 py-0.5 rounded text-xs ${getScoreColor(trail.confidence_score)}`}>
              {Math.round(trail.confidence_score * 100)}%
            </span>
          </div>
          <ChevronDownIcon className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </button>

        {isExpanded && (
          <div className="mt-3 space-y-2">
            {trail.sources.slice(0, 3).map((source, idx) => (
              <div key={source.id} className="text-xs bg-slate-800/50 p-2 rounded">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-400">منبع {idx + 1}</span>
                  <span className={`px-1.5 py-0.5 rounded ${getScoreColor(source.score)}`}>
                    {Math.round(source.score * 100)}%
                  </span>
                </div>
                <p className="text-slate-300 line-clamp-2">{source.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="bg-slate-800/50 px-4 py-3 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <DocumentTextIcon className="w-5 h-5 text-primary-400" />
            <div>
              <h3 className="font-semibold text-slate-100">مسیر شواهد</h3>
              <p className="text-xs text-slate-400">
                {trail.total_evidence} منبع • {Math.round(trail.confidence_score * 100)}% اطمینان
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ClockIcon className="w-4 h-4" />
            <span>{trail.processing_time_ms}ms</span>
          </div>
        </div>
      </div>

      {/* Verification Chain */}
      <div className="px-4 py-3 border-b border-slate-700">
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {trail.verification_chain.map((step, idx) => (
            <div key={step.step} className="flex items-center gap-2 flex-shrink-0">
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${
                step.status === 'verified' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                step.status === 'failed' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
              }`}>
                {getVerificationStatus(step.status)}
                <span className="text-xs font-medium">{step.step}</span>
              </div>
              {idx < trail.verification_chain.length - 1 && (
                <div className="w-2 h-0.5 bg-slate-600" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Evidence Sources */}
      <div className="p-4">
        <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <ChartBarIcon className="w-4 h-4" />
          منابع بازیابی شده
        </h4>
        <div className="space-y-2">
          {trail.sources.map((source, idx) => (
            <div
              key={source.id}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                selectedSource?.id === source.id
                  ? 'bg-primary-500/10 border-primary-500/30'
                  : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
              }`}
              onClick={() => setSelectedSource(source)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">#{idx + 1}</span>
                  <span className="text-sm font-medium text-slate-200">{source.metadata.source}</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getScoreColor(source.score)}`}>
                  {Math.round(source.score * 100)}%
                </span>
              </div>
              <p className="text-sm text-slate-400 line-clamp-2">{source.text}</p>
              {source.metadata.verdict_id && (
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                  <LinkIcon className="w-3 h-3" />
                  <span>{source.metadata.verdict_id}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Graph Context */}
      {trail.graph_context && (
        <div className="px-4 py-3 border-t border-slate-700">
          <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <LinkIcon className="w-4 h-4" />
            بافت گراف دانش
          </h4>
          
          {trail.graph_context.related_articles.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-slate-400 mb-2">مواد قانونی مرتبط:</p>
              <div className="flex flex-wrap gap-1.5">
                {trail.graph_context.related_articles.map((article, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-400 rounded text-xs"
                  >
                    ماده {article.number} - {article.law_name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {trail.graph_context.legal_concepts.length > 0 && (
            <div>
              <p className="text-xs text-slate-400 mb-2">مفاهیم حقوقی:</p>
              <div className="flex flex-wrap gap-1.5">
                {trail.graph_context.legal_concepts.map((concept, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded text-xs"
                  >
                    {concept}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Selected Source Detail */}
      {selectedSource && (
        <div className="px-4 py-3 border-t border-slate-700 bg-slate-800/30">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-slate-300">جزئیات منبع</h4>
            <button
              onClick={() => setSelectedSource(null)}
              className="text-slate-400 hover:text-slate-300"
            >
              <XCircleIcon className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">منبع:</span>
              <span className="text-slate-200">{selectedSource.metadata.source}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">دسته:</span>
              <span className="text-slate-200">{selectedSource.metadata.category}</span>
            </div>
            {selectedSource.metadata.court_level && (
              <div className="flex justify-between">
                <span className="text-slate-400">سطح دادگاه:</span>
                <span className="text-slate-200">{selectedSource.metadata.court_level}</span>
              </div>
            )}
            {selectedSource.metadata.case_type && (
              <div className="flex justify-between">
                <span className="text-slate-400">نوع پرونده:</span>
                <span className="text-slate-200">{selectedSource.metadata.case_type}</span>
              </div>
            )}
            <div className="mt-2 p-2 bg-slate-900 rounded">
              <p className="text-slate-300">{selectedSource.text}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
