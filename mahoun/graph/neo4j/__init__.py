"""
MAHOUN Neo4j Module
===================

Neo4j database connection and operations.

Components:
- Connection Manager: Database connection pooling
- Query Builder: Cypher query construction
- Transaction Manager: ACID transaction handling
- Batch Operations: Bulk data operations

Features:
- Connection pooling
- Automatic retry logic
- Query optimization
- Transaction management
- Error handling

LAZY LOADING:
Submodules are imported on-demand via __getattr__ to minimize import-time overhead.
"""
from typing import Any, Optional

__version__ = "2.0.0"

try:
    import neo4j  # type: ignore
    _NEO4J_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    neo4j: Optional[Any] = None
    _NEO4J_AVAILABLE = False

class _Neo4jMissingDependency(RuntimeError):
    pass

def _raise():
    raise _Neo4jMissingDependency(
        "Neo4j backend is not installed. Install with: pip install neo4j"
    )

# LAZY LOADING: Use __getattr__ to defer imports until first access
__all__ = [
    "Neo4jConnection",
    "get_connection",
    "QueryBuilder",
    "CypherQueryBuilder",
    "GraphOperations",
    "SchemaManager",
    "Constraint",
    "Index",
]

def __getattr__(name: str) -> Any:
    """Lazy-load submodules on first access to minimize import time."""
    
    if not _NEO4J_AVAILABLE:
        # Neo4j driver not installed — return stub
        if name in ("Neo4jConnection", "get_connection", "CypherQueryBuilder", 
                    "QueryBuilder", "GraphOperations", "SchemaManager", "Constraint", "Index"):
            if name in ("get_connection",):
                return lambda *a, **kw: _raise()
            # Return stub class
            class _Stub:
                def __init__(self, *a, **kw): _raise()
            _Stub.__name__ = name
            return _Stub
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    
    # Lazy import map
    if name == "Neo4jConnection":
        from mahoun.graph.neo4j.connection import Neo4jConnection
        return Neo4jConnection
    elif name == "get_connection":
        from mahoun.graph.neo4j.connection import get_connection
        return get_connection
    elif name == "CypherQueryBuilder":
        from mahoun.graph.neo4j.query_builder import CypherQueryBuilder
        return CypherQueryBuilder
    elif name == "QueryBuilder":
        # Alias
        from mahoun.graph.neo4j.query_builder import CypherQueryBuilder
        return CypherQueryBuilder
    elif name == "GraphOperations":
        from mahoun.graph.neo4j.operations import GraphOperations
        return GraphOperations
    elif name == "SchemaManager":
        from mahoun.graph.neo4j.schema import SchemaManager
        return SchemaManager
    elif name == "Constraint":
        from mahoun.graph.neo4j.schema import Constraint
        return Constraint
    elif name == "Index":
        from mahoun.graph.neo4j.schema import Index
        return Index
    elif name == "QueryRunner":
        from mahoun.graph.neo4j.runner import QueryRunner
        return QueryRunner
    elif name == "GovernedSchemaRunner":
        from mahoun.graph.neo4j.runner import GovernedSchemaRunner
        return GovernedSchemaRunner
    elif name == "RawSessionRunner":
        # DEPRECATED: RawSessionRunner bypasses MutationAuthorizationBoundary.
        # This export is for backward compatibility only. New code should use
        # GovernedNeo4jSession for mutations or execute_query() for reads.
        # In production, this will raise RuntimeError unless allow_unsafe=True.
        from mahoun.graph.neo4j.runner import RawSessionRunner
        return RawSessionRunner
    elif name == "_RawSessionRunner":
        # Internal alias (preferred for tests that need unsafe session access)
        from mahoun.graph.neo4j.runner import RawSessionRunner
        return RawSessionRunner
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
