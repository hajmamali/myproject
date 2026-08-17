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
from typing import Any, Optional

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

    def __init__(self, use_rete: bool = False):
        """Initialize container with empty state."""
        self._query_router: QueryRouterProtocol | None = None
        self._rag_service: RAGServiceProtocol | None = None
        self._model_orchestrator: ModelOrchestratorProtocol | None = None
        self._reasoning_engine: ReasoningEngineProtocol | None = None
        self._contradiction_detector: ContradictionDetectorProtocol | None = None
        self._symbolic_reasoner: Optional[Any] = None
        self._reasoning_recorder: Optional[Any] = None
        self._use_rete = use_rete

        # Thread locks for safe lazy initialization
        self._router_lock = threading.Lock()
        self._rag_lock = threading.Lock()
        self._orchestrator_lock = threading.Lock()
        self._engine_lock = threading.Lock()
        self._detector_lock = threading.Lock()
        self._symbolic_lock = threading.Lock()
        self._recorder_lock = threading.Lock()

        # Initialization flags for observability
        self._initialized: dict[str, bool] = {
            "query_router": False,
            "rag_service": False,
            "model_orchestrator": False,
            "reasoning_engine": False,
            "contradiction_detector": False,
            "symbolic_reasoner": False,
            "reasoning_recorder": False,
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

    @property
    def symbolic_reasoner(self) -> Optional[Any]:
        """
        Get SymbolicReasoner instance (lazy singleton, optional).

        Returns:
            SymbolicReasoner instance or None if not available

        SymbolicReasoner provides deterministic, LLM-free reasoning using
        forward/backward chaining for high-stakes decisions.
        """
        if self._symbolic_reasoner is None:
            with self._symbolic_lock:
                if self._symbolic_reasoner is None:
                    logger.info("Attempting to initialize SymbolicReasoner (lazy)")
                    try:
                        self._symbolic_reasoner = self._create_symbolic_reasoner()
                        if self._symbolic_reasoner is not None:
                            self._initialized["symbolic_reasoner"] = True
                            logger.info("SymbolicReasoner initialized successfully")
                        else:
                            logger.info("SymbolicReasoner not available (optional)")
                    except Exception as e:
                        logger.warning(f"SymbolicReasoner initialization failed: {e}")
                        self._symbolic_reasoner = None

        return self._symbolic_reasoner

    @property
    def reasoning_recorder(self) -> Optional[Any]:
        """
        Get ReasoningRecorder instance (lazy singleton, optional).

        Returns:
            ReasoningRecorder instance or None if not available

        ReasoningRecorder provides immutable audit trail for reasoning steps
        with cryptographic hash-chain verification.
        """
        if self._reasoning_recorder is None:
            with self._recorder_lock:
                if self._reasoning_recorder is None:
                    logger.info("Attempting to initialize ReasoningRecorder (lazy)")
                    try:
                        self._reasoning_recorder = self._create_reasoning_recorder()
                        if self._reasoning_recorder is not None:
                            self._initialized["reasoning_recorder"] = True
                            logger.info("ReasoningRecorder initialized successfully")
                        else:
                            logger.info("ReasoningRecorder not available (optional)")
                    except Exception as e:
                        logger.warning(f"ReasoningRecorder initialization failed: {e}")
                        self._reasoning_recorder = None

        return self._reasoning_recorder

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

        Feature Flag Support:
        - MAHOUN_USE_POLICY_AWARE_RAG=true: Use PolicyAwareRAGService (governance-aware wrapper)
        - MAHOUN_USE_POLICY_AWARE_RAG=false (default): Use HybridRAGService (standard retrieval)

        Architecture:
        - PolicyAwareRAGService wraps HybridRAGService (composition pattern)
        - Receives GovernanceContext from middleware (doesn't create it)
        - Only performs retrieval + policy filtering (no decisions)
        - Maintains architectural boundaries (no reasoning engine calls)

        Note:
            Uses rag_adapter to avoid direct import from RAG module.
            This maintains architectural boundary between core and non-core.
        """
        import os

        # Check feature flag for PolicyAwareRAGService
        use_policy_aware = os.getenv("MAHOUN_USE_POLICY_AWARE_RAG", "false").lower() == "true"

        if use_policy_aware:
            logger.info("Feature flag enabled: Using PolicyAwareRAGService")
            try:
                from mahoun.reasoning.rag_adapter import create_rag_service as create_base
                from mahoun.rag.policy_aware_rag_service import PolicyAwareRAGService

                # Create base HybridRAGService
                base_service = create_base()
                if base_service is None:
                    raise RuntimeError("Base HybridRAGService not available for PolicyAwareRAGService wrapper")

                # Wrap with PolicyAwareRAGService
                logger.info("Wrapping HybridRAGService with PolicyAwareRAGService")
                service = PolicyAwareRAGService(
                    base_service=base_service,
                    enable_governance=True,  # Governance enforcement enabled
                    enable_cache=True,  # Policy-aware caching enabled
                )

                logger.info("PolicyAwareRAGService initialized successfully")
                return service

            except ImportError as e:
                logger.error(f"PolicyAwareRAGService not available: {e}")
                logger.warning("Falling back to HybridRAGService")
                # Fall through to standard service

        # Standard HybridRAGService (default)
        logger.info("Using standard HybridRAGService")
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

    def _create_symbolic_reasoner(self) -> Optional[Any]:
        """
        Factory method for SymbolicReasoningEngine (optional).

        Returns None if not available (graceful degradation).

        SymbolicReasoningEngine provides deterministic, LLM-free reasoning using
        first-order logic, forward chaining, and backward chaining.
        """
        try:
            from mahoun.reasoning.symbolic_reasoner import SymbolicReasoningEngine
            return SymbolicReasoningEngine(use_rete=self._use_rete)
        except ImportError as e:
            logger.warning(f"SymbolicReasoningEngine not available: {e}")
            return None

    def _create_reasoning_recorder(self) -> Optional[Any]:
        """
        Factory method for ReasoningRecorder (optional).

        Returns None if not available (graceful degradation).

        ReasoningRecorder provides immutable audit trail for reasoning steps
        with cryptographic hash-chain verification.
        """
        try:
            from mahoun.reasoning.reasoning_recorder import ReasoningRecorder
            return ReasoningRecorder()
        except ImportError as e:
            logger.warning(f"ReasoningRecorder not available: {e}")
            return None

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

        with self._router_lock, self._rag_lock, self._orchestrator_lock, self._engine_lock, self._detector_lock, self._symbolic_lock, self._recorder_lock:
            self._query_router = None
            self._rag_service = None
            self._model_orchestrator = None
            self._reasoning_engine = None
            self._contradiction_detector = None
            self._symbolic_reasoner = None
            self._reasoning_recorder = None

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


def get_symbolic_reasoner() -> Optional[Any]:
    """
    Get SymbolicReasoner instance (convenience accessor).

    Returns:
        SymbolicReasoner instance or None if not available
    """
    return get_reasoning_dependencies().symbolic_reasoner


def get_reasoning_recorder() -> Optional[Any]:
    """
    Get ReasoningRecorder instance (convenience accessor).

    Returns:
        ReasoningRecorder instance or None if not available
    """
    return get_reasoning_dependencies().reasoning_recorder


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
