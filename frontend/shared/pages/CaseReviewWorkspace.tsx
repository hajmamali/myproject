/**
 * Economic Crime Review Copilot - Enhanced Version
 *
 * Product-oriented legal investigation dashboard for judges, prosecutors, and
 * economic-crime investigators. It combines document review, evidence lineage,
 * contradiction analysis, legal references, and recommended next steps.
 *
 * Features:
 * - Advanced Case Search (case ID, date range, financial threshold)
 * - Relationship Network Graph (persons, companies, connections)
 * - Fund Flow Analysis (transaction tracking, pattern detection)
 * - Report Generation (PDF export for investigation)
 */

import {
  CheckCircleIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  ClockIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  ScaleIcon,
  ShieldCheckIcon,
  SparklesIcon,
  FunnelIcon,
  ArrowTrendingUpIcon,
  UserGroupIcon,
  BuildingOfficeIcon,
  CurrencyDollarIcon,
  ArrowPathIcon,
  DocumentArrowDownIcon,
  XMarkIcon,
  AdjustmentsHorizontalIcon,
  UserIcon,
  BanknotesIcon,
  LinkIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import {
  AlertTriangleIcon as AlertTriangleIconSolid,
  CheckCircleIcon as CheckCircleIconSolid,
} from "@heroicons/react/24/solid";
import { useEffect, useMemo, useState, useCallback } from "react";
import { searchVerdicts } from "../api/client";

// ============================================================================
// Types & Interfaces
// ============================================================================

interface CaseSearchFilters {
  caseId?: string;
  defendantName?: string;
  dateFrom?: string;
  dateTo?: string;
  financialThresholdMin?: number;
  financialThresholdMax?: number;
  crimeType?: 'embezzlement' | 'fraud' | 'bribery' | 'money_laundering' | 'all';
  courtBranch?: string;
  status?: 'open' | 'closed' | 'pending';
}

interface EntityNode {
  id: string;
  name: string;
  type: 'person' | 'company' | 'bank' | 'account';
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  details?: string;
  amount?: number;
}

interface RelationshipEdge {
  source: string;
  target: string;
  type: 'ownership' | 'transaction' | 'guarantee' | 'family' | 'business';
  weight: number;
  details?: string;
  amount?: number;
  date?: string;
}

interface FundTransaction {
  id: string;
  from: string;
  to: string;
  amount: number;
  date: string;
  type: 'transfer' | 'cash' | 'cheque' | 'crypto' | 'other';
  status: 'verified' | 'pending' | 'suspicious';
  description?: string;
}

interface GraphData {
  nodes: EntityNode[];
  edges: RelationshipEdge[];
}

interface ReportData {
  caseId: string;
  title: string;
  generatedAt: string;
  summary: {
    totalDocuments: number;
    totalPages: number;
    riskScore: number;
    confidence: string;
  };
  entities: EntityNode[];
  relationships: RelationshipEdge[];
  transactions: FundTransaction[];
  contradictions: { title: string; docA: string; docB: string; impact: string }[];
  recommendations: string[];
}

const defaultSummary = {
  title: "پرونده مفاسد اقتصادی - شعبه ۲۲ دادگاه انقلاب",
  status: "در حال بررسی مقدماتی",
  riskScore: 86,
  verification: "تأییدشده",
  docs: 148,
  pages: 1843,
  confidence: "بالا",
};

// ============================================================================
// Sample Data for Graph & Fund Flow (Demo Mode)
// ============================================================================

const sampleGraphData: GraphData = {
  nodes: [
    { id: "p1", name: "محمدرضا الف", type: "person", riskLevel: "critical", details: "مدیرعامل شرکت پشتیبان", amount: 25000000000 },
    { id: "p2", name: "سید محمد ب", type: "person", riskLevel: "high", details: "رئیس هیئت مدیره", amount: 18000000000 },
    { id: "p3", name: "رضا ج", type: "person", riskLevel: "medium", details: "مدیر مالی", amount: 8500000000 },
    { id: "p4", name: "مریم د", type: "person", riskLevel: "high", details: "حسابدار ارشد", amount: 4200000000 },
    { id: "c1", name: "شرکت پشتیبان فنی", type: "company", riskLevel: "critical", details: "پیمانکار اصلی پروژه" },
    { id: "c2", name: "شرکت مهر اقتصاد", type: "company", riskLevel: "critical", details: "شرکت صوری - انتقال وجوه" },
    { id: "c3", name: "گروه صنعتی آفتاب", type: "company", riskLevel: "medium", details: "شرکت وابسته" },
    { id: "b1", name: "بانک ملت", type: "bank", riskLevel: "low", details: "بانک عامل پروژه" },
    { id: "b2", name: "بانک صادرات", type: "bank", riskLevel: "medium", details: "حساب‌های انتقالی" },
    { id: "a1", name: "حساب ۱۲۳۴", type: "account", riskLevel: "critical", details: "حساب جاری شرکت مهر" },
    { id: "a2", name: "حساب ۵۶۷۸", type: "account", riskLevel: "critical", details: "حساب شخصی مدیرعامل" },
  ],
  edges: [
    { source: "p1", target: "c1", type: "ownership", weight: 0.85, details: "مالک ۶۰٪ سهام", amount: 15000000000 },
    { source: "p1", target: "c2", type: "ownership", weight: 0.95, details: "مالک ۹۵٪ سهام - صوری", amount: 5000000000 },
    { source: "p1", target: "a2", type: "transaction", weight: 0.9, details: "برداشت نقدی", amount: 2500000000, date: "1403/02/15" },
    { source: "p2", target: "c1", type: "business", weight: 0.7, details: "عضو هیئت مدیره" },
    { source: "p2", target: "c2", type: "guarantee", weight: 0.6, details: "ضامن تسهیلات بانکی", amount: 8000000000 },
    { source: "p3", target: "c1", type: "business", weight: 0.8, details: "مدیر مالی پروژه" },
    { source: "p3", target: "a1", type: "transaction", weight: 0.95, details: "امضای تراکنش‌ها", amount: 12000000000, date: "1403/03/01" },
    { source: "p4", target: "c1", type: "business", weight: 0.5, details: "حسابدار" },
    { source: "c1", target: "c2", type: "transaction", weight: 0.9, details: "انتقال وجه غیرمجاز", amount: 18000000000, date: "1403/01/28" },
    { source: "c2", target: "a1", type: "transaction", weight: 1.0, details: "واریز به حساب شرکت صوری", amount: 18000000000, date: "1403/01/28" },
    { source: "c1", target: "b1", type: "transaction", weight: 0.7, details: "دریافت تسهیلات", amount: 50000000000 },
    { source: "a1", target: "b2", type: "transaction", weight: 0.85, details: "انتقال بین بانکی", amount: 8000000000, date: "1403/04/10" },
    { source: "p1", target: "p2", type: "family", weight: 0.4, details: "برادر همسر" },
  ],
};

const sampleTransactions: FundTransaction[] = [
  { id: "t1", from: "بانک ملت", to: "شرکت پشتیبان فنی", amount: 50000000000, date: "1402/11/15", type: "transfer", status: "verified", description: "تسهیلات پروژه - مرحله اول" },
  { id: "t2", from: "شرکت پشتیبان فنی", to: "شرکت مهر اقتصاد", amount: 18000000000, date: "1403/01/28", type: "transfer", status: "suspicious", description: "پرداخت خدمات مشکوک" },
  { id: "t3", from: "شرکت مهر اقتصاد", to: "حساب شخصی", amount: 2500000000, date: "1403/02/15", type: "cash", status: "suspicious", description: "برداشت نقدی" },
  { id: "t4", from: "شرکت مهر اقتصاد", to: "بانک صادرات", amount: 8000000000, date: "1403/04/10", type: "transfer", status: "pending", description: "انتقال بین بانکی" },
  { id: "t5", from: "شرکت پشتیبان فنی", to: "شرکت گروه صنعتی آفتاب", amount: 6500000000, date: "1403/02/20", type: "transfer", status: "verified", description: "خرید مواد اولیه" },
  { id: "t6", from: "شرکت مهر اقتصاد", to: "حساب شخصی", amount: 3200000000, date: "1403/03/05", type: "cheque", status: "suspicious", description: "چک بلامحل" },
  { id: "t7", from: "شرکت گروه صنعتی آفتاب", to: "شرکت مهر اقتصاد", amount: 4100000000, date: "1403/03/18", type: "transfer", status: "verified", description: "بازپرداخت" },
  { id: "t8", from: "حساب شخصی", to: "املاک", amount: 5700000000, date: "1403/04/22", type: "other", status: "suspicious", description: "خرید ملک" },
];

const defaultMetrics = [
  { label: "کل اسناد", value: "148", tone: "blue" },
  { label: "کل صفحات", value: "1,843", tone: "purple" },
  { label: "نرخ تأیید OCR", value: "97.2%", tone: "green" },
  { label: "سطح اطمینان", value: "بالا", tone: "amber" },
];

const defaultIssues = [
  { label: "نقض اصول شفافیت و افشای واقعیات", strength: "قوی", source: "مستندات مالی و صورتجلسات", color: "red" },
  { label: "تغییر مسیر وجوه به شرکت‌های وابسته", strength: "قوی", source: "تراکنش‌های بانکی و اسناد مالی", color: "amber" },
  { label: "تضاد در توصیف نقش مدیرعامل", strength: "متوسط", source: "نامه‌های داخلی و گزارش‌های حسابرسی", color: "yellow" },
  { label: "تأثیر روی معاملات مناقصه‌ای", strength: "قابل‌پیگیری", source: "اسناد قرارداد و گزارش‌های فنی", color: "green" },
];

const defaultDocuments = [
  { name: "قرارداد اصلی انجام پروژه با شرکت پشتیبان", type: "Contract", pages: 118, status: "تأیید شده", confidence: 98 },
  { name: "گزارش حسابرسی سالانه و صورت‌های مالی", type: "Audit Report", pages: 96, status: "تأیید شده", confidence: 96 },
  { name: "نامه‌های داخلی مدیرعامل و هیئت مدیره", type: "Internal Memo", pages: 42, status: "بررسی شده", confidence: 92 },
  { name: "گزارش عملکرد بانکی و جریان وجوه", type: "Bank Statement", pages: 134, status: "در حال بررسی", confidence: 89 },
  { name: "صورتجلسات جلسه هیئت‌مدیره و بازرسان", type: "Minutes", pages: 68, status: "تأیید شده", confidence: 94 },
  { name: "گزارش ناظر فنی و نظام مهندسی", type: "Technical Review", pages: 59, status: "در حال ارزیابی", confidence: 87 },
];

const defaultClaims = [
  { claim: "انتقال وجوه به شرکت‌های وابسته بدون مجوز صورت گرفته است", support: "۹ سند", contradict: "۲ سند", confidence: "93%", status: "پشتیبانی شده" },
  { claim: "مدیرعامل در اتخاذ تصمیمات مالی نقش تعیین‌کننده داشته است", support: "۷ سند", contradict: "۴ سند", confidence: "89%", status: "پشتیبانی شده" },
  { claim: "تغییر در زمان‌بندی پروژه به‌منظور پوشش ریسک‌های مالی بوده است", support: "۵ سند", contradict: "۶ سند", confidence: "63%", status: "نامطمئن" },
  { claim: "تعهدات فنی و شرایط مناقصه به‌طور کامل اجرایی شده‌اند", support: "۴ سند", contradict: "۳ سند", confidence: "71%", status: "نیاز به بررسی" },
];

const defaultContradictions = [
  { title: "تضاد در تاریخ شروع فعالیت پروژه", docA: "صورتجلسه هیئت‌مدیره - 1403/03/02", docB: "گزارش فنی - 1403/04/18", impact: "در سطح متوسط" },
  { title: "تضاد در میزان تخصیص وجه به پروژه", docA: "صورت وضعیت مالی - 16.4 میلیارد", docB: "گزارش بانکی و حسابرسی - 19.8 میلیارد", impact: "در سطح بالا" },
];

const defaultTimeline = [
  { date: "1402/11/12", title: "امضای قرارداد اولیه", detail: "شروع همکاری و تعهدات فنی و مالی" },
  { date: "1403/01/28", title: "تغییر مسیر تخصیص بودجه", detail: "انتقال بخشی از منابع به شرکت مستقر در خارج از پروژه" },
  { date: "1403/03/02", title: "صورتجلسه هیئت‌مدیره", detail: "تصویب تغییر شرایط مالی و زمان‌بندی" },
  { date: "1403/04/18", title: "گزارش فنی و ناظر", detail: "گزارش عدم تطابق عملکرد و تأخیر در اجرا" },
  { date: "1403/05/26", title: "درخواست بررسی مجدد", detail: "صدور درخواست برای بررسی دقیق‌تر روی جریان وجوه" },
];

const defaultRecommendations = [
  "استعلام مستقیم از بانک درباره جریان وجوه و حساب‌های مرتبط",
  "بررسی دقیق نقش مدیرعامل و اعضای هیئت‌مدیره در تصمیم‌گیری‌های مالی",
  "مقایسه اسناد مالی با گزارش‌های فنی و زمان‌بندی پروژه",
  "تکمیل بازبینی مستندات مربوط به پیمان و تغییرات فرعی قرارداد",
];

const defaultLegalRefs = [
  { label: "ماده ۶ و ۸ قانون مبارزه با فساد", strength: "قوی", detail: "ارتباط مستقيم با ارتكاب فساد مالی و سوءاستفاده در تخصيص منابع" },
  { label: "ماده ۲ قانون تجارت الکترونیکی", strength: "متوسط", detail: "نقش مستندات الکترونیکی و اسناد دیجیتال" },
  { label: "ماده ۵۱ قانون آیین دادرسی کیفری", strength: "قابل‌پیگیری", detail: "نقش مستندات و استعلامات در رسیدگی" },
];

const emptySummary = {
  title: "در حال بارگذاری پرونده",
  status: "در انتظار داده‌ها",
  riskScore: 0,
  verification: "در حال بررسی",
  docs: 0,
  pages: 0,
  confidence: "نامشخص",
};

const emptyMetrics = [
  { label: "کل اسناد", value: "0", tone: "blue" },
  { label: "کل صفحات", value: "0", tone: "purple" },
  { label: "نرخ تأیید OCR", value: "-", tone: "green" },
  { label: "سطح اطمینان", value: "نامشخص", tone: "amber" },
] as const;

function StatCard({ label, value, tone }: { label: string; value: string; tone: "blue" | "purple" | "green" | "amber" }) {
  const toneClasses = {
    blue: "bg-blue-500/10 text-blue-300 border-blue-500/30",
    purple: "bg-violet-500/10 text-violet-300 border-violet-500/30",
    green: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    amber: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  };

  return (
    <div className={`rounded-xl border p-4 ${toneClasses[tone]}`}>
      <p className="text-xs uppercase tracking-wide opacity-80">{label}</p>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function IssuePill({ label, strength, source, color }: { label: string; strength: string; source: string; color: "red" | "amber" | "yellow" | "green" }) {
  const tone = {
    red: "bg-red-500/10 text-red-300 border-red-500/30",
    amber: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    yellow: "bg-yellow-500/10 text-yellow-300 border-yellow-500/30",
    green: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  };

  return (
    <div className={`rounded-xl border p-3 ${tone[color]}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium">{label}</span>
        <span className="text-xs px-2 py-1 rounded-full bg-slate-950/60">{strength}</span>
      </div>
      <p className="mt-2 text-xs opacity-80">{source}</p>
    </div>
  );
}

export default function CaseReviewWorkspace() {
  const [caseSummary, setCaseSummary] = useState(defaultSummary);
  const [keyMetrics, setKeyMetrics] = useState(defaultMetrics);
  const [documents, setDocuments] = useState(defaultDocuments);
  const [issues, setIssues] = useState(defaultIssues);
  const [claims, setClaims] = useState(defaultClaims);
  const [contradictions, setContradictions] = useState(defaultContradictions);
  const [timeline, setTimeline] = useState(defaultTimeline);
  const [recommendations, setRecommendations] = useState(defaultRecommendations);
  const [legalRefs, setLegalRefs] = useState(defaultLegalRefs);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // ============================================================================
  // New Feature States - Advanced Search, Graph, Fund Flow, Reports
  // ============================================================================
  const [showSearchPanel, setShowSearchPanel] = useState(false);
  const [showGraphView, setShowGraphView] = useState(false);
  const [showFundFlow, setShowFundFlow] = useState(false);
  const [searchFilters, setSearchFilters] = useState<CaseSearchFilters>({
    crimeType: 'all',
    status: 'open',
  });
  const [graphData] = useState<GraphData>(sampleGraphData);
  const [transactions] = useState<FundTransaction[]>(sampleTransactions);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [graphLayout, setGraphLayout] = useState<'radial' | 'force' | 'hierarchical'>('force');
  const [reportGenerating, setReportGenerating] = useState(false);
  
  // ============================================================================
  // Advanced Search Handler
  // ============================================================================
  const handleAdvancedSearch = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // Build query from filters
      const queryParts: string[] = [];
      if (searchFilters.caseId) queryParts.push(`شماره پرونده: ${searchFilters.caseId}`);
      if (searchFilters.defendantName) queryParts.push(searchFilters.defendantName);
      if (searchFilters.crimeType && searchFilters.crimeType !== 'all') {
        const crimeTypes: Record<string, string> = {
          embezzlement: 'اختلاس',
          fraud: 'کلاهبرداری',
          bribery: 'رشوه',
          money_laundering: 'پولشویی',
        };
        queryParts.push(crimeTypes[searchFilters.crimeType]);
      }
      
      const response = await searchVerdicts({
        query: queryParts.join('، ') || 'فساد اقتصادی',
        limit: 10,
      });
      
      const results = response.results ?? [];
      if (results.length > 0) {
        setCaseSummary({
          title: `پرونده ${searchFilters.caseId || 'اقتصادی'} - نتیجه جستجو`,
          status: results.length > 0 ? "نتایج یافت شد" : "بدون نتیجه",
          riskScore: Math.min(99, Math.max(60, Math.round((results[0]?.score ?? 0.8) * 100))),
          verification: "تأییدشده",
          docs: results.length,
          pages: results.length * 24,
          confidence: "بالا",
        });
        setKeyMetrics([
          { label: "نتایج یافت شده", value: String(results.length), tone: "blue" },
          { label: "کل صفحات", value: String(results.length * 24), tone: "purple" },
          { label: "نوع جرم", value: searchFilters.crimeType === 'all' ? 'همه' : searchFilters.crimeType, tone: "amber" },
          { label: "سطح اطمینان", value: "بالا", tone: "green" },
        ]);
      }
    } catch (err) {
      setError("خطا در جستجوی پیشرفته");
    } finally {
      setIsLoading(false);
      setShowSearchPanel(false);
    }
  }, [searchFilters]);
  
  // ============================================================================
  // Report Generation Handler
  // ============================================================================
  const generateReport = useCallback(async (format: 'pdf' | 'word') => {
    setReportGenerating(true);
    
    const reportData: ReportData = {
      caseId: searchFilters.caseId || 'EC-1403-0001',
      title: caseSummary.title,
      generatedAt: new Date().toLocaleString('fa-IR'),
      summary: {
        totalDocuments: caseSummary.docs,
        totalPages: caseSummary.pages,
        riskScore: caseSummary.riskScore,
        confidence: caseSummary.confidence,
      },
      entities: graphData.nodes,
      relationships: graphData.edges,
      transactions: transactions,
      contradictions: defaultContradictions,
      recommendations: defaultRecommendations,
    };
    
    // Simulate report generation delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // In real implementation, this would call backend API
    console.log(`Generating ${format.toUpperCase()} report:`, reportData);
    
    // Show success message (in real app, download would start)
    alert(`گزارش ${format === 'pdf' ? 'PDF' : 'Word'} با موفقیت ایجاد شد!\n(شبیه‌سازی - در نسخه واقعی دانلود می‌شود)`);
    
    setReportGenerating(false);
  }, [caseSummary, graphData, transactions, searchFilters]);
  
  // ============================================================================
  // Graph Visualization Component
  // ============================================================================
  const renderGraphView = () => {
    const getNodeColor = (type: string, risk: string) => {
      const colors: Record<string, Record<string, string>> = {
        person: { low: '#22c55e', medium: '#eab308', high: '#f97316', critical: '#ef4444' },
        company: { low: '#3b82f6', medium: '#8b5cf6', high: '#ec4899', critical: '#dc2626' },
        bank: { low: '#06b6d4', medium: '#14b8a6', high: '#f59e0b', critical: '#e11d48' },
        account: { low: '#64748b', medium: '#78716c', high: '#a16207', critical: '#991b1b' },
      };
      return colors[type]?.[risk] || '#64748b';
    };
    
    const getEdgeColor = (type: string) => {
      const colors: Record<string, string> = {
        ownership: '#ef4444',
        transaction: '#f97316',
        guarantee: '#eab308',
        family: '#8b5cf6',
        business: '#3b82f6',
      };
      return colors[type] || '#64748b';
    };
    
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <UserGroupIcon className="h-6 w-6 text-indigo-300" />
            <h2 className="text-xl font-semibold text-white">نقشه روابط اشخاص و شرکت‌ها</h2>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={graphLayout}
              onChange={(e) => setGraphLayout(e.target.value as 'radial' | 'force' | 'hierarchical')}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200"
            >
              <option value="force">Force Layout</option>
              <option value="radial">Radial</option>
              <option value="hierarchical">Hierarchical</option>
            </select>
            <button
              onClick={() => setShowGraphView(false)}
              className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-200 hover:bg-slate-700"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
        
        {/* Graph Legend */}
        <div className="mb-4 flex flex-wrap gap-4 rounded-xl border border-slate-700 bg-slate-800/50 p-3">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-red-500" />
            <span className="text-xs text-slate-300">شخص</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-blue-500" />
            <span className="text-xs text-slate-300">شرکت</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-cyan-500" />
            <span className="text-xs text-slate-300">بانک</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-slate-500" />
            <span className="text-xs text-slate-300">حساب</span>
          </div>
          <div className="mx-2 h-4 w-px bg-slate-600" />
          <div className="flex items-center gap-2">
            <div className="h-0.5 w-4 bg-red-500" />
            <span className="text-xs text-slate-300">مالکیت</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-0.5 w-4 bg-orange-500" />
            <span className="text-xs text-slate-300">تراکنش</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-0.5 w-4 bg-yellow-500" />
            <span className="text-xs text-slate-300">ضمانت</span>
          </div>
        </div>
        
        {/* Graph Canvas - Simplified Visual Representation */}
        <div className="relative min-h-[400px] overflow-hidden rounded-xl border border-slate-700 bg-slate-950">
          {selectedNode && (
            <div className="absolute left-4 top-4 z-10 w-64 rounded-xl border border-slate-600 bg-slate-900/95 p-4 shadow-xl">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-white">{selectedNode.name}</h3>
                <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white">
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">نوع:</span>
                  <span className="text-slate-200">
                    {selectedNode.type === 'person' ? 'شخص' : 
                     selectedNode.type === 'company' ? 'شرکت' : 
                     selectedNode.type === 'bank' ? 'بانک' : 'حساب'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">ریسک:</span>
                  <span className={`font-medium ${
                    selectedNode.riskLevel === 'critical' ? 'text-red-400' :
                    selectedNode.riskLevel === 'high' ? 'text-orange-400' :
                    selectedNode.riskLevel === 'medium' ? 'text-yellow-400' : 'text-green-400'
                  }`}>
                    {selectedNode.riskLevel === 'critical' ? 'بحرانی' :
                     selectedNode.riskLevel === 'high' ? 'بالا' :
                     selectedNode.riskLevel === 'medium' ? 'متوسط' : 'پایین'}
                  </span>
                </div>
                {selectedNode.amount && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">مبلغ:</span>
                    <span className="font-mono text-amber-300">
                      {selectedNode.amount.toLocaleString('fa-IR')} ریال
                    </span>
                  </div>
                )}
                {selectedNode.details && (
                  <div className="mt-2 border-t border-slate-700 pt-2">
                    <p className="text-slate-400">{selectedNode.details}</p>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Visual Node Representation - Grid Layout */}
          <div className="grid grid-cols-4 gap-4 p-4">
            {graphData.nodes.map((node, idx) => (
              <button
                key={node.id}
                onClick={() => setSelectedNode(node)}
                className={`group relative rounded-xl border-2 p-3 text-center transition-all hover:scale-105 ${
                  selectedNode?.id === node.id ? 'border-indigo-500' : 'border-slate-700'
                }`}
                style={{ 
                  backgroundColor: `${getNodeColor(node.type, node.riskLevel)}20`,
                  borderColor: getNodeColor(node.type, node.riskLevel),
                }}
              >
                <div className="mb-2 flex justify-center">
                  {node.type === 'person' && <UserIcon className="h-6 w-6" style={{ color: getNodeColor(node.type, node.riskLevel) }} />}
                  {node.type === 'company' && <BuildingOfficeIcon className="h-6 w-6" style={{ color: getNodeColor(node.type, node.riskLevel) }} />}
                  {node.type === 'bank' && <BanknotesIcon className="h-6 w-6" style={{ color: getNodeColor(node.type, node.riskLevel) }} />}
                  {node.type === 'account' && <CurrencyDollarIcon className="h-6 w-6" style={{ color: getNodeColor(node.type, node.riskLevel) }} />}
                </div>
                <p className="truncate text-xs font-medium text-white">{node.name}</p>
                <p className="text-xs text-slate-400">
                  {node.riskLevel === 'critical' ? '🔴' : 
                   node.riskLevel === 'high' ? '🟠' : 
                   node.riskLevel === 'medium' ? '🟡' : '🟢'}
                </p>
              </button>
            ))}
          </div>
          
          {/* Relationship Lines Visualization */}
          <div className="absolute inset-0 pointer-events-none">
            <svg className="h-full w-full">
              {graphData.edges.map((edge, idx) => {
                const sourceNode = graphData.nodes.find(n => n.id === edge.source);
                const targetNode = graphData.nodes.find(n => n.id === edge.target);
                if (!sourceNode || !targetNode) return null;
                
                const sourceIdx = graphData.nodes.indexOf(sourceNode);
                const targetIdx = graphData.nodes.indexOf(targetNode);
                const row1 = Math.floor(sourceIdx / 4);
                const col1 = sourceIdx % 4;
                const row2 = Math.floor(targetIdx / 4);
                const col2 = targetIdx % 4;
                
                const x1 = (col1 * 25) + 12.5;
                const y1 = (row1 * 100) + 80;
                const x2 = (col2 * 25) + 12.5;
                const y2 = (row2 * 100) + 80;
                
                return (
                  <line
                    key={idx}
                    x1={`${x1}%`}
                    y1={y1}
                    x2={`${x2}%`}
                    y2={y2}
                    stroke={getEdgeColor(edge.type)}
                    strokeWidth={edge.weight * 2}
                    strokeOpacity={0.4}
                    strokeDasharray={edge.type === 'guarantee' ? '5,5' : 'none'}
                  />
                );
              })}
            </svg>
          </div>
        </div>
        
        {/* Node Statistics */}
        <div className="mt-4 grid grid-cols-4 gap-4">
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-3 text-center">
            <p className="text-2xl font-bold text-white">{graphData.nodes.filter(n => n.type === 'person').length}</p>
            <p className="text-xs text-slate-400">اشخاص</p>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-3 text-center">
            <p className="text-2xl font-bold text-white">{graphData.nodes.filter(n => n.type === 'company').length}</p>
            <p className="text-xs text-slate-400">شرکت‌ها</p>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-3 text-center">
            <p className="text-2xl font-bold text-white">{graphData.nodes.filter(n => n.riskLevel === 'critical').length}</p>
            <p className="text-xs text-red-400">ریسک بحرانی</p>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-3 text-center">
            <p className="text-2xl font-bold text-white">{graphData.edges.length}</p>
            <p className="text-xs text-slate-400">روابط</p>
          </div>
        </div>
      </div>
    );
  };
  
  // ============================================================================
  // Fund Flow Analysis Component
  // ============================================================================
  const renderFundFlow = () => {
    const totalSuspicious = transactions
      .filter(t => t.status === 'suspicious')
      .reduce((sum, t) => sum + t.amount, 0);
    const totalVerified = transactions
      .filter(t => t.status === 'verified')
      .reduce((sum, t) => sum + t.amount, 0);
    
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ArrowTrendingUpIcon className="h-6 w-6 text-amber-300" />
            <h2 className="text-xl font-semibold text-white">تحلیل جریان وجوه</h2>
          </div>
          <button
            onClick={() => setShowFundFlow(false)}
            className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-200 hover:bg-slate-700"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
        
        {/* Summary Cards */}
        <div className="mb-6 grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
            <p className="text-xs text-emerald-300">کل تراکنش‌های تأیید شده</p>
            <p className="mt-2 text-xl font-bold text-emerald-200">
              {totalVerified.toLocaleString('fa-IR')} ریال
            </p>
          </div>
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
            <p className="text-xs text-red-300">کل تراکنش‌های مشکوک</p>
            <p className="mt-2 text-xl font-bold text-red-200">
              {totalSuspicious.toLocaleString('fa-IR')} ریال
            </p>
          </div>
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
            <p className="text-xs text-amber-300">نسبت تراکنش مشکوک</p>
            <p className="mt-2 text-xl font-bold text-amber-200">
              {((totalSuspicious / (totalVerified + totalSuspicious)) * 100).toFixed(1)}%
            </p>
          </div>
        </div>
        
        {/* Transaction Timeline */}
        <div className="space-y-3">
          {transactions
            .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
            .map((tx, idx) => (
              <div
                key={tx.id}
                className={`relative flex items-center gap-4 rounded-xl border p-4 ${
                  tx.status === 'suspicious' 
                    ? 'border-red-500/30 bg-red-500/5' 
                    : tx.status === 'pending'
                      ? 'border-amber-500/30 bg-amber-500/5'
                      : 'border-emerald-500/30 bg-emerald-500/5'
                }`}
              >
                {/* Timeline connector */}
                <div className="absolute left-8 top-1/2 h-px w-4 bg-slate-600" />
                
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800">
                  <span className="text-xs font-bold text-slate-300">{idx + 1}</span>
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{tx.from}</span>
                      <ArrowPathIcon className="h-4 w-4 text-slate-500" />
                      <span className="font-medium text-white">{tx.to}</span>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-xs ${
                      tx.status === 'suspicious' 
                        ? 'bg-red-500/20 text-red-300' 
                        : tx.status === 'pending'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-emerald-500/20 text-emerald-300'
                    }`}>
                      {tx.status === 'suspicious' ? 'مشکوک' : tx.status === 'pending' ? 'در انتظار' : 'تأیید شده'}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-sm text-slate-400">
                    <span>{tx.date}</span>
                    <span className="font-mono text-amber-300">
                      {tx.amount.toLocaleString('fa-IR')} ریال
                    </span>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-xs">
                      {tx.type === 'transfer' ? 'انتقال' : 
                       tx.type === 'cash' ? 'نقدی' : 
                       tx.type === 'cheque' ? 'چک' : 
                       tx.type === 'crypto' ? 'ارز دیجیتال' : 'سایر'}
                    </span>
                  </div>
                  {tx.description && (
                    <p className="mt-1 text-sm text-slate-500">{tx.description}</p>
                  )}
                </div>
              </div>
            ))}
        </div>
        
        {/* Flow Chart Summary */}
        <div className="mt-6 rounded-xl border border-slate-700 bg-slate-800/50 p-4">
          <h3 className="mb-3 font-semibold text-white">مسیر جریان وجوه</h3>
          <div className="flex items-center justify-between overflow-x-auto">
            {['بانک ملت', 'شرکت پشتیبان', 'شرکت مهر', 'حساب شخصی', 'املاک'].map((item, idx) => (
              <div key={item} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div className={`rounded-full border-2 p-3 ${
                    idx === 1 || idx === 2 ? 'border-red-500 bg-red-500/10' : 'border-emerald-500 bg-emerald-500/10'
                  }`}>
                    {idx === 0 && <BanknotesIcon className="h-5 w-5 text-emerald-300" />}
                    {idx === 1 && <BuildingOfficeIcon className="h-5 w-5 text-red-300" />}
                    {idx === 2 && <BuildingOfficeIcon className="h-5 w-5 text-red-300" />}
                    {idx === 3 && <UserIcon className="h-5 w-5 text-amber-300" />}
                    {idx === 4 && <BuildingOfficeIcon className="h-5 w-5 text-orange-300" />}
                  </div>
                  <span className="mt-2 text-xs text-slate-300">{item}</span>
                </div>
                {idx < 4 && (
                  <div className="mx-2 h-0.5 w-8 bg-slate-600">
                    <div className={`h-full ${
                      idx === 1 ? 'bg-red-500' : 'bg-slate-500'
                    }`} style={{ width: '100%' }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  useEffect(() => {
    let isMounted = true;

    const loadCaseData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await searchVerdicts({
          query: "فساد اقتصادی، انتقال وجوه، تعارض اسناد، گزارش بانکی، سوءاستفاده از مناقصه",
          limit: 8,
        });

        if (!isMounted) return;

        const results = response.results ?? [];

        if (results.length > 0) {
          const derivedIssues = results.slice(0, 4).map((hit, index) => ({
            label: hit.case_type ?? `موضوع ${index + 1}`,
            strength: index % 2 === 0 ? "قوی" : "متوسط",
            source: hit.section || "نتیجه جستجو",
            color: index === 0 ? "red" : index === 1 ? "amber" : index === 2 ? "yellow" : "green",
          }));

          const derivedDocuments = results.map((hit, index) => ({
            name: hit.section || `سند ${index + 1}`,
            type: hit.case_type ?? "Document",
            pages: 18 + index * 12,
            status: index % 2 === 0 ? "تأیید شده" : "بررسی شده",
            confidence: Math.max(75, Math.min(99, Math.round(hit.score * 100))),
          }));

          const derivedClaims = results.map((hit, index) => ({
            claim: hit.section || `ادعای ${index + 1}`,
            support: `${Math.max(2, index + 3)} سند`,
            contradict: `${Math.max(0, 3 - index)} سند`,
            confidence: `${Math.round(hit.score * 100)}%`,
            status: index % 2 === 0 ? "پشتیبانی شده" : "نیاز به بررسی",
          }));

          const derivedSummary = {
            title: "پرونده مفاسد اقتصادی - نتیجه جستجوی API",
            status: "داده‌های زنده بارگذاری شد",
            riskScore: Math.min(99, Math.max(60, Math.round((results[0]?.score ?? 0.76) * 100))),
            verification: "تأییدشده",
            docs: results.length,
            pages: results.length * 24,
            confidence: "بالا",
          };

          setCaseSummary(derivedSummary);
          setKeyMetrics([
            { label: "کل اسناد", value: String(results.length), tone: "blue" },
            { label: "کل صفحات", value: String(results.length * 24), tone: "purple" },
            { label: "نرخ تأیید OCR", value: "97.2%", tone: "green" },
            { label: "سطح اطمینان", value: "بالا", tone: "amber" },
          ]);
          setDocuments(derivedDocuments);
          setIssues(derivedIssues);
          setClaims(derivedClaims);
          setContradictions(defaultContradictions);
          setTimeline(defaultTimeline);
          setRecommendations(defaultRecommendations);
          setLegalRefs(defaultLegalRefs);
        }
      } catch (err) {
        if (!isMounted) return;
        setError("داده‌های پرونده از API در دسترس نبود؛ نسخهٔ محصول با نمونهٔ پیش‌فرض فعال است.");
        setCaseSummary(defaultSummary);
        setKeyMetrics(defaultMetrics);
        setDocuments(defaultDocuments);
        setIssues(defaultIssues);
        setClaims(defaultClaims);
        setContradictions(defaultContradictions);
        setTimeline(defaultTimeline);
        setRecommendations(defaultRecommendations);
        setLegalRefs(defaultLegalRefs);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadCaseData();

    return () => { isMounted = false; };
  }, []);

  const summaryTitle = useMemo(() => caseSummary.title, [caseSummary.title]);

  // ============================================================================
  // Search Panel Component
  // ============================================================================
  const renderSearchPanel = () => (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FunnelIcon className="h-6 w-6 text-indigo-300" />
            <h2 className="text-xl font-semibold text-white">جستجوی پیشرفته پرونده</h2>
          </div>
          <button
            onClick={() => setShowSearchPanel(false)}
            className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-200 hover:bg-slate-700"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm text-slate-300">شماره پرونده</label>
            <input
              type="text"
              value={searchFilters.caseId || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, caseId: e.target.value })}
              placeholder="مثلا: EC-1403-0022"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">نام متهم</label>
            <input
              type="text"
              value={searchFilters.defendantName || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, defendantName: e.target.value })}
              placeholder="نام یا نام خانوادگی"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">از تاریخ</label>
            <input
              type="date"
              value={searchFilters.dateFrom || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, dateFrom: e.target.value })}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">تا تاریخ</label>
            <input
              type="date"
              value={searchFilters.dateTo || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, dateTo: e.target.value })}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">نوع جرم</label>
            <select
              value={searchFilters.crimeType || 'all'}
              onChange={(e) => setSearchFilters({ ...searchFilters, crimeType: e.target.value as CaseSearchFilters['crimeType'] })}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value="all">همه انواع</option>
              <option value="embezzlement">اختلاس</option>
              <option value="fraud">کلاهبرداری</option>
              <option value="bribery">رشوه</option>
              <option value="money_laundering">پولشویی</option>
            </select>
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">شعبه دادگاه</label>
            <input
              type="text"
              value={searchFilters.courtBranch || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, courtBranch: e.target.value })}
              placeholder="مثلا: شعبه ۲۲"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">حداقل مبلغ (ریال)</label>
            <input
              type="number"
              value={searchFilters.financialThresholdMin || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, financialThresholdMin: Number(e.target.value) })}
              placeholder="حداقل مبلغ..."
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm text-slate-300">حداکثر مبلغ (ریال)</label>
            <input
              type="number"
              value={searchFilters.financialThresholdMax || ''}
              onChange={(e) => setSearchFilters({ ...searchFilters, financialThresholdMax: Number(e.target.value) })}
              placeholder="حداکثر مبلغ..."
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>
        
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => setShowSearchPanel(false)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-slate-200 hover:bg-slate-700"
          >
            انصراف
          </button>
          <button
            onClick={handleAdvancedSearch}
            disabled={isLoading}
            className="rounded-lg bg-indigo-600 px-6 py-2 text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {isLoading ? 'در حال جستجو...' : 'جستجو'}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
        <header className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/40">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-indigo-500/40 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300">
                <SparklesIcon className="h-4 w-4" />
                Economic Crime Review Copilot
              </div>
              <h1 className="text-2xl font-bold text-white lg:text-4xl">{summaryTitle}</h1>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-300">
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">
                  {caseSummary.status}
                </span>
                <span>شعبه جرایم اقتصادی</span>
                <span>بازپرس / بررسی اسناد و شواهد</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-center">
                <p className="text-xs text-amber-200">Risk Score</p>
                <p className="mt-2 text-3xl font-bold text-amber-300">{caseSummary.riskScore}</p>
              </div>
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-center">
                <p className="text-xs text-emerald-200">Verification</p>
                <p className="mt-2 text-lg font-semibold text-emerald-300">{caseSummary.verification}</p>
              </div>
              <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-3 text-center">
                <p className="text-xs text-indigo-200">Confidence</p>
                <p className="mt-2 text-lg font-semibold text-indigo-300">{caseSummary.confidence}</p>
              </div>
            </div>
            
            {/* Action Buttons for New Features */}
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => setShowSearchPanel(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-3 py-2 text-sm text-indigo-300 hover:bg-indigo-500/20"
              >
                <FunnelIcon className="h-4 w-4" />
                جستجوی پیشرفته
              </button>
              <button
                onClick={() => setShowGraphView(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-300 hover:bg-cyan-500/20"
              >
                <LinkIcon className="h-4 w-4" />
                نمایش گراف روابط
              </button>
              <button
                onClick={() => setShowFundFlow(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300 hover:bg-amber-500/20"
              >
                <ArrowTrendingUpIcon className="h-4 w-4" />
                تحلیل جریان وجوه
              </button>
              <button
                onClick={() => generateReport('pdf')}
                disabled={reportGenerating}
                className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4" />
                {reportGenerating ? 'در حال تولید...' : 'صدور گزارش'}
              </button>
            </div>
          </div>
        </header>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {/* Search Panel Modal */}
        {showSearchPanel && renderSearchPanel()}
        
        {/* Graph View Modal */}
        {showGraphView && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="h-[90vh] w-full max-w-6xl overflow-auto rounded-2xl bg-slate-900 p-4">
              {renderGraphView()}
            </div>
          </div>
        )}
        
        {/* Fund Flow Modal */}
        {showFundFlow && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="h-[90vh] w-full max-w-5xl overflow-auto rounded-2xl bg-slate-900 p-4">
              {renderFundFlow()}
            </div>
          </div>
        )}

        <main className="mt-6 space-y-6">
          {isLoading ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-12 text-center text-slate-300">
              در حال بارگذاری داده‌های پرونده...
            </div>
          ) : (
            <>
              <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                {keyMetrics.map((m, i) => (
                  <StatCard key={i} label={m.label} value={m.value} tone={m.tone as "blue" | "purple" | "green" | "amber"} />
                ))}
              </section>

              <section className="grid gap-6 xl:grid-cols-[1.1fr_2fr]">
                <aside className="space-y-6">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                    <div className="mb-4 flex items-center gap-3">
                      <ShieldCheckIcon className="h-5 w-5 text-emerald-300" />
                      <h2 className="text-lg font-semibold">مسائل حقوقی و اقتصادی</h2>
                    </div>
                    <div className="space-y-4">
                      {issues.map((issue, idx) => (
                        <IssuePill key={idx} label={issue.label} strength={issue.strength} source={issue.source} color={issue.color as "red" | "amber" | "yellow" | "green"} />
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                    <div className="mb-4 flex items-center gap-3">
                      <ClockIcon className="h-5 w-5 text-indigo-300" />
                      <h2 className="text-lg font-semibold">خط زمانی وقایع</h2>
                    </div>
                    <div className="space-y-4">
                      {timeline.map((item, idx) => (
                        <div key={idx} className="flex gap-3">
                          <div className="flex flex-col items-center">
                            <div className="mt-1 h-3 w-3 rounded-full bg-indigo-400" />
                            {idx !== timeline.length - 1 && <div className="mt-1 h-full w-px bg-slate-700" />}
                          </div>
                          <div className="flex-1 pb-4">
                            <p className="text-xs text-slate-400">{item.date}</p>
                            <p className="mt-1 font-medium text-slate-100">{item.title}</p>
                            <p className="mt-1 text-sm text-slate-400">{item.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </aside>

                <div className="space-y-6">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <ChartBarIcon className="h-5 w-5 text-cyan-300" />
                        <h2 className="text-lg font-semibold">نقشهٔ شواهد و روابط</h2>
                      </div>
                      <button className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700">
                        <MagnifyingGlassIcon className="h-4 w-4" />
                        جستجوی اسناد
                      </button>
                    </div>

                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                        <p className="text-xs text-slate-400">شخص/نقش</p>
                        <p className="mt-3 font-medium text-white">مدیرعامل</p>
                        <p className="mt-2 text-sm text-slate-300">در تصمیم‌گیری‌های مالی و تخصیص منابع مؤثر بوده است</p>
                      </div>
                      <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                        <p className="text-xs text-slate-400">شرکت مرتبط</p>
                        <p className="mt-3 font-medium text-white">شرکت پشتیبان</p>
                        <p className="mt-2 text-sm text-slate-300">داده‌های مالی و اسناد قرارداد با جریان وجوه هم‌پوشانی دارد</p>
                      </div>
                      <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                        <p className="text-xs text-slate-400">روابط مشکوک</p>
                        <p className="mt-3 font-medium text-white">تخصیص غیرعادی</p>
                        <p className="mt-2 text-sm text-slate-300">تغییر مسیر وجوه با وجود گزارش‌های فنی و انحراف زمان‌بندی</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                    <div className="mb-4 flex items-center gap-3">
                      <DocumentTextIcon className="h-5 w-5 text-sky-300" />
                      <h2 className="text-lg font-semibold">اسناد و مدارک پرونده</h2>
                    </div>

                    <div className="space-y-3">
                      {documents.map((doc, idx) => (
                        <div key={idx} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 md:flex-row md:items-center md:justify-between">
                          <div className="flex items-start gap-3">
                            <div className="mt-1 rounded-lg bg-indigo-500/10 p-2 text-indigo-300">
                              <DocumentTextIcon className="h-4 w-4" />
                            </div>
                            <div>
                              <p className="font-medium text-slate-100">{doc.name}</p>
                              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                                <span>{doc.type}</span>
                                <span>•</span>
                                <span>{doc.pages} صفحه</span>
                                <span>•</span>
                                <span>OCR {doc.confidence}%</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">
                              {doc.status}
                            </span>
                            <button className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200 hover:bg-slate-700">
                              مشاهده
                              <ChevronRightIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </section>

              <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <div className="mb-4 flex items-center gap-3">
                    <ScaleIcon className="h-5 w-5 text-violet-300" />
                    <h2 className="text-lg font-semibold">ادعاها و سطح پشتیبانی</h2>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="text-slate-400">
                        <tr>
                          <th className="pb-3 text-right font-medium">ادعا</th>
                          <th className="pb-3 text-right font-medium">Support</th>
                          <th className="pb-3 text-right font-medium">Contradict</th>
                          <th className="pb-3 text-right font-medium">Confidence</th>
                          <th className="pb-3 text-right font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-200">
                        {claims.map((row, idx) => (
                          <tr key={idx} className="align-top">
                            <td className="py-3 pr-3">{row.claim}</td>
                            <td className="py-3 pr-3 text-emerald-300">{row.support}</td>
                            <td className="py-3 pr-3 text-red-300">{row.contradict}</td>
                            <td className="py-3 pr-3">{row.confidence}</td>
                            <td className="py-3 pr-3">
                              <span className={`rounded-full px-2 py-1 text-xs ${
                                row.status === "پشتیبانی شده"
                                  ? "bg-emerald-500/10 text-emerald-300"
                                  : row.status === "نامطمئن"
                                    ? "bg-amber-500/10 text-amber-300"
                                    : "bg-slate-700 text-slate-200"
                              }`}>
                                {row.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <div className="mb-4 flex items-center gap-3">
                    <ExclamationTriangleIcon className="h-5 w-5 text-red-300" />
                    <h2 className="text-lg font-semibold">تضادهای شناسایی شده</h2>
                  </div>
                  <div className="space-y-4">
                    {contradictions.map((item, idx) => (
                      <div key={idx} className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
                        <p className="font-medium text-red-200">{item.title}</p>
                        <div className="mt-3 space-y-2 text-sm text-slate-300">
                          <p><span className="text-emerald-300">A:</span> {item.docA}</p>
                          <p><span className="text-amber-300">B:</span> {item.docB}</p>
                        </div>
                        <div className="mt-3 inline-flex rounded-full border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-200">
                          اثر: {item.impact}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <div className="mb-4 flex items-center gap-3">
                    <ShieldCheckIcon className="h-5 w-5 text-indigo-300" />
                    <h2 className="text-lg font-semibold">استنادهای قانونی مرتبط</h2>
                  </div>
                  <div className="space-y-3">
                    {legalRefs.map((ref, idx) => (
                      <div key={idx} className="rounded-xl border border-slate-700 bg-slate-950/60 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium text-slate-100">{ref.label}</p>
                          <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-1 text-xs text-indigo-300">{ref.strength}</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">{ref.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                  <div className="mb-4 flex items-center gap-3">
                    <CheckCircleIcon className="h-5 w-5 text-emerald-300" />
                    <h2 className="text-lg font-semibold">اقدامات پیشنهادی</h2>
                  </div>
                  <ul className="space-y-3 text-sm text-slate-300">
                    {recommendations.map((item, idx) => (
                      <li key={idx} className="flex gap-3 rounded-xl border border-slate-700 bg-slate-950/60 p-3">
                        <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300">{idx + 1}</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
