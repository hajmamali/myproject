/**
 * Cryptographic Proof Verification Badge
 * ======================================
 * 
 * Displays cryptographic proof status for AI responses.
 * Mirrors backend proof system architecture.
 * 
 * Constitutional Authority: mahoun/constitutional/constitution/CONSTITUTION.md
 */

import { useState } from 'react';
import { 
  ShieldCheckIcon, 
  ShieldExclamationIcon,
  ChevronDownIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

export interface ProofData {
  proof_hash: string;
  signature: string;
  timestamp: string;
  evidence_count: number;
  verification_status: 'verified' | 'pending' | 'failed';
  ledger_reference?: string;
  blockchain_height?: number;
}

interface ProofBadgeProps {
  proof: ProofData;
  compact?: boolean;
}

export default function CryptographicProofBadge({ proof, compact = false }: ProofBadgeProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusColors = {
    verified: 'bg-green-500/10 border-green-500 text-green-400',
    pending: 'bg-yellow-500/10 border-yellow-500 text-yellow-400',
    failed: 'bg-red-500/10 border-red-500 text-red-400',
  };

  const statusIcons = {
    verified: ShieldCheckIcon,
    pending: ShieldExclamationIcon,
    failed: ShieldExclamationIcon,
  };

  const StatusIcon = statusIcons[proof.verification_status];

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs ${statusColors[proof.verification_status]}`}>
        <StatusIcon className="w-3.5 h-3.5" />
        <span className="font-medium">
          {proof.verification_status === 'verified' ? 'تایید شده' : 
           proof.verification_status === 'pending' ? 'در انتظار' : 'نامعتبر'}
        </span>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border p-4 ${statusColors[proof.verification_status]}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon className="w-6 h-6" />
          <div>
            <h3 className="font-bold text-sm">اثبات رمزنگاری</h3>
            <p className="text-xs opacity-75">
              {proof.verification_status === 'verified' ? 'این پاسخ با اثبات رمزنگاری تایید شده است' :
               proof.verification_status === 'pending' ? 'در حال بررسی اثبات رمزنگاری' :
               'اثبات رمزنگاری نامعتبر است'}
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-white/10 rounded transition-colors"
        >
          <ChevronDownIcon className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-4 space-y-3 text-xs">
          {/* Proof Hash */}
          <div className="flex items-start gap-2">
            <DocumentTextIcon className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-medium mb-1">هش اثبات:</p>
              <code className="block bg-black/20 p-2 rounded break-all font-mono">
                {proof.proof_hash}
              </code>
            </div>
          </div>

          {/* Signature */}
          <div>
            <p className="font-medium mb-1">امضا دیجیتال:</p>
            <code className="block bg-black/20 p-2 rounded break-all font-mono">
              {proof.signature}
            </code>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-black/20 p-2 rounded">
              <p className="opacity-75 mb-1">زمان:</p>
              <p className="font-mono">{new Date(proof.timestamp).toLocaleString('fa-IR')}</p>
            </div>
            <div className="bg-black/20 p-2 rounded">
              <p className="opacity-75 mb-1">تعداد شواهد:</p>
              <p className="font-mono">{proof.evidence_count.toLocaleString('fa-IR')}</p>
            </div>
          </div>

          {/* Ledger Reference */}
          {proof.ledger_reference && (
            <div className="bg-black/20 p-2 rounded">
              <p className="opacity-75 mb-1">ارجاه دفتر کل:</p>
              <p className="font-mono">{proof.ledger_reference}</p>
            </div>
          )}

          {/* Blockchain Height */}
          {proof.blockchain_height && (
            <div className="bg-black/20 p-2 rounded">
              <p className="opacity-75 mb-1">ارتفاع بلاک‌چین:</p>
              <p className="font-mono">{proof.blockchain_height.toLocaleString('fa-IR')}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
