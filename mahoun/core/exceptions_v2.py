"""
MAHOUN Unified Exception Hierarchy V2
======================================
Single canonical exception base with HTTP-aware + error_code unification.

This resolves the P0 duplication between MahounError and BaseMahounError.

Migration Strategy:
- All new code MUST use exceptions from this module
- Old exceptions.py maintained for backward compatibility with deprecation warnings
- imports should be: from mahoun.core.exceptions_v2 import MahounException, ...
"""

from typing import Any, Dict, Optional


# =============================================================================
# UNIFIED ROOT EXCEPTION (HTTP-AWARE + ERROR_CODE)
# =============================================================================

class MahounException(Exception):
    """
    Unified root exception for all MAHOUN platform errors.
    
    Combines:
    - HTTP status_code (from BaseMahounError)
    - error_code machine-readable identifier (from MahounError)
    - Consistent to_dict() signature
    - Deterministic HTTP response mapping
    
    All subclasses MUST:
    1. Declare immutable status_code
    2. Declare unique error_code
    3. Preserve to_dict() signature
    """
    
    status_code: int = 500  # Default: Internal Server Error
    error_code: str = "MAHOUN_ERROR"
    
    def __init__(
        self,
        message: str,
        *,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.correlation_id = correlation_id
        self.details = details or {}
        
        # Allow per-instance error_code override (for backward compat)
        if error_code:
            self.error_code = error_code
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for deterministic API responses.
        
        Returns:
            dict with error_type, error_code, message, correlation_id, details
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "details": self.details,
        }


# =============================================================================
# GOVERNANCE & SECURITY ERRORS (P0 CRITICAL - FAIL-CLOSED)
# =============================================================================

class SecurityBreachException(MahounException):
    """
    RedLine / constitutional / governance bypass detected.
    
    MUST always map to HTTP 403 Forbidden.
    Never return 500 for known security violations.
    """
    status_code = 403
    error_code = "SECURITY_BREACH"


class LogicViolationException(MahounException):
    """
    Business logic or ontology invariants violated.
    
    MUST map to HTTP 422 Unprocessable Entity.
    Examples:
    - Invalid state transitions
    - Ontology constraint violations
    - Domain rule violations
    """
    status_code = 422
    error_code = "LOGIC_VIOLATION"


class GraphIntegrityException(MahounException):
    """
    Graph provenance / hash chain / mutation receipt violation.
    
    Examples:
    - Merkle tree mismatch
    - Missing mutation receipt
    - Provenance chain break
    """
    status_code = 422
    error_code = "GRAPH_INTEGRITY_VIOLATION"


class AuditFailureException(MahounException):
    """
    Immutable audit append failed.
    
    Must fail-closed before any mutation proceeds.
    This is an internal error (500) because audit system
    must be operational for platform integrity.
    """
    status_code = 500
    error_code = "AUDIT_FAILURE"


class GovernanceViolationException(MahounException):
    """
    Governance policy violation (from governance kernel).
    
    Links to unified governance kernel violation model.
    Use for typed governance failures.
    """
    status_code = 403
    error_code = "GOVERNANCE_VIOLATION"


class UnauthorizedMutationException(MahounException):
    """
    Attempted mutation without authorization context.
    
    Raised by GovernedNeo4jSession when write attempted
    outside authorized context.
    """
    status_code = 403
    error_code = "UNAUTHORIZED_MUTATION"


# =============================================================================
# LEDGER ERRORS
# =============================================================================

class LedgerError(MahounException):
    """Base for evidence ledger errors."""
    status_code = 500
    error_code = "LEDGER_ERROR"


class LedgerWriteError(LedgerError):
    """Failed to write to evidence ledger."""
    status_code = 500
    error_code = "LEDGER_WRITE_ERROR"


class LedgerIntegrityError(LedgerError):
    """Hash chain integrity violation detected."""
    status_code = 422
    error_code = "LEDGER_INTEGRITY_ERROR"


# =============================================================================
# KNOWLEDGE GRAPH ERRORS
# =============================================================================

class KnowledgeGraphError(MahounException):
    """Base for knowledge graph errors."""
    status_code = 500
    error_code = "KNOWLEDGE_GRAPH_ERROR"


class RuleNotFoundError(KnowledgeGraphError):
    """Requested rule not found in knowledge graph."""
    status_code = 404
    error_code = "RULE_NOT_FOUND"


class PrecedentNotFoundError(KnowledgeGraphError):
    """Requested precedent not found in knowledge graph."""
    status_code = 404
    error_code = "PRECEDENT_NOT_FOUND"


class GraphConnectionError(KnowledgeGraphError):
    """Failed to connect to graph database."""
    status_code = 503
    error_code = "GRAPH_CONNECTION_ERROR"


class GraphResolutionFailure(KnowledgeGraphError):
    """Graph retrieval required but could not produce valid result."""
    status_code = 422
    error_code = "GRAPH_RESOLUTION_FAILURE"


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================

class ConfigurationError(MahounException):
    """Base for configuration errors."""
    status_code = 500
    error_code = "CONFIGURATION_ERROR"


class MissingSecretError(ConfigurationError):
    """Required secret not set in environment."""
    status_code = 500
    error_code = "MISSING_SECRET"


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid."""
    status_code = 500
    error_code = "INVALID_CONFIG"


# =============================================================================
# LLM ROUTER ERRORS
# =============================================================================

class LLMRouterError(MahounException):
    """Base for LLM routing errors."""
    status_code = 503
    error_code = "LLM_ROUTER_ERROR"


class ModelNotFoundError(LLMRouterError):
    """Requested model not found in registry."""
    status_code = 404
    error_code = "MODEL_NOT_FOUND"


class ModelUnavailableError(LLMRouterError):
    """Model is unavailable (timeout, error, etc.)."""
    status_code = 503
    error_code = "MODEL_UNAVAILABLE"


class NoFallbackAvailableError(LLMRouterError):
    """No fallback model available after primary failure."""
    status_code = 503
    error_code = "NO_FALLBACK_AVAILABLE"


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(MahounException):
    """Base for input validation errors."""
    status_code = 400
    error_code = "VALIDATION_ERROR"


class InputTooLargeError(ValidationError):
    """Input exceeds size limit."""
    status_code = 413
    error_code = "INPUT_TOO_LARGE"


class InvalidInputTypeError(ValidationError):
    """Input has wrong type."""
    status_code = 400
    error_code = "INVALID_INPUT_TYPE"


class MissingRequiredFieldError(ValidationError):
    """Required field is missing."""
    status_code = 400
    error_code = "MISSING_REQUIRED_FIELD"


class SecurityConstraintError(ValidationError):
    """Security constraint violation (e.g., OCR confidence too low)."""
    status_code = 422
    error_code = "SECURITY_CONSTRAINT_ERROR"


# =============================================================================
# REASONING ERRORS
# =============================================================================

class ReasoningError(MahounException):
    """Base for reasoning/verdict generation errors."""
    status_code = 422
    error_code = "REASONING_ERROR"


class InsufficientEvidenceError(ReasoningError):
    """Not enough evidence to generate verdict."""
    status_code = 422
    error_code = "INSUFFICIENT_EVIDENCE"


class ContradictionError(ReasoningError):
    """Unresolvable contradiction in evidence."""
    status_code = 422
    error_code = "UNRESOLVABLE_CONTRADICTION"


class InvariantViolationError(ReasoningError):
    """Runtime invariant was violated."""
    status_code = 422
    error_code = "INVARIANT_VIOLATION"


# =============================================================================
# EXTERNAL SERVICE ERRORS
# =============================================================================

class ExternalServiceError(MahounException):
    """Base for external service communication errors."""
    status_code = 503
    error_code = "EXTERNAL_SERVICE_ERROR"


class TimeoutError(ExternalServiceError):
    """Operation timed out."""
    status_code = 504
    error_code = "TIMEOUT_ERROR"


class ConnectionError(ExternalServiceError):
    """Failed to connect to external service."""
    status_code = 503
    error_code = "CONNECTION_ERROR"


# =============================================================================
# SERIALIZATION ERRORS
# =============================================================================

class SerializationError(MahounException):
    """Error during serialization/deserialization."""
    status_code = 500
    error_code = "SERIALIZATION_ERROR"


class UnsafeSerializationError(SerializationError):
    """Attempted to use unsafe serialization format (e.g., pickle)."""
    status_code = 403
    error_code = "UNSAFE_SERIALIZATION"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def wrap_exception(
    exc: Exception,
    error_class: type[MahounException] = MahounException,
    message: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> MahounException:
    """
    Wrap a generic exception in a MahounException.
    
    Args:
        exc: Original exception
        error_class: MahounException subclass to use
        message: Optional custom message
        correlation_id: Optional correlation ID for tracing
        
    Returns:
        MahounException instance with original exception details
    """
    msg = message or str(exc)
    return error_class(
        message=msg,
        correlation_id=correlation_id,
        details={
            "original_type": type(exc).__name__,
            "original_message": str(exc)
        }
    )


# =============================================================================
# TYPE ALIASES FOR COMMON ERROR COMBINATIONS
# =============================================================================

# Governance errors that must fail-closed
GovernanceError = GovernanceViolationException

# Legacy name compatibility (will add deprecation in next phase)
BaseMahounError = MahounException
