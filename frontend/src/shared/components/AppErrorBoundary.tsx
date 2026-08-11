/**
 * AppErrorBoundary - Enhanced Error Boundary Component
 * 
 * Centralized error boundary with Sentry integration, governance context,
 * and user-friendly error displays for the MahouN application
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { ShieldCheckIcon, ArrowPathIcon, HomeIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { AppError } from '../errors/AppError';
import { ErrorSeverity, Domain, ErrorContext } from '../errors/types';
import { errorService } from '../services/errorService';
import { showError } from './Toast';

// ============================================================================
// Props and State Types
// ============================================================================

interface AppErrorBoundaryProps {
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>;
  onError?: (error: AppError, errorInfo: ErrorInfo) => void;
  domain?: Domain;
  context?: ErrorContext;
  showGovernanceInfo?: boolean;
}

interface AppErrorBoundaryState {
  error: AppError | null;
  errorInfo: ErrorInfo | null;
  hasRetried: boolean;
}

// ============================================================================
// Default Fallback Component
// ============================================================================

interface FallbackComponentProps {
  error: AppError;
  reset: () => void;
  retry?: () => void;
  goHome?: () => void;
}

const DefaultFallback: React.FC<FallbackComponentProps> = ({ error, reset, retry, goHome }) => {
  // Determine if we should show governance-specific UI
  const isGovernanceError = error.isGovernanceError();
  const requiresAuth = error.requiresAuthentication();
  const isRetryable = error.isRetryable();

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-slate-950"
      dir="rtl"
    >
      <div className="max-w-lg w-full mx-4">
        {/* Main Error Card */}
        <div className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-700/60 p-8 relative overflow-hidden">
          {/* Background Pattern */}
          <div className="absolute inset-0 bg-gradient-to-br from-slate-800/30 to-slate-900/30 opacity-50" />
          <div className="absolute inset-0 bg-grid-pattern opacity-10" />

          <div className="relative">
            {/* Header */}
            <div className="text-center mb-6">
              {isGovernanceError ? (
                <div className="w-16 h-16 bg-red-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-red-500/30">
                  <ShieldCheckIcon className="h-8 w-8 text-red-400" />
                </div>
              ) : requiresAuth ? (
                <div className="w-16 h-16 bg-yellow-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-yellow-500/30">
                  <ShieldCheckIcon className="h-8 w-8 text-yellow-400" />
                </div>
              ) : error.severity === ErrorSeverity.CRITICAL ? (
                <div className="w-16 h-16 bg-red-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-red-500/30">
                  <DocumentTextIcon className="h-8 w-8 text-red-400" />
                </div>
              ) : (
                <div className="w-16 h-16 bg-slate-700/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-slate-600/30">
                  <DocumentTextIcon className="h-8 w-8 text-slate-400" />
                </div>
              )}

              <h1 className="text-2xl font-bold text-white mb-2">
                {isGovernanceError 
                  ? 'نقص در انطباق با قوانین حکمرانی' 
                  : requiresAuth 
                    ? 'دسترسی محدود شده' 
                    : error.severity === ErrorSeverity.CRITICAL
                      ? 'خطای بحرانی' 
                      : 'خطای غیرمنتظره'}
              </h1>

              <p className="text-slate-400 text-sm">
                {error.getUserMessage() || 'خطای ناشناخته‌ای رخ داد. لطفاً دوباره تلاش کنید.'}
              </p>
            </div>

            {/* Error Details Section */}
            <div className="space-y-4">
              {/* Error Metadata */}
              <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/40">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">کد خطا:</span>
                    <span className="font-mono text-slate-300 bg-slate-700/60 px-2 py-0.5 rounded">{error.code}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">حیطه:</span>
                    <span className="font-mono text-slate-300 bg-slate-700/60 px-2 py-0.5 rounded">{error.domain}</span>
                  </div>
                  <div className="flex items-center gap-2 col-span-2">
                    <span className="text-slate-500">سطح:</span>
                    <span className={`font-mono px-2 py-0.5 rounded ${
                      error.severity === ErrorSeverity.CRITICAL ? 'text-red-400 bg-red-900/40' :
                      error.severity === ErrorSeverity.HIGH ? 'text-orange-400 bg-orange-900/40' :
                      error.severity === ErrorSeverity.MEDIUM ? 'text-yellow-400 bg-yellow-900/40' :
                      'text-slate-300 bg-slate-700/60'
                    }`}>
                      {error.severity}
                    </span>
                  </div>
                </div>
              </div>

              {/* Governance Information */}
              {isGovernanceError && (
                <div className="bg-red-900/20 rounded-xl p-4 border border-red-700/30">
                  <div className="flex items-start gap-3">
                    <ShieldCheckIcon className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-red-200/80">
                      <p className="font-semibold text-red-300 mb-1">مinformation حکمرانی</p>
                      <p>
                        این خطا نشان دهنده نقض قوانین حکمرانی سیستم است. 
                        تمام تغییرات تا رسیدگی به این مشکل متوقف شده‌اند.
                      </p>
                      {error.context?.policy && (
                        <p className="mt-2 text-red-400">
                          سیاست نقض شده: <code className="bg-red-900/40 px-1 rounded">{error.context.policy}</code>
                        </p>
                      )}
                      {error.context?.rule && (
                        <p className="text-red-400">
                          قانون نقض شده: <code className="bg-red-900/40 px-1 rounded">{error.context.rule}</code>
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3">
                {retry && isRetryable && !requiresAuth && (
                  <button
                    onClick={retry}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600/20 text-indigo-300 rounded-xl hover:bg-indigo-600/30 border border-indigo-600/30 transition-all font-semibold text-sm"
                  >
                    <ArrowPathIcon className="h-5 w-5" />
                    تلاش مجدد
                  </button>
                )}

                {goHome && (
                  <button
                    onClick={goHome}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-700/20 text-slate-300 rounded-xl hover:bg-slate-700/30 border border-slate-600/30 transition-all font-semibold text-sm"
                  >
                    <HomeIcon className="h-5 w-5" />
                    بازگشت به صفحه اصلی
                  </button>
                )}

                <button
                  onClick={reset}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-600/20 text-red-300 rounded-xl hover:bg-red-600/30 border border-red-600/30 transition-all font-semibold text-sm"
                >
                  <ArrowPathIcon className="h-5 w-5" />
                  بارگذاری مجدد
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Development Details (only in dev mode) */}
        {import.meta.env.DEV && (
          <div className="mt-6 max-w-4xl mx-auto">
            <details className="bg-slate-800/60 rounded-xl border border-slate-700/40 p-4">
              <summary className="cursor-pointer font-semibold text-slate-300 text-sm flex items-center gap-2">
                جزئیات فنی (نسخه توسعه)
              </summary>
              <div className="mt-4 space-y-2 text-xs font-mono text-slate-500">
                <div>
                  <span className="text-slate-400">Error:</span> <span className="text-white">{error.message}</span>
                </div>
                <div>
                  <span className="text-slate-400">Code:</span> <span className="text-white">{error.code}</span>
                </div>
                <div>
                  <span className="text-slate-400">Domain:</span> <span className="text-white">{error.domain}</span>
                </div>
                <div>
                  <span className="text-slate-400">Severity:</span> <span className="text-white">{error.severity}</span>
                </div>
                <div>
                  <span className="text-slate-400">Timestamp:</span> <span className="text-white">{error.context.timestamp}</span>
                </div>
                {error.context && Object.keys(error.context).length > 0 && (
                  <div>
                    <span className="text-slate-400">Context:</span>
                    <pre className="text-white mt-1 bg-slate-900/60 p-2 rounded overflow-auto">
                      {JSON.stringify(error.context, null, 2)}
                    </pre>
                  </div>
                )}
                {error.stack && (
                  <div>
                    <span className="text-slate-400">Stack Trace:</span>
                    <pre className="text-white mt-1 bg-slate-900/60 p-2 rounded overflow-auto max-h-40">
                      {error.stack}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
};

// CSS for grid pattern background
const GridPatternCSS = (
  <style>
    {`.bg-grid-pattern {
      background-image: 
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
      background-size: 20px 20px;
    }`}
  </style>
);

// ============================================================================
// Main AppErrorBoundary Component
// ============================================================================

class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  private governanceContext: ErrorContext = {};

  constructor(props: AppErrorBoundaryProps) {
    super(props);
    this.state = {
      error: null,
      errorInfo: null,
      hasRetried: false,
    };
    
    // Merge provided context with domain
    this.governanceContext = {
      ...props.context,
      domain: props.domain,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<AppErrorBoundaryState> {
    return { error: AppError.fromUnknown(error) };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const appError = AppError.fromUnknown(error, {
      ...this.governanceContext,
      componentStack: errorInfo.componentStack ?? undefined,
    });

    // Log error to service
    errorService.logError(appError);
    errorService.trackError(appError);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(appError, errorInfo);
    }

    // Show toast notification for critical errors
    if (appError.severity === ErrorSeverity.CRITICAL || appError.isGovernanceError()) {
      showError(
        appError.getUserMessage(),
        appError.isGovernanceError() ? 'نقض قوانین حکمرانی' : 'خطای بحرانی',
        appError.severity
      );
    }

    // Update state
    this.setState({ error: appError, errorInfo, hasRetried: false });
  }

  resetErrorBoundary = () => {
    this.setState({ error: null, errorInfo: null, hasRetried: false });
    // Clear governance context on reset
    this.governanceContext = {};
  };

  retryAction = () => {
    this.setState({ hasRetried: true });
    this.resetErrorBoundary();
  };

  goHomeAction = () => {
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
  };

  override render() {
    const { children, fallbackComponent } = this.props;
    const { error } = this.state;

    if (error) {
      // Use custom fallback if provided
      if (fallbackComponent) {
        const Fallback = fallbackComponent;
        return <Fallback error={error} reset={this.resetErrorBoundary} />;
      }

      // Use default fallback
      return (
        <>
          {GridPatternCSS}
          <DefaultFallback
            error={error}
            reset={this.resetErrorBoundary}
            retry={this.retryAction}
            goHome={this.goHomeAction}
          />
        </>
      );
    }

    return <>{children}</>;
  }
}

// ============================================================================
// Higher-Order Components for Domain-Specific Error Boundaries
// ============================================================================

/**
 * Create a domain-specific error boundary
 */
export function withDomainErrorBoundary(
  domain: Domain,
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>
) {
  return class DomainErrorBoundary extends Component<{ children: ReactNode }> {
    override render() {
      return (
        <AppErrorBoundary
          domain={domain}
          fallbackComponent={fallbackComponent}
        >
          {this.props.children}
        </AppErrorBoundary>
      );
    }
  };
}

/**
 * Error boundary for governance-protected components
 */
export function withGovernanceErrorBoundary(
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>
) {
  return class GovernanceErrorBoundary extends Component<{ children: ReactNode }> {
    override render() {
      return (
        <AppErrorBoundary
          domain={Domain.GOVERNANCE}
          fallbackComponent={fallbackComponent}
        >
          {this.props.children}
        </AppErrorBoundary>
      );
    }
  };
}

// ============================================================================
// Convenience Wrappers for Different Domains
// ============================================================================

/**
 * Knowledge Graph Error Boundary
 */
export const KnowledgeGraphErrorBoundary: React.FC<{
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>;
}> = ({ children, fallbackComponent }) => (
  <AppErrorBoundary domain={Domain.KNOWLEDGE_GRAPH} fallbackComponent={fallbackComponent}>
    {children}
  </AppErrorBoundary>
);

/**
 * AI Model Error Boundary
 */
export const AIModelErrorBoundary: React.FC<{
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>;
}> = ({ children, fallbackComponent }) => (
  <AppErrorBoundary domain={Domain.AI_MODELS} fallbackComponent={fallbackComponent}>
    {children}
  </AppErrorBoundary>
);

/**
 * Training Error Boundary
 */
export const TrainingErrorBoundary: React.FC<{
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>;
}> = ({ children, fallbackComponent }) => (
  <AppErrorBoundary domain={Domain.TRAINING} fallbackComponent={fallbackComponent}>
    {children}
  </AppErrorBoundary>
);

/**
 * Dataset Error Boundary
 */
export const DatasetErrorBoundary: React.FC<{
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>;
}> = ({ children, fallbackComponent }) => (
  <AppErrorBoundary domain={Domain.DATASETS} fallbackComponent={fallbackComponent}>
    {children}
  </AppErrorBoundary>
);

/**
 * Governance Error Boundary
 */
export const GovernanceErrorBoundary: React.FC<{
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: AppError; reset: () => void }>;
}> = ({ children, fallbackComponent }) => (
  <AppErrorBoundary 
    domain={Domain.GOVERNANCE} 
    fallbackComponent={fallbackComponent}
    showGovernanceInfo={true}
  >
    {children}
  </AppErrorBoundary>
);

// ============================================================================
// Export
// ============================================================================

export default AppErrorBoundary;
export type { AppErrorBoundaryProps, AppErrorBoundaryState, FallbackComponentProps };
