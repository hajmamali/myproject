/**
 * Error Service
 * 
 * Centralized error logging and reporting service
 * Handles error reporting to Sentry and other tracking services
 */

import { AppError } from '../errors/AppError';
import { ErrorCode, ErrorSeverity, ErrorContext, DEFAULT_ERROR_CONFIG, ErrorHandlerConfig } from '../errors/types';

// ============================================================================
// Sentry Configuration
// ============================================================================

interface SentryConfig {
  dsn: string;
  environment: string;
  tracesSampleRate: number;
  replaySessionSampleRate: number;
  release: string;
  dist: string;
  beforeSend?: (event: any) => any;
  integrations?: any[];
}

// ============================================================================
// Console Logger Levels
// ============================================================================

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
  CRITICAL = 'CRITICAL',
}

// ============================================================================
// Error Service Class
// ============================================================================

export class ErrorService {
  private config: ErrorHandlerConfig;
  private isInitialized = false;
  private sentryInitialized = false;

  constructor(config: Partial<ErrorHandlerConfig> = {}) {
    this.config = { ...DEFAULT_ERROR_CONFIG, ...config };
  }

  // ============================================================================
  // Initialization
  // ============================================================================

  /**
   * Initialize the error service
   */
  init(config: Partial<ErrorHandlerConfig> = {}): void {
    this.config = { ...this.config, ...config };
    this.isInitialized = true;
    this.logInit();
  }

  /**
   * Initialize Sentry
   */
  initSentry(sentryConfig: SentryConfig): void {
    if (this.sentryInitialized) return;
    
    try {
      // Check if Sentry is available
      if (typeof window !== 'undefined' && 'Sentry' in window) {
        const Sentry = (window as any).Sentry;
        
        Sentry.init({
          dsn: sentryConfig.dsn,
          environment: sentryConfig.environment || import.meta.env.VITE_ENVIRONMENT || 'development',
          tracesSampleRate: sentryConfig.tracesSampleRate ?? 1.0,
          replaySessionSampleRate: sentryConfig.replaySessionSampleRate ?? 0.1,
          release: sentryConfig.release || `mahoun@${import.meta.env.VITE_VERSION || '1.0.0'}`,
          dist: sentryConfig.dist || 'frontend',
          beforeSend: sentryConfig.beforeSend || this.beforeSendHandler.bind(this),
          integrations: sentryConfig.integrations || [
            new (window as any).Sentry.Replay(),
            new (window as any).Sentry.BrowserTracing(),
          ],
        });
        
        this.sentryInitialized = true;
        this.logMessage(LogLevel.INFO, 'Sentry initialized successfully');
      } else {
        this.logMessage(LogLevel.WARN, 'Sentry is not available. Running without error tracking.');
      }
    } catch (error) {
      this.logMessage(LogLevel.ERROR, 'Failed to initialize Sentry:', error);
    }
  }

  // ============================================================================
  // Sentry Before Send Handler
  // ============================================================================

  private beforeSendHandler(event: any): any {
    // Filter out sensitive data
    this.filterSensitiveData(event);
    
    // Add governance context if available
    this.addGovernanceContext(event);
    
    // Don't send in development if configured
    if (import.meta.env.DEV && !this.config.reportToTrackingService) {
      return null;
    }
    
    return event;
  }

  /**
   * Filter sensitive data from error events
   */
  private filterSensitiveData(event: any): void {
    const sensitiveKeys = [
      'password', 'token', 'secret', 'api_key', 'apikey',
      'authorization', 'auth', 'credential', 'cookie',
      'ssn', 'national_id', 'passport', 'bank_account',
    ];
    
    const filterRecursive = (obj: any): any => {
      if (!obj || typeof obj !== 'object') return obj;
      
      if (Array.isArray(obj)) {
        return obj.map(filterRecursive);
      }
      
      const filtered: Record<string, any> = {};
      for (const [key, value] of Object.entries(obj)) {
        const lowerKey = key.toLowerCase();
        const isSensitive = sensitiveKeys.some(sensitive => lowerKey.includes(sensitive));
        
        if (isSensitive) {
          filtered[key] = '[FILTERED]';
        } else {
          filtered[key] = filterRecursive(value);
        }
      }
      return filtered;
    };
    
    if (event.request) {
      event.request.data = filterRecursive(event.request.data);
      event.request.headers = filterRecursive(event.request.headers);
      event.request.url = this.filterUrl(event.request.url);
    }
    
    if (event.extra) {
      event.extra = filterRecursive(event.extra);
    }
  }

  /**
   * Filter sensitive data from URLs
   */
  private filterUrl(url: string): string {
    if (!url) return url;
    
    // Filter out query parameters with sensitive data
    const sensitiveParams = ['token', 'password', 'key', 'secret', 'auth'];
    
    try {
      const urlObj = new URL(url);
      sensitiveParams.forEach(param => {
        if (urlObj.searchParams.has(param)) {
          urlObj.searchParams.set(param, '[FILTERED]');
        }
      });
      return urlObj.toString();
    } catch {
      return url;
    }
  }

  /**
   * Add governance context to error events
   */
  private addGovernanceContext(event: any): void {
    try {
      // Get governance context from storage or global state
      const governanceContext = this.getGovernanceContext();
      
      if (governanceContext) {
        event.contexts = event.contexts || {};
        event.contexts.governance = {
          ...governanceContext,
          timestamp: new Date().toISOString(),
        };
        
        // Add tags for easier filtering in Sentry
        event.tags = event.tags || {};
        if (governanceContext.request_id) {
          event.tags.request_id = governanceContext.request_id;
        }
        if (governanceContext.trace_id) {
          event.tags.trace_id = governanceContext.trace_id;
        }
      }
    } catch (error) {
      this.logMessage(LogLevel.ERROR, 'Failed to add governance context:', error);
    }
  }

  /**
   * Get governance context from various sources
   */
  private getGovernanceContext(): Record<string, string> | null {
    try {
      // Try to get from localStorage
      if (typeof window !== 'undefined') {
        const stored = localStorage.getItem('mahoun-governance-context');
        if (stored) {
          return JSON.parse(stored);
        }
      }
      
      // Try to get from global variable
      if (typeof window !== 'undefined' && (window as any).MahouN?.governanceContext) {
        return (window as any).MahouN.governanceContext;
      }
      
      return null;
    } catch {
      return null;
    }
  }

  // ============================================================================
  // Error Logging
  // ============================================================================

  /**
   * Log an error
   */
  logError(error: AppError | Error): void {
    if (!this.isInitialized) {
      this.init();
    }
    
    // Normalize to AppError
    const appError = error instanceof AppError ? error : AppError.fromUnknown(error);
    
    // Log to console if configured
    if (this.config.logToConsole) {
      this.logAppError(appError);
    }
    
    // Report to tracking service if configured
    if (this.config.reportToTrackingService && this.sentryInitialized) {
      this.reportToSentry(appError);
    }
  }

  /**
   * Log an AppError to console
   */
  private logAppError(error: AppError): void {
    const severity = this.mapSeverityToLogLevel(error.severity);
    const domain = error.domain;
    const code = error.code;
    
    const message = `[
${new Date().toISOString()}]
[
${severity}]
[
${domain}]
[
${code}]
${error.message}`;

    this.logMessage(severity, message, error);
  }

  /**
   * Report error to Sentry
   */
  private reportToSentry(error: AppError): void {
    try {
      if (typeof window !== 'undefined' && 'Sentry' in window) {
        const Sentry = (window as any).Sentry;
        
        // Capture exception with context
        Sentry.captureException(error.originalError || error, {
          contexts: {
            error: {
              code: error.code,
              domain: error.domain,
              severity: error.severity,
              timestamp: error.timestamp,
              isRetryable: error.isRetryable(),
              requiresAuth: error.requiresAuthentication(),
              isGovernance: error.isGovernanceError(),
            },
            ...error.context,
          },
          tags: {
            error_code: error.code,
            domain: error.domain,
            severity: error.severity,
            is_retryable: String(error.isRetryable()),
          },
          level: this.mapSeverityToSentryLevel(error.severity),
          fingerprint: [`mahoun-${error.code}`, error.domain],
        });
        
        // Set user context if available
        if (error.context.userId) {
          Sentry.setUser({ id: error.context.userId });
        }
        
        // Set request context
        if (error.context.requestId) {
          Sentry.setContext('request', { request_id: error.context.requestId });
        }
      }
    } catch (sentryError) {
      this.logMessage(LogLevel.ERROR, 'Failed to report to Sentry:', sentryError);
    }
  }

  /**
   * Log a message to console
   */
  logMessage(level: LogLevel, message: string, error?: unknown): void {
    if (!this.config.logToConsole) return;
    
    const timestamp = new Date().toISOString();
    const formattedMessage = `[
${timestamp}] [
MahouN] [
${level}] ${message}`;

    switch (level) {
      case LogLevel.DEBUG:
        console.debug(formattedMessage, error);
        break;
      case LogLevel.INFO:
        console.info(formattedMessage, error);
        break;
      case LogLevel.WARN:
        console.warn(formattedMessage, error);
        break;
      case LogLevel.ERROR:
      case LogLevel.CRITICAL:
        console.error(formattedMessage, error);
        break;
    }
  }

  /**
   * Log initialization message
   */
  private logInit(): void {
    this.logMessage(
      LogLevel.INFO,
      `Error Service initialized with config: {
        logToConsole: ${this.config.logToConsole},
        reportToTrackingService: ${this.config.reportToTrackingService},
        showDetailsInDevelopment: ${this.config.showDetailsInDevelopment},
        maxMessageLength: ${this.config.maxMessageLength},
        includeStackTraces: ${this.config.includeStackTraces}
      }`
    );
  }

  // ============================================================================
  // Severity Mapping
  // ============================================================================

  private mapSeverityToLogLevel(severity: ErrorSeverity): LogLevel {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return LogLevel.CRITICAL;
      case ErrorSeverity.HIGH:
        return LogLevel.ERROR;
      case ErrorSeverity.MEDIUM:
        return LogLevel.WARN;
      case ErrorSeverity.LOW:
        return LogLevel.INFO;
      default:
        return LogLevel.ERROR;
    }
  }

  private mapSeverityToSentryLevel(severity: ErrorSeverity): string {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return 'fatal';
      case ErrorSeverity.HIGH:
        return 'error';
      case ErrorSeverity.MEDIUM:
        return 'warning';
      case ErrorSeverity.LOW:
        return 'info';
      default:
        return 'error';
    }
  }

  // ============================================================================
  // Error Transformation
  // ============================================================================

  /**
   * Transform fetch error to AppError
   */
  fromFetchError(error: unknown, url: string, context: ErrorContext = {}): AppError {
    if (error instanceof AppError) {
      return error;
    }
    
    if (error instanceof Error) {
      // Network errors
      if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
        return new AppError(
          ErrorCode.NETWORK_ERROR,
          'خطا در اتصال به شبکه',
          { ...context, url }
        );
      }
      
      // Abort errors
      if (error.name === 'AbortError') {
        return new AppError(
          ErrorCode.ABORT_ERROR,
          'عملیات توسط کاربر لغو شد',
          { ...context, url }
        );
      }
      
      // Timeout errors
      if (error.message.includes('timeout') || error.message.includes('Time out')) {
        return new AppError(
          ErrorCode.TIMEOUT_ERROR,
          'زمان انتظار برای پاسخ سرور به پایان رسید',
          { ...context, url }
        );
      }
    }
    
    // Generic network error
    return new AppError(
      ErrorCode.NETWORK_ERROR,
      'خطا در اتصال به سرور',
      { ...context, url }
    );
  }

  /**
   * Transform HTTP response to AppError
   */
  fromHttpResponse(response: Response, context: ErrorContext = {}): AppError {
    return AppError.fromHttpStatus(
      response.status,
      response.statusText || `HTTP ${response.status}`,
      { ...context, url: response.url }
    );
  }

  // ============================================================================
  // Error Grouping and Analytics
  // ============================================================================

  private errorCounts: Record<string, number> = {};
  private lastErrorTimestamps: Record<string, number> = {};

  /**
   * Track error occurrence
   */
  trackError(error: AppError): void {
    const key = `${error.code}:${error.domain}`;
    this.errorCounts[key] = (this.errorCounts[key] || 0) + 1;
    this.lastErrorTimestamps[key] = Date.now();
  }

  /**
   * Get error statistics
   */
  getErrorStats(): Record<string, { count: number; lastOccurred: string }> {
    const stats: Record<string, { count: number; lastOccurred: string }> = {};
    
    for (const [key, count] of Object.entries(this.errorCounts)) {
      const lastTimestamp = this.lastErrorTimestamps[key];
      stats[key] = {
        count,
        lastOccurred: lastTimestamp ? new Date(lastTimestamp).toISOString() : 'N/A',
      };
    }
    
    return stats;
  }

  /**
   * Check if an error has occurred recently
   */
  hasRecentError(error: AppError, withinMs = 30000): boolean {
    const key = `${error.code}:${error.domain}`;
    const lastTimestamp = this.lastErrorTimestamps[key];
    
    if (!lastTimestamp) return false;
    return Date.now() - lastTimestamp < withinMs;
  }

  // ============================================================================
  // Global Error Handler
  // ============================================================================

  /**
   * Set up global error handlers
   */
  setupGlobalHandlers(): void {
    // Window error handler
    if (typeof window !== 'undefined') {
      window.onerror = (message, source, lineno, colno, error) => {
        const appError = error 
          ? AppError.fromUnknown(error, { source, line: String(lineno), column: String(colno) })
          : new AppError(ErrorCode.UNKNOWN_ERROR, String(message), { source, line: String(lineno), column: String(colno) });
        
        this.logError(appError);
        this.trackError(appError);
        
        // Return true to prevent default browser error handling
        return true;
      };
      
      // Unhandled promise rejection handler
      window.addEventListener('unhandledrejection', (event) => {
        const error = event.reason;
        const appError = AppError.fromUnknown(error, { 
          type: 'unhandled_rejection',
          promise: event.promise !== undefined ? '[Promise]' : 'unknown',
        });
        
        this.logError(appError);
        this.trackError(appError);
        
        // Prevent default handling
        event.preventDefault();
      });
    }
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Set governance context for future errors
   */
  setGovernanceContext(context: Record<string, string>): void {
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('mahoun-governance-context', JSON.stringify(context));
        (window as any).MahouN = { ...(window as any).MahouN, governanceContext: context };
      }
    } catch {
      // Ignore storage errors
    }
  }

  /**
   * Clear governance context
   */
  clearGovernanceContext(): void {
    try {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('mahoun-governance-context');
        delete (window as any).MahouN?.governanceContext;
      }
    } catch {
      // Ignore storage errors
    }
  }

  /**
   * Reset error tracking
   */
  reset(): void {
    this.errorCounts = {};
    this.lastErrorTimestamps = {};
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

export const errorService = new ErrorService();

// ============================================================================
// Initialization Function
// ============================================================================

/**
 * Initialize error service with configuration
 */
export function initErrorService(config?: Partial<ErrorHandlerConfig>): void {
  errorService.init(config);
}

/**
 * Initialize Sentry with configuration
 */
export function initSentry(config: SentryConfig): void {
  errorService.initSentry(config);
}

/**
 * Setup global error handlers
 */
export function setupGlobalErrorHandlers(): void {
  errorService.setupGlobalHandlers();
}

// ============================================================================
// Export Types
// ============================================================================

export type { SentryConfig, ErrorHandlerConfig };
export { DEFAULT_ERROR_CONFIG };
