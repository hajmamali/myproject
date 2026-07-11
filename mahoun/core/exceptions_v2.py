"""
mahoun.core.exceptions_v2 — Compatibility shim
================================================

This module re-exports all exceptions from mahoun.core.exceptions (the canonical
source of truth) and adds OperationalError which was introduced in exceptions_v2
but not yet merged into exceptions.py.

Invariants:
- This module MUST NOT define a parallel exception hierarchy.
- All classes here are either re-exports or thin subclasses of MahounError.
- New exception types must be added to exceptions.py first; this file only
  provides the alias so existing importers continue to work.

Migration path:
- Callers importing from exceptions_v2 should be migrated to exceptions.py.
- This file will be removed once all imports have been redirected.
"""

# Re-export everything from the canonical module so callers get the same objects.
from mahoun.core.exceptions import (  # noqa: F401
    MahounError,
    BaseMahounError,
    SerializationError,
    UnsafeSerializationError,
    LedgerError,
    LedgerWriteError,
    LedgerIntegrityError,
    KnowledgeGraphError,
    RuleNotFoundError,
    PrecedentNotFoundError,
    GraphConnectionError,
    ConfigurationError,
    MissingSecretError,
    InvalidConfigError,
    LLMRouterError,
    ModelNotFoundError,
    ModelUnavailableError,
    NoFallbackAvailableError,
    ValidationError,
    InputTooLargeError,
    InvalidInputTypeError,
    MissingRequiredFieldError,
    SecurityConstraintError,
    ReasoningError,
    InsufficientEvidenceError,
    ContradictionError,
    InvariantViolationError,
    GovernanceError,
    ExternalServiceError,
    TimeoutError,
    ConnectionError,
    SecurityBreachException,
    LogicViolationException,
    GraphIntegrityException,
    AuditFailureException,
    wrap_exception,
)


# -------------------------------------------------------------------------
# OperationalError — not yet in exceptions.py; defined here until merged.
# -------------------------------------------------------------------------

class OperationalError(MahounError):
    """
    Runtime operational error (deployment, rollback, system operations).

    Pre-conditions:  caller has established a governance context.
    Post-conditions: always raises; never swallowed silently.
    Failure mode:    surfaces as HTTP 500 Internal Server Error.
    Security:        does not expose internal state in message.
    """

    error_code = "OPERATIONAL_ERROR"
