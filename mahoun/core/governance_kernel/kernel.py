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

# Canonical authorization state — import from single source of truth.
# This guarantees kernel._authorized_write_ctx is mutation_boundary._authorized_write_ctx.
from mahoun.core.governance.authorization_state import (
    _authorized_write_ctx,
    is_authorized as _is_authorized_state,
    set_authorized as _set_authorized_state,
    reset_authorized as _reset_authorized_state,
)

class KernelMutationBoundary:
    """Zero-dependency Cypher inspector."""

    @staticmethod
    def classify_query(query: str) -> QueryType:
        """Classify Cypher intent by delegating to the canonical boundary."""
        from mahoun.core.governance.mutation_boundary import CypherLexer
        is_mutation, violations = CypherLexer.analyze_intent(query)
        
        if violations:
            return QueryType.FORBIDDEN
        
        return QueryType.WRITE if is_mutation else QueryType.READ

    @staticmethod
    def inspect(query: str) -> None:
        """Kernel-level enforcement gate."""
        q_type = KernelMutationBoundary.classify_query(query)
        
        if q_type == QueryType.READ:
            return

        if _is_authorized_state():
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
    return _is_authorized_state()

def set_governance_authority(state: bool) -> Any:
    """Set authority state and return token for reset."""
    return _set_authorized_state(state)

def reset_governance_authority(token: Any) -> None:
    _reset_authorized_state(token)
