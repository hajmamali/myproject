/**
 * App Layout Component
 * Main application layout wrapper for the user portal.
 *
 * Renders a responsive sidebar + header shell and surfaces nested routes
 * through <Outlet />. Falling back to the optional children/sidebar/header
 * props when provided directly (kept for test/fixture reuse).
 */

import type { ReactNode } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/authStore';

interface AppLayoutProps {
  children?: ReactNode;
  sidebar?: ReactNode;
  header?: ReactNode;
}

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

const PORTAL_NAV: NavItem[] = [
  { to: '/app/portal/dashboard', label: 'داشبورد', icon: '🏠' },
  { to: '/app/portal/search', label: 'جستجوی حقوقی', icon: '🔍' },
  { to: '/app/portal/chat', label: 'گفتگو با هوش مصنوعی', icon: '💬' },
  { to: '/app/portal/upload', label: 'بارگذاری سند', icon: '📄' },
  { to: '/app/portal/delay', label: 'تحلیل تأخیر', icon: '⏱' },
  { to: '/app/portal/timeline', label: 'خط زمانی', icon: '📅' },
  { to: '/app/portal/contract-qa', label: 'پرسش قرارداد', icon: '📑' },
];

function SidebarNav() {
  return (
    <nav className="flex flex-col gap-1 p-4" aria-label="پیمایش پورتال">
      {PORTAL_NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
              isActive
                ? 'bg-primary-50 font-medium text-primary-700'
                : 'text-slate-600 hover:bg-slate-100'
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

function HeaderBar({ onLogout }: { onLogout: () => void }) {
  const { user } = useAuth();
  return (
    <div className="flex items-center justify-between px-4 py-3" aria-label="نوار بالا">
      <div className="text-sm font-semibold text-slate-800">
        {user?.name ?? user?.email ?? 'کاربر ماحون'}
      </div>
      <button
        type="button"
        onClick={onLogout}
        className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100"
      >
        خروج
      </button>
    </div>
  );
}

export default function AppLayout({ children, sidebar, header }: AppLayoutProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    void navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="flex w-64 flex-col border-l border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-4">
          <h1 className="text-lg font-bold text-primary-700">ماحون</h1>
          <p className="text-xs text-slate-500">پورتال کاربری</p>
        </div>
        <div className="flex-1 overflow-auto">{sidebar ?? <SidebarNav />}</div>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="border-b border-slate-200 bg-white">{header ?? <HeaderBar onLogout={handleLogout} />}</header>
        <main className="flex-1 overflow-auto">{children ?? <Outlet />}</main>
      </div>
    </div>
  );
}
