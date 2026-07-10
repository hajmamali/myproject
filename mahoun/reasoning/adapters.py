"""
Dependency Injection Adapters for Reasoning Layer
==================================================

This module provides a sophisticated dependency injection container
for the reasoning layer, enabling:

- Lazy initialization of expensive resources
- Singleton lifecycle management
- Thread-safe access
- Testability through protocol-based interfaces
- Graceful degradation on missing dependencies

Design Patterns:
- Dependency Injection Container
- Lazy Initialization
- Singleton Pattern (thread-safe)
- Factory Pattern
- Adapter Pattern

Architecture:
- All dependencies are accessed through protocols
- Concrete implementations are hidden behind adapters
- Container manages lifecycle and initialization order
- Supports both production and test configurations
"""

import logging
import threading
from functools import lru_cache
from typing import Optional

from mahoun.core.protocols import (
    ContradictionDetectorProtocol,
    ModelOrchestratorProtocol,
    QueryRouterProtocol,
    RAGServiceProtocol,
    ReasoningEngineProtocol,
    validate_protocol_implementation,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Dependency Container Implementation
# ============================================================================


class ReasoningDependencyContainer:
    """
    Thread-safe dependency injection container for reasoning layer.

    Features:
    - Lazy initialization (resources created on first access)
    - Singleton lifecycle (one instance per dependency)
    - Thread-safe (uses locks for initialization)
    - Protocol validation (ensures implementations match contracts)
    - Graceful fallbacks (handles missing optional dependencies)

    Usage:
        container = ReasoningDependencyContainer()
        router = container.query_router
        engine = container.reasoning_engine
    """

    def __init__(self):
        """Initialize container with empty state."""
        self._query_router: QueryRouterProtocol | None = None
        self._rag_service: RAGServiceProtocol | None = None
        self._model_orchestrator: ModelOrchestratorProtocol | None = None
        self._reasoning_engine: ReasoningEngineProtocol | None = None
        self._contradiction_detector: ContradictionDetectorProtocol | None = None

        # Thread locks for safe lazy initialization
        self._router_lock = threading.Lock()
        self._rag_lock = threading.Lock()
        self._orchestrator_lock = threading.Lock()
        self._engine_lock = threading.Lock()
        self._detector_lock = threading.Lock()

        # Initialization flags for observability
        self._initialized: dict[str, bool] = {
            "query_router": False,
            "rag_service": False,
            "model_orchestrator": False,
            "reasoning_engine": False,
            "contradiction_detector": False,
        }

        logger.info("ReasoningDependencyContainer initialized")

    @property
    def query_router(self) -> QueryRouterProtocol:
        """
        Get QueryRouter instance (lazy singleton).

        Returns:
            QueryRouterProtocol implementation

        Raises:
            RuntimeError: If initialization fails
        """
        if self._query_router is None:
            with self._router_lock:
                # Double-checked locking pattern
                if self._query_router is None:
                    logger.info("Initializing QueryRouter (lazy)")
                    self._query_router = self._create_query_router()
                    validate_protocol_implementation(self._query_router, QueryRouterProtocol)
                    self._initialized["query_router"] = True
                    logger.info("QueryRouter initialized successfully")

        return self._query_router

    @property
    def rag_service(self) -> RAGServiceProtocol:
        """
        Get RAG service instance (lazy singleton).

        Returns:
            RAGServiceProtocol implementation

        Raises:
            RuntimeError: If initialization fails
        """
        if self._rag_service is None:
            with self._rag_lock:
                if self._rag_service is None:
                    logger.info("Initializing RAG service (lazy)")
                    self._rag_service = self._create_rag_service()
                    validate_protocol_implementation(self._rag_service, RAGServiceProtocol)
                    self._initialized["rag_service"] = True
                    logger.info("RAG service initialized successfully")

        return self._rag_service

    @property
    def model_orchestrator(self) -> ModelOrchestratorProtocol:
        """
        Get model orchestrator instance (lazy singleton).

        Returns:
            ModelOrchestratorProtocol implementation

        Raises:
            RuntimeError: If initialization fails
        """
        if self._model_orchestrator is None:
            with self._orchestrator_lock:
                if self._model_orchestrator is None:
                    logger.info("Initializing ModelOrchestrator (lazy)")
                    self._model_orchestrator = self._create_model_orchestrator()
                    validate_protocol_implementation(self._model_orchestrator, ModelOrchestratorProtocol)
                    self._initialized["model_orchestrator"] = True
                    logger.info("ModelOrchestrator initialized successfully")

        return self._model_orchestrator

    @property
    def reasoning_engine(self) -> ReasoningEngineProtocol:
        """
        Get reasoning engine instance (lazy singleton).

        Returns:
            ReasoningEngineProtocol implementation

        Raises:
            RuntimeError: If initialization fails
        """
        if self._reasoning_engine is None:
            with self._engine_lock:
                if self._reasoning_engine is None:
                    logger.info("Initializing ReasoningEngine (lazy)")
                    self._reasoning_engine = self._create_reasoning_engine()
                    validate_protocol_implementation(self._reasoning_engine, ReasoningEngineProtocol)
                    self._initialized["reasoning_engine"] = True
                    logger.info("ReasoningEngine initialized successfully")

        return self._reasoning_engine

    @property
    def contradiction_detector(self) -> Optional["ContradictionDetectorProtocol"]:
        """
        Get contradiction detector instance (lazy singleton, optional).

        Returns:
            ContradictionDetectorProtocol implementation or None if not available
        """
        if self._contradiction_detector is None:
            with self._detector_lock:
                if self._contradiction_detector is None:
                    logger.info("Attempting to initialize ContradictionDetector (lazy)")
                    try:
                        self._contradiction_detector = self._create_contradiction_detector()
                        if self._contradiction_detector is not None:
                            from mahoun.core.protocols import ContradictionDetectorProtocol

                            validate_protocol_implementation(
                                self._contradiction_detector, ContradictionDetectorProtocol
                            )
                            self._initialized["contradiction_detector"] = True
                            logger.info("ContradictionDetector initialized successfully")
                        else:
                            logger.info("ContradictionDetector not available (optional)")
                    except Exception as e:
                        logger.warning(f"ContradictionDetector initialization failed: {e}")
                        self._contradiction_detector = None

        return self._contradiction_detector

    # ========================================================================
    # Factory Methods (Override in tests for mocking)
    # ========================================================================

    def _create_query_router(self) -> QueryRouterProtocol:
        """
        Factory method for QueryRouter.

        Override this in tests to inject mocks.

        Note:
            Uses rag_adapter to avoid direct import from RAG module.
            This maintains architectural boundary between core and non-core.
        """
        from mahoun.reasoning.rag_adapter import create_query_router

        router = create_query_router(rag_service=None)
        if router is None:
            raise RuntimeError("QueryRouter not available. Ensure mahoun.rag module is installed and configured.")
        return router

    def _create_rag_service(self) -> RAGServiceProtocol:
        """
        Factory method for RAG service.

        Override this in tests to inject mocks.

        Note:
            Uses rag_adapter to avoid direct import from RAG module.
            This maintains architectural boundary between core and non-core.
        """
        from mahoun.reasoning.rag_adapter import create_rag_service

        service = create_rag_service()
        if service is None:
            raise RuntimeError("HybridRAGService not available. Ensure mahoun.rag.hybrid_rag_service is installed.")
        return service

    def _create_model_orchestrator(self) -> ModelOrchestratorProtocol:
        """
        Factory method for ModelOrchestrator.

        Override this in tests to inject mocks.
        """
        import importlib

        orchestrator_mod = importlib.import_module("mahoun.llm.orchestrator")
        get_orchestrator = orchestrator_mod.get_orchestrator

        return get_orchestrator()

    def _create_reasoning_engine(self) -> ReasoningEngineProtocol:
        """
        Factory method for ReasoningEngine.

        Override this in tests to inject mocks.

        Note:
            This creates a circular dependency (engine depends on container).
            We break it by passing the router explicitly.
            Uses rag_adapter to maintain architectural boundaries.
        """
        from mahoun.reasoning.rag_adapter import create_unified_reasoning_engine

        engine = create_unified_reasoning_engine(router=self.query_router)
        if engine is None:
            raise RuntimeError(
                "UnifiedReasoningEngine not available. Ensure mahoun.reasoning.unified_engine is installed."
            )
        return engine

    def _create_contradiction_detector(self) -> Optional["ContradictionDetectorProtocol"]:
        """
        Factory method for ContradictionDetector (optional).

        Returns None if not available (graceful degradation).

        Note:
            Uses guardrails_adapter to avoid direct import from guardrails.
            This maintains architectural boundary between core and non-core.
        """
        from mahoun.reasoning.guardrails_adapter import create_contradiction_detector

        return create_contradiction_detector()

    # ========================================================================
    # Observability and Management
    # ========================================================================

    def get_initialization_status(self) -> dict[str, bool]:
        """
        Get initialization status of all dependencies.

        Returns:
            Dict mapping dependency name to initialization status
        """
        return self._initialized.copy()

    def is_fully_initialized(self) -> bool:
        """Check if all dependencies are initialized."""
        return all(self._initialized.values())

    def reset(self) -> None:
        """
        Reset container (for testing only).

        WARNING: This will destroy all singletons.
        Only use in test teardown.
        """
        logger.warning("Resetting ReasoningDependencyContainer (test mode)")

        with self._router_lock, self._rag_lock, self._orchestrator_lock, self._engine_lock, self._detector_lock:
            self._query_router = None
            self._rag_service = None
            self._model_orchestrator = None
            self._reasoning_engine = None
            self._contradiction_detector = None

            self._initialized = {k: False for k in self._initialized}

        logger.info("Container reset complete")

    def __repr__(self) -> str:
        """String representation for debugging."""
        status = self.get_initialization_status()
        initialized_count = sum(status.values())
        total_count = len(status)

        return f"ReasoningDependencyContainer(initialized={initialized_count}/{total_count}, status={status})"


# ============================================================================
# Global Container Instance (Singleton)
# ============================================================================


_global_container: ReasoningDependencyContainer | None = None
_container_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_reasoning_dependencies() -> ReasoningDependencyContainer:
    """
    Get the global reasoning dependency container (singleton).

    This is the primary entry point for accessing reasoning dependencies.

    Returns:
        ReasoningDependencyContainer instance

    Usage:
        from mahoun.reasoning.adapters import get_reasoning_dependencies

        container = get_reasoning_dependencies()
        router = container.query_router
        engine = container.reasoning_engine
    """
    global _global_container

    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                logger.info("Creating global ReasoningDependencyContainer")
                _global_container = ReasoningDependencyContainer()

    return _global_container


def reset_global_container() -> None:
    """
    Reset the global container (for testing only).

    WARNING: This will destroy all singletons globally.
    Only use in test teardown.
    """
    global _global_container

    with _container_lock:
        if _global_container is not None:
            _global_container.reset()
            _global_container = None
            get_reasoning_dependencies.cache_clear()
            logger.info("Global container reset")


# ============================================================================
# Convenience Accessors
# ============================================================================


def get_query_router() -> QueryRouterProtocol:
    """
    Get QueryRouter instance (convenience accessor).

    Returns:
        QueryRouterProtocol implementation
    """
    return get_reasoning_dependencies().query_router


def get_rag_service() -> RAGServiceProtocol:
    """
    Get RAG service instance (convenience accessor).

    Returns:
        RAGServiceProtocol implementation
    """
    return get_reasoning_dependencies().rag_service


def get_model_orchestrator() -> ModelOrchestratorProtocol:
    """
    Get model orchestrator instance (convenience accessor).

    Returns:
        ModelOrchestratorProtocol implementation
    """
    return get_reasoning_dependencies().model_orchestrator


def get_reasoning_engine() -> ReasoningEngineProtocol:
    """
    Get reasoning engine instance (convenience accessor).

    Returns:
        ReasoningEngineProtocol implementation
    """
    return get_reasoning_dependencies().reasoning_engine


# ============================================================================
# Test Utilities
# ============================================================================


class MockDependencyContainer(ReasoningDependencyContainer):
    """
    Mock container for testing.

    Allows injecting mock implementations of protocols.

    Usage:
        mock_router = Mock(spec=QueryRouterProtocol)
        container = MockDependencyContainer(query_router=mock_router)

        # Use in tests
        engine = UnifiedReasoningEngine(router=container.query_router)
    """

    def __init__(
        self,
        query_router: QueryRouterProtocol | None = None,
        rag_service: RAGServiceProtocol | None = None,
        model_orchestrator: ModelOrchestratorProtocol | None = None,
        reasoning_engine: ReasoningEngineProtocol | None = None,
    ):
        """
        Initialize mock container with optional mock implementations.

        Args:
            query_router: Mock QueryRouter
            rag_service: Mock RAG service
            model_orchestrator: Mock orchestrator
            reasoning_engine: Mock reasoning engine
        """
        super().__init__()

        if query_router is not None:
            self._query_router = query_router
            self._initialized["query_router"] = True

        if rag_service is not None:
            self._rag_service = rag_service
            self._initialized["rag_service"] = True

        if model_orchestrator is not None:
            self._model_orchestrator = model_orchestrator
            self._initialized["model_orchestrator"] = True

        if reasoning_engine is not None:
            self._reasoning_engine = reasoning_engine
            self._initialized["reasoning_engine"] = True

        logger.info("MockDependencyContainer initialized")
