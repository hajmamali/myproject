/**
 * MahouN AppError Class
 * 
 * Base error class for all application errors
 * Provides standardized error handling across the application
 */

import { ErrorCode, ErrorSeverity, Domain, ErrorContext, SerializedError } from './types';

// ============================================================================
// User-Friendly Error Messages (Persian)
// ============================================================================

const USER_FRIENDLY_MESSAGES: Record<ErrorCode, string> = {
  // Network Errors
  [ErrorCode.NETWORK_ERROR]: 'خطا در اتصال به شبکه. لطفاً اتصال اینترنت خود را بررسی کنید.',
  [ErrorCode.TIMEOUT_ERROR]: 'زمان انتظار برای پاسخ سرور به پایان رسید. لطفاً دوباره تلاش کنید.',
  [ErrorCode.CONNECTION_ERROR]: 'اتصال به سرور قطع شد. لطفاً دوباره تلاش کنید.',
  [ErrorCode.ABORT_ERROR]: 'عملیات توسط کاربر لغو شد.',
  
  // Authentication Errors
  [ErrorCode.UNAUTHORIZED]: 'شما مجوز دسترسی به این بخش را ندارید. لطفاً وارد سیستم شوید.',
  [ErrorCode.FORBIDDEN]: 'شما اجازه انجام این عمل را ندارید.',
  [ErrorCode.SESSION_EXPIRED]: 'جلسه شما منقضی شده است. لطفاً دوباره وارد شوید.',
  [ErrorCode.INVALID_TOKEN]: 'توکن معتبر نیست. لطفاً دوباره وارد سیستم شوید.',
  [ErrorCode.PERMISSION_DENIED]: 'شما مجوز کافی برای انجام این عمل را ندارید.',
  
  // Validation Errors
  [ErrorCode.VALIDATION_ERROR]: 'داده‌های وارد شده معتبر نیستند.',
  [ErrorCode.SCHEMA_VALIDATION_FAILED]: 'ساختار داده‌ها درست نیست.',
  [ErrorCode.INVALID_INPUT]: 'ورودی معتبر نیست.',
  [ErrorCode.REQUIRED_FIELD_MISSING]: 'فیلدهای الزامی را پر کنید.',
  
  // Business Logic Errors
  [ErrorCode.NOT_FOUND]: 'مورد مورد نظر یافت نشد.',
  [ErrorCode.DUPLICATE_ENTRY]: 'این مورد قبلاً ثبت شده است.',
  [ErrorCode.INVALID_OPERATION]: 'این عمل در وضعیت فعلی ممکن نیست.',
  [ErrorCode.STATE_CONFLICT]: 'وضعیت فعلی با عمل درخواستی سازگار نیست.',
  [ErrorCode.RATE_LIMITED]: 'تعداد درخواست‌ها بیش از حد مجاز است. لطفاً چند دقیقه صبر کنید.',
  
  // Database Errors
  [ErrorCode.DATABASE_ERROR]: 'خطا در پایگاه داده رخ داد. لطفاً دوباره تلاش کنید.',
  [ErrorCode.TRANSACTION_FAILED]: 'تراکنش با شکست مواجه شد.',
  [ErrorCode.CONSTRAINT_VIOLATION]: 'محدودیت پایگاه داده نقض شده است.',
  
  // Graph Errors
  [ErrorCode.GRAPH_QUERY_ERROR]: 'خطا در پرس و جو گراف دانش.',
  [ErrorCode.GRAPH_MUTATION_ERROR]: 'خطا در اعمال تغییرات روی گراف دانش.',
  [ErrorCode.CYPHER_SYNTAX_ERROR]: 'سینتکس پرس و جو ناشر است.',
  [ErrorCode.ONTOLOGY_VIOLATION]: 'تغییری باعث نقض هستی‌شناسی می‌شود.',
  
  // AI/ML Errors
  [ErrorCode.MODEL_LOAD_ERROR]: 'خطا در بارگذاری مدل هوش مصنوعی.',
  [ErrorCode.INFERENCE_ERROR]: 'خطا در استنتاج مدل رخ داد.',
  [ErrorCode.EMBEDDING_ERROR]: 'خطا در تولید بردارهای معنایی.',
  [ErrorCode.FINE_TUNING_ERROR]: 'خطا در فرآیند تنظیم دقیق مدل.',
  [ErrorCode.VECTOR_SEARCH_ERROR]: 'خطا در جستجوی برداری.',
  
  // Governance Errors
  [ErrorCode.GOVERNANCE_VIOLATION]: 'این عمل باعث نقض قوانین حکمرانی می‌شود.',
  [ErrorCode.CONSTITUTIONAL_VIOLATION]: 'این عمل با قانون اساسی سیستم مغایرت دارد.',
  [ErrorCode.POLICY_VIOLATION]: 'این عمل با سیاست‌های سیستم مغایرت دارد.',
  [ErrorCode.FAIL_CLOSED_TRIGGERED]: 'به دلیل نقص اطلاعات، سیستم به حالت ایمن وارد شد.',
  [ErrorCode.MUTATION_UNAUTHORIZED]: 'تغییرات مورد نظر مجوز لازم را ندارند.',
  [ErrorCode.AUDIT_FAILED]: 'ثبت رویداد ممیزی با شکست مواجه شد.',
  
  // File/Storage Errors
  [ErrorCode.FILE_UPLOAD_ERROR]: 'خطا در آپلود فایل.',
  [ErrorCode.FILE_PROCESSING_ERROR]: 'خطا در پردازش فایل.',
  [ErrorCode.STORAGE_ERROR]: 'خطا در ذخیره‌سازی فایل.',
  [ErrorCode.FILE_NOT_FOUND]: 'فایل مورد نظر یافت نشد.',
  [ErrorCode.FILE_TOO_LARGE]: 'حجم فایل بیش از حد مجاز است.',
  [ErrorCode.INVALID_FILE_TYPE]: 'نوع فایل پذیرفته نمی‌شود.',
  
  // System Errors
  [ErrorCode.INTERNAL_SERVER_ERROR]: 'خطای داخلی سرور رخ داد. لطفاً دوباره تلاش کنید.',
  [ErrorCode.SERVICE_UNAVAILABLE]: 'سرویس در حال حاضر در دسترس نیست. لطفاً دوباره تلاش کنید.',
  [ErrorCode.CONFIGURATION_ERROR]: 'خطا در تنظیمات سیستم.',
  [ErrorCode.CACHE_ERROR]: 'خطا در کش سیستم.',
  
  // Unknown Error
  [ErrorCode.UNKNOWN_ERROR]: 'خطای ناشناخته‌ای رخ داد. لطفاً دوباره تلاش کنید.',
};

// ============================================================================
// Severity Levels by Error Code
// ============================================================================

const ERROR_SEVERITIES: Partial<Record<ErrorCode, ErrorSeverity>> = {
  // Critical Errors
  [ErrorCode.INTERNAL_SERVER_ERROR]: ErrorSeverity.CRITICAL,
  [ErrorCode.SERVICE_UNAVAILABLE]: ErrorSeverity.CRITICAL,
  [ErrorCode.DATABASE_ERROR]: ErrorSeverity.CRITICAL,
  [ErrorCode.CONSTITUTIONAL_VIOLATION]: ErrorSeverity.CRITICAL,
  [ErrorCode.FAIL_CLOSED_TRIGGERED]: ErrorSeverity.CRITICAL,
  [ErrorCode.GOVERNANCE_VIOLATION]: ErrorSeverity.CRITICAL,
  
  // High Severity Errors
  [ErrorCode.UNAUTHORIZED]: ErrorSeverity.HIGH,
  [ErrorCode.FORBIDDEN]: ErrorSeverity.HIGH,
  [ErrorCode.SESSION_EXPIRED]: ErrorSeverity.HIGH,
  [ErrorCode.PERMISSION_DENIED]: ErrorSeverity.HIGH,
  [ErrorCode.VALIDATION_ERROR]: ErrorSeverity.HIGH,
  [ErrorCode.MUTATION_UNAUTHORIZED]: ErrorSeverity.HIGH,
  [ErrorCode.POLICY_VIOLATION]: ErrorSeverity.HIGH,
  
  // Medium Severity Errors
  [ErrorCode.NETWORK_ERROR]: ErrorSeverity.MEDIUM,
  [ErrorCode.TIMEOUT_ERROR]: ErrorSeverity.MEDIUM,
  [ErrorCode.CONNECTION_ERROR]: ErrorSeverity.MEDIUM,
  [ErrorCode.NOT_FOUND]: ErrorSeverity.MEDIUM,
  [ErrorCode.DUPLICATE_ENTRY]: ErrorSeverity.MEDIUM,
  [ErrorCode.INVALID_OPERATION]: ErrorSeverity.MEDIUM,
  [ErrorCode.RATE_LIMITED]: ErrorSeverity.MEDIUM,
  [ErrorCode.MODEL_LOAD_ERROR]: ErrorSeverity.MEDIUM,
  [ErrorCode.INFERENCE_ERROR]: ErrorSeverity.MEDIUM,
  
  // Low Severity Errors
  [ErrorCode.ABORT_ERROR]: ErrorSeverity.LOW,
  [ErrorCode.INVALID_INPUT]: ErrorSeverity.LOW,
  [ErrorCode.REQUIRED_FIELD_MISSING]: ErrorSeverity.LOW,
};

// ============================================================================
// Domain by Error Code
// ============================================================================

const ERROR_DOMAINS: Partial<Record<ErrorCode, Domain>> = {
  [ErrorCode.UNAUTHORIZED]: Domain.AUTH,
  [ErrorCode.FORBIDDEN]: Domain.AUTH,
  [ErrorCode.SESSION_EXPIRED]: Domain.SESSION,
  [ErrorCode.INVALID_TOKEN]: Domain.AUTH,
  [ErrorCode.PERMISSION_DENIED]: Domain.AUTH,
  
  [ErrorCode.GRAPH_QUERY_ERROR]: Domain.KNOWLEDGE_GRAPH,
  [ErrorCode.GRAPH_MUTATION_ERROR]: Domain.KNOWLEDGE_GRAPH,
  [ErrorCode.CYPHER_SYNTAX_ERROR]: Domain.KNOWLEDGE_GRAPH,
  [ErrorCode.ONTOLOGY_VIOLATION]: Domain.ONTOLOGY,
  
  [ErrorCode.MODEL_LOAD_ERROR]: Domain.AI_MODELS,
  [ErrorCode.INFERENCE_ERROR]: Domain.AI_MODELS,
  [ErrorCode.EMBEDDING_ERROR]: Domain.EMBEDDINGS,
  [ErrorCode.FINE_TUNING_ERROR]: Domain.FINE_TUNING,
  [ErrorCode.VECTOR_SEARCH_ERROR]: Domain.VECTOR_DB,
  
  [ErrorCode.GOVERNANCE_VIOLATION]: Domain.GOVERNANCE,
  [ErrorCode.CONSTITUTIONAL_VIOLATION]: Domain.GOVERNANCE,
  [ErrorCode.POLICY_VIOLATION]: Domain.POLICY,
  [ErrorCode.FAIL_CLOSED_TRIGGERED]: Domain.GOVERNANCE,
  [ErrorCode.MUTATION_UNAUTHORIZED]: Domain.GOVERNANCE,
  [ErrorCode.AUDIT_FAILED]: Domain.AUDIT,
  
  [ErrorCode.FILE_UPLOAD_ERROR]: Domain.FILES,
  [ErrorCode.FILE_PROCESSING_ERROR]: Domain.FILES,
  [ErrorCode.STORAGE_ERROR]: Domain.STORAGE,
  [ErrorCode.FILE_NOT_FOUND]: Domain.FILES,
  [ErrorCode.FILE_TOO_LARGE]: Domain.FILES,
  [ErrorCode.INVALID_FILE_TYPE]: Domain.FILES,
};

/**
 * Base Application Error Class
 * All custom errors should extend this class
 */
export class AppError extends Error {
  public readonly code: ErrorCode;
  public readonly severity: ErrorSeverity;
  public readonly domain: Domain;
  public readonly context: ErrorContext;
  public readonly timestamp: string;
  public readonly originalError?: Error;
  public override readonly stack?: string;

  constructor(
    code: ErrorCode,
    message?: string,
    context: ErrorContext = {},
    originalError?: Error
  ) {
    // Use user-friendly message if not provided
    const userFriendlyMessage = message || USER_FRIENDLY_MESSAGES[code] || 'خطای ناشناخته‌ای رخ داد.';
    
    super(userFriendlyMessage);
    
    // Set error properties
    this.code = code;
    this.severity = ERROR_SEVERITIES[code] || ErrorSeverity.MEDIUM;
    this.domain = ERROR_DOMAINS[code] || Domain.UNKNOWN;
    this.context = context;
    this.timestamp = new Date().toISOString();
    this.originalError = originalError;
    this.stack = this.getFullStackTrace();
    
    // Maintain proper stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AppError);
    }
    
    // Set error name
    this.name = 'AppError';
  }

  /**
   * Get full stack trace including cause chain
   */
  private getFullStackTrace(): string {
    const stackParts: string[] = [];
    
    // Current error stack
    if (this.stack) {
      stackParts.push(`AppError (${this.code}): ${this.message}`);
      stackParts.push(this.stack);
    }
    
    // Original error stack
    if (this.originalError?.stack) {
      stackParts.push('\nCaused by:');
      stackParts.push(this.originalError.stack);
    }
    
    return stackParts.join('\n');
  }

  /**
   * Convert to serialized error for API responses
   */
  toSerializedError(): SerializedError {
    return {
      code: this.code,
      message: this.message,
      severity: this.severity,
      domain: this.domain,
      context: this.context,
      timestamp: this.timestamp,
      stack: process.env.NODE_ENV === 'development' ? this.stack : undefined,
      cause: this.originalError ? new AppError(
        ErrorCode.UNKNOWN_ERROR,
        this.originalError.message,
        {},
        this.originalError
      ).toSerializedError() : undefined,
    };
  }

  /**
   * Get user-friendly message
   */
  getUserMessage(): string {
    return USER_FRIENDLY_MESSAGES[this.code] || this.message || 'خطای ناشناخته‌ای رخ داد.';
  }

  /**
   * Check if error is retryable
   */
  isRetryable(): boolean {
    const nonRetryableErrors = [
      ErrorCode.UNAUTHORIZED,
      ErrorCode.FORBIDDEN,
      ErrorCode.PERMISSION_DENIED,
      ErrorCode.VALIDATION_ERROR,
      ErrorCode.NOT_FOUND,
      ErrorCode.DUPLICATE_ENTRY,
      ErrorCode.INVALID_OPERATION,
      ErrorCode.STATE_CONFLICT,
      ErrorCode.GOVERNANCE_VIOLATION,
      ErrorCode.CONSTITUTIONAL_VIOLATION,
      ErrorCode.POLICY_VIOLATION,
      ErrorCode.MUTATION_UNAUTHORIZED,
    ];
    
    return !nonRetryableErrors.includes(this.code);
  }

  /**
   * Check if error requires user authentication
   */
  requiresAuthentication(): boolean {
    return [
      ErrorCode.UNAUTHORIZED,
      ErrorCode.SESSION_EXPIRED,
      ErrorCode.INVALID_TOKEN,
    ].includes(this.code);
  }

  /**
   * Check if error is related to governance
   */
  isGovernanceError(): boolean {
    return [
      ErrorCode.GOVERNANCE_VIOLATION,
      ErrorCode.CONSTITUTIONAL_VIOLATION,
      ErrorCode.POLICY_VIOLATION,
      ErrorCode.FAIL_CLOSED_TRIGGERED,
      ErrorCode.MUTATION_UNAUTHORIZED,
      ErrorCode.AUDIT_FAILED,
      ErrorCode.ONTOLOGY_VIOLATION,
    ].includes(this.code);
  }

  /**
   * Create error from HTTP status code
   */
  static fromHttpStatus(
    statusCode: number,
    message?: string,
    context: ErrorContext = {}
  ): AppError {
    switch (statusCode) {
      case 400:
        return new AppError(ErrorCode.VALIDATION_ERROR, message, context);
      case 401:
        return new AppError(ErrorCode.UNAUTHORIZED, message, context);
      case 403:
        return new AppError(ErrorCode.FORBIDDEN, message, context);
      case 404:
        return new AppError(ErrorCode.NOT_FOUND, message, context);
      case 409:
        return new AppError(ErrorCode.STATE_CONFLICT, message, context);
      case 422:
        return new AppError(ErrorCode.VALIDATION_ERROR, message, context);
      case 429:
        return new AppError(ErrorCode.RATE_LIMITED, message, context);
      case 500:
        return new AppError(ErrorCode.INTERNAL_SERVER_ERROR, message, context);
      case 502:
      case 503:
      case 504:
        return new AppError(ErrorCode.SERVICE_UNAVAILABLE, message, context);
      default:
        return new AppError(ErrorCode.UNKNOWN_ERROR, message, context);
    }
  }

  /**
   * Create error from unknown error
   */
  static fromUnknown(
    error: unknown,
    context: ErrorContext = {}
  ): AppError {
    if (error instanceof AppError) {
      return error;
    }
    
    // Extract meaningful message
    let message = 'خطای ناشناخته‌ای رخ داد.';
    let code = ErrorCode.UNKNOWN_ERROR;
    let domain = context.domain || Domain.UNKNOWN;
    
    if (error instanceof Error) {
      message = error.message || message;
      
      // Try to determine code from error name
      if (error.name === 'TypeError') {
        code = ErrorCode.VALIDATION_ERROR;
      } else if (error.name === 'RangeError') {
        code = ErrorCode.VALIDATION_ERROR;
      } else if (error.name === 'ReferenceError') {
        code = ErrorCode.NOT_FOUND;
      } else if (error.name === 'SyntaxError') {
        code = ErrorCode.INVALID_OPERATION;
      }
      
      return new AppError(code, message, { ...context, domain }, error);
    }
    
    // Handle string errors
    if (typeof error === 'string') {
      message = error;
      return new AppError(code, message, { ...context, domain });
    }
    
    // Handle objects with message property
    if (typeof error === 'object' && error !== null) {
      const objError = error as Record<string, unknown>;
      
      if ('message' in objError) {
        message = String(objError.message);
      }
      
      if ('code' in objError) {
        code = objError.code as ErrorCode;
      }
      
      if ('domain' in objError) {
        domain = objError.domain as Domain;
      }
      
      return new AppError(code, message, { ...context, domain });
    }
    
    return new AppError(code, message, { ...context, domain });
  }

  /**
   * Check if value is an AppError
   */
  static isAppError(error: unknown): error is AppError {
    return error instanceof AppError;
  }
}

// ============================================================================
// Specialized Error Classes
// ============================================================================

/**
 * Network Error - For network-related issues
 */
export class NetworkError extends AppError {
  constructor(
    message?: string,
    context: ErrorContext = {},
    originalError?: Error
  ) {
    super(ErrorCode.NETWORK_ERROR, message, context, originalError);
    this.name = 'NetworkError';
  }

  static fromError(error: Error, context: ErrorContext = {}): NetworkError {
    return new NetworkError(error.message, context, error);
  }
}

/**
 * Authentication Error - For authentication-related issues
 */
export class AuthenticationError extends AppError {
  constructor(
    message?: string,
    context: ErrorContext = {},
    originalError?: Error
  ) {
    super(ErrorCode.UNAUTHORIZED, message, context, originalError);
    this.name = 'AuthenticationError';
  }

  static fromError(error: Error, context: ErrorContext = {}): AuthenticationError {
    return new AuthenticationError(error.message, context, error);
  }
}

/**
 * Validation Error - For input validation issues
 */
export class ValidationError extends AppError {
  public readonly field?: string;
  public readonly value?: unknown;

  constructor(
    message: string,
    field?: string,
    value?: unknown,
    context: ErrorContext = {}
  ) {
    super(ErrorCode.VALIDATION_ERROR, message, context);
    this.field = field;
    this.value = value;
    this.name = 'ValidationError';
  }

  override toSerializedError(): SerializedError {
    const base = super.toSerializedError();
    return {
      ...base,
      context: {
        ...base.context,
        field: this.field,
        value: this.value !== undefined ? String(this.value) : undefined,
      },
    };
  }

  static fromZodError(error: any, context: ErrorContext = {}): ValidationError {
    if (error?.errors && Array.isArray(error.errors)) {
      const firstError = error.errors[0];
      return new ValidationError(
        firstError?.message || 'Validation failed',
        firstError?.path?.[0],
        firstError?.value,
        context
      );
    }
    return new ValidationError(error?.message || 'Validation failed', undefined, undefined, context);
  }
}

/**
 * Governance Error - For governance-related violations
 */
export class GovernanceError extends AppError {
  public readonly policy?: string;
  public readonly rule?: string;

  constructor(
    message: string,
    code: ErrorCode = ErrorCode.GOVERNANCE_VIOLATION,
    policy?: string,
    rule?: string,
    context: ErrorContext = {}
  ) {
    super(code, message, context);
    this.policy = policy;
    this.rule = rule;
    this.name = 'GovernanceError';
  }

  override toSerializedError(): SerializedError {
    const base = super.toSerializedError();
    return {
      ...base,
      context: {
        ...base.context,
        policy: this.policy,
        rule: this.rule,
      },
    };
  }

  static forMutationUnauthorized(message: string = 'Mutation not authorized', context: ErrorContext = {}): GovernanceError {
    return new GovernanceError(
      message,
      ErrorCode.MUTATION_UNAUTHORIZED,
      undefined,
      undefined,
      context
    );
  }

  static forPolicyViolation(policy: string, rule: string, message: string, context: ErrorContext = {}): GovernanceError {
    return new GovernanceError(
      message,
      ErrorCode.POLICY_VIOLATION,
      policy,
      rule,
      context
    );
  }

  static forFailClosed(message: string = 'Fail-closed mode triggered', context: ErrorContext = {}): GovernanceError {
    return new GovernanceError(
      message,
      ErrorCode.FAIL_CLOSED_TRIGGERED,
      undefined,
      undefined,
      context
    );
  }
}

/**
 * Not Found Error - For missing resources
 */
export class NotFoundError extends AppError {
  public readonly resourceType: string;
  public readonly resourceId?: string;

  constructor(
    resourceType: string,
    resourceId?: string,
    context: ErrorContext = {}
  ) {
    super(
      ErrorCode.NOT_FOUND,
      `مورد مورد نظر از نوع ${resourceType} یافت نشد.`,
      context
    );
    this.resourceType = resourceType;
    this.resourceId = resourceId;
    this.name = 'NotFoundError';
  }

  override toSerializedError(): SerializedError {
    const base = super.toSerializedError();
    return {
      ...base,
      context: {
        ...base.context,
        resourceType: this.resourceType,
        resourceId: this.resourceId,
      },
    };
  }
}

/**
 * Rate Limit Error - For rate limiting
 */
export class RateLimitError extends AppError {
  public readonly retryAfter?: number;

  constructor(
    retryAfter?: number,
    context: ErrorContext = {}
  ) {
    super(
      ErrorCode.RATE_LIMITED,
      retryAfter 
        ? `لطفاً ${Math.ceil(retryAfter / 1000)} ثانیه صبر کنید.` 
        : undefined,
      context
    );
    this.retryAfter = retryAfter;
    this.name = 'RateLimitError';
  }
}
