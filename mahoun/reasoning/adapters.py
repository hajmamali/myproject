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
    # Advanced protocols
    UncertaintyServiceProtocol,
    OntologyGateProtocol,
    UltraRAGProtocol,
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
        
        # Advanced services
        self._uncertainty_service: UncertaintyServiceProtocol | None = None
        self._ontology_gate: OntologyGateProtocol | None = None
        self._ultra_rag: UltraRAGProtocol | None = None

        # Thread locks for safe lazy initialization
        self._router_lock = threading.Lock()
        self._rag_lock = threading.Lock()
        self._orchestrator_lock = threading.Lock()
        self._engine_lock = threading.Lock()
        self._detector_lock = threading.Lock()
        self._uncertainty_lock = threading.Lock()
        self._ontology_lock = threading.Lock()
        self._ultra_rag_lock = threading.Lock()

        # Initialization flags for observability
        self._initialized: dict[str, bool] = {
            "query_router": False,
            "rag_service": False,
            "model_orchestrator": False,
            "reasoning_engine": False,
            "contradiction_detector": False,
            "uncertainty_service": False,
            "ontology_gate": False,
            "ultra_rag": False,
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
    def uncertainty_service(self) -> Optional["UncertaintyServiceProtocol"]:
        """
        Get uncertainty service instance (lazy singleton, optional).

        Returns:
            UncertaintyServiceProtocol implementation or None if not available
        """
        if self._uncertainty_service is None:
            with self._uncertainty_lock:
                if self._uncertainty_service is None:
                    logger.info("Attempting to initialize UncertaintyService (lazy)")
                    try:
                        self._uncertainty_service = self._create_uncertainty_service()
                        if self._uncertainty_service is not None:
                            validate_protocol_implementation(
                                self._uncertainty_service, UncertaintyServiceProtocol
                            )
                            self._initialized["uncertainty_service"] = True
                            logger.info("UncertaintyService initialized successfully")
                        else:
                            logger.info("UncertaintyService not available (optional)")
                    except Exception as e:
                        logger.warning(f"UncertaintyService initialization failed: {e}")
                        self._uncertainty_service = None

        return self._uncertainty_service

    @property
    def ontology_gate(self) -> Optional["OntologyGateProtocol"]:
        """
        Get ontology gate instance (lazy singleton, optional).

        Returns:
            OntologyGateProtocol implementation or None if not available
        """
        if self._ontology_gate is None:
            with self._ontology_lock:
                if self._ontology_gate is None:
                    logger.info("Attempting to initialize OntologyGate (lazy)")
                    try:
                        self._ontology_gate = self._create_ontology_gate()
                        if self._ontology_gate is not None:
                            validate_protocol_implementation(
                                self._ontology_gate, OntologyGateProtocol
                            )
                            self._initialized["ontology_gate"] = True
                            logger.info("OntologyGate initialized successfully")
                        else:
                            logger.info("OntologyGate not available (optional)")
                    except Exception as e:
                        logger.warning(f"OntologyGate initialization failed: {e}")
                        self._ontology_gate = None

        return self._ontology_gate

    @property
    def ultra_rag(self) -> Optional["UltraRAGProtocol"]:
        """
        Get Ultra RAG instance (lazy singleton, optional).

        Returns:
            UltraRAGProtocol implementation or None if not available
        """
        if self._ultra_rag is None:
            with self._ultra_rag_lock:
                if self._ultra_rag is None:
                    logger.info("Attempting to initialize UltraRAG (lazy)")
                    try:
                        self._ultra_rag = self._create_ultra_rag()
                        if self._ultra_rag is not None:
                            validate_protocol_implementation(
                                self._ultra_rag, UltraRAGProtocol
                            )
                            self._initialized["ultra_rag"] = True
                            logger.info("UltraRAG initialized successfully")
                        else:
                            logger.info("UltraRAG not available (optional)")
                    except Exception as e:
                        logger.warning(f"UltraRAG initialization failed: {e}")
                        self._ultra_rag = None

        return self._ultra_rag

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
            
            Retrieves graph_retriever from bootstrap registry if available.
            
        CRITICAL FIX (B2+B7 — P1 Error Handling):
            Replaces silent exception catch with explicit error distinction:
            - KeyError → Service not registered (bootstrap not called or failed)
            - Service is None → Registered but None (bootstrap wiring error)
            
            This prevents silent degradation when bootstrap fails.
        """
        from mahoun.reasoning.rag_adapter import create_rag_service
        
        # Try to get graph_retriever from bootstrap registry
        graph_retriever = None
        try:
            from mahoun.bootstrap.runtime import get_service
            graph_retriever = get_service("graph_retriever")
            logger.info("✅ Graph retriever obtained from bootstrap registry")
        except KeyError as e:
            # CRITICAL: Service not registered → bootstrap not called or failed
            raise RuntimeError(
                "CRITICAL: graph_retriever not found in SERVICE_REGISTRY. "
                "This indicates bootstrap_runtime() was not called during startup. "
                "Check api/main.py lifespan to ensure bootstrap is executed. "
                f"Original error: {e}"
            ) from e
        except ImportError as e:
            # Bootstrap module not available
            raise RuntimeError(
                "CRITICAL: mahoun.bootstrap.runtime module not available. "
                "Ensure bootstrap module is properly installed."
            ) from e
        except Exception as e:
            # Other unexpected errors during service retrieval
            logger.error(
                f"❌ Unexpected error retrieving graph_retriever from bootstrap: {e}",
                exc_info=True
            )
            raise RuntimeError(
                f"CRITICAL: Failed to retrieve graph_retriever from bootstrap registry. "
                f"Error: {type(e).__name__}: {e}"
            ) from e
        
        # CRITICAL: Verify graph_retriever is not None (registered but None = wiring error)
        if graph_retriever is None:
            raise RuntimeError(
                "CRITICAL: graph_retriever is registered in SERVICE_REGISTRY but is None. "
                "This indicates a bootstrap wiring error in mahoun/bootstrap/runtime.py. "
                "The service was registered but not properly initialized."
            )

        service = create_rag_service(graph_retriever=graph_retriever)
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

    def _create_uncertainty_service(self) -> Optional["UncertaintyServiceProtocol"]:
        """
        Factory method for UncertaintyService (optional).

        Returns None if not available (graceful degradation).
        """
        try:
            from mahoun.uncertainty.service import UncertaintyService
            
            logger.info("UncertaintyService module found, creating instance")
            return UncertaintyService()
        except ImportError as e:
            logger.warning(f"UncertaintyService not available: {e}")
            return None

    def _create_ontology_gate(self) -> Optional["OntologyGateProtocol"]:
        """
        Factory method for OntologyGate (optional).

        Returns None if not available (graceful degradation).
        
        Note:
            Wraps existing OntologyEnforcer with schema-level validation.
        """
        try:
            from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
            from mahoun.core.governance.ontology_gate_adapter import OntologyGateAdapter
            
            logger.info("Creating OntologyGateAdapter wrapping OntologyEnforcer")
            enforcer = OntologyEnforcer()
            return OntologyGateAdapter(enforcer)
        except ImportError as e:
            logger.warning(f"OntologyGate not available: {e}")
            return None

    def _create_ultra_rag(self) -> Optional["UltraRAGProtocol"]:
        """
        Factory method for UltraRAG (optional).

        Returns None if not available (graceful degradation).
        """
        try:
            from mahoun.rag.ultra_graph_rag import UltraGraphRAG
            from mahoun.rag.ultra_rag_adapter import UltraRAGAdapter
            
            logger.info("UltraGraphRAG module found, creating adapter")
            
            # Get graph and retriever from bootstrap if available
            graph = None
            base_retriever = None
            try:
                from mahoun.bootstrap.runtime import get_service
                graph = get_service("graph")
                base_retriever = get_service("base_retriever")
            except Exception as e:
                logger.warning(f"Could not get graph/retriever from bootstrap: {e}")
            
            # Create UltraGraphRAG instance
            ultra_rag = UltraGraphRAG(
                graph=graph,
                base_retriever=base_retriever,
                enable_quantum_scoring=False,  # Disabled per codebase comment
                enable_causal_inference=True,
                enable_attention_flow=True,
                enable_feedback_learning=False  # Start conservative
            )
            
            # Wrap with adapter to satisfy protocol
            return UltraRAGAdapter(ultra_rag)
        except ImportError as e:
            logger.warning(f"UltraRAG not available: {e}")
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

        with self._router_lock, self._rag_lock, self._orchestrator_lock, self._engine_lock, self._detector_lock, \
             self._uncertainty_lock, self._ontology_lock, self._ultra_rag_lock:
            self._query_router = None
            self._rag_service = None
            self._model_orchestrator = None
            self._reasoning_engine = None
            self._contradiction_detector = None
            self._uncertainty_service = None
            self._ontology_gate = None
            self._ultra_rag = None

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
