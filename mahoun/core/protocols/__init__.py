"""
Core Protocol Definitions for MAHOUN

This module contains the fundamental protocol definitions that form
the contract boundaries for MAHOUN's architecture.

G-0 FREEZE STATUS: These protocols are candidates for G-0 freeze
and should not be modified without architecture review.
"""

from .ai_runtime import AIRuntimeProtocol, HealthStatus, ModelMetadata

# Load legacy protocols module directly to avoid circular import with package
import importlib.util
import sys
from pathlib import Path

_legacy_path = Path(__file__).parent.parent / "protocols.py"
_spec = importlib.util.spec_from_file_location("mahoun_core_protocols_legacy", _legacy_path)
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
sys.modules["mahoun_core_protocols_legacy"] = _legacy

# Re-export all legacy protocols
from mahoun_core_protocols_legacy import (
    QueryType,
    QueryClassificationResult,
    RoutedQueryResult,
    QueryRouterProtocol,
    RAGServiceProtocol,
    ModelDriverProtocol,
    ModelOrchestratorProtocol,
    ReasoningEngineProtocol,
    ContradictionDetectorProtocol,
    QueryClassifierProtocol,
    LLMServiceProtocol,
    DependencyContainerProtocol,
    validate_protocol_implementation,
    is_query_router,
    is_rag_service,
    is_model_driver,
    is_reasoning_engine,
    is_contradiction_detector,
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
    "ContradictionDetectorProtocol",
    "validate_protocol_implementation",
    "is_query_router",
    "is_rag_service",
    "is_model_driver",
    "is_reasoning_engine",
    "is_contradiction_detector",
]
