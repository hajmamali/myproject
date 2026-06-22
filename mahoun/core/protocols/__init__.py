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
    "ContradictionDetectorProtocol"
]