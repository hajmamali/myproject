"""
MAHOUN Governance Kernel
========================

Lightweight governance components that can be imported without heavy dependencies.
Provides unified interface for both simple and advanced governance operations.
"""

# Import kernel components
from .kernel import (
    QueryType,
    GovernanceViolation,
    GovernanceViolationError,
    KernelMutationBoundary,
    is_governance_authorized,
    set_governance_authority,
    reset_governance_authority,
    ViolationCategory,
    ViolationSeverity,
)

# Legacy simple interface components
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

# =============================================================================
# Legacy Simple Interface (for backward compatibility)
# =============================================================================

class GovernanceError(Exception):
    """Raised when governance policy is violated."""
    pass

@dataclass
class GovernanceContext:
    """Governance context for audit trail."""
    correlation_id: str
    actor_id: str
    scope_id: Optional[str] = None
    query_type: Optional[QueryType] = None  # Optional for backward compatibility
    origin: Optional[str] = None  # Optional tracking field

_governance_context: ContextVar[Optional[GovernanceContext]] = ContextVar(
    "mahoun_governance_context", default=None
)

def get_current_context() -> Optional[GovernanceContext]:
    """Get the current governance context."""
    return _governance_context.get()

def set_governance_context(ctx: GovernanceContext) -> None:
    """Set the governance context."""
    _governance_context.set(ctx)

def clear_governance_context() -> None:
    """Clear the governance context."""
    _governance_context.set(None)

class MutationAuthorizationBoundary:
    """
    Authorization boundary for graph mutations.
    Enforces governance policies before any mutation.
    """
    
    @staticmethod
    def validate(
        query_type: QueryType,
        correlation_id: Optional[str],
        actor_id: Optional[str],
        allow_destructive: bool = False,
    ) -> None:
        """
        Validate mutation against governance policies.
        
        Raises GovernanceError if validation fails.
        """
        if query_type == QueryType.READ:
            return
        
        if query_type == QueryType.WRITE:
            if not correlation_id or not actor_id:
                raise GovernanceError(
                    "WRITE queries require correlation_id and actor_id"
                )
            return
        
        # Handle DDL as WRITE for compatibility
        if query_type.value == "DDL":
            if not correlation_id or not actor_id:
                raise GovernanceError(
                    "DDL queries require correlation_id and actor_id"
                )
            return
        
        if query_type.value == "FORBIDDEN":
            raise GovernanceError(
                "FORBIDDEN query type - cannot execute"
            )

def enforce_governance(
    query_type: QueryType,
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    allow_destructive: bool = False,
) -> None:
    """
    Enforce governance policy based on query type.
    
    Raises GovernanceError if policy violated.
    """
    MutationAuthorizationBoundary.validate(
        query_type, correlation_id, actor_id, allow_destructive
    )

# Compatibility function for classify_query
def classify_query(query: str) -> QueryType:
    """
    Classify query type for governance enforcement.
    Maps to KernelMutationBoundary.classify_query
    """
    return KernelMutationBoundary.classify_query(query)

__all__ = [
    # Kernel interface
    "QueryType",
    "GovernanceViolation", 
    "GovernanceViolationError",
    "KernelMutationBoundary",
    "is_governance_authorized",
    "set_governance_authority", 
    "reset_governance_authority",
    "ViolationCategory",
    "ViolationSeverity",
    # Simple interface
    "GovernanceError",
    "GovernanceContext",
    "MutationAuthorizationBoundary",
    "enforce_governance",
    "get_current_context",
    "set_governance_context",
    "clear_governance_context",
    "classify_query",
]