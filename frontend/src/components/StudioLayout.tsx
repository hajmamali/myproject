/**
 * Studio Layout Component
 *
 * Shell for the operations/engineer workbench (Studio). Renders a dark
 * sidebar with Studio navigation and surfaces nested routes via <Outlet />.
 */

import type { ReactNode } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth, Role, Permission } from '../store/authStore';
import { apiClient } from '../api/client';

interface StudioLayoutProps {
  children?: ReactNode;
}

interface StudioNavItem {
  to: string;
  label: string;
  icon: string;
  roles?: Role[];
  permissions?: Permission[];
}

const STUDIO_NAV: StudioNavItem[] = [
  { to: '/app/studio/graph', label: 'مرکز گراف دانش', icon: '🕸', permissions: [Permission.READ] },
  { to: '/app/studio/datasets', label: 'مدیریت دیتاست', icon: '🗃', permissions: [Permission.READ] },
  { to: '/app/studio/datasets/upload', label: 'بارگذاری دیتاست', icon: '⬆', permissions: [Permission.WRITE] },
  { to: '/app/studio/models', label: 'مدیریت مدل‌ها', icon: '🧠', permissions: [Permission.ADMIN] },
  { to: '/app/studio/training', label: 'آموزش مدل', icon: '🎯', permissions: [Permission.ADMIN] },
  { to: '/app/studio/finetuning', label: 'فاین‌تیونینگ', icon: '🔧', permissions: [Permission.ADMIN] },
  { to: '/app/studio/monitoring', label: 'مانیتورینگ سیستم', icon: '📊', permissions: [Permission.READ] },
  { to: '/app/studio/experiments', label: 'آزمایش‌های A/B', icon: '🧪', permissions: [Permission.ADMIN] },
  { to: '/app/studio/governance', label: 'مرکز حاکمیت', icon: '⚖', permissions: [Permission.READ] },
];

function StudioSidebar() {
  const { user, hasPermission } = useAuth();

  const visible = STUDIO_NAV.filter(
    (item) => !item.permissions || item.permissions.every((p) => hasPermission(p))
  );

  return (
    <nav className="flex flex-col gap-1 p-4" aria-label="پیمایش استودیو">
      {visible.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-slate-800 font-medium text-white'
                : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
            }`
          }
        >
          <span aria-hidden="true">{item.icon}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function StudioHeader({ onLogout }: { onLogout: () => void }) {
  const { user } = useAuth();
  return (
    <div className="flex items-center justify-between px-4 py-3" aria-label="نوار استودیو">
      <div className="text-sm font-semibold text-white">
        استودیو · {user?.name ?? 'مهندس'}
      </div>
      <button
        type="button"
        onClick={onLogout}
        className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:bg-slate-800"
      >
        خروج
      </button>
    </div>
  );
}

export default function StudioLayout({ children }: StudioLayoutProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleLogout = () => {
    logout();
    void navigate('/login');
  };

  const handleHealthCheck = async () => {
    await apiClient.get('/api/system/health').catch(() => undefined);
    void navigate('/app/studio/monitoring');
  };

  return (
    <div className="flex h-screen flex-col bg-slate-900 text-white" dir="rtl">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950">
        <StudioHeader onLogout={handleLogout} />
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0 overflow-y-auto border-l border-slate-800 bg-slate-900">
          <StudioSidebar />
        </aside>

        {/* Routed content */}
        <main className="flex-1 overflow-auto bg-slate-950">
          {children ?? <Outlet />}
        </main>
      </div>

      {/* Footer status strip */}
      <footer className="flex items-center justify-between border-t border-slate-800 bg-slate-950 px-4 py-2 text-xs text-slate-500">
        <span>استودیوی ماحون — محیط مهندسی</span>
        <button
          type="button"
          onClick={handleHealthCheck}
          className="text-slate-400 transition-colors hover:text-primary-400"
        >
          بررسی سلامت سیستم
        </button>
      </footer>
    </div>
  );
}
