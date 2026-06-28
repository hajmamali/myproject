"""
Guardrails Exception Classes
============================

Exception classes for governance and guardrail violations.
These are raised when governance invariants are violated.

DESIGN PHILOSOPHY:
- Keep exceptions lightweight (performance-critical path)
- Use tuple-based args for compatibility with Python exception pattern
- Rich context comes from args tuple, not complex __init__
- Simple marker classes enable fast isinstance() checks
"""

class InvariantViolation(Exception):
    """
    Raised when a governance invariant is violated.
    
    This indicates a critical violation of system guarantees
    that must be addressed immediately.
    
    Usage:
        raise InvariantViolation(invariant_name, details_dict)
    
    Access:
        exc.args[0]  # invariant name (str)
        exc.args[1]  # details (dict)
    
    Example:
        try:
            raise InvariantViolation("G2_Evidence", {"node_id": "n123"})
        except InvariantViolation as e:
            name = e.args[0]  # "G2_Evidence"
            details = e.args[1]  # {"node_id": "n123"}
    """
    
    @property
    def invariant_name(self) -> str:
        """Get invariant name from args (convenience property)"""
        return self.args[0] if self.args else "UNKNOWN"
    
    @property
    def details(self) -> dict:
        """Get details dict from args (convenience property)"""
        return self.args[1] if len(self.args) > 1 else {}


class GuardrailViolation(Exception):
    """
    Raised when a guardrail check fails.
    
    This indicates potential security or integrity issues.
    
    Usage:
        raise GuardrailViolation(check_name, context)
    """
    
    @property
    def check_name(self) -> str:
        """Get check name from args"""
        return self.args[0] if self.args else "UNKNOWN"
    
    @property
    def context(self) -> dict:
        """Get context dict from args"""
        return self.args[1] if len(self.args) > 1 else {}


class GovernanceBypassAttempt(Exception):
    """
    Raised when an attempt to bypass governance is detected.
    
    This is a security-critical violation.
    """
    pass