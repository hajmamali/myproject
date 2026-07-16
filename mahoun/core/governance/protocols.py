"""
MAHOUN Governance Protocols — Task 4: Eliminate Duck Typing
============================================================

Classification: KERNEL / CONSTITUTIONAL / STATIC-VERIFIABLE

Defines explicit Protocols for every mutation surface so that
static type checkers (mypy / pyright) can verify the call chain
without relying on runtime duck-typing.

Invariant enforced:
    I5 — No raw mutation sessions outside canonical write path.

Any code that previously used `Any` for the mutation executor or
session types must now use these Protocols.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# RawQueryExecutor Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class RawQueryExecutor(Protocol):
    """
    Minimal protocol for the raw_executor callable injected into
    GovernedNeo4jSession.

    Only _raw_execute on Neo4jConnection satisfies this protocol.
    Passing `Any` or a lambda is a type error.

    The executor receives a Cypher string + params and returns a list
    of result records. It must call MutationAuthorizationBoundary.inspect()
    before dispatching to the driver — that is enforced inside
    Neo4jConnection._raw_execute(), not here.
    """

    def __call__(self, query: str, params: Dict[str, Any]) -> List[Any]:
        ...


# ---------------------------------------------------------------------------
# GovernedGraphSession Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class GovernedGraphSession(Protocol):
    """
    Explicit protocol for the governed session surface.

    Every caller that previously typed its session as `Any` must
    switch to this protocol.  This makes all call sites statically
    verifiable: if a method is not on this protocol, the type checker
    will flag it before the code reaches CI.

    Implemented by: GovernedNeo4jSession (mutation_boundary.py)
    """

    def write_node(
        self,
        label: str,
        node_data: Dict[str, Any],
        merge: bool = True,
    ) -> Any:
        """Write or merge a node through the governed boundary."""
        ...

    def write_relationship(
        self,
        source_type: str,
        source_id: str,
        relationship_type: str,
        target_type: str,
        target_id: str,
        rel_data: Dict[str, Any],
        merge: bool = True,
    ) -> Any:
        """Write or merge a relationship through the governed boundary."""
        ...

    def delete_node(
        self,
        label: str,
        node_id: str,
        soft_delete: bool = True,
        deleted_reason: str = "governance_delete",
        source_event_id: str = "",
    ) -> Any:
        """Delete (soft-tombstone or hard) a node through the governed boundary."""
        ...

    def begin_transaction(self) -> Any:
        """Begin an atomic governed transaction."""
        ...

    @property
    def ledger(self) -> Any:
        """Immutable view of mutation receipts for this session."""
        ...

    @property
    def mutation_count(self) -> int:
        """Number of mutations executed in this session."""
        ...


# ---------------------------------------------------------------------------
# Runtime assertion helpers
# ---------------------------------------------------------------------------

def assert_governed_session(obj: Any, context: str = "") -> None:
    """
    Assert at runtime that `obj` satisfies the GovernedGraphSession protocol.

    This is a defence-in-depth check for call sites that receive a session
    from DI and want to fail-fast if something unexpected is passed.

    Raises:
        TypeError: If `obj` does not satisfy GovernedGraphSession.
    """
    if not isinstance(obj, GovernedGraphSession):
        missing = [
            m for m in ("write_node", "write_relationship", "delete_node",
                        "begin_transaction")
            if not hasattr(obj, m)
        ]
        raise TypeError(
            f"Expected GovernedGraphSession but got {type(obj).__name__}. "
            f"Missing methods: {missing}. "
            f"Context: {context or 'unknown'}. "
            "Pass a GovernedNeo4jSession obtained via connection.governed_session()."
        )


def assert_raw_executor(obj: Any, context: str = "") -> None:
    """
    Assert that `obj` is a callable accepting (query, params).

    Raises:
        TypeError: If obj is not callable.
    """
    if not callable(obj):
        raise TypeError(
            f"Expected RawQueryExecutor (callable) but got {type(obj).__name__}. "
            f"Context: {context or 'unknown'}. "
            "Pass Neo4jConnection._raw_execute."
        )


# ---------------------------------------------------------------------------
# MetricsCollector Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class MetricsCollectorProtocol(Protocol):
    """
    Protocol for dependency-injected metrics collection in the Kernel.
    
    Prevents the Kernel Runtime from depending directly on infrastructure
    observability layers, satisfying the dependency inversion principle.
    """
    def register_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Any:
        ...

    def register_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Any:
        ...

    def register_histogram(self, name: str, buckets: Optional[list] = None, labels: Optional[Dict[str, str]] = None) -> Any:
        ...


# ---------------------------------------------------------------------------
# AuditSinkProtocol
# ---------------------------------------------------------------------------

@runtime_checkable
class AuditSinkProtocol(Protocol):
    """
    Append-only persistence surface for governance audit events.

    The kernel boundary calls ``AuditSinkProtocol.append(entry)`` exactly
    once per successfully validated mutation. The concrete implementation
    (filesystem, remote ledger, in-memory test sink) is injected at the
    application composition root. The kernel does not know the medium.
    """
    def append(self, entry: Dict[str, Any]) -> None:
        """Persist a single immutable audit entry. Raises on failure."""
        ...


# ---------------------------------------------------------------------------
# SchemaValidatorProtocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SchemaValidatorProtocol(Protocol):
    """
    Validates a payload dict against an opaque schema object.

    The kernel exposes a registry of label -> SchemaValidatorProtocol
    implementations. Concrete validators (Pydantic, JSON Schema, dataclass,
    in-memory prototypes) live in ``mahoun/contracts`` or ``mahoun/infrastructure``.

    The kernel does not import pydantic itself; conforming adapters wrap it.
    """
    def validate(
        self,
        payload: Dict[str, Any],
        schema: Any,
        *,
        label: str,
    ) -> None:
        """Validate ``payload`` against ``schema`` or raise."""
        ...


# ---------------------------------------------------------------------------
# GovernedWriteSessionProtocol (vendor-neutral)
# ---------------------------------------------------------------------------

@runtime_checkable
class GovernedWriteSessionProtocol(Protocol):
    """
    Vendor-neutral abstraction of the only authorized write surface.

    The kernel enforces classification, audit ordering, and authorization
    token management. The adapter (e.g., GovernedNeo4jSession under
    mahoun/graph/neo4j) implements the protocol with its driver-specific
    Cypher / driver / session abstraction.

    The protocol is the *contract*; the implementation carries driver
    semantics and stays outside the kernel.
    """
    def write_node(
        self,
        label: str,
        node_data: Dict[str, Any],
        merge: bool = True,
    ) -> Any:
        ...

    def write_relationship(
        self,
        source_type: str,
        source_id: str,
        relationship_type: str,
        target_type: str,
        target_id: str,
        rel_data: Dict[str, Any],
        merge: bool = True,
    ) -> Any:
        ...

    def delete_node(
        self,
        label: str,
        node_id: str,
        soft_delete: bool = True,
        deleted_reason: str = "governance_delete",
        source_event_id: str = "",
    ) -> Any:
        ...

    def begin_transaction(self) -> Any:
        ...

    @property
    def ledger(self) -> Any:
        ...

    @property
    def mutation_count(self) -> int:
        ...


class NoOpMetric:
    """Null Object pattern for a metric."""
    def inc(self, amount: float = 1) -> None:
        pass
    def set(self, value: float) -> None:
        pass
    def observe(self, value: float) -> None:
        pass


class NoOpMetricsCollector:
    """
    Null Object pattern implementation of MetricsCollectorProtocol.
    Used as a fail-safe default when no external collector is injected.
    """
    def register_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> Any:
        return NoOpMetric()
        
    def register_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Any:
        return NoOpMetric()
        
    def register_histogram(self, name: str, buckets: Optional[list] = None, labels: Optional[Dict[str, str]] = None) -> Any:
        return NoOpMetric()
