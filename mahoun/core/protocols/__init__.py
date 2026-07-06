"""
Core Protocol Definitions for MAHOUN

This module contains the fundamental protocol definitions that form
the contract boundaries for MAHOUN's architecture.

G-0 FREEZE STATUS: These protocols are candidates for G-0 freeze
and should not be modified without architecture review.
"""

from .ai_runtime import AIRuntimeProtocol, HealthStatus, ModelMetadata
from .legacy_protocols import (
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
    validate_protocol_implementation,
    is_query_router,
    is_rag_service,
    is_model_driver,
    is_reasoning_engine,
    is_contradiction_detector,
    ContradictionDetectorProtocol
)
from .advanced_protocols import (
    # Uncertainty
    UncertaintyEstimate,
    UncertaintyServiceProtocol,
    is_uncertainty_service,
    # Ontology
    OntologyValidationResult,
    OntologyGateProtocol,
    is_ontology_gate,
    # Ultra RAG
    GraphReasoningPath,
    UltraRAGResult,
    UltraRAGProtocol,
    is_ultra_rag,
)

__all__ = [
    "AIRuntimeProtocol", 
    "HealthStatus", 
    "ModelMetadata",
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
    "validate_protocol_implementation",
    "is_query_router",
    "is_rag_service",
    "is_model_driver",
    "is_reasoning_engine",
    "is_contradiction_detector",
    "ContradictionDetectorProtocol",
    # Advanced protocols
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