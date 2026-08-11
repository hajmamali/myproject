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
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  ArrowUpTrayIcon,
  MagnifyingGlassIcon,
  ChartBarIcon,
  SparklesIcon,
  CommandLineIcon,
} from "@heroicons/react/24/outline";
import { useAuth, Role } from "../store/authStore";

interface NavItem {
  name: string;
  href: string;
  icon: any; // Simplified for Heroicons compatibility
}

const portalNavigation: NavItem[] = [
  { name: "داشبورد", href: "/app/portal/dashboard", icon: HomeIcon },
  { name: "چت AI", href: "/app/portal/chat", icon: SparklesIcon },
  { name: "آپلود مدارک", href: "/app/portal/upload", icon: ArrowUpTrayIcon },
  { name: "جستجو", href: "/app/portal/search", icon: MagnifyingGlassIcon },
  { name: "تحلیل تأخیر", href: "/app/portal/delay", icon: ChartBarIcon },
];

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const isActive = (href: string) => {
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

  const isOperator = user?.role === Role.ADMIN || user?.role === Role.ANALYST;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
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
          fixed inset-y-0 right-0 z-50 w-64 bg-slate-900 border-l border-slate-800 flex flex-col
          transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:h-screen
          ${sidebarOpen ? "translate-x-0" : "translate-x-full"}
        `}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-800">
          <h1 className="text-xl font-bold bg-gradient-to-l from-primary-400 to-indigo-400 bg-clip-text text-transparent">ماحون</h1>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-slate-800 text-slate-400"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {portalNavigation.map((item) => {
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
        <div className="p-4 border-t border-slate-800 bg-slate-950/40 space-y-3">
          {isOperator && (
            <button
              onClick={() => navigate("/app/studio/graph")}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-indigo-300 hover:text-white bg-indigo-950/40 hover:bg-indigo-900/60 border border-indigo-800/40 hover:border-indigo-700 transition-all cursor-pointer"
            >
              <CommandLineIcon className="h-4 w-4" />
              <span>ورود به محیط استودیو</span>
            </button>
          )}
          <div className="px-4 py-3 bg-slate-800/60 rounded-lg border border-slate-700/50">
            <p className="text-[10px] text-slate-400">پرتال کاربری ماحون</p>
            <p className="text-[10px] text-slate-500 mt-1">Zero-Hallucination AI</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen overflow-x-hidden">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between h-16 px-6 bg-slate-900 border-b border-slate-800">
          <h1 className="text-lg font-bold bg-gradient-to-l from-primary-400 to-indigo-400 bg-clip-text text-transparent">ماحون</h1>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-slate-800 text-slate-400"
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 bg-slate-950 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
