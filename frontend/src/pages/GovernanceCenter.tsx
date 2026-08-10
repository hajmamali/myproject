/**
 * Governance Center - Constitutional Compliance Dashboard
 * 
 * The heart of MahouN's governance-first architecture.
 * Provides real-time visibility into constitutional health,
 * audit events, policy enforcement, and compliance status.
 */

import { useState } from 'react';
import { 
  ShieldCheckIcon, 
  DocumentTextIcon, 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ChartBarIcon,
  BoltIcon,
  LockClosedIcon
} from '@heroicons/react/24/outline';
import { useQuery } from '@tanstack/react-query';

// ============================================================================
// Types
// ============================================================================

interface ConstitutionalHealth {
  status: 'healthy' | 'degraded' | 'critical';
  score: number;  // 0-100
  issues: Issue[];
  lastValidation: string;
}

interface Issue {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  message: string;
  timestamp: string;
}

interface AuditMetrics {
  totalEvents: number;
  criticalEvents: number;
  complianceRate: number;
  trends: TrendData[];
}

interface TrendData {
  timestamp: string;
  value: number;
}

interface FailClosedEvent {
  id: string;
  type: string;
  reason: string;
  impact: string;
  timestamp: string;
  recovered: boolean;
}

interface MutationAuthorization {
  pendingRequests: number;
  approvalRate: number;
  averageReviewTime: number;
  riskDistribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
}

// ============================================================================
// API Functions
// ============================================================================

async function fetchGovernanceHealth(): Promise<ConstitutionalHealth> {
  const response = await fetch('/api/v1/governance/health');
  if (!response.ok) throw new Error('Failed to fetch governance health');
  return response.json();
}

async function fetchAuditMetrics(): Promise<AuditMetrics> {
  const response = await fetch('/api/v1/governance/audit/metrics');
  if (!response.ok) throw new Error('Failed to fetch audit metrics');
  return response.json();
}

async function fetchFailClosedEvents(): Promise<FailClosedEvent[]> {
  const response = await fetch('/api/v1/governance/fail-closed/recent');
  if (!response.ok) throw new Error('Failed to fetch fail-closed events');
  return response.json();
}

async function fetchMutationAuth(): Promise<MutationAuthorization> {
  const response = await fetch('/api/v1/governance/mutations/stats');
  if (!response.ok) throw new Error('Failed to fetch mutation stats');
  return response.json();
}

// ============================================================================
// Components
// ============================================================================

function StatusBadge({ status }: { status: 'healthy' | 'degraded' | 'critical' }) {
  const config = {
    healthy: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      icon: CheckCircleIcon,
      label: 'سالم'
    },
    degraded: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-800',
      icon: ExclamationTriangleIcon,
      label: 'تخریب‌شده'
    },
    critical: {
      bg: 'bg-red-100',
      text: 'text-red-800',
      icon: XCircleIcon,
      label: 'بحرانی'
    }
  };

  const { bg, text, icon: Icon, label } = config[status];

  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${bg} ${text}`}>
      <Icon className="h-4 w-4" />
      {label}
    </span>
  );
}

function MetricCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon,
  trend,
  color = 'blue'
}: { 
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: 'up' | 'down' | 'stable';
  color?: 'blue' | 'green' | 'yellow' | 'red';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-900',
    green: 'bg-green-50 border-green-200 text-green-900',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-900',
    red: 'bg-red-50 border-red-200 text-red-900',
  };

  return (
    <div className={`rounded-lg border-2 p-6 ${colorClasses[color]}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <p className="text-sm font-medium opacity-80">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
          {subtitle && (
            <p className="text-sm opacity-70 mt-1">{subtitle}</p>
          )}
        </div>
        <Icon className="h-10 w-10 opacity-50" />
      </div>
      
      {trend && (
        <div className="flex items-center gap-1 text-xs font-medium">
          {trend === 'up' && <span className="text-green-600">↑ بهبود</span>}
          {trend === 'down' && <span className="text-red-600">↓ کاهش</span>}
          {trend === 'stable' && <span className="text-gray-600">→ ثابت</span>}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function GovernanceCenter() {
  const [selectedTab, setSelectedTab] = useState<'overview' | 'audit' | 'fail-closed' | 'mutations'>('overview');

  // Queries
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['governance', 'health'],
    queryFn: fetchGovernanceHealth,
    refetchInterval: 30000, // Refresh every 30s
  });

  const { data: auditMetrics, isLoading: auditLoading } = useQuery({
    queryKey: ['governance', 'audit'],
    queryFn: fetchAuditMetrics,
    refetchInterval: 30000,
  });

  const { data: failClosedEvents, isLoading: failClosedLoading } = useQuery({
    queryKey: ['governance', 'fail-closed'],
    queryFn: fetchFailClosedEvents,
    refetchInterval: 10000, // More frequent for critical events
  });

  const { data: mutationAuth, isLoading: mutationLoading } = useQuery({
    queryKey: ['governance', 'mutations'],
    queryFn: fetchMutationAuth,
    refetchInterval: 30000,
  });

  const isLoading = healthLoading || auditLoading || failClosedLoading || mutationLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">بارگذاری مرکز حکمرانی...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <ShieldCheckIcon className="h-8 w-8 text-blue-600" />
                مرکز حکمرانی
              </h1>
              <p className="text-gray-600 mt-1">
                نظارت بر سلامت قانون اساسی و انطباق سیستم
              </p>
            </div>
            
            {health && (
              <div className="flex items-center gap-4">
                <StatusBadge status={health.status} />
                <div className="text-right">
                  <div className="text-2xl font-bold text-gray-900">
                    {health.score}%
                  </div>
                  <div className="text-xs text-gray-500">
                    امتیاز انطباق
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <nav className="flex gap-8">
            {[
              { id: 'overview', label: 'نمای کلی', icon: ChartBarIcon },
              { id: 'audit', label: 'رویدادهای ممیزی', icon: DocumentTextIcon },
              { id: 'fail-closed', label: 'رویدادهای Fail-Closed', icon: BoltIcon },
              { id: 'mutations', label: 'مجوز تغییرات', icon: LockClosedIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedTab(tab.id as any)}
                className={`flex items-center gap-2 py-4 px-2 border-b-2 transition-colors ${
                  selectedTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {selectedTab === 'overview' && (
          <div className="space-y-8">
            {/* Key Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="وضعیت قانون اساسی"
                value={health?.score || 0}
                subtitle={`${health?.issues.length || 0} مشکل فعال`}
                icon={ShieldCheckIcon}
                color={health?.status === 'healthy' ? 'green' : health?.status === 'degraded' ? 'yellow' : 'red'}
                trend={health?.score && health.score > 90 ? 'up' : 'stable'}
              />
              
              <MetricCard
                title="رویدادهای ممیزی"
                value={auditMetrics?.totalEvents.toLocaleString('fa-IR') || '0'}
                subtitle={`${auditMetrics?.criticalEvents || 0} بحرانی`}
                icon={DocumentTextIcon}
                color="blue"
              />
              
              <MetricCard
                title="نرخ انطباق"
                value={`${auditMetrics?.complianceRate || 0}%`}
                subtitle="7 روز گذشته"
                icon={CheckCircleIcon}
                color={auditMetrics && auditMetrics.complianceRate > 95 ? 'green' : 'yellow'}
                trend={auditMetrics && auditMetrics.complianceRate > 95 ? 'up' : 'stable'}
              />
              
              <MetricCard
                title="درخواست‌های معلق"
                value={mutationAuth?.pendingRequests || 0}
                subtitle={`${mutationAuth?.averageReviewTime || 0}ms متوسط بررسی`}
                icon={ClockIcon}
                color={mutationAuth && mutationAuth.pendingRequests > 10 ? 'yellow' : 'green'}
              />
            </div>

            {/* Recent Issues */}
            {health && health.issues.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  مشکلات فعال
                </h2>
                <div className="space-y-3">
                  {health.issues.slice(0, 5).map((issue) => (
                    <div
                      key={issue.id}
                      className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200"
                    >
                      <ExclamationTriangleIcon 
                        className={`h-6 w-6 flex-shrink-0 ${
                          issue.severity === 'critical' ? 'text-red-600' :
                          issue.severity === 'high' ? 'text-orange-600' :
                          issue.severity === 'medium' ? 'text-yellow-600' :
                          'text-gray-600'
                        }`}
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-gray-900">{issue.category}</span>
                          <span className="text-xs text-gray-500">
                            {new Date(issue.timestamp).toLocaleString('fa-IR')}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{issue.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Fail-Closed Events Summary */}
            {failClosedEvents && failClosedEvents.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <BoltIcon className="h-6 w-6 text-yellow-600" />
                  رویدادهای Fail-Closed اخیر
                </h2>
                <div className="space-y-3">
                  {failClosedEvents.slice(0, 3).map((event) => (
                    <div
                      key={event.id}
                      className="flex items-start gap-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-gray-900">{event.type}</span>
                          {event.recovered && (
                            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded-full">
                              بازیابی شده
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 mb-1">{event.reason}</p>
                        <p className="text-xs text-gray-600">تاثیر: {event.impact}</p>
                      </div>
                      <span className="text-xs text-gray-500">
                        {new Date(event.timestamp).toLocaleString('fa-IR')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {selectedTab === 'audit' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              رویدادهای ممیزی
            </h2>
            <p className="text-gray-600">
              نمایش جزئیات رویدادهای ممیزی در حال توسعه...
            </p>
          </div>
        )}

        {selectedTab === 'fail-closed' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              رویدادهای Fail-Closed
            </h2>
            <p className="text-gray-600">
              نمایش جزئیات رویدادهای fail-closed در حال توسعه...
            </p>
          </div>
        )}

        {selectedTab === 'mutations' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              مجوز تغییرات
            </h2>
            {mutationAuth && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900">
                    {mutationAuth.riskDistribution.low}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">ریسک پایین</div>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-900">
                    {mutationAuth.riskDistribution.medium}
                  </div>
                  <div className="text-sm text-yellow-700 mt-1">ریسک متوسط</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-900">
                    {mutationAuth.riskDistribution.high}
                  </div>
                  <div className="text-sm text-orange-700 mt-1">ریسک بالا</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-900">
                    {mutationAuth.riskDistribution.critical}
                  </div>
                  <div className="text-sm text-red-700 mt-1">ریسک بحرانی</div>
                </div>
              </div>
            )}
            <p className="text-gray-600">
              نمایش جزئیات درخواست‌های تغییر در حال توسعه...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
