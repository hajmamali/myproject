"""
Query Runner Abstraction
========================

Minimal interface for executing Cypher queries.
Decouples schema management from concrete session implementations.
"""

from typing import Any, Dict, List, Optional, Protocol


class QueryRunner(Protocol):
    """Minimal query execution interface."""

    def run(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as list of dicts."""
        ...


class GovernedSchemaRunner:
    """
    Adapter that wraps GovernedNeo4jSession for schema operations (DDL).

    Schema mutations (CREATE/DROP CONSTRAINT/INDEX) must go through
    the governance boundary. This adapter uses the session's internal
    authorized executor to ensure MutationAuthorizationBoundary is respected.
    """

    def __init__(self, governed_session: Any) -> None:
        """
        Args:
            governed_session: GovernedNeo4jSession instance (duck-typed to avoid circular import)
        """
        self._session = governed_session

    def run(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute query through governed session's authorized executor."""
        # Use the internal _execute_authorized which sets _authorized_write_ctx
        # This ensures MutationAuthorizationBoundary.inspect() passes
        result = self._session._execute_authorized(query, parameters or {})
        # Convert neo4j Record objects to dicts for compatibility
        return [dict(record) for record in result]


class RawSessionRunner:
    """Adapter for raw neo4j.Session (backward compatibility for tests/examples)."""

    def __init__(self, session: Any) -> None:
        self._session = session

    def run(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        result = self._session.run(query, parameters or {})
        return [dict(record) for record in result]
