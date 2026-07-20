"""
GOVERNANCE KERNEL (ISOLATED LAYER)
P0.4 - Zero external dependencies, import-safe in any context.

This module contains ONLY stdlib imports and provides:
- QueryType enum
- Basic query classification
- Minimal governance enforcement functions

For full governance functionality, import from:
- mahoun.core.governance.governance_context (GovernanceContext)
- mahoun.core.governance.mutation_boundary (MutationAuthorizationBoundary)
"""

from __future__ import annotations

from contextvars import ContextVar
from enum import Enum
from typing import Optional


# =============================================================================
# Query Classification
# =============================================================================

class QueryType(str, Enum):
    """Query classification types for governance enforcement."""
    READ = "READ"
    WRITE = "WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    UNKNOWN = "UNKNOWN"


# =============================================================================
# Governance Error
# =============================================================================

class GovernanceError(Exception):
    """Raised when governance policy is violated."""
    pass


# For full governance functionality, import from:
# - mahoun.core.governance.governance_context (GovernanceContext)
# - mahoun.core.governance.mutation_boundary (MutationAuthorizationBoundary)