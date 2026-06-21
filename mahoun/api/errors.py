"""
MAHOUN API Error Handling
==========================

Structured error responses for API endpoints.

Architecture:
- Consistent error format across all endpoints
- Detailed error codes for client debugging
- Security-conscious (no internal details leaked)
- Logging integration for monitoring
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mahoun.core.logging import setup_logger

log = setup_logger("api_errors")


class ErrorCode(str, Enum):
    """Standard error codes for MAHOUN API"""
    
    # Client errors (4xx)
    INVALID_REQUEST = "invalid_request"
    MISSING_PARAMETER = "missing_parameter"
    INVALID_PARAMETER = "invalid_parameter"
    RESOURCE_NOT_FOUND = "resource_not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    VERDICT_GENERATION_FAILED = "verdict_generation_failed"
    LEDGER_WRITE_FAILED = "ledger_write_failed"
    PROOF_GENERATION_FAILED = "proof_generation_failed"
    VERIFICATION_FAILED = "verification_failed"
    GRAPH_OPERATION_FAILED = "graph_operation_failed"
    
    # Resource constraint errors
    RESOURCE_CONSTRAINT = "resource_constraint"
    MODE_NOT_SUPPORTED = "mode_not_supported"


class ErrorResponse(BaseModel):
    """Structured error response"""
    
    error: str  # Error code
    message: str  # Human-readable message
    details: Optional[Dict[str, Any]] = None  # Additional context
    timestamp: str  # ISO 8601 timestamp
    request_id: Optional[str] = None  # For tracing


class MAHOUNAPIError(Exception):
    """Base exception for MAHOUN API errors"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_response(self) -> JSONResponse:
        """Convert to FastAPI JSONResponse"""
        error_response = ErrorResponse(
            error=self.error_code.value,
            message=self.message,
            details=self.details,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Log error
        log.error(
            f"API Error: {self.error_code.value} - {self.message}",
            extra={"details": self.details}
        )
        
        return JSONResponse(
            status_code=self.status_code,
            content=error_response.model_dump()
        )


# ============================================================================
# Specific Error Classes
# ============================================================================


class InvalidRequestError(MAHOUNAPIError):
    """Invalid request error (400)"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.INVALID_REQUEST,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class ResourceNotFoundError(MAHOUNAPIError):
    """Resource not found error (404)"""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=f"{resource_type} not found: {resource_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ServiceUnavailableError(MAHOUNAPIError):
    """Service unavailable error (503)"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class VerdictGenerationError(MAHOUNAPIError):
    """Verdict generation failed error (500)"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.VERDICT_GENERATION_FAILED,
            message=f"Verdict generation failed: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class LedgerWriteError(MAHOUNAPIError):
    """Ledger write failed error (500)"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.LEDGER_WRITE_FAILED,
            message=f"Ledger write failed: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ProofGenerationError(MAHOUNAPIError):
    """Proof generation failed error (500)"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.PROOF_GENERATION_FAILED,
            message=f"Proof generation failed: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class VerificationError(MAHOUNAPIError):
    """Verification failed error (500)"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=ErrorCode.VERIFICATION_FAILED,
            message=f"Verification failed: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ResourceConstraintError(MAHOUNAPIError):
    """Resource constraint error (503)"""
    
    def __init__(self, operation: str, mode: str, required_mode: str):
        super().__init__(
            error_code=ErrorCode.RESOURCE_CONSTRAINT,
            message=(
                f"Operation '{operation}' requires {required_mode} mode. "
                f"Current mode: {mode}. "
                f"Please run in {required_mode} mode or enable required resources."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "operation": operation,
                "current_mode": mode,
                "required_mode": required_mode
            }
        )


# ============================================================================
# Error Handler Utilities
# ============================================================================


def handle_runtime_error(e: RuntimeError) -> MAHOUNAPIError:
    """
    Convert RuntimeError to appropriate API error
    
    Args:
        e: RuntimeError from internal operations
    
    Returns:
        MAHOUNAPIError with appropriate code and status
    """
    error_msg = str(e)
    
    # Check for resource constraint errors
    if "DESKTOP_MINIMAL" in error_msg or "ENTERPRISE_FULL" in error_msg:
        return ServiceUnavailableError(
            message=error_msg,
            details={"error_type": "resource_constraint"}
        )
    
    # Check for ledger errors
    if "ledger" in error_msg.lower():
        return LedgerWriteError(message=error_msg)
    
    # Check for graph errors
    if "graph" in error_msg.lower():
        return MAHOUNAPIError(
            error_code=ErrorCode.GRAPH_OPERATION_FAILED,
            message=f"Graph operation failed: {error_msg}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Generic internal error
    return MAHOUNAPIError(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=error_msg,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def handle_value_error(e: ValueError) -> MAHOUNAPIError:
    """
    Convert ValueError to appropriate API error
    
    Args:
        e: ValueError from validation
    
    Returns:
        MAHOUNAPIError with appropriate code and status
    """
    return InvalidRequestError(
        message=str(e),
        details={"error_type": "validation_error"}
    )


def create_error_response(
    error_code: ErrorCode,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create error response
    
    Args:
        error_code: Error code
        message: Error message
        status_code: HTTP status code
        details: Additional details
    
    Returns:
        JSONResponse with error
    """
    error = MAHOUNAPIError(
        error_code=error_code,
        message=message,
        status_code=status_code,
        details=details
    )
    return error.to_response()
