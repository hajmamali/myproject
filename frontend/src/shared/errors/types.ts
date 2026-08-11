/**
 * Error Types and Configuration
 */

export enum ErrorCode {
  NETWORK_ERROR = 'NETWORK_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  GOVERNANCE_ERROR = 'GOVERNANCE_ERROR',
  GOVERNANCE_VIOLATION = 'GOVERNANCE_VIOLATION',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  CONFLICT = 'CONFLICT',
  RATE_LIMIT = 'RATE_LIMIT',
  SERVER_ERROR = 'SERVER_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
  ABORT_ERROR = 'ABORT_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum Domain {
  API = 'API',
  AUTH = 'AUTH',
  GOVERNANCE = 'GOVERNANCE',
  SEARCH = 'SEARCH',
  DOCUMENT = 'DOCUMENT',
  GENERAL = 'GENERAL',
  KNOWLEDGE_GRAPH = 'KNOWLEDGE_GRAPH',
  AI_MODELS = 'AI_MODELS',
  TRAINING = 'TRAINING',
  DATASETS = 'DATASETS',
}

export interface ErrorContext {
  timestamp?: number;
  requestId?: string;
  traceId?: string;
  userId?: string;
  endpoint?: string;
  method?: string;
  statusCode?: number;
  details?: Record<string, any>;
  policy?: string;
  rule?: string;
  field?: string;
  value?: unknown;
  url?: string;
  componentStack?: string;
  source?: string;
  type?: string;
  domain?: Domain;
  line?: string;
  column?: string;
  promise?: string;
}

export interface SerializedError {
  code: ErrorCode;
  message: string;
  severity: ErrorSeverity;
  domain: Domain;
  context: ErrorContext;
  stack?: string;
}

export interface ErrorHandlerConfig {
  enableSentry: boolean;
  sentryDSN?: string;
  environment: string;
  logLevel: string;
  retryAttempts: number;
  retryDelay: number;
  logToConsole?: boolean;
  reportToTrackingService?: boolean;
  showDetailsInDevelopment?: boolean;
  maxMessageLength?: number;
  includeStackTraces?: boolean;
}

export const DEFAULT_ERROR_CONFIG: ErrorHandlerConfig = {
  enableSentry: false,
  environment: 'development',
  logLevel: 'info',
  retryAttempts: 3,
  retryDelay: 1000,
  logToConsole: true,
  reportToTrackingService: false,
  showDetailsInDevelopment: true,
  maxMessageLength: 500,
  includeStackTraces: true,
};
