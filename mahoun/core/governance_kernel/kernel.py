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
# mahoun.core.governance.authorization_state (single source of truth
# per AGENTRULES.md §1 and tests/test_authorization_state_singleton.py).
from mahoun.core.governance.authorization_state import (
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
        from mahoun.core.governance.mutation_boundary import classify_cypher
        # classify_cypher returns True for mutation/forbidden, False for read-only
        if classify_cypher(query):
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
