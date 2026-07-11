"""
Policy-enforced Query Executor
--------------------------------

Small wrapper to provide a single import point for executing Cypher queries
under unified governance. This delegates to `GraphQueryService` which already
integrates `UnifiedGovernanceController`.

Usage:
    from mahoun.core.query_executor import execute_cypher
    results = execute_cypher("MATCH (n) RETURN n LIMIT 10", correlation_id="cid", actor_id="user")

"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from mahoun.graph.graph_query_service import GraphQueryService, GraphQueryConfig

logger = logging.getLogger(__name__)


def execute_cypher(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    timeout: Optional[float] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """Synchronous execute helper that routes through GraphQueryService.

    This function exists to provide a single import point for services that
    need to execute Cypher queries under unified governance. GraphQueryService
    already applies UnifiedGovernanceController transformations and audit.
    """
    service = GraphQueryService()
    res = service.query(
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
    service = GraphQueryService()
    res = await service.query_async(
        query=query,
        params=params,
        use_cache=use_cache,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )
    return res.results
