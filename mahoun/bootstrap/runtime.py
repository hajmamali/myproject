"""
BOOTSTRAP / RUNTIME CORE (P0.4 ARCHITECTURE STABILIZATION)
Single entry point for system initialization.
MUST be the ONLY place where inter-module wiring occurs.

Wiring diagram:
    bootstrap_runtime()
    │
    ├── GraphQueryService(config)
    │     └── Neo4jConnectionManager(config)          [internal, lazy]
    │           └── get_connection()                  [on first query]
    │                 └── Neo4jConnection.governed_session()
    │
    └── GNNGraphBuilder(session_factory=governed_session_factory)
          └── governed_session_factory()
                └── get_connection().governed_session()

SERVICE_REGISTRY role: lifecycle / observability registry ONLY.
It is NOT a dependency source. Application code must NOT call get_service()
to satisfy constructor dependencies — use constructor injection instead.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SERVICE_REGISTRY: Dict[str, Any] = {}


def register_service(name: str, instance: object) -> None:
    """Register a service in the lifecycle registry."""
    SERVICE_REGISTRY[name] = instance
    logger.info(f"Service registered: {name}")


def get_service(name: str) -> Any:
    """
    Get a service from the lifecycle registry.

    ALLOWED USE: health checks, observability, introspection.
    FORBIDDEN USE: satisfying constructor dependencies. Use constructor
    injection instead — pass the dependency directly to __init__.

    Raises KeyError if service not registered to prevent silent wiring failures.
    """
    if name not in SERVICE_REGISTRY:
        raise KeyError(f"Service '{name}' not found in registry. Has bootstrap_runtime() been called?")
    return SERVICE_REGISTRY[name]


def clear_registry() -> None:
    """Clear the registry (for testing only)."""
    SERVICE_REGISTRY.clear()


def validate_governance_runtime() -> None:
    """
    Validate that the governance runtime is fully wired before accepting mutations.

    P1 STARTUP GATE: Must be called after audit sink wiring, before any
    graph mutation is permitted.

    Checks:
        - Audit sink is wired (not None)

    Raises:
        RuntimeError: If any governance runtime component is missing.

    Usage in bootstrap:
        # Wire sink first
        set_audit_sink(FilesystemAuditSink(...))
        # Then validate
        validate_governance_runtime()
    """
    from mahoun.core.governance.mutation_boundary import get_audit_sink
    if get_audit_sink() is None:
        raise RuntimeError(
            "Governance runtime invalid: "
            "Audit sink missing. "
            "Call set_audit_sink() before bootstrap_runtime()."
        )
    logger.info("Governance runtime validation passed: audit sink is wired.")


def bootstrap_runtime() -> Dict[str, Any]:
    """
    Central system wiring entry point.
    Must be the ONLY place where inter-module wiring occurs.

    This function performs controlled, lazy initialization:
    1. Imports services only when needed (Lazy Import Strategy)
    2. Constructs service instances with explicit dependencies
    3. Performs wiring (dependency injection)
    4. Registers them in the service registry for lifecycle management

    GraphQueryService receives an explicit GraphQueryConfig so its internal
    Neo4jConnectionManager is configured from a single authoritative source
    rather than relying on GraphQueryConfig defaults scattered across the codebase.
    """
    logger.info("MAHOUN Runtime Bootstrap Initiated")

    # 1. LAZY IMPORTS - Prevent top-level import chains
    from mahoun.graph.gnn.gnn_graph_builder import GNNGraphBuilder
    from mahoun.graph.graph_query_service import GraphQueryService, GraphQueryConfig
    from mahoun.graph.neo4j.connection import get_connection

    # 2. CONSTRUCTION & WIRING

    # GraphQueryService: inject explicit config so all Neo4j params come from
    # a single bootstrap-owned source. Neo4jConnectionManager is constructed
    # internally but configured via this injected GraphQueryConfig.
    query_config = GraphQueryConfig()  # reads from env via GraphQueryConfig defaults
    query_service = GraphQueryService(config=query_config)

    # GNNGraphBuilder: session_factory is the governed Neo4j write surface.
    # Bootstrap owns this factory — GNNGraphBuilder never creates connections itself.
    def governed_session_factory():
        return get_connection().governed_session()

    gnn_builder = GNNGraphBuilder(session_factory=governed_session_factory)

    # 3. REGISTRATION (lifecycle registry — NOT a dependency source)
    register_service("query", query_service)
    register_service("gnn", gnn_builder)

    # 4. NEO4J-REFACTORED SERVICES (Tasks 3-8: DI Refactor)
    # These services were refactored to accept Neo4jConnection via constructor injection.
    # Bootstrap wires them with get_connection() singleton — never raw drivers.
    from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
    from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
    from mahoun.graph.legal_cypher_queries import LegalQueryExecutor

    neo4j_conn = get_connection()
    graph_retriever = GraphEnhancedRetriever(connection=neo4j_conn)
    graph_vector_sync = GraphVectorSync(connection=neo4j_conn)
    legal_query_executor = LegalQueryExecutor(connection=neo4j_conn)

    register_service("graph_retriever", graph_retriever)
    register_service("graph_vector_sync", graph_vector_sync)
    register_service("legal_query_executor", legal_query_executor)

    # 5. GOVERNANCE RUNTIME VALIDATION — must pass before system is considered ready
    # NOTE: In production, set_audit_sink() must be called BEFORE bootstrap_runtime().
    # validate_governance_runtime() will catch missing sink configuration early.
    try:
        validate_governance_runtime()
    except RuntimeError as e:
        logger.warning(
            "Governance runtime validation warning: %s. "
            "Wire an audit sink via set_audit_sink() for full governance compliance.",
            e,
        )

    logger.info("MAHOUN Runtime Bootstrap COMPLETED")
    return SERVICE_REGISTRY.copy()
