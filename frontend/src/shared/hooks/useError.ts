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
  
  // Toast functions
  showToast: (toast: Omit<ToastMessage, 'id' | 'createdAt'>) => string;
  dismissToast: (id: string) => void;
  clearToasts: () => void;
  
  // Utility functions
  normalizeError: (error: unknown, context?: ErrorContext) => AppError;
  getErrorMessage: (error: unknown) => string;
  isRetryableError: (error: unknown) => boolean;
  requiresAuth: (error: unknown) => boolean;
}

// ============================================================================
// Default Toast Configuration
// ============================================================================

const DEFAULT_TOAST_DURATION = 5000;

// ============================================================================
// useError Hook Implementation
// ============================================================================

export function useError(): UseErrorReturn {
  const [error, setError] = useState<AppError | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastIdRef = useRef(0);

  // Auto-dismiss toasts
  useEffect(() => {
    if (toasts.length === 0) return;
    
    const timers = toasts.map(toast => {
      if (toast.dismissible === false) return null;
      
      const duration = toast.duration ?? DEFAULT_TOAST_DURATION;
      return setTimeout(() => {
        dismissToast(toast.id);
      }, duration);
    });
    
    return () => {
      timers.forEach(timer => timer && clearTimeout(timer));
    };
  }, [toasts]);

  // ============================================================================
  // Error Handling Functions
  // ============================================================================

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const showToast = useCallback((toast: Omit<ToastMessage, 'id' | 'createdAt'>): string => {
    const id = String(++toastIdRef.current);
    const newToast: ToastMessage = {
      id,
      createdAt: Date.now(),
      ...toast,
    };
    setToasts(prev => [...prev, newToast]);
    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const normalizeError = useCallback((err: unknown, context: ErrorContext = {}): AppError => {
    try {
      if (err instanceof AppError) {
        return err;
      }
      
      if (err instanceof Error) {
        // Check for specific error types
        if (err.name === 'AbortError') {
          return new AppError(ErrorCode.ABORT_ERROR, err.message, context);
        }
        
        if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
          return new NetworkError(err.message, context);
        }
        
        // Generic error
        return AppError.fromUnknown(err, context);
      }
      
      // Handle string errors
      if (typeof err === 'string') {
        return new AppError(ErrorCode.UNKNOWN_ERROR, err, context);
      }
      
      // Handle objects with error properties
      if (typeof err === 'object' && err !== null) {
        const errorObj = err as Record<string, unknown>;
        
        // Handle API error responses
        if ('error' in errorObj && typeof errorObj.error === 'object') {
          const apiError = errorObj.error as Partial<SerializedError>;
          return new AppError(
            apiError.code as ErrorCode || ErrorCode.UNKNOWN_ERROR,
            apiError.message,
            { ...context, ...apiError.context }
          );
        }
        
        // Handle error with message
        if ('message' in errorObj) {
          return new AppError(
            ErrorCode.UNKNOWN_ERROR,
            errorObj.message as string,
            context
          );
        }
      }
      
      return new AppError(ErrorCode.UNKNOWN_ERROR, 'خطای ناشناخته‌ای رخ داد.', context);
    } catch {
      return new AppError(ErrorCode.UNKNOWN_ERROR, 'خطای ناشناخته‌ای رخ داد.', context);
    }
  }, []);

  const handleError = useCallback((err: unknown, context: ErrorContext = {}) => {
    const appError = normalizeError(err, context);
    
    // Log error to service
    errorService.logError(appError);
    
    // Set error state
    setError(appError);
    
    // Show toast for non-retryable or high severity errors
    if (!appError.isRetryable() || appError.severity === ErrorSeverity.HIGH || appError.severity === ErrorSeverity.CRITICAL) {
      showToast({
        type: 'error',
        title: 'خطا',
        message: appError.getUserMessage(),
        severity: appError.severity,
        domain: appError.domain,
        code: appError.code,
        duration: appError.severity === ErrorSeverity.CRITICAL ? 10000 : DEFAULT_TOAST_DURATION,
      });
    }
  }, [normalizeError]);

  const handleNetworkError = useCallback((err: unknown, context: ErrorContext = {}) => {
    const error = NetworkError.fromError(
      err instanceof Error ? err : new Error(String(err)),
      context
    );
    handleError(error, context);
  }, [handleError]);

  const handleValidationError = useCallback((
    message: string,
    field?: string,
    value?: unknown,
    context: ErrorContext = {}
  ) => {
    const error = new ValidationError(message, field, value, context);
    handleError(error, context);
  }, [handleError]);

  const handleGovernanceError = useCallback((
    message: string,
    policy?: string,
    rule?: string,
    context: ErrorContext = {}
  ) => {
    const error = GovernanceError.forPolicyViolation(
      policy || '',
      rule || '',
      message,
      context
    );
    handleError(error, context);
    
    // Governance errors are critical - show persistent toast
    showToast({
      type: 'error',
      title: 'نقص در انطباق با قوانین حکمرانی',
      message: message,
      severity: ErrorSeverity.CRITICAL,
      domain: Domain.GOVERNANCE,
      code: ErrorCode.GOVERNANCE_VIOLATION,
      duration: 0, // Persistent
      dismissible: true,
    });
  }, [handleError, showToast]);

  const handleApiError = useCallback(async (response: Response, context: ErrorContext = {}): Promise<never> => {
    const status = response.status;
    let message = 'خطای سرور';
    
    try {
      const data = await response.json().catch(() => ({}));
      if (data?.message) {
        message = data.message;
      } else if (data?.error?.message) {
        message = data.error.message;
      }
    } catch {
      // Ignore JSON parse errors
    }
    
    const error = AppError.fromHttpStatus(status, message, context);
    
    // Log error
    errorService.logError(error);
    
    // Set error state
    setError(error);
    
    // Show toast for API errors
    showToast({
      type: 'error',
      title: 'خطای سرور',
      message: error.getUserMessage(),
      severity: error.severity,
      domain: error.domain,
      code: error.code,
      duration: status === 401 || status === 403 ? 0 : DEFAULT_TOAST_DURATION, // Persistent for auth errors
      dismissible: true,
    });
    
    // Throw error to stop execution
    throw error;
  }, [showToast, dismissToast]);

  // ============================================================================
  // Utility Functions
  // ============================================================================

  const getErrorMessage = useCallback((err: unknown): string => {
    const error = normalizeError(err);
    return error.getUserMessage();
  }, [normalizeError]);

  const isRetryableError = useCallback((err: unknown): boolean => {
    const error = normalizeError(err);
    return error.isRetryable();
  }, [normalizeError]);

  const requiresAuth = useCallback((err: unknown): boolean => {
    const error = normalizeError(err);
    return error.requiresAuthentication();
  }, [normalizeError]);

  // ============================================================================
  // Return all functions and state
  // ============================================================================

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
    showToast,
    dismissToast,
    clearToasts,
    normalizeError,
    getErrorMessage,
    isRetryableError,
    requiresAuth,
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
      return new AppError(ErrorCode.ABORT_ERROR, err.message, context);
    }
    
    if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
      return new NetworkError(err.message, context);
    }
    
    return AppError.fromUnknown(err, context);
  }
  
  if (typeof err === 'string') {
    return new AppError(ErrorCode.UNKNOWN_ERROR, err, context);
  }
  
  if (typeof err === 'object' && err !== null) {
    const errorObj = err as Record<string, unknown>;
    
    if ('error' in errorObj && typeof errorObj.error === 'object') {
      const apiError = errorObj.error as Partial<SerializedError>;
      return new AppError(
        apiError.code as ErrorCode || ErrorCode.UNKNOWN_ERROR,
        apiError.message,
        { ...context, ...apiError.context }
      );
    }
    
    if ('message' in errorObj) {
      return new AppError(
        ErrorCode.UNKNOWN_ERROR,
        errorObj.message as string,
        context
      );
    }
  }
  
  return new AppError(ErrorCode.UNKNOWN_ERROR, 'خطای ناشناخته‌ای رخ داد.', context);
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
