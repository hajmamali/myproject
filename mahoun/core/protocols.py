"""
DEPRECATED FACADE - Use mahoun.core.protocols package instead
==============================================================

This file is a temporary compatibility facade. All new code should import from:
    from mahoun.core.protocols import <protocol_name>

Or more specifically:
    from mahoun.core.protocols.legacy_protocols import QueryType, ...
    from mahoun.core.protocols.ai_runtime import AIRuntimeProtocol, ...
    from mahoun.core.protocols.advanced_protocols import UncertaintyEstimate, ...

This facade will be removed in version 2.0.
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "Importing from mahoun.core.protocols.py (file) is deprecated. "
    "Use 'from mahoun.core.protocols import ...' (package) instead. "
    "This facade file will be removed in version 2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the protocols package for backward compatibility
from mahoun.core.protocols import (
    # From legacy_protocols
    QueryType,
    QueryClassificationResult,
    RoutedQueryResult,
    QueryClassifierProtocol,
    QueryRouterProtocol,
    RAGServiceProtocol,
    LLMServiceProtocol,
    ModelDriverProtocol,
    ModelOrchestratorProtocol,
    ReasoningEngineProtocol,
    DependencyContainerProtocol,
    ContradictionDetectorProtocol,
    validate_protocol_implementation,
    is_query_router,
    is_rag_service,
    is_model_driver,
    is_reasoning_engine,
    is_contradiction_detector,
    # From ai_runtime
    AIRuntimeProtocol,
    HealthStatus,
    ModelMetadata,
    # From advanced_protocols
    UncertaintyEstimate,
    UncertaintyServiceProtocol,
    is_uncertainty_service,
    OntologyValidationResult,
    OntologyGateProtocol,
    is_ontology_gate,
    GraphReasoningPath,
    UltraRAGResult,
    UltraRAGProtocol,
    is_ultra_rag,
)

__all__ = [
    "QueryType",
    "QueryClassificationResult",
    "RoutedQueryResult",
    "QueryClassifierProtocol",
    "QueryRouterProtocol",
    "RAGServiceProtocol",
    "LLMServiceProtocol",
    "ModelDriverProtocol",
    "ModelOrchestratorProtocol",
    "ReasoningEngineProtocol",
    "DependencyContainerProtocol",
    "ContradictionDetectorProtocol",
    "validate_protocol_implementation",
    "is_query_router",
    "is_rag_service",
    "is_model_driver",
    "is_reasoning_engine",
    "is_contradiction_detector",
    "AIRuntimeProtocol",
    "HealthStatus",
    "ModelMetadata",
    "UncertaintyEstimate",
    "UncertaintyServiceProtocol",
    "is_uncertainty_service",
    "OntologyValidationResult",
    "OntologyGateProtocol",
    "is_ontology_gate",
    "GraphReasoningPath",
    "UltraRAGResult",
    "UltraRAGProtocol",
    "is_ultra_rag",
]
