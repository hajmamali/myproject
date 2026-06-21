/**
 * AppLayout - Main Application Layout
 * 
 * Enterprise-grade layout with:
 * - Responsive sidebar navigation
 * - Mobile menu support
 * - Active route highlighting
 * - Nested routing with Outlet
 */

import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import {
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  ArrowUpTrayIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  AcademicCapIcon,
  BeakerIcon,
  CpuChipIcon,
  Cog6ToothIcon,
} from "@heroicons/react/24/outline";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigation: NavItem[] = [
  { name: "داشبورد", href: "/dashboard", icon: HomeIcon },
  { name: "آپلود مدارک", href: "/upload", icon: ArrowUpTrayIcon },
  { name: "جستجو", href: "/search", icon: MagnifyingGlassIcon },
  { name: "تحلیل تأخیر", href: "/delay", icon: ChartBarIcon },
  { name: "آموزش مدل", href: "/training", icon: AcademicCapIcon },
  { name: "فاین‌تیونینگ", href: "/finetuning", icon: BeakerIcon },
  { name: "مانیتورینگ", href: "/monitoring", icon: CpuChipIcon },
  { name: "آزمایش‌ها", href: "/experiments", icon: Cog6ToothIcon },
];

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const isActive = (href: string) => {
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 right-0 z-50 w-64 bg-slate-900 border-l border-slate-700
          transform transition-transform duration-300 ease-in-out
          lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "translate-x-full"}
        `}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-700">
          <h1 className="text-xl font-bold text-slate-100">ماحون</h1>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <XMarkIcon className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium
                  transition-all duration-200
                  ${
                    active
                      ? "bg-primary-700 text-white shadow-lg shadow-primary-700/50"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-800"
                  }
                `}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="p-4 border-t border-slate-700">
          <div className="px-4 py-3 bg-slate-800 rounded-lg">
            <p className="text-xs text-slate-400">نسخه 1.0.0</p>
            <p className="text-xs text-slate-500 mt-1">Zero-Hallucination AI</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:mr-64">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between h-16 px-4 bg-slate-900/95 backdrop-blur border-b border-slate-700">
          <h1 className="text-lg font-bold text-slate-100">ماحون</h1>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <Bars3Icon className="h-6 w-6 text-slate-400" />
          </button>
        </header>

        {/* Page content */}
        <main className="min-h-screen">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
