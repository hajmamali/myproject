"""
Query Execution Protocols
==========================

Protocol definitions for graph query execution with governance.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable


@runtime_checkable
class GraphQueryExecutorProtocol(Protocol):
    """
    Protocol for executing Cypher queries under unified governance.
    
    Implementations must:
    - Enforce governance policies
    - Provide audit trail
    - Handle connection lifecycle
    - Support both sync and async execution
    """
    
    def query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> Any:  # Returns QueryResult
        """
        Execute a Cypher query synchronously.
        
        Args:
            query: Cypher query string
            params: Query parameters
            use_cache: Whether to use query cache
            correlation_id: Correlation ID for tracing
            actor_id: Actor ID for audit
            
        Returns:
            QueryResult with results and metadata
        """
        ...
    
    async def query_async(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        correlation_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> Any:
        """
        Execute a Cypher query asynchronously.
        
        Args:
            query: Cypher query string
            params: Query parameters
            use_cache: Whether to use query cache
            correlation_id: Correlation ID for tracing
            actor_id: Actor ID for audit
            
        Returns:
            QueryResult with results and metadata
        """
        ...
