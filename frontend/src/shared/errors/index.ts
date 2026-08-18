/**
 * Error System Index
 * Central export for all error handling utilities
 */

export * from './types';
export * from './AppError';
export { default as AppErrorBoundary } from '../components/AppErrorBoundary';
export { default as ToastContainer, registerToastContainer } from '../components/Toast';
export { useError } from '../hooks/useError';
export { errorService, initErrorService, setupGlobalErrorHandlers } from '../services/errorService';
