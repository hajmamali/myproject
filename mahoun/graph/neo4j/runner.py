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
    """Adapter for raw neo4j.Session.

    WARNING: Using RawSessionRunner in production bypasses the
    MutationAuthorizationBoundary and audit guarantees. This adapter
    is intended ONLY for local tests and backwards-compatibility
    examples. In production environments this constructor will raise
    a RuntimeError to prevent accidental governance bypass.
    """

    def __init__(self, session: Any, allow_unsafe: bool = False) -> None:
        """Create a RawSessionRunner.

        Args:
            session: neo4j.Session-like object
            allow_unsafe: must be True to permit raw session usage (tests only)
        """
        # Fail-closed by default: prevent accidental use in production
        if not allow_unsafe:
            raise RuntimeError(
                "RawSessionRunner is unsafe in production. "
                "Pass allow_unsafe=True only in isolated test harnesses."
            )
        self._session = session

    def run(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        # Delegate directly to driver session for tests only
        result = self._session.run(query, parameters or {})
        return [dict(record) for record in result]
