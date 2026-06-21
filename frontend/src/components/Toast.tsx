/**
 * Toast Notifications
 * Simple toast notification system without external dependencies
 */

import { useState, useEffect } from "react";
import {
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

export type ToastType = "success" | "error" | "info" | "warning";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastProps {
  toast: Toast;
  onClose: (id: string) => void;
}

function ToastItem({ toast, onClose }: ToastProps) {
  useEffect(() => {
    const duration = toast.duration || 5000;
    const timer = setTimeout(() => {
      onClose(toast.id);
    }, duration);

    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onClose]);

  const icons = {
    success: <CheckCircleIcon className="h-6 w-6 text-green-500" />,
    error: <XCircleIcon className="h-6 w-6 text-red-500" />,
    warning: <ExclamationTriangleIcon className="h-6 w-6 text-yellow-500" />,
    info: <InformationCircleIcon className="h-6 w-6 text-blue-500" />,
  };

  const colors = {
    success: "bg-green-50 border-green-200",
    error: "bg-red-50 border-red-200",
    warning: "bg-yellow-50 border-yellow-200",
    info: "bg-blue-50 border-blue-200",
  };

  return (
    <div
      className={`${colors[toast.type]} border rounded-lg shadow-lg p-4 mb-3 flex items-start gap-3 min-w-[300px] max-w-md animate-slide-in`}
    >
      {icons[toast.type]}
      <p className="flex-1 text-sm text-slate-100">{toast.message}</p>
      <button
        onClick={() => onClose(toast.id)}
        className="flex-shrink-0 text-slate-400 hover:text-slate-400"
      >
        <XMarkIcon className="h-5 w-5" />
      </button>
    </div>
  );
}

let toastIdCounter = 0;
let toastListeners: ((toasts: Toast[]) => void)[] = [];
let currentToasts: Toast[] = [];

export const toast = {
  success: (message: string, duration?: number) => {
    addToast({ type: "success", message, duration });
  },
  error: (message: string, duration?: number) => {
    addToast({ type: "error", message, duration });
  },
  info: (message: string, duration?: number) => {
    addToast({ type: "info", message, duration });
  },
  warning: (message: string, duration?: number) => {
    addToast({ type: "warning", message, duration });
  },
};

function addToast(toast: Omit<Toast, "id">) {
  const newToast: Toast = {
    ...toast,
    id: `toast-${++toastIdCounter}`,
  };
  currentToasts = [...currentToasts, newToast];
  notifyListeners();
}

function removeToast(id: string) {
  currentToasts = currentToasts.filter((t) => t.id !== id);
  notifyListeners();
}

function notifyListeners() {
  toastListeners.forEach((listener) => listener(currentToasts));
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>(currentToasts);

  useEffect(() => {
    toastListeners.push(setToasts);
    return () => {
      toastListeners = toastListeners.filter((l) => l !== setToasts);
    };
  }, []);

  return (
    <div className="fixed top-4 left-4 z-50">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={removeToast} />
      ))}
    </div>
  );
}

