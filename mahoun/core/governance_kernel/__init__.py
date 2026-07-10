"""
GOVERNANCE KERNEL (ISOLATED LAYER)
P0.4 - Zero external dependencies, import-safe in any context.

This module contains ONLY stdlib imports and provides:
- MutationAuthorizationBoundary
- QueryType enum
- enforce_governance()
- Context management for governance state
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any


# =============================================================================
# Query Classification
# =============================================================================

class QueryType(str, Enum):
    """Query classification types for governance enforcement."""
    READ = "READ"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    UNKNOWN = "UNKNOWN"


def classify_query(query: str) -> QueryType:
    """
    Classify query type for governance enforcement.
    
    READ: MATCH, RETURN, OPTIONAL MATCH
    WRITE: CREATE, MERGE, SET, REMOVE
    DESTRUCTIVE: DELETE, DETACH DELETE, DROP, REMOVE without WHERE
    UNKNOWN: anything ambiguous → treated as WRITE (fail-safe)
    """
    if not query or not query.strip():
        return QueryType.UNKNOWN
    
    query_upper = query.upper()
    
    if any(kw in query_upper for kw in ["MATCH", "RETURN", "OPTIONAL MATCH"]):
        if not any(kw in query_upper for kw in ["CREATE", "MERGE", "SET", "DELETE", "DETACH"]):
            return QueryType.READ
    
    if any(kw in query_upper for kw in ["DETACH DELETE", "DELETE ALL", "DROP"]):
        return QueryType.DESTRUCTIVE
    
    if "DELETE" in query_upper:
        if "WHERE" not in query_upper:
            return QueryType.DESTRUCTIVE
        return QueryType.WRITE
    
    if any(kw in query_upper for kw in ["CREATE", "MERGE"]):
        return QueryType.WRITE
    
    if "SET" in query_upper or "REMOVE" in query_upper:
        return QueryType.WRITE
    
    return QueryType.UNKNOWN


# =============================================================================
# Governance Error
# =============================================================================

class GovernanceError(Exception):
    """Raised when governance policy is violated."""
    pass


# =============================================================================
# Governance Context
# =============================================================================

@dataclass
class GovernanceContext:
    """Governance context for audit trail."""
    correlation_id: str
    actor_id: str
    scope_id: Optional[str] = None


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


# =============================================================================
# Mutation Authorization Boundary
# =============================================================================

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
        
        if query_type == QueryType.DESTRUCTIVE:
            if not correlation_id or not actor_id:
                raise GovernanceError(
                    "DESTRUCTIVE queries require correlation_id and actor_id"
                )
            if not allow_destructive:
                raise GovernanceError(
                    "DESTRUCTIVE queries require allow_destructive=True"
                )
            return
        
        if query_type == QueryType.UNKNOWN:
            raise GovernanceError(
                "UNKNOWN query type - cannot execute. Treat as WRITE by default."
            )


# =============================================================================
# Main Enforcement Function
# =============================================================================

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