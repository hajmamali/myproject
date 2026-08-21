/**
 * Violations List Component
 * =========================
 * Interactive list of graph integrity violations with filtering and actions.
 * 
 * Features:
 * - Severity-based filtering
 * - Pagination
 * - Detailed violation view
 * - Quick actions (remediation, ignore)
 */

import { useState, useMemo } from 'react';

interface Violation {
  id: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  entity_id: string;
  entity_label: string;
  message: string;
  detected_at: string;
  remediation?: string;
}

interface ViolationsListProps {
  violations: Violation[];
  onRemediate?: (violationId: string) => void;
  onIgnore?: (violationId: string) => void;
}

export default function ViolationsList({ 
  violations, 
  onRemediate, 
  onIgnore 
}: ViolationsListProps) {
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(null);

  // Extract unique violation types
  const violationTypes = useMemo(() => {
    const types = new Set(violations.map(v => v.type));
    return Array.from(types);
  }, [violations]);

  // Filter violations
  const filteredViolations = useMemo(() => {
    return violations.filter(v => {
      if (severityFilter !== 'all' && v.severity !== severityFilter) return false;
      if (typeFilter !== 'all' && v.type !== typeFilter) return false;
      return true;
    });
  }, [violations, severityFilter, typeFilter]);

  // Count by severity
  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    violations.forEach(v => {
      counts[v.severity]++;
    });
    return counts;
  }, [violations]);

  const severityBadgeClasses = {
    critical: 'bg-red-100 text-red-700',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-blue-100 text-blue-700',
  };

  const formatTime = (iso: string): string => {
    try {
      return new Date(iso).toLocaleString('fa-IR');
    } catch {
      return iso;
    }
  };

  if (violations.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500">
        <p className="text-2xl">✓</p>
        <p className="mt-2">هیچ نقضی یافت نشد</p>
      </div>
    );
  }

  return (
    <div>
      {/* Severity Summary Badges */}
      <div className="mb-4 flex gap-2">
        <SeverityBadge
          label="بحرانی"
          count={severityCounts.critical}
          color="red"
          onClick={() => setSeverityFilter(severityFilter === 'critical' ? 'all' : 'critical')}
          active={severityFilter === 'critical'}
        />
        <SeverityBadge
          label="بالا"
          count={severityCounts.high}
          color="orange"
          onClick={() => setSeverityFilter(severityFilter === 'high' ? 'all' : 'high')}
          active={severityFilter === 'high'}
        />
        <SeverityBadge
          label="متوسط"
          count={severityCounts.medium}
          color="yellow"
          onClick={() => setSeverityFilter(severityFilter === 'medium' ? 'all' : 'medium')}
          active={severityFilter === 'medium'}
        />
        <SeverityBadge
          label="پایین"
          count={severityCounts.low}
          color="blue"
          onClick={() => setSeverityFilter(severityFilter === 'low' ? 'all' : 'low')}
          active={severityFilter === 'low'}
        />
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="all">همه شدت‌ها</option>
          <option value="critical">بحرانی</option>
          <option value="high">بالا</option>
          <option value="medium">متوسط</option>
          <option value="low">پایین</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="all">همه انواع</option>
          {violationTypes.map(type => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>

        <div className="mr-auto text-sm text-slate-500">
          {filteredViolations.length} از {violations.length} نقض
        </div>
      </div>

      {/* Violations Table */}
      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                شدت
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                نوع
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                موجودیت
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                پیام
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                زمان
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500">
                اقدامات
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white">
            {filteredViolations.map((violation) => (
              <tr
                key={violation.id}
                className={`cursor-pointer transition-colors hover:bg-slate-50 ${
                  selectedViolation?.id === violation.id ? 'bg-blue-50' : ''
                }`}
                onClick={() => setSelectedViolation(violation)}
              >
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                    severityBadgeClasses[violation.severity]
                  }`}>
                    {violation.severity === 'critical' ? 'بحرانی' :
                     violation.severity === 'high' ? 'بالا' :
                     violation.severity === 'medium' ? 'متوسط' : 'پایین'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-900">
                  {violation.type}
                </td>
                <td className="px-4 py-3 text-sm">
                  <div className="font-medium text-slate-900">{violation.entity_label}</div>
                  <div className="text-xs text-slate-500">{violation.entity_id}</div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">
                  {violation.message}
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {formatTime(violation.detected_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {onRemediate && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemediate(violation.id);
                        }}
                        className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                      >
                        رفع
                      </button>
                    )}
                    {onIgnore && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onIgnore(violation.id);
                        }}
                        className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-300"
                      >
                        نادیده
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Selected Violation Detail Modal */}
      {selectedViolation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">
                جزئیات نقض
              </h3>
              <button
                type="button"
                onClick={() => setSelectedViolation(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-600">شناسه:</label>
                <p className="mt-1 text-slate-900">{selectedViolation.id}</p>
              </div>

              <div>
                <label className="text-sm font-medium text-slate-600">پیام:</label>
                <p className="mt-1 text-slate-900">{selectedViolation.message}</p>
              </div>

              {selectedViolation.remediation && (
                <div className="rounded-lg bg-blue-50 p-4">
                  <label className="text-sm font-medium text-blue-900">پیشنهاد رفع:</label>
                  <p className="mt-1 text-blue-800">{selectedViolation.remediation}</p>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              {onIgnore && (
                <button
                  type="button"
                  onClick={() => {
                    onIgnore(selectedViolation.id);
                    setSelectedViolation(null);
                  }}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-slate-700 hover:bg-slate-50"
                >
                  نادیده گرفتن
                </button>
              )}
              {onRemediate && (
                <button
                  type="button"
                  onClick={() => {
                    onRemediate(selectedViolation.id);
                    setSelectedViolation(null);
                  }}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                >
                  رفع نقض
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SeverityBadge({
  label,
  count,
  color,
  onClick,
  active,
}: {
  label: string;
  count: number;
  color: 'red' | 'orange' | 'yellow' | 'blue';
  onClick: () => void;
  active: boolean;
}) {
  const colorClasses = {
    red: active ? 'bg-red-500 text-white' : 'bg-red-100 text-red-700',
    orange: active ? 'bg-orange-500 text-white' : 'bg-orange-100 text-orange-700',
    yellow: active ? 'bg-yellow-500 text-white' : 'bg-yellow-100 text-yellow-700',
    blue: active ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-700',
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${colorClasses[color]}`}
    >
      {label}: {count}
    </button>
  );
}