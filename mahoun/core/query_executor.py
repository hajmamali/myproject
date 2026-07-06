"""
Policy-enforced Query Executor
--------------------------------

Provides a dependency-injection friendly interface for executing Cypher queries
under unified governance. Uses protocol-based design to avoid layer boundary violations.

Usage:
    from mahoun.core.query_executor import execute_cypher
    results = execute_cypher("MATCH (n) RETURN n LIMIT 10", correlation_id="cid", actor_id="user")

Architecture:
    - Core layer defines the protocol (GraphQueryExecutorProtocol)
    - Graph layer provides the implementation (GraphQueryService)
    - Bootstrap wires them together via set_query_executor()
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mahoun.core.protocols.query_protocols import GraphQueryExecutorProtocol

if TYPE_CHECKING:
    from mahoun.graph.graph_query_service import GraphQueryService

logger = logging.getLogger(__name__)

# Global executor instance - injected at bootstrap
_executor_instance: Optional[GraphQueryExecutorProtocol] = None


def set_query_executor(executor: GraphQueryExecutorProtocol) -> None:
    """
    Set the query executor implementation (Dependency Injection).
    
    This should be called during bootstrap to wire the concrete implementation.
    
    Args:
        executor: Implementation of GraphQueryExecutorProtocol
    """
    global _executor_instance
    _executor_instance = executor
    logger.info("Query executor registered via DI")


def get_query_executor() -> GraphQueryExecutorProtocol:
    """
    Get the current query executor.
    
    Returns:
        GraphQueryExecutorProtocol implementation
        
    Raises:
        RuntimeError: If no executor has been registered
    """
    if _executor_instance is None:
        # Fallback: lazy import for backward compatibility
        # In production, this should never execute - bootstrap should wire it
        logger.warning(
            "Query executor not registered via DI - falling back to direct import. "
            "This is a bootstrap configuration issue."
        )
        from mahoun.graph.graph_query_service import GraphQueryService
        return GraphQueryService()
    
    return _executor_instance


def execute_cypher(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    timeout: Optional[float] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    Synchronous execute helper that routes through registered executor.

    This function provides a simple import point for services that need to
    execute Cypher queries. The actual implementation is injected at bootstrap.
    
    Args:
        query: Cypher query string
        params: Query parameters
        correlation_id: Correlation ID for tracing
        actor_id: Actor ID for audit
        timeout: Query timeout (not used currently)
        use_cache: Whether to use query cache
        
    Returns:
        List of result dictionaries
    """
    executor = get_query_executor()
    res = executor.query(
        query=query,
        params=params,
        use_cache=use_cache,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )

    return res.results


async def execute_cypher_async(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    timeout: Optional[float] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """
    Asynchronous execute helper that routes through registered executor.
    
    Args:
        query: Cypher query string
        params: Query parameters
        correlation_id: Correlation ID for tracing
        actor_id: Actor ID for audit
        timeout: Query timeout (not used currently)
        use_cache: Whether to use query cache
        
    Returns:
        List of result dictionaries
    """
    executor = get_query_executor()
    res = await executor.query_async(
        query=query,
        params=params,
        use_cache=use_cache,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )

    return res.results
