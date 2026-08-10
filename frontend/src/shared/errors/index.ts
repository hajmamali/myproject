/**
 * MahouN Centralized Error Handling System
 * 
 * Complete error handling solution including:
 * - Error types and codes
 * - Base error classes
 * - Error service
 * - React hooks
 * - Error boundaries
 * - Toast notifications
 */

// Re-export all error types
export * from './types';

// Re-export all error classes
export {
  AppError,
  NetworkError,
  AuthenticationError,
  ValidationError,
  GovernanceError,
  NotFoundError,
  RateLimitError,
} from './AppError';

// Re-export error service
export {
  errorService,
  initErrorService,
  initSentry,
  setupGlobalErrorHandlers,
  ErrorService,
} from '../services/errorService';

// Re-export hook
export {
  useError,
  normalizeError,
  getErrorMessage,
  isRetryableError,
  requiresAuthentication,
} from '../hooks/useError';

// Re-export components
export {
  default as AppErrorBoundary,
  withDomainErrorBoundary,
  withGovernanceErrorBoundary,
  KnowledgeGraphErrorBoundary,
  AIModelErrorBoundary,
  TrainingErrorBoundary,
  DatasetErrorBoundary,
  GovernanceErrorBoundary,
} from '../components/AppErrorBoundary';

export type {
  AppErrorBoundaryProps,
  AppErrorBoundaryState,
  FallbackComponentProps,
} from '../components/AppErrorBoundary';

// Re-export toast components
export {
  default as ToastContainer,
  ToastProvider,
  useToast,
  showToast,
  dismissToast,
  clearToasts,
  registerToastContainer,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  showErrorFromAppError,
} from '../components/Toast';

export type {
  ToastMessage,
  ToastPosition,
  ToastContainerProps,
} from '../components/Toast';
