"""
MAHOUN Core Models
==================

Backward-compatibility shim. All reasoning models have been relocated to:
mahoun/core/models/reasoning.py

This file provides transparent re-exports to maintain existing import paths.

CANONICAL LOCATION: mahoun/core/models/reasoning.py
"""

# Re-export all public symbols from canonical location
from mahoun.core.models.reasoning import *  # noqa: F401, F403

# Explicit re-exports for clarity (optional but improves IDE support)
from mahoun.core.models.reasoning import (
    # Legal Documents
    LegalDocType,
    LegalDocument,
    LegalEntity,
    # Reasoning
    ReasoningStep,
    CausalRelation,
    ReasoningResult,
    # Uncertainty
    UncertaintyEstimate,
    # Exports list
    __all__,
)

__all__ = [
    # Legal Documents
    "LegalDocType",
    "LegalDocument",
    "LegalEntity",
    # Reasoning
    "ReasoningStep",
    "CausalRelation",
    "ReasoningResult",
    # Uncertainty
    "UncertaintyEstimate",
]
