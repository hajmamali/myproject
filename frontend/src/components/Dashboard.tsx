/**
 * MAHOUN Main Dashboard
 * 
 * Advanced dashboard with:
 * - Project overview
 * - Statistics and metrics
 * - Quick actions
 * - Recent activities
 */

import { useState, useEffect } from "react";
import { 
  DocumentTextIcon, 
  ChartBarIcon, 
  ClockIcon,
  QuestionMarkCircleIcon,
  DocumentArrowDownIcon,
  PlusIcon
} from "@heroicons/react/24/outline";

interface DashboardStats {
  total_documents: number;
  total_projects: number;
  pending_analyses: number;
  generated_reports: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    total_documents: 0,
    total_projects: 0,
    pending_analyses: 0,
    generated_reports: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load dashboard stats
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      // Fetch stats from backend
      const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE_URL}/system/health`);
      const data = await response.json();
      
      // Map API response to dashboard stats
      setStats({
        total_documents: data.total_documents || 0,
        total_projects: data.total_queries || 0,
        pending_analyses: 0,
        generated_reports: 0,
      });
    } catch (error) {
      console.error("Failed to load stats:", error);
      // Fallback to default values on error
      setStats({
        total_documents: 0,
        total_projects: 0,
        pending_analyses: 0,
        generated_reports: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      title: "مدارک",
      value: stats.total_documents,
      icon: DocumentTextIcon,
      color: "bg-primary-700",
      description: "مدارک آپلود شده",
    },
    {
      title: "پروژه‌ها",
      value: stats.total_projects,
      icon: ChartBarIcon,
      color: "bg-primary-600",
      description: "پروژه‌های فعال",
    },
    {
      title: "تحلیل‌های در انتظار",
      value: stats.pending_analyses,
      icon: ClockIcon,
      color: "bg-accent-600",
      description: "تحلیل‌های در حال پردازش",
    },
    {
      title: "گزارش‌ها",
      value: stats.generated_reports,
      icon: DocumentArrowDownIcon,
      color: "bg-slate-700",
      description: "گزارش‌های تولید شده",
    },
  ];

  const quickActions = [
    {
      title: "آپلود مدرک",
      description: "آپلود و پردازش مدارک جدید",
      icon: PlusIcon,
      href: "/upload",
      color: "bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700",
    },
    {
      title: "تحلیل تأخیر",
      description: "تحلیل تأخیرات پروژه",
      icon: ChartBarIcon,
      href: "/delay-analysis",
      color: "bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700",
    },
    {
      title: "تولید دعوی",
      description: "تولید محتوای دعوی",
      icon: DocumentTextIcon,
      href: "/claim-generator",
      color: "bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700",
    },
    {
      title: "سؤال پیمانی",
      description: "پرسش و پاسخ درباره قراردادها",
      icon: QuestionMarkCircleIcon,
      href: "/contract-qa",
      color: "bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700",
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-slate-900/90 backdrop-blur border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 page-enter">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-100">داشبورد ماحون</h1>
              <p className="mt-1 text-sm text-slate-500">
                سیستم هوشمند مدیریت و تحلیل پیمانکاری
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-colors">
                پروژه جدید
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 page-enter">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((stat, index) => (
            <div
              key={index}
              className="bg-slate-900 rounded-xl shadow-sm border border-slate-700 p-6 hover:shadow-md transition-shadow stagger-enter"
              style={{ animationDelay: `${index * 60}ms` }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-400">{stat.title}</p>
                  <p className="mt-2 text-3xl font-bold text-slate-100">{stat.value}</p>
                  <p className="mt-1 text-xs text-slate-500">{stat.description}</p>
                </div>
                <div className={`${stat.color} p-3 rounded-lg shadow-sm`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-slate-100 mb-4">اقدامات سریع</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map((action, index) => (
              <button
                key={index}
                className={`${action.color} rounded-xl p-6 text-right transition-all hover:-translate-y-0.5 hover:shadow-md stagger-enter`}
                style={{ animationDelay: `${index * 80}ms` }}
                onClick={() => {
                  // TODO: Implement navigation
                  window.location.hash = action.href;
                }}
              >
                <div className="w-10 h-10 rounded-lg bg-primary-50 border border-primary-100 flex items-center justify-center mb-3">
                  <action.icon className="h-5 w-5 text-primary-700" />
                </div>
                <h3 className="font-semibold text-lg mb-1">{action.title}</h3>
                <p className="text-sm text-slate-400">{action.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Recent Activities */}
        <div className="bg-slate-900 rounded-xl shadow-sm border border-slate-700 p-6">
          <h2 className="text-xl font-semibold text-slate-100 mb-4">فعالیت‌های اخیر</h2>
          <div className="space-y-4">
            {/* Placeholder for recent activities */}
            <div className="text-center text-slate-500 py-8">
              هیچ فعالیتی ثبت نشده است
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
