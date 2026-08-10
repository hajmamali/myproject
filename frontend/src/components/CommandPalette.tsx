/**
 * Command Palette (Cmd+K) - Harvey-Style
 * 
 * Features:
 * - Keyboard shortcuts (Cmd+K / Ctrl+K)
 * - Fuzzy search
 * - Quick actions
 * - Navigation shortcuts
 * - Recent commands
 */

import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { 
  MagnifyingGlassIcon,
  HomeIcon,
  ArrowUpTrayIcon,
  ChartBarIcon,
  SparklesIcon,
  XMarkIcon
} from "@heroicons/react/24/outline";

interface Command {
  id: string;
  label: string;
  description?: string;
  icon: any;
  action: () => void;
  keywords?: string[];
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  // Define all available commands
  const commands: Command[] = [
    {
      id: "nav-dashboard",
      label: "داشبورد",
      description: "برو به صفحه اصلی",
      icon: HomeIcon,
      action: () => {
        navigate("/app/dashboard");
        onClose();
      },
      keywords: ["dashboard", "home", "خانه"],
    },
    {
      id: "nav-search",
      label: "جستجوی قانونی",
      description: "جستجو در آرای قانونی",
      icon: MagnifyingGlassIcon,
      action: () => {
        navigate("/app/search");
        onClose();
      },
      keywords: ["search", "legal", "جستجو", "قانونی"],
    },
    {
      id: "nav-upload",
      label: "آپلود مدرک",
      description: "بارگذاری اسناد جدید",
      icon: ArrowUpTrayIcon,
      action: () => {
        navigate("/app/upload");
        onClose();
      },
      keywords: ["upload", "document", "آپلود", "مدرک"],
    },
    {
      id: "nav-analysis",
      label: "تحلیل تأخیر",
      description: "تحلیل تأخیرات پروژه",
      icon: ChartBarIcon,
      action: () => {
        navigate("/app/delay");
        onClose();
      },
      keywords: ["delay", "analysis", "تأخیر", "تحلیل"],
    },
    {
      id: "nav-training",
      label: "آموزش مدل",
      description: "آموزش مدل‌های AI",
      icon: SparklesIcon,
      action: () => {
        navigate("/app/training");
        onClose();
      },
      keywords: ["training", "ai", "آموزش", "مدل"],
    },
  ];

  // Fuzzy search filter
  const filteredCommands = commands.filter((cmd) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      cmd.label.toLowerCase().includes(searchLower) ||
      cmd.description?.toLowerCase().includes(searchLower) ||
      cmd.keywords?.some((k) => k.toLowerCase().includes(searchLower))
    );
  });

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, onClose]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setSearch("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Command Palette */}
      <div className="relative min-h-screen flex items-start justify-center p-4 pt-[20vh]">
        <div className="relative w-full max-w-2xl bg-slate-900 rounded-xl shadow-2xl border border-slate-700 overflow-hidden animate-slide-up">
          
          {/* Search Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700">
            <MagnifyingGlassIcon className="h-5 w-5 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSelectedIndex(0);
              }}
              placeholder="جستجو یا انتخاب دستور..."
              className="flex-1 bg-transparent border-none outline-none text-slate-100 placeholder-slate-500 text-lg"
            />
            <button
              onClick={onClose}
              className="p-1 hover:bg-slate-800 rounded-md transition-colors"
            >
              <XMarkIcon className="h-5 w-5 text-slate-400" />
            </button>
          </div>

          {/* Commands List */}
          <div className="max-h-96 overflow-y-auto">
            {filteredCommands.length === 0 ? (
              <div className="px-4 py-8 text-center text-slate-500">
                نتیجه‌ای یافت نشد
              </div>
            ) : (
              filteredCommands.map((cmd, index) => {
                const Icon = cmd.icon;
                const isSelected = index === selectedIndex;

                return (
                  <button
                    key={cmd.id}
                    onClick={cmd.action}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 text-right transition-colors
                      ${isSelected ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-800"}
                    `}
                  >
                    <Icon className={`h-5 w-5 ${isSelected ? "text-white" : "text-slate-400"}`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{cmd.label}</div>
                      {cmd.description && (
                        <div className={`text-sm truncate ${isSelected ? "text-blue-100" : "text-slate-500"}`}>
                          {cmd.description}
                        </div>
                      )}
                    </div>
                    {isSelected && (
                      <kbd className="px-2 py-1 text-xs bg-white/20 rounded border border-white/30">
                        ↵
                      </kbd>
                    )}
                  </button>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-2 border-t border-slate-700 bg-slate-800/50 text-xs text-slate-500">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-slate-700 rounded">↑↓</kbd>
                <span>Navigate</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-slate-700 rounded">↵</kbd>
                <span>Select</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <kbd className="px-2 py-1 bg-slate-700 rounded">ESC</kbd>
              <span>Close</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Hook to use Command Palette globally
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen(true);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
  };
}
