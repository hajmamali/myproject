"""
Core Protocol Definitions for MAHOUN Platform
==============================================

This module defines the core protocols (interfaces) that enable
dependency injection, testability, and loose coupling across the platform.

Design Principles:
- Protocol-Oriented Programming (POP)
- Liskov Substitution Principle (LSP)
- Interface Segregation Principle (ISP)
- Dependency Inversion Principle (DIP)

All protocols use runtime_checkable for isinstance() support.
"""

from typing import Protocol, runtime_checkable, Dict, Any, Optional, List, Tuple
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# Query Routing Protocols
# ============================================================================


class QueryType(str, Enum):
    """Query type enumeration for classification."""

    CONTRACT = "contract"
    DELAY_ANALYSIS = "delay_analysis"
    LEGAL_INQUIRY = "legal_inquiry"
    TECHNICAL_INQUIRY = "technical_inquiry"
    CYPHER_GENERATION = "cypher_generation"
    GENERAL = "general"


@dataclass(frozen=True)
class QueryClassificationResult:
    """
    Immutable result of query classification.

    Invariants:
    - confidence must be in [0.0, 1.0]
    - query must be non-empty
    - keywords_found must be a list (can be empty)
    """

    query: str
    query_type: QueryType
    confidence: float
    keywords_found: List[str]
    metadata: Dict[str, Any]
    required_capability: Optional[str] = None

    def __post_init__(self):
        """Validate invariants."""
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")
        if not isinstance(self.keywords_found, list):
            raise TypeError("keywords_found must be a list")


@dataclass(frozen=True)
class RoutedQueryResult:
    """
    Immutable result of query routing with RAG retrieval.

    Contains:
    - Original query and classification
    - Retrieved context from RAG
    - Model capability routing decision
    - Metadata for observability
    """

    query: str
    query_type: QueryType
    rag_result: Any  # HybridRAGResult (avoid circular import)
    classification: QueryClassificationResult
    metadata: Dict[str, Any]
    model_capability: Optional[str] = None

    def __post_init__(self):
        """Validate invariants."""
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        if not isinstance(self.classification, QueryClassificationResult):
            raise TypeError("classification must be QueryClassificationResult")


@runtime_checkable
class QueryClassifierProtocol(Protocol):
    """
    Protocol for query classification.

    Implementations must:
    - Be stateless or thread-safe
    - Return deterministic results for same input
    - Handle edge cases (empty, malformed queries)
    """

    @abstractmethod
    async def classify(self, query: str) -> QueryClassificationResult:
        """
        Classify a query into a QueryType with confidence.

        Args:
            query: User query string (non-empty)

        Returns:
            QueryClassificationResult with type and confidence

        Raises:
            ValueError: If query is empty or invalid
        """
        ...


@runtime_checkable
class QueryRouterProtocol(Protocol):
    """
    Protocol for query routing with RAG retrieval.

    Implementations must:
    - Integrate classification + RAG retrieval
    - Be async-safe
    - Handle RAG service failures gracefully
    - Provide observability metadata
    """

    @abstractmethod
    async def route(
        self, query: str, top_k: int = 10, rag_mode: Optional[str] = None
    ) -> RoutedQueryResult:
        """
        Route query to appropriate RAG service and retrieve context.

        Args:
            query: User query string
            top_k: Number of results to retrieve
            rag_mode: Optional RAG mode override

        Returns:
            RoutedQueryResult with classification and retrieved context

        Raises:
            ValueError: If query is invalid
            RuntimeError: If RAG service fails
        """
        ...

    @abstractmethod
    async def classify(self, query: str) -> QueryClassificationResult:
        """
        Classify query without RAG retrieval.

        Args:
            query: User query string

        Returns:
            QueryClassificationResult
        """
        ...

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get router statistics for observability.

        Returns:
            Dict with metrics (total_queries, type_distribution, etc.)
        """
        ...


# ============================================================================
# RAG Service Protocols
# ============================================================================


@runtime_checkable
class RAGServiceProtocol(Protocol):
    """
    Protocol for Retrieval-Augmented Generation services.

    Implementations must:
    - Support multiple retrieval modes (text, graph, hybrid)
    - Be async-safe
    - Handle missing/corrupted indices gracefully
    - Provide result quality metrics
    """

    @abstractmethod
    async def retrieve(
        self, query: str, mode: Any, top_k: int = 10
    ) -> Any:  # Returns HybridRAGResult
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            mode: RAG mode (text_only, graph_only, hybrid, etc.)
            top_k: Number of results

        Returns:
            RAGResult with retrieved documents and metadata

        Raises:
            ValueError: If query is invalid
            RuntimeError: If retrieval fails
        """
        ...


# ============================================================================
# Model Orchestration Protocols
# ============================================================================

@runtime_checkable
class LLMServiceProtocol(Protocol):
    """
    Protocol for basic LLM generation service.
    """
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        ...


@runtime_checkable
class ModelDriverProtocol(Protocol):
    """
    Protocol for LLM model drivers.

    Implementations must:
    - Support synchronous generation
    - Handle model loading/unloading
    - Provide model metadata (name, capabilities)
    - Be thread-safe for concurrent requests
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name/identifier."""
        ...

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            **kwargs: Model-specific parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If generation fails
        """
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded in memory."""
        ...


@runtime_checkable
class ModelOrchestratorProtocol(Protocol):
    """
    Protocol for model orchestration and lifecycle management.

    Implementations must:
    - Support capability-based model selection
    - Handle model warm/cold swapping
    - Manage memory efficiently
    - Provide model availability status
    """

    @abstractmethod
    async def get_driver(self, capability: Any) -> ModelDriverProtocol:
        """
        Get a model driver for the specified capability.

        Args:
            capability: ModelCapability enum value

        Returns:
            ModelDriverProtocol instance

        Raises:
            ValueError: If capability is invalid
            RuntimeError: If model loading fails
        """
        ...


# ============================================================================
# Reasoning Engine Protocols
# ============================================================================


@runtime_checkable
class ReasoningEngineProtocol(Protocol):
    """
    Protocol for reasoning engines.

    Implementations must:
    - Process queries end-to-end
    - Integrate routing + retrieval + inference
    - Provide full observability metadata
    - Handle failures gracefully with fallbacks
    """

    @abstractmethod
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a query end-to-end.

        Args:
            query: User query string

        Returns:
            Dict with:
            - response: Generated answer
            - query_type: Classified query type
            - model_used: Model identifier
            - capability: Model capability used
            - confidence: Classification confidence
            - context_sources: Number of retrieved documents
            - metadata: Additional observability data

        Raises:
            ValueError: If query is invalid
            RuntimeError: If processing fails
        """
        ...


# ============================================================================
# Dependency Container Protocol
# ============================================================================


@runtime_checkable
class DependencyContainerProtocol(Protocol):
    """
    Protocol for dependency injection containers.

    Implementations must:
    - Support lazy initialization
    - Handle circular dependencies
    - Provide singleton and transient scopes
    - Be thread-safe
    """

    @abstractmethod
    def get_query_router(self) -> QueryRouterProtocol:
        """Get QueryRouter instance (singleton)."""
        ...

    @abstractmethod
    def get_rag_service(self) -> RAGServiceProtocol:
        """Get RAG service instance (singleton)."""
        ...

    @abstractmethod
    def get_model_orchestrator(self) -> ModelOrchestratorProtocol:
        """Get model orchestrator instance (singleton)."""
        ...

    @abstractmethod
    def get_reasoning_engine(self) -> ReasoningEngineProtocol:
        """Get reasoning engine instance (singleton)."""
        ...

    @abstractmethod
    def get_contradiction_detector(self) -> Optional["ContradictionDetectorProtocol"]:
        """Get contradiction detector instance (optional)."""
        ...


# ============================================================================
# Type Guards and Validators
# ============================================================================


def validate_protocol_implementation(instance: Any, protocol: type) -> None:
    """
    Validate that an instance implements a protocol.

    Args:
        instance: Object to validate
        protocol: Protocol class to check against

    Raises:
        TypeError: If instance doesn't implement protocol
    """
    if not isinstance(instance, protocol):
        raise TypeError(
            f"Instance {type(instance).__name__} does not implement "
            f"protocol {protocol.__name__}"
        )


def is_query_router(obj: Any) -> bool:
    """Type guard for QueryRouterProtocol."""
    return isinstance(obj, QueryRouterProtocol)


def is_rag_service(obj: Any) -> bool:
    """Type guard for RAGServiceProtocol."""
    return isinstance(obj, RAGServiceProtocol)


def is_model_driver(obj: Any) -> bool:
    """Type guard for ModelDriverProtocol."""
    return isinstance(obj, ModelDriverProtocol)


def is_reasoning_engine(obj: Any) -> bool:
    """Type guard for ReasoningEngineProtocol."""
    return isinstance(obj, ReasoningEngineProtocol)


def is_contradiction_detector(obj: Any) -> bool:
    """Type guard for ContradictionDetectorProtocol."""
    return (
        hasattr(obj, "detect_contradiction")
        and callable(obj.detect_contradiction)
        and hasattr(obj, "batch_detect")
        and callable(obj.batch_detect)
    )


@runtime_checkable
class ContradictionDetectorProtocol(Protocol):
    """
    Protocol for contradiction detection in reasoning chains.

    Implementations must:
    - Detect logical contradictions between statements
    - Provide confidence scores
    - Be thread-safe
    - Handle edge cases gracefully
    """

    @abstractmethod
    def detect_contradiction(
        self, statement1: str, statement2: str
    ) -> Tuple[bool, float]:
        """
        Detect contradiction between two statements.

        Args:
            statement1: First statement
            statement2: Second statement

        Returns:
            Tuple of (is_contradiction, confidence_score)

        Raises:
            ValueError: If statements are invalid
        """
        ...

    @abstractmethod
    def batch_detect(
        self, statements: List[Tuple[str, str]]
    ) -> List[Tuple[bool, float]]:
        """
        Batch contradiction detection for efficiency.

        Args:
            statements: List of statement pairs

        Returns:
            List of (is_contradiction, confidence_score) tuples
        """
        ...
