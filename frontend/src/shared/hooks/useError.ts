/**
 * useError Hook
 * 
 * Custom hook for centralized error handling in React components
 * Provides consistent error management across the application
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { AppError, NetworkError, ValidationError, GovernanceError } from '../errors/AppError';
import { ErrorCode, ErrorSeverity, Domain, ErrorContext, SerializedError } from '../errors/types';
import { errorService } from '../services/errorService';

// ============================================================================
// Toast Message Types
// ============================================================================

export interface ToastMessage {
  id: string;
  type: 'error' | 'warning' | 'success' | 'info';
  title: string;
  message: string;
  severity: ErrorSeverity;
  domain?: Domain;
  code?: ErrorCode;
  duration?: number;
  dismissible?: boolean;
  createdAt: number;
}

// ============================================================================
// UseError Hook Return Type
// ============================================================================

export interface UseErrorReturn {
  // Current error state
  error: AppError | null;
  
  // Array of toast messages
  toasts: ToastMessage[];
  
  // Error handling functions
  setError: (error: AppError | null) => void;
  clearError: () => void;
  handleError: (error: unknown, context?: ErrorContext) => void;
  handleNetworkError: (error: unknown, context?: ErrorContext) => void;
  handleValidationError: (message: string, field?: string, value?: unknown, context?: ErrorContext) => void;
  handleApiError: (response: Response, context?: ErrorContext) => Promise<never>;
  handleGovernanceError: (message: string, policy?: string, rule?: string, context?: ErrorContext) => void;
  handleGovernanceViolationError: (message: string, context?: ErrorContext) => void;
  addToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => void;
  dismissToast: (id: string) => void;
}

// ============================================================================
// useError Hook
// ============================================================================

export function useError(): UseErrorReturn {
  const [error, setError] = useState<AppError | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const addToast = useCallback((toast: Omit<ToastMessage, 'id' | 'createdAt'>) => {
    const id = `toast_${Date.now()}_${Math.random()}`;
    const newToast: ToastMessage = {
      ...toast,
      id,
      createdAt: Date.now(),
    };

    setToasts((prev) => [...prev, newToast]);

    if (toast.duration !== undefined) {
      const timeout = setTimeout(() => {
        dismissToast(id);
      }, toast.duration);
      toastTimeouts.current.set(id, timeout);
    }
  }, []);

  const dismissToast = useCallback((id: string) => {
    const timeout = toastTimeouts.current.get(id);
    if (timeout) {
      clearTimeout(timeout);
      toastTimeouts.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleError = useCallback(
    (error: unknown, _context: ErrorContext = {}) => {
      const appError = AppError.fromError(error);
      setError(appError);
      errorService.logError(appError.serialize());

      addToast({
        type: 'error',
        title: 'Error',
        message: appError.message,
        severity: appError.severity,
        domain: appError.domain,
        code: appError.code,
        duration: 5000,
        dismissible: true,
      });
    },
    [addToast]
  );

  const handleNetworkError = useCallback(
    (error: unknown, context: ErrorContext = {}) => {
      const appError = new NetworkError(
        error instanceof Error ? error.message : 'Network error',
        context
      );
      setError(appError);
      errorService.logError(appError.serialize());

      addToast({
        type: 'error',
        title: 'Network Error',
        message: appError.message,
        severity: ErrorSeverity.HIGH,
        domain: Domain.API,
        duration: 5000,
        dismissible: true,
      });
    },
    [addToast]
  );

  const handleValidationError = useCallback(
    (message: string, field?: string, value?: unknown, context: ErrorContext = {}) => {
      const appError = new ValidationError(message, field, value, context);
      setError(appError);

      addToast({
        type: 'warning',
        title: 'Validation Error',
        message: appError.message,
        severity: ErrorSeverity.MEDIUM,
        domain: Domain.GENERAL,
        duration: 4000,
        dismissible: true,
      });
    },
    [addToast]
  );

  const handleApiError = useCallback(
    async (response: Response, context: ErrorContext = {}) => {
      const data = await response.json().catch(() => ({}));
      const appError = new NetworkError(
        data.message || `API Error: ${response.status}`,
        {
          ...context,
          statusCode: response.status,
        }
      );
      throw appError;
    },
    []
  );

  const handleGovernanceError = useCallback(
    (message: string, policy?: string, rule?: string, context: ErrorContext = {}) => {
      const appError = new GovernanceError(message, {
        ...context,
        policy,
        rule,
      });
      setError(appError);
      errorService.logError(appError.serialize());

      addToast({
        type: 'error',
        title: 'Governance Error',
        message: appError.message,
        severity: ErrorSeverity.CRITICAL,
        domain: Domain.GOVERNANCE,
        duration: 6000,
        dismissible: true,
      });
    },
    [addToast]
  );

  const handleGovernanceViolationError = useCallback(
    (message: string, context: ErrorContext = {}) => {
      const appError = new GovernanceViolationError(message, context);
      setError(appError);
      errorService.logError(appError.serialize());

      addToast({
        type: 'error',
        title: 'Governance Violation',
        message: appError.message,
        severity: ErrorSeverity.CRITICAL,
        domain: Domain.GOVERNANCE,
        duration: 6000,
        dismissible: true,
      });
    },
    [addToast]
  );

  useEffect(() => {
    return () => {
      toastTimeouts.current.forEach((timeout) => clearTimeout(timeout));
      toastTimeouts.current.clear();
    };
  }, []);

  return {
    error,
    toasts,
    setError,
    clearError,
    handleError,
    handleNetworkError,
    handleValidationError,
    handleApiError,
    handleGovernanceError,
    handleGovernanceViolationError,
    addToast,
    dismissToast,
  };
}

// ============================================================================
// Helper Functions (for use outside of React components)
// ============================================================================

/**
 * Normalize error to AppError (standalone function)
 */
export function normalizeError(err: unknown, context: ErrorContext = {}): AppError {
  if (err instanceof AppError) {
    return err;
  }
  
  if (err instanceof Error) {
    if (err.name === 'AbortError') {
      return new AppError(err.message, ErrorCode.ABORT_ERROR, ErrorSeverity.MEDIUM, Domain.GENERAL, context);
    }
    
    if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
      return new NetworkError(err.message, context);
    }
    
    return AppError.fromUnknown(err, context);
  }
  
  if (typeof err === 'string') {
    return new AppError(err, ErrorCode.UNKNOWN_ERROR, ErrorSeverity.MEDIUM, Domain.GENERAL, context);
  }
  
  if (typeof err === 'object' && err !== null) {
    const errorObj = err as Record<string, unknown>;
    
    if ('error' in errorObj && typeof errorObj.error === 'object') {
      const apiError = errorObj.error as Partial<SerializedError>;
      return new AppError(
        apiError.message || 'Unknown error',
        apiError.code as ErrorCode || ErrorCode.UNKNOWN_ERROR,
        ErrorSeverity.MEDIUM,
        Domain.API,
        { ...context, ...apiError.context }
      );
    }
    
    if ('message' in errorObj) {
      return new AppError(
        errorObj.message as string,
        ErrorCode.UNKNOWN_ERROR,
        ErrorSeverity.MEDIUM,
        Domain.GENERAL,
        context
      );
    }
  }
  
  return new AppError('خطای ناشناخته‌ای رخ داد.', ErrorCode.UNKNOWN_ERROR, ErrorSeverity.MEDIUM, Domain.GENERAL, context);
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(err: unknown): string {
  return normalizeError(err).getUserMessage();
}

/**
 * Check if error is retryable
 */
export function isRetryableError(err: unknown): boolean {
  return normalizeError(err).isRetryable();
}

/**
 * Check if error requires authentication
 */
export function requiresAuthentication(err: unknown): boolean {
  return normalizeError(err).requiresAuthentication();
}
