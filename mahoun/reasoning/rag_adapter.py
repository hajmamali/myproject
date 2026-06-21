"""
RAG Adapter for Reasoning Module
==================================

Enterprise-grade adapter providing runtime access to RAG services
without creating compile-time architectural boundary violations.

ARCHITECTURE PRINCIPLES:
- Reasoning (core) → RAG (non-core): FORBIDDEN at compile-time
- Runtime dependency injection: ALLOWED via adapter pattern
- Graceful degradation: System remains functional without RAG
- Protocol-based contracts: Type-safe interfaces without coupling

DESIGN PATTERNS:
- Adapter Pattern: Bridges incompatible interfaces
- Lazy Initialization: Defers expensive resource creation
- Null Object Pattern: Provides no-op fallback implementations
- Dependency Injection: Inverts control flow for testability

THREAD SAFETY:
- All factory functions are thread-safe
- No shared mutable state
- Idempotent operations

PERFORMANCE:
- Lazy imports minimize startup overhead
- Caching at container level (not here)
- Zero-cost abstraction when RAG unavailable
"""

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mahoun.core.protocols import QueryRouterProtocol, RAGServiceProtocol

logger = logging.getLogger(__name__)


# ============================================================================
# QueryRouter Factory
# ============================================================================


def create_query_router(
    rag_service: Optional['RAGServiceProtocol'] = None
) -> Optional['QueryRouterProtocol']:
    """
    Create QueryRouter instance with runtime import.
    
    This factory function provides late binding to RAG infrastructure,
    allowing reasoning module to remain independent of RAG implementation.
    
    Args:
        rag_service: Optional pre-configured RAG service instance.
                    If None, QueryRouter will lazy-initialize its own.
    
    Returns:
        QueryRouterProtocol implementation or None if unavailable
        
    Raises:
        None - All exceptions are caught and logged
        
    Thread Safety:
        Thread-safe - no shared mutable state
        
    Performance:
        O(1) - Simple import and instantiation
        Lazy import defers cost until first call
        
    Example:
        >>> router = create_query_router()
        >>> if router:
        ...     result = await router.route("legal query")
    """
    try:
        from mahoun.rag.query_router import QueryRouter
        
        router = QueryRouter(rag_service=rag_service)
        logger.info("QueryRouter created successfully via adapter")
        return router
        
    except ImportError as e:
        logger.info(
            f"QueryRouter not available (RAG module not installed): {e}",
            extra={"adapter": "rag_adapter", "component": "QueryRouter"}
        )
        return None
        
    except Exception as e:
        logger.error(
            f"QueryRouter creation failed: {e}",
            extra={"adapter": "rag_adapter", "component": "QueryRouter"},
            exc_info=True
        )
        return None


# ============================================================================
# RAG Service Factory
# ============================================================================


def create_rag_service() -> Optional['RAGServiceProtocol']:
    """
    Create HybridRAGService instance with runtime import.
    
    This factory provides access to the hybrid RAG service combining:
    - Dense retrieval (vector similarity)
    - Sparse retrieval (BM25/keyword)
    - Graph-based retrieval (knowledge graph traversal)
    
    Returns:
        RAGServiceProtocol implementation or None if unavailable
        
    Raises:
        None - All exceptions are caught and logged
        
    Thread Safety:
        Thread-safe - no shared mutable state
        
    Performance:
        O(1) for instantiation
        Note: Actual RAG service may have expensive initialization
              (loading embeddings, indices, etc.)
        
    Graceful Degradation:
        Returns None if RAG unavailable
        Caller must handle None case appropriately
        
    Example:
        >>> rag = create_rag_service()
        >>> if rag:
        ...     results = await rag.retrieve("query", mode=RAGMode.HYBRID)
        ... else:
        ...     # Fallback to non-RAG reasoning
        ...     results = fallback_retrieval("query")
    """
    try:
        from mahoun.rag.hybrid_rag_service import HybridRAGService
        
        service = HybridRAGService()
        logger.info("HybridRAGService created successfully via adapter")
        return service
        
    except ImportError as e:
        logger.info(
            f"HybridRAGService not available (RAG module not installed): {e}",
            extra={"adapter": "rag_adapter", "component": "HybridRAGService"}
        )
        return None
        
    except Exception as e:
        logger.error(
            f"HybridRAGService creation failed: {e}",
            extra={"adapter": "rag_adapter", "component": "HybridRAGService"},
            exc_info=True
        )
        return None


# ============================================================================
# Unified Reasoning Engine Factory
# ============================================================================


def create_unified_reasoning_engine(
    router: 'QueryRouterProtocol'
) -> Optional['ReasoningEngineProtocol']:
    """
    Create UnifiedReasoningEngine instance with runtime import.
    
    The unified reasoning engine orchestrates:
    - Query classification and routing
    - RAG-based context retrieval
    - Model selection and inference
    - Response generation and validation
    
    Args:
        router: QueryRouter instance for query classification
        
    Returns:
        ReasoningEngineProtocol implementation or None if unavailable
        
    Raises:
        None - All exceptions are caught and logged
        
    Thread Safety:
        Thread-safe - no shared mutable state
        
    Performance:
        O(1) - Simple instantiation
        Engine itself may have lazy initialization
        
    Example:
        >>> router = create_query_router()
        >>> engine = create_unified_reasoning_engine(router)
        >>> if engine:
        ...     response = await engine.process_query("legal question")
    """
    try:
        from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
        
        engine = UnifiedReasoningEngine(router=router)
        logger.info("UnifiedReasoningEngine created successfully via adapter")
        return engine
        
    except ImportError as e:
        logger.info(
            f"UnifiedReasoningEngine not available: {e}",
            extra={"adapter": "rag_adapter", "component": "UnifiedReasoningEngine"}
        )
        return None
        
    except Exception as e:
        logger.error(
            f"UnifiedReasoningEngine creation failed: {e}",
            extra={"adapter": "rag_adapter", "component": "UnifiedReasoningEngine"},
            exc_info=True
        )
        return None


# ============================================================================
# Validation and Health Checks
# ============================================================================


def validate_rag_availability() -> bool:
    """
    Check if RAG infrastructure is available without instantiating.
    
    This lightweight check verifies module availability without
    triggering expensive initialization (loading models, indices, etc.)
    
    Returns:
        True if RAG modules can be imported, False otherwise
        
    Thread Safety:
        Thread-safe - read-only operation
        
    Performance:
        O(1) - Simple import check, no instantiation
        
    Use Cases:
        - Startup health checks
        - Feature flag determination
        - Graceful degradation decisions
        
    Example:
        >>> if validate_rag_availability():
        ...     router = create_query_router()
        ... else:
        ...     logger.warning("RAG unavailable, using fallback reasoning")
    """
    try:
        import mahoun.rag.query_router
        import mahoun.rag.hybrid_rag_service
        return True
    except ImportError:
        return False


def get_rag_adapter_info() -> dict:
    """
    Get diagnostic information about RAG adapter status.
    
    Returns:
        Dict containing:
        - available: bool - Whether RAG is available
        - components: dict - Status of individual components
        - version: str - Adapter version
        
    Thread Safety:
        Thread-safe - read-only operation
        
    Performance:
        O(1) - Simple checks, no instantiation
        
    Example:
        >>> info = get_rag_adapter_info()
        >>> print(f"RAG available: {info['available']}")
        >>> print(f"Components: {info['components']}")
    """
    components = {}
    
    # Check QueryRouter
    try:
        import mahoun.rag.query_router
        components['query_router'] = 'available'
    except ImportError:
        components['query_router'] = 'unavailable'
    
    # Check HybridRAGService
    try:
        import mahoun.rag.hybrid_rag_service
        components['hybrid_rag_service'] = 'available'
    except ImportError:
        components['hybrid_rag_service'] = 'unavailable'
    
    # Check UnifiedReasoningEngine
    try:
        import mahoun.reasoning.unified_engine
        components['unified_reasoning_engine'] = 'available'
    except ImportError:
        components['unified_reasoning_engine'] = 'unavailable'
    
    return {
        'available': all(v == 'available' for v in components.values()),
        'components': components,
        'version': '1.0.0',
        'adapter': 'rag_adapter'
    }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'create_query_router',
    'create_rag_service',
    'create_unified_reasoning_engine',
    'validate_rag_availability',
    'get_rag_adapter_info',
]
