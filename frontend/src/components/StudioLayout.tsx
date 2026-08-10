import { useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  XMarkIcon,
  Bars3Icon,
  ShareIcon,
  CommandLineIcon,
  CircleStackIcon,
  AcademicCapIcon,
  AdjustmentsHorizontalIcon,
  ChartBarIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  UserIcon,
  LockClosedIcon,
} from "@heroicons/react/24/outline";
import { useAuth } from "../store/authStore";

interface NavGroup {
  title: string;
  items: {
    name: string;
    href: string;
    icon: React.ComponentType<{ className?: string }>;
  }[];
}

const studioNavigation: NavGroup[] = [
  {
    title: "Knowledge & Data",
    items: [
      { name: "Knowledge Graph Center", href: "/app/studio/graph", icon: ShareIcon },
      { name: "Dataset Engineering", href: "/app/studio/datasets", icon: CircleStackIcon },
    ],
  },
  {
    title: "Model Operations",
    items: [
      { name: "AI Training", href: "/app/studio/training", icon: AcademicCapIcon },
      { name: "Fine-Tuning & Eval", href: "/app/studio/finetuning", icon: AdjustmentsHorizontalIcon },
      { name: "Model Registry", href: "/app/studio/models", icon: CommandLineIcon },
    ],
  },
  {
    title: "Observability",
    items: [
      { name: "System Monitor", href: "/app/studio/monitoring", icon: CpuChipIcon },
      { name: "A/B Testing", href: "/app/studio/experiments", icon: ChartBarIcon },
    ],
  },
  {
    title: "Governance",
    items: [
      { name: "Governance Center", href: "/app/studio/governance", icon: ShieldCheckIcon },
    ],
  },
];

export default function StudioLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const isActive = (href: string) => {
    return location.pathname === href || location.pathname.startsWith(href + "/");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Mobile Sidebar Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-955/80 backdrop-blur-sm lg:hidden"
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
        {/* Header */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xl font-extrabold bg-gradient-to-l from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              MahouN Studio
            </span>
            <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded font-mono border border-indigo-500/30">
              v1.0
            </span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-slate-800 text-slate-400"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* User Info / Role */}
        <div className="px-6 py-4 border-b border-slate-800/60 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold uppercase">
              {user?.username?.[0] || "O"}
            </div>
            <div className="text-right overflow-hidden">
              <p className="text-sm font-semibold truncate text-slate-200">{user?.username || "Operator"}</p>
              <p className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                <LockClosedIcon className="h-3 w-3 text-indigo-400" />
                ROLE_{user?.role?.toUpperCase() || "ANALYST"}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Groups */}
        <nav className="flex-1 px-4 py-6 space-y-6 overflow-y-auto">
          {studioNavigation.map((group) => (
            <div key={group.title} className="space-y-1.5">
              <h3 className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                {group.title}
              </h3>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={`
                        flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-200
                        ${
                          active
                            ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                        }
                      `}
                    >
                      <item.icon className="h-4 w-4 flex-shrink-0" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Sidebar Footer - Toggle to Portal */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <button
            onClick={() => navigate("/app/portal/dashboard")}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 transition-all cursor-pointer"
          >
            <UserIcon className="h-4 w-4 text-indigo-400" />
            <span>بازگشت به پرتال کاربری</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen overflow-x-hidden">
        {/* Mobile Header */}
        <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between h-16 px-6 bg-slate-900 border-b border-slate-800">
          <span className="text-lg font-bold bg-gradient-to-l from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            MahouN Studio
          </span>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-slate-800 text-slate-400"
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
        </header>

        {/* Content Outlet */}
        <main className="flex-1 bg-slate-950 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
