/**
 * Navigation Sidebar Component
 * Role-aware navigation for different sections of the platform
 */

import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth, Role, Permission } from '../store/authStore';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  requiredRoles?: Role[];
  requiredPermissions?: Permission[];
  children?: NavItem[];
}

export default function NavigationSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, hasRole, hasPermission } = useAuth();

  const navItems: NavItem[] = [
    {
      path: '/app/portal/dashboard',
      label: 'داشبورد کاربر',
      icon: '🏠',
      requiredRoles: [Role.LEGAL_PROFESSIONAL, Role.ANALYST, Role.ADMIN],
    },
    {
      path: '/app/portal/search',
      label: 'جستجوی حقوقی',
      icon: '🔍',
      requiredRoles: [Role.LEGAL_PROFESSIONAL, Role.ANALYST, Role.ADMIN],
    },
    {
      path: '/app/portal/chat',
      label: 'دستیار هوشمند',
      icon: '💬',
      requiredRoles: [Role.LEGAL_PROFESSIONAL, Role.ANALYST, Role.ADMIN],
    },
    {
      path: '/app/portal/upload',
      label: 'بارگذاری سند',
      icon: '📄',
      requiredRoles: [Role.LEGAL_PROFESSIONAL, Role.ANALYST, Role.ADMIN],
      requiredPermissions: [Permission.WRITE],
    },
    {
      path: '/app/studio',
      label: 'محیط توسعه',
      icon: '🔬',
      requiredRoles: [Role.ANALYST, Role.ADMIN],
      children: [
        {
          path: '/app/studio/governance',
          label: 'Governance Center',
          icon: '🛡️',
          requiredRoles: [Role.ANALYST, Role.ADMIN],
        },
        {
          path: '/app/studio/graph',
          label: 'Knowledge Graph',
          icon: '🕸️',
          requiredRoles: [Role.ANALYST, Role.ADMIN],
        },
        {
          path: '/app/studio/models',
          label: 'مدل‌ها',
          icon: '🤖',
          requiredRoles: [Role.ADMIN],
        },
        {
          path: '/app/studio/finetuning',
          label: 'Fine-Tuning',
          icon: '⚙️',
          requiredRoles: [Role.ADMIN],
        },
        {
          path: '/app/studio/training',
          label: 'آموزش',
          icon: '📊',
          requiredRoles: [Role.ADMIN],
        },
        {
          path: '/app/studio/monitoring',
          label: 'نظارت',
          icon: '📈',
          requiredRoles: [Role.ANALYST, Role.ADMIN],
        },
        {
          path: '/app/studio/experiments',
          label: 'آزمایش‌ها',
          icon: '🧪',
          requiredRoles: [Role.ADMIN],
        },
      ],
    },
  ];

  const canAccess = (item: NavItem): boolean => {
    if (item.requiredRoles && !item.requiredRoles.some(role => hasRole(role))) {
      return false;
    }
    if (item.requiredPermissions && !item.requiredPermissions.some(perm => hasPermission(perm))) {
      return false;
    }
    return true;
  };

  const isActive = (path: string): boolean => {
    if (path === location.pathname) return true;
    if (location.pathname.startsWith(path + '/')) return true;
    return false;
  };

  return (
    <div className="w-64 bg-slate-900 border-l border-slate-800 h-screen fixed left-0 top-0 overflow-y-auto">
      <div className="p-4">
        {/* Logo */}
        <div className="mb-8">
          <h1 className="text-xl font-bold text-white">MahouN</h1>
          <p className="text-xs text-slate-400">Legal AI Platform</p>
        </div>

        {/* Navigation */}
        <nav className="space-y-2">
          {navItems.map((item) => {
            if (!canAccess(item)) return null;

            if (item.children) {
              return (
                <div key={item.path} className="space-y-1">
                  <button
                    onClick={() => navigate(item.path)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                      isActive(item.path)
                        ? 'bg-primary-600 text-white'
                        : 'text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                  
                  {/* Sub-items */}
                  {isActive(item.path) && (
                    <div className="mr-4 space-y-1 mt-1">
                      {item.children.map((child) => {
                        if (!canAccess(child)) return null;
                        return (
                          <button
                            key={child.path}
                            onClick={() => navigate(child.path)}
                            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                              isActive(child.path)
                                ? 'bg-primary-600/50 text-white'
                                : 'text-slate-400 hover:bg-slate-800'
                            }`}
                          >
                            <span>{child.icon}</span>
                            <span>{child.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }

            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive(item.path)
                    ? 'bg-primary-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* User Info */}
        {user && (
          <div className="mt-8 pt-4 border-t border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                {user.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user.email}</p>
                <p className="text-xs text-slate-400">{user.role}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
