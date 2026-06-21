"""
Guardrails Exception Classes
============================

Exception classes for governance and guardrail violations.
These are raised when governance invariants are violated.
"""

class InvariantViolation(Exception):
    """
    Raised when a governance invariant is violated.
    
    This indicates a critical violation of system guarantees
    that must be addressed immediately.
    """
    pass

class GuardrailViolation(Exception):
    """
    Raised when a guardrail check fails.
    
    This indicates potential security or integrity issues.
    """
    pass

class GovernanceBypassAttempt(Exception):
    """
    Raised when an attempt to bypass governance is detected.
    
    This is a security-critical violation.
    """
    pass