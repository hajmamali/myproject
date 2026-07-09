"""
🚀 MAHOUN Core Module - Developer Shortcuts
===========================================

Core infrastructure components for MAHOUN platform.

Quick Imports (most common):
    from mahoun.core import ReasoningResult, SecurityBreachException
    from mahoun.core import Entity, FortressValidator

Advanced Imports:
    from mahoun.core.models import ReasoningStep, Entity  
    from mahoun.core.protocols import QueryRouterProtocol

DUPLICATE CLASS GUIDE:
- ReasoningResult → USE THIS (canonical in .models)  
- Entity → USE THIS (canonical in .models)
- SecurityBreachException → USE THIS (canonical in .exceptions)

Components:
- FortressValidator: Governance enforcement layer
- PolicyResolver: Centralized execution policy engine  
- Models: Core business objects (ReasoningResult, Entity, etc.)
- Exceptions: Structured error types
- Protocols: Interface definitions for DI

NOTE: Fortress validator imports are lazy-loaded to avoid torch import chain.
Use `from mahoun.core.fortress_validator import FortressValidator` directly
when needed, or access via lazy imports at runtime.
"""

# 🎯 Most Used Classes (Daily Imports) - Developer Shortcuts
from .models import ReasoningResult, ReasoningStep, Entity
from .exceptions import SecurityBreachException, LogicViolationException

# 🔧 Protocol Interfaces (Architecture) 
from .protocols import QueryRouterProtocol, ModelDriverProtocol

# Policy resolver exports (direct imports - no heavy dependencies)
from mahoun.core.policy_resolver import (
    PolicyResolver,
    ExecutionPolicy,
    ViewMode,
    EmbeddingMode,
    ReasoningBudget,
    create_default_policy_resolver,
)

# Unified governance controller (direct imports - coordinates Kernel + Policy)
from mahoun.core.unified_governance import (
    UnifiedGovernanceController,
    UnifiedGovernanceDecision,
    create_default_unified_controller,
    validate_query_with_unified_governance,
)

# Lazy imports for fortress_validator to avoid torch import chain
# Do NOT import fortress_validator at module level - it pulls reasoning → torch
# Users should import directly: from mahoun.core.fortress_validator import ...

__all__ = [
    # 🎯 Core business objects (Developer Daily Use)
    "ReasoningResult", "ReasoningStep", "Entity",
    # 🚨 Exceptions & validation  
    "SecurityBreachException", "LogicViolationException", "FortressValidator",
    # 🔧 Protocols (Architecture)
    "QueryRouterProtocol", "ModelDriverProtocol",
    # Fortress Validator (lazy)
    "ExecutionMode",
    "ReasoningResponse",
    "ValidationResult",
    "ViolationSeverity",
    "ViolationType",
    "validate_reasoning_response",
    # Policy Resolver (direct)
    "PolicyResolver",
    "ExecutionPolicy",
    "ViewMode",
    "EmbeddingMode",
    "ReasoningBudget",
    "create_default_policy_resolver",
    # Unified Governance Controller (direct)
    "UnifiedGovernanceController",
    "UnifiedGovernanceDecision",
    "create_default_unified_controller",
    "validate_query_with_unified_governance",
]

def __getattr__(name: str):
    """Lazy import fortress_validator components to avoid eager torch loading"""
    if name in ["ExecutionMode", "FortressValidator", "ReasoningResponse", 
                "SecurityBreachException", "ValidationResult", "ViolationSeverity",
                "ViolationType", "validate_reasoning_response"]:
        from mahoun.core.fortress_validator import (
            ExecutionMode,
            FortressValidator,
            ReasoningResponse,
            SecurityBreachException,
            ValidationResult,
            ViolationSeverity,
            ViolationType,
            validate_reasoning_response,
        )
        globals().update({
            "ExecutionMode": ExecutionMode,
            "FortressValidator": FortressValidator,
            "ReasoningResponse": ReasoningResponse,
            "SecurityBreachException": SecurityBreachException,
            "ValidationResult": ValidationResult,
            "ViolationSeverity": ViolationSeverity,
            "ViolationType": ViolationType,
            "validate_reasoning_response": validate_reasoning_response,
        })
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
