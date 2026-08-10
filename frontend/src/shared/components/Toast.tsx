/**
 * Toast Notification System
 * 
 * Centralized toast notification component for displaying user-friendly messages
 */

import React, { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon, CheckCircleIcon, ExclamationCircleIcon, InformationCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { ErrorSeverity, Domain, ErrorCode } from '../errors/types';
import { AppError } from '../errors/AppError';

// ============================================================================
// Toast Types
// ============================================================================

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  severity?: ErrorSeverity;
  domain?: Domain;
  code?: ErrorCode;
  duration?: number;
  dismissible?: boolean;
  createdAt: number;
  onDismiss?: () => void;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'danger';
  };
}

// ============================================================================
// Toast Configuration
// ============================================================================

const TOAST_POSITIONS = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'top-center', 'bottom-center'] as const;
type ToastPosition = typeof TOAST_POSITIONS[number];

interface ToastContainerProps {
  position?: ToastPosition;
  maxToasts?: number;
  preventDuplicate?: boolean;
  newestOnTop?: boolean;
  children?: React.ReactNode;
}

// ============================================================================
// Toast Component Styles
// ============================================================================

const POSITION_STYLES: Record<ToastPosition, string> = {
  'top-left': 'top-6 left-6',
  'top-right': 'top-6 right-6',
  'bottom-left': 'bottom-6 left-6',
  'bottom-right': 'bottom-6 right-6',
  'top-center': 'top-6 left-1/2 transform -translate-x-1/2',
  'bottom-center': 'bottom-6 left-1/2 transform -translate-x-1/2',
};

const TYPE_CONFIG = {
  success: {
    icon: CheckCircleIcon,
    background: 'bg-green-900/90 backdrop-blur-sm',
    border: 'border-green-700/50',
    text: 'text-green-200',
    iconText: 'text-green-400',
  },
  error: {
    icon: ExclamationCircleIcon,
    background: 'bg-red-900/90 backdrop-blur-sm',
    border: 'border-red-700/50',
    text: 'text-red-200',
    iconText: 'text-red-400',
  },
  warning: {
    icon: ExclamationTriangleIcon,
    background: 'bg-yellow-900/90 backdrop-blur-sm',
    border: 'border-yellow-700/50',
    text: 'text-yellow-200',
    iconText: 'text-yellow-400',
  },
  info: {
    icon: InformationCircleIcon,
    background: 'bg-blue-900/90 backdrop-blur-sm',
    border: 'border-blue-700/50',
    text: 'text-blue-200',
    iconText: 'text-blue-400',
  },
};

// ============================================================================
// Single Toast Component
// ============================================================================

interface SingleToastProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

function SingleToast({ toast, onDismiss }: SingleToastProps) {
  const [isExiting, setIsExiting] = useState(false);
  const [progress, setProgress] = useState(100);
  
  const config = TYPE_CONFIG[toast.type] || TYPE_CONFIG.info;
  const Icon = config.icon;

  // Calculate progress for duration
  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const interval = setInterval(() => {
        setProgress(() => {
          const elapsed = (Date.now() - toast.createdAt) / (toast.duration || 1) * 100;
          return Math.max(0, 100 - elapsed);
        });
      }, 100);
      
      return () => clearInterval(interval);
    }
    return undefined;
  }, [toast.duration, toast.createdAt]);

  // Handle dismiss with exit animation
  const handleDismiss = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onDismiss(toast.id);
    }, 300); // Match animation duration
  }, [onDismiss, toast.id]);

  // Auto-dismiss when progress reaches 0
  useEffect(() => {
    if (progress <= 0 && toast.duration && toast.duration > 0) {
      handleDismiss();
    }
  }, [progress, toast.duration, handleDismiss]);

  // Get severity color for border
  const getSeverityBorder = () => {
    switch (toast.severity) {
      case ErrorSeverity.CRITICAL:
        return 'border-red-500/80';
      case ErrorSeverity.HIGH:
        return 'border-orange-500/80';
      case ErrorSeverity.MEDIUM:
        return 'border-yellow-500/80';
      default:
        return config.border;
    }
  };

  return (
    <div
      className={`{
        ${isExiting ? 'animate-fade-out-slide-up' : 'animate-fade-in-slide-down'}
        ${config.background}
        border border-slate-700/60 ${getSeverityBorder()}
        rounded-xl shadow-2xl overflow-hidden
        ${toast.duration && toast.duration > 0 ? 'relative' : ''}
      `}
      style={{
        animationDuration: '300ms',
        animationFillMode: 'both',
      }}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      {/* Progress bar for timed toasts */}
      {toast.duration && toast.duration > 0 && (
        <div className="absolute bottom-0 left-0 h-1 bg-slate-700/60 w-full">
          <div
            className="h-full bg-slate-400/60 transition-all duration-100 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <div className="p-4 flex gap-3">
        {/* Icon */}
        <div className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg ${
          toast.severity === ErrorSeverity.CRITICAL 
            ? 'bg-red-900/40' :
            toast.severity === ErrorSeverity.HIGH 
              ? 'bg-orange-900/40' :
            config.iconText === 'text-green-400' 
              ? 'bg-green-900/40' :
            config.iconText === 'text-yellow-400' 
              ? 'bg-yellow-900/40' :
              'bg-blue-900/40'
        }`}>
          <Icon className={`h-5 w-5 ${config.iconText}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className={`font-bold text-sm ${config.text} truncate`}>
                {toast.title}
              </h3>
              <p className={`text-xs mt-0.5 ${config.text}/80`} dir="rtl">
                {toast.message}
              </p>
            </div>
            
            {/* Dismiss button */}
            {toast.dismissible !== false && (
              <button
                onClick={handleDismiss}
                className={`{
                  p-1 rounded-lg hover:bg-slate-700/50 transition-colors
                  ${config.text}/70 hover:${config.text}
                }`}
                aria-label="بستن"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Action button */}
          {toast.action && (
            <div className="mt-3 flex gap-2">
              <button
                onClick={toast.action.onClick}
                className={`{
                  px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors
                  ${
                    toast.action.variant === 'danger' 
                      ? 'bg-red-600/20 text-red-300 hover:bg-red-600/30'
                      : toast.action.variant === 'primary' 
                        ? 'bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30'
                        : 'bg-slate-600/20 text-slate-300 hover:bg-slate-600/30'
                  }
                }`}
              >
                {toast.action.label}
              </button>
            </div>
          )}

          {/* Error metadata for governance errors */}
          {toast.severity === ErrorSeverity.CRITICAL && toast.code && (
            <div className="mt-2 flex gap-2">
              <span className="text-[10px] bg-slate-700/60 px-2 py-0.5 rounded-full font-mono text-slate-400">
                {toast.code}
              </span>
              {toast.domain && (
                <span className="text-[10px] bg-slate-700/60 px-2 py-0.5 rounded-full font-mono text-slate-400">
                  {toast.domain}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Toast Container Component
// ============================================================================


const ToastContainer = forwardRef<{
  addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
}, ToastContainerProps>((props, ref) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastIdRef = useRef(0);
  const seenToastsRef = useRef(new Set<string>());

  const position = props.position || 'top-right';
  const maxToasts = props.maxToasts || 5;
  const preventDuplicate = props.preventDuplicate !== false;
  const newestOnTop = props.newestOnTop !== false;

  // Add toast
  const addToast = useCallback((toast: Omit<ToastMessage, 'id' | 'createdAt'>): string => {
    const id = String(++toastIdRef.current);
    
    // Check for duplicates if enabled
    if (preventDuplicate && toast.message) {
      const messageHash = String(toast.message).substring(0, 50);
      if (seenToastsRef.current.has(messageHash)) {
        return id; // Return ID but don't show duplicate
      }
      seenToastsRef.current.add(messageHash);
    }
    
    const newToast: ToastMessage = {
      ...toast,
      id,
      createdAt: Date.now(),
      duration: toast.duration ?? (toast.type === 'error' ? 8000 : 5000),
      dismissible: toast.dismissible ?? true,
    };
    
    setToasts(prev => {
      // Remove oldest toast if we exceed max
      if (prev.length >= maxToasts) {
        const oldest = prev[0];
        if (oldest.id) seenToastsRef.current.delete(String(oldest.message).substring(0, 50));
        return [...prev.slice(1), newToast];
      }
      return [...prev, newToast];
    });
    
    // Auto-dismiss if not persistent
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        dismissToast(id);
        if (newToast.message) {
          seenToastsRef.current.delete(String(newToast.message).substring(0, 50));
        }
      }, newToast.duration);
    }
    
    return id;
  }, [maxToasts, preventDuplicate]);

  // Dismiss toast
  const dismissToast = useCallback((id: string) => {
    setToasts(prev => {
      const dismissed = prev.find(t => t.id === id);
      if (dismissed?.message) {
        seenToastsRef.current.delete(String(dismissed.message).substring(0, 50));
      }
      return prev.filter(t => t.id !== id);
    });
  }, []);

  // Clear all toasts
  const clearToasts = useCallback(() => {
    setToasts([]);
    seenToastsRef.current.clear();
  }, []);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    addToast,
    dismissToast,
    clearToasts,
  }));

  // Render toasts
  const renderToasts = () => {
    return toasts.map(toast => (
      <SingleToast
        key={toast.id}
        toast={toast}
        onDismiss={dismissToast}
      />
    ));
  };

  return createPortal(
    <div
      className={`{
        fixed z-50 pointer-events-none
        ${POSITION_STYLES[position]}
      }`}
      style={{ width: 'min(400px, 90vw)' }}
    >
      <div className="flex flex-col gap-3 pointer-events-auto">
        {newestOnTop ? renderToasts() : renderToasts().reverse()}
      </div>
    </div>,
    document.body
  );
});

ToastContainer.displayName = 'ToastContainer';

// ============================================================================
// Toast Provider for Context API (Optional)
// ============================================================================

import { createContext, useContext, useRef } from 'react';

interface ToastContextValue {
  addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

interface ToastProviderProps {
  children: React.ReactNode;
  position?: ToastPosition;
  maxToasts?: number;
  preventDuplicate?: boolean;
  newestOnTop?: boolean;
}

export function ToastProvider({
  children,
  position,
  maxToasts,
  preventDuplicate,
  newestOnTop,
}: ToastProviderProps) {
  const toastRef = useRef<{
    addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
    dismissToast: (id: string) => void;
    clearToasts: () => void;
  }>(null);

  return (
    <>
      <ToastContainer
        ref={toastRef}
        position={position}
        maxToasts={maxToasts}
        preventDuplicate={preventDuplicate}
        newestOnTop={newestOnTop}
      />
      <ToastContext.Provider value={toastRef.current || {
        addToast: () => '',
        dismissToast: () => {},
        clearToasts: () => {},
      }}>
        {children}
      </ToastContext.Provider>
    </>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// ============================================================================
// Standalone Toast Functions (for direct use)
// ============================================================================

let toastContainerRef: {
  addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
} | null = null;

/**
 * Register the toast container reference
 * Call this from your root component after rendering ToastContainer
 */
export function registerToastContainer(ref: {
  addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
}) {
  toastContainerRef = ref;
}

/**
 * Show a toast message (standalone function)
 */
export function showToast(toast: Omit<ToastMessage, 'id' | 'createdAt'>): string {
  if (toastContainerRef) {
    return toastContainerRef.addToast(toast);
  }
  console.warn('Toast container not registered. Toast will not be shown.');
  return '';
}

/**
 * Dismiss a toast by ID (standalone function)
 */
export function dismissToast(id: string): void {
  if (toastContainerRef) {
    toastContainerRef.dismissToast(id);
  }
}

/**
 * Clear all toasts (standalone function)
 */
export function clearToasts(): void {
  if (toastContainerRef) {
    toastContainerRef.clearToasts();
  }
}

// ============================================================================
// Toast Helper Functions
// ============================================================================

/**
 * Show success toast
 */
export function showSuccess(message: string, title: string = 'موفق') {
  return showToast({
    type: 'success',
    title,
    message,
    severity: ErrorSeverity.LOW,
  });
}

/**
 * Show error toast
 */
export function showError(message: string, title: string = 'خطا', severity?: ErrorSeverity) {
  return showToast({
    type: 'error',
    title,
    message,
    severity: severity || ErrorSeverity.HIGH,
    duration: severity === ErrorSeverity.CRITICAL ? 0 : 8000, // Persistent for critical
  });
}

/**
 * Show warning toast
 */
export function showWarning(message: string, title: string = 'هشدار') {
  return showToast({
    type: 'warning',
    title,
    message,
    severity: ErrorSeverity.MEDIUM,
  });
}

/**
 * Show info toast
 */
export function showInfo(message: string, title: string = 'اطلاعات') {
  return showToast({
    type: 'info',
    title,
    message,
    severity: ErrorSeverity.LOW,
  });
}

/**
 * Show toast from AppError
 */
export function showErrorFromAppError(error: AppError) {
  return showError(
    error.getUserMessage(),
    'خطا',
    error.severity
  );
}

// ============================================================================
// Default Export
// ============================================================================

export default ToastContainer;
export type { ToastPosition, ToastContainerProps };
