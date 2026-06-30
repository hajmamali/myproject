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
]