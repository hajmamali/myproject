"""
MAHOUN Governance Kernel - Tier 0
=================================

Classification: KERNEL / ZERO-DEPENDENCY / NON-BYPASSABLE
Purpose: Core governance state and boundary enforcement.

TIER 0 RULES:
- MUST use ONLY stdlib imports.
- FORBIDDEN: any external library (torch, neo4j, etc.).
- Purpose: Ensure governance remains functional even if high-level dependencies fail.
"""

import contextvars
import enum
import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Generator

# ============================================================================
# KERNEL ENUMS
# ============================================================================

class QueryType(str, enum.Enum):
    READ = "READ"
    WRITE = "WRITE"
    DDL = "DDL"  # Schema/Index/Constraint operations
    FORBIDDEN = "FORBIDDEN"

class ViolationCategory(str, enum.Enum):
    ARCHITECTURE_BOUNDARY = "ARCHITECTURE_BOUNDARY"
    MISSING_PROVENANCE = "MISSING_PROVENANCE"
    ONTOLOGY_VIOLATION = "ONTOLOGY_VIOLATION"
    AUDIT_FAILURE = "AUDIT_FAILURE"
    GOVERNANCE_BYPASS = "GOVERNANCE_BYPASS"

class ViolationSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"

# ============================================================================
# KERNEL EXCEPTIONS
# ============================================================================

@dataclass(frozen=True)
class GovernanceViolation:
    category: ViolationCategory
    severity: ViolationSeverity
    message: str
    details: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""
    correlation_id: Optional[str] = None

class GovernanceViolationError(Exception):
    def __init__(self, violation: GovernanceViolation) -> None:
        self.violation = violation
        super().__init__(f"[GOVERNANCE KERNEL VIOLATION] {violation.message}")

# ============================================================================
# MUTATION AUTHORIZATION BOUNDARY
# ============================================================================
# The ContextVar is owned canonically by
# mahoun.core.governance_kernel.authorization_state (Tier-0, single source
# of truth per kernel.manifest.yaml §tier_0 and glmreport.md Section F).
# Importing from the same Tier-0 package is an intra-kernel import — allowed.
from mahoun.core.governance_kernel.authorization_state import (
    _authorized_write_ctx,
    is_authorized as _is_authorized,
    set_authorized as _set_authorized,
    reset_authorized as _reset_authorized,
)

class KernelMutationBoundary:
    """Zero-dependency Cypher inspector."""

    @staticmethod
    def classify_query(query: str) -> QueryType:
        """Classify Cypher intent by delegating to the canonical classifier lazily."""
        # Lazy import to preserve Tier 0 zero-dependency at module load time
        from mahoun.core.governance.mutation_boundary import CypherLexer
        # Use CypherLexer.analyze_intent to distinguish between WRITE and FORBIDDEN
        is_mutation, violations = CypherLexer.analyze_intent(query)
        
        if violations:
            # Forbidden procedures (apoc, dbms, etc.) take precedence
            return QueryType.FORBIDDEN
        
        if is_mutation:
            return QueryType.WRITE
        
        return QueryType.READ

    @staticmethod
    def inspect(query: str) -> None:
        """Kernel-level enforcement gate."""
        q_type = KernelMutationBoundary.classify_query(query)
        
        if q_type == QueryType.READ:
            return

        if _is_authorized():
            return

        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ARCHITECTURE_BOUNDARY,
                severity=ViolationSeverity.CRITICAL,
                message="Mutation Cypher detected outside authorized governed context.",
                details={"query_preview": query[:100], "type": q_type.value},
                source="KernelMutationBoundary"
            )
        )

# ============================================================================
# KERNEL CONTEXT MANAGEMENT
# ============================================================================

def is_governance_authorized() -> bool:
    return _is_authorized()

def set_governance_authority(state: bool) -> Any:
    """Set authority state and return token for reset."""
    return _set_authorized(state)

def reset_governance_authority(token: Any) -> None:
    _reset_authorized(token)


# ============================================================================
# GOVERNANCE KERNEL SERVICE CLASS
# ============================================================================
# Used by governance_kernel_main.py (containerized HTTP service)

class GovernanceKernel:
    """
    Top-level governance kernel service for the containerized runtime.

    Provides HTTP-facing governance validation via:
    - validate_request(): Enforce governance rules on incoming requests
    - get_uptime(): Report service uptime
    - get_stats(): Report validation statistics
    """

    def __init__(self) -> None:
        self._start_time = datetime.now(timezone.utc)
        self._stats: Dict[str, int] = {
            "total_requests": 0,
            "allowed": 0,
            "denied": 0,
            "errors": 0,
        }

    async def validate_request(
        self,
        query_type: str,
        correlation_id: str,
        actor_id: str,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "GovernanceResponse":
        """Validate a governance request and return a structured response."""
        import uuid

        self._stats["total_requests"] += 1

        # Map string query_type to our enum
        try:
            q_type = QueryType(query_type.upper())
        except ValueError:
            q_type = QueryType.READ  # Default to read for unknown types

        # READ queries are always allowed
        if q_type == QueryType.READ:
            self._stats["allowed"] += 1
            return _GovernanceResponse(
                allowed=True,
                reason="Read query permitted",
                correlation_id=correlation_id,
                validation_id=str(uuid.uuid4()),
                metadata={"query_type": q_type.value, "actor_id": actor_id},
            )

        # WRITE/DDL/FORBIDDEN queries require authorization
        if _is_authorized():
            self._stats["allowed"] += 1
            return _GovernanceResponse(
                allowed=True,
                reason="Write authorized via governance context",
                correlation_id=correlation_id,
                validation_id=str(uuid.uuid4()),
                metadata={"query_type": q_type.value, "actor_id": actor_id},
            )

        # Deny unauthorized mutations
        self._stats["denied"] += 1
        return _GovernanceResponse(
            allowed=False,
            reason="Mutation denied: no active governance authorization",
            correlation_id=correlation_id,
            validation_id=str(uuid.uuid4()),
            metadata={"query_type": q_type.value, "actor_id": actor_id},
        )

    def get_uptime(self) -> float:
        """Return uptime in seconds."""
        delta = datetime.now(timezone.utc) - self._start_time
        return delta.total_seconds()

    def get_stats(self) -> Dict[str, int]:
        """Return validation statistics."""
        return dict(self._stats)


@dataclass
class _GovernanceResponse:
    """Internal response structure matching the Pydantic model in main.py."""
    allowed: bool
    reason: str
    correlation_id: str
    validation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

