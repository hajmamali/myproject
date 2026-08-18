/**
 * MahouN Error Types
 * 
 * Standard error types and interfaces for centralized error handling
 */

// ============================================================================
// Error Codes Enum
// ============================================================================

export enum ErrorCode {
  // Network Errors (1xxx)
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  CONNECTION_ERROR = 'CONNECTION_ERROR',
  ABORT_ERROR = 'ABORT_ERROR',
  
  // Authentication Errors (2xxx)
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  SESSION_EXPIRED = 'SESSION_EXPIRED',
  INVALID_TOKEN = 'INVALID_TOKEN',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  
  // Validation Errors (3xxx)
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  SCHEMA_VALIDATION_FAILED = 'SCHEMA_VALIDATION_FAILED',
  INVALID_INPUT = 'INVALID_INPUT',
  REQUIRED_FIELD_MISSING = 'REQUIRED_FIELD_MISSING',
  
  // Business Logic Errors (4xxx)
  NOT_FOUND = 'NOT_FOUND',
  DUPLICATE_ENTRY = 'DUPLICATE_ENTRY',
  INVALID_OPERATION = 'INVALID_OPERATION',
  STATE_CONFLICT = 'STATE_CONFLICT',
  RATE_LIMITED = 'RATE_LIMITED',
  
  // Database Errors (5xxx)
  DATABASE_ERROR = 'DATABASE_ERROR',
  TRANSACTION_FAILED = 'TRANSACTION_FAILED',
  CONSTRAINT_VIOLATION = 'CONSTRAINT_VIOLATION',
  
  // Graph Errors (6xxx)
  GRAPH_QUERY_ERROR = 'GRAPH_QUERY_ERROR',
  GRAPH_MUTATION_ERROR = 'GRAPH_MUTATION_ERROR',
  CYPHER_SYNTAX_ERROR = 'CYPHER_SYNTAX_ERROR',
  ONTOLOGY_VIOLATION = 'ONTOLOGY_VIOLATION',
  
  // AI/ML Errors (7xxx)
  MODEL_LOAD_ERROR = 'MODEL_LOAD_ERROR',
  INFERENCE_ERROR = 'INFERENCE_ERROR',
  EMBEDDING_ERROR = 'EMBEDDING_ERROR',
  FINE_TUNING_ERROR = 'FINE_TUNING_ERROR',
  VECTOR_SEARCH_ERROR = 'VECTOR_SEARCH_ERROR',
  
  // Governance Errors (8xxx)
  GOVERNANCE_VIOLATION = 'GOVERNANCE_VIOLATION',
  CONSTITUTIONAL_VIOLATION = 'CONSTITUTIONAL_VIOLATION',
  POLICY_VIOLATION = 'POLICY_VIOLATION',
  FAIL_CLOSED_TRIGGERED = 'FAIL_CLOSED_TRIGGERED',
  MUTATION_UNAUTHORIZED = 'MUTATION_UNAUTHORIZED',
  AUDIT_FAILED = 'AUDIT_FAILED',
  
  // File/Storage Errors (9xxx)
  FILE_UPLOAD_ERROR = 'FILE_UPLOAD_ERROR',
  FILE_PROCESSING_ERROR = 'FILE_PROCESSING_ERROR',
  STORAGE_ERROR = 'STORAGE_ERROR',
  FILE_NOT_FOUND = 'FILE_NOT_FOUND',
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  INVALID_FILE_TYPE = 'INVALID_FILE_TYPE',
  
  // System Errors (10xxx)
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  CONFIGURATION_ERROR = 'CONFIGURATION_ERROR',
  CACHE_ERROR = 'CACHE_ERROR',
  
  // Unknown Error
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

// ============================================================================
// Error Severity Levels
// ============================================================================

export enum ErrorSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

// ============================================================================
// Application Domains
// ============================================================================

export enum Domain {
  // Core
  AUTH = 'AUTH',
  USER = 'USER',
  SESSION = 'SESSION',
  
  // Knowledge Graph
  KNOWLEDGE_GRAPH = 'KNOWLEDGE_GRAPH',
  ONTOLOGY = 'ONTOLOGY',
  SEMANTIC_SEARCH = 'SEMANTIC_SEARCH',
  
  // AI/ML
  AI_MODELS = 'AI_MODELS',
  FINE_TUNING = 'FINE_TUNING',
  TRAINING = 'TRAINING',
  EVALUATION = 'EVALUATION',
  EMBEDDINGS = 'EMBEDDINGS',
  VECTOR_DB = 'VECTOR_DB',
  
  // Data
  DATASETS = 'DATASETS',
  DOCUMENTS = 'DOCUMENTS',
  DATA_PIPELINE = 'DATA_PIPELINE',
  DATA_ENGINEERING = 'DATA_ENGINEERING',
  
  // Governance
  GOVERNANCE = 'GOVERNANCE',
  AUDIT = 'AUDIT',
  COMPLIANCE = 'COMPLIANCE',
  POLICY = 'POLICY',
  
  // Observability
  MONITORING = 'MONITORING',
  LOGGING = 'LOGGING',
  METRICS = 'METRICS',
  TRACING = 'TRACING',
  
  // Experiments
  EXPERIMENTS = 'EXPERIMENTS',
  AB_TESTING = 'AB_TESTING',
  
  // Deployments
  DEPLOYMENT = 'DEPLOYMENT',
  MODEL_REGISTRY = 'MODEL_REGISTRY',
  RUNTIME = 'RUNTIME',
  
  // Files
  FILES = 'FILES',
  STORAGE = 'STORAGE',
  OCR = 'OCR',
  NER = 'NER',
  
  // Unknown
  UNKNOWN = 'UNKNOWN',
}

// ============================================================================
// Error Context Interface
// ============================================================================

export interface ErrorContext {
  timestamp?: string;
  requestId?: string;
  traceId?: string;
  userId?: string;
  sessionId?: string;
  [key: string]: string | undefined;
}

// ============================================================================
// Serialized Error for API Responses
// ============================================================================

export interface SerializedError {
  code: ErrorCode;
  message: string;
  severity: ErrorSeverity;
  domain: Domain;
  context?: ErrorContext;
  timestamp: string;
  stack?: string;
  cause?: SerializedError;
}

// ============================================================================
// Error Response from API
// ============================================================================

export interface ApiErrorResponse {
  error: SerializedError;
  statusCode: number;
  success: false;
}

// ============================================================================
// Error Handler Configuration
// ============================================================================

export interface ErrorHandlerConfig {
  // Whether to show error details to users (development only)
  showDetailsInDevelopment: boolean;
  
  // Whether to log errors to console
  logToConsole: boolean;
  
  // Whether to report errors to error tracking service (Sentry, etc.)
  reportToTrackingService: boolean;
  
  // Maximum error message length to display
  maxMessageLength: number;
  
  // Whether to include stack traces in error reports
  includeStackTraces: boolean;
  
  // Custom error mappings (for transforming backend errors)
  errorMappings: Record<string, Partial<SerializedError>>;
}

export const DEFAULT_ERROR_CONFIG: ErrorHandlerConfig = {
  showDetailsInDevelopment: true,
  logToConsole: true,
  reportToTrackingService: true,
  maxMessageLength: 500,
  includeStackTraces: true,
  errorMappings: {},
};
