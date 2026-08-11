/**
 * Application Error Classes
 */

import { ErrorCode, ErrorSeverity, Domain, ErrorContext, SerializedError } from './types';

export class AppError extends Error {
  public readonly code: ErrorCode;
  public readonly severity: ErrorSeverity;
  public readonly domain: Domain;
  public readonly context: ErrorContext;
  public readonly originalError?: Error;

  constructor(
    message: string,
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    domain: Domain = Domain.GENERAL,
    context: ErrorContext = {}
  ) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.severity = severity;
    this.domain = domain;
    this.context = {
      timestamp: Date.now(),
      ...context,
    };

    Object.setPrototypeOf(this, AppError.prototype);
  }

  public serialize(): SerializedError {
    return {
      code: this.code,
      message: this.message,
      severity: this.severity,
      domain: this.domain,
      context: this.context,
      stack: this.stack,
    };
  }

  public isRetryable(): boolean {
    return [ErrorCode.NETWORK_ERROR, ErrorCode.TIMEOUT_ERROR, ErrorCode.RATE_LIMIT].includes(
      this.code
    );
  }

  public requiresAuthentication(): boolean {
    return [ErrorCode.AUTHENTICATION_ERROR, ErrorCode.AUTHORIZATION_ERROR].includes(this.code);
  }

  public isGovernanceError(): boolean {
    return this.code === ErrorCode.GOVERNANCE_ERROR;
  }

  public getUserMessage(): string {
    return this.message;
  }

  public static fromUnknown(error: unknown, context: ErrorContext = {}): AppError {
    if (error instanceof AppError) {
      return error;
    }
    
    if (error instanceof Error) {
      return new AppError(error.message, ErrorCode.UNKNOWN_ERROR, ErrorSeverity.MEDIUM, Domain.GENERAL, context);
    }
    
    return new AppError(String(error), ErrorCode.UNKNOWN_ERROR, ErrorSeverity.MEDIUM, Domain.GENERAL, context);
  }

  public static fromError(error: unknown, domain: Domain = Domain.GENERAL): AppError {
    if (error instanceof AppError) {
      return error;
    }

    if (error instanceof Error) {
      return new AppError(error.message, ErrorCode.UNKNOWN_ERROR, ErrorSeverity.MEDIUM, domain);
    }

    return new AppError(String(error), ErrorCode.UNKNOWN_ERROR, ErrorSeverity.MEDIUM, domain);
  }

  public static fromHttpStatus(
    status: number,
    message: string,
    context: ErrorContext = {}
  ): AppError {
    let code: ErrorCode = ErrorCode.SERVER_ERROR;
    let severity: ErrorSeverity = ErrorSeverity.HIGH;

    if (status === 400) {
      code = ErrorCode.VALIDATION_ERROR;
      severity = ErrorSeverity.MEDIUM;
    } else if (status === 401) {
      code = ErrorCode.AUTHENTICATION_ERROR;
      severity = ErrorSeverity.HIGH;
    } else if (status === 403) {
      code = ErrorCode.AUTHORIZATION_ERROR;
      severity = ErrorSeverity.HIGH;
    } else if (status === 404) {
      code = ErrorCode.NOT_FOUND;
      severity = ErrorSeverity.LOW;
    } else if (status === 409) {
      code = ErrorCode.CONFLICT;
      severity = ErrorSeverity.MEDIUM;
    } else if (status === 429) {
      code = ErrorCode.RATE_LIMIT;
      severity = ErrorSeverity.MEDIUM;
    }

    return new AppError(message, code, severity, Domain.API, context);
  }
}

export class NetworkError extends AppError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, ErrorCode.NETWORK_ERROR, ErrorSeverity.HIGH, Domain.API, context);
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, field?: string, value?: unknown, context: ErrorContext = {}) {
    super(message, ErrorCode.VALIDATION_ERROR, ErrorSeverity.MEDIUM, Domain.GENERAL, { ...context, field, value });
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

export class GovernanceError extends AppError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, ErrorCode.GOVERNANCE_ERROR, ErrorSeverity.CRITICAL, Domain.GOVERNANCE, context);
    this.name = 'GovernanceError';
    Object.setPrototypeOf(this, GovernanceError.prototype);
  }

  public static forPolicyViolation(policy: string, rule: string, message: string, context: ErrorContext = {}): GovernanceError {
    return new GovernanceError(message, { ...context, policy, rule });
  }
}

export class AuthenticationError extends AppError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, ErrorCode.AUTHENTICATION_ERROR, ErrorSeverity.HIGH, Domain.AUTH, context);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

export class AuthorizationError extends AppError {
  constructor(message: string, context: ErrorContext = {}) {
    super(message, ErrorCode.AUTHORIZATION_ERROR, ErrorSeverity.HIGH, Domain.AUTH, context);
    this.name = 'AuthorizationError';
    Object.setPrototypeOf(this, AuthorizationError.prototype);
  }
}
