"""
Knowledge Graph Adapters - GOVERNANCE-HARDENED
========================

Adapters to fetch graph-derived signals from external systems (e.g., Neo4j)
for use in the reasoning engine.

CONSTITUTIONAL COMPLIANCE:
- NO raw driver access
- ALL operations require correlation_id + actor_id
- ALL operations use GovernedNeo4jSession
"""

from typing import Callable, Dict, List
from datetime import datetime, timezone

from mahoun.core.governance.mutation_boundary import (
    GovernedNeo4jSession,
    _append_governance_audit,
)
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.exceptions import (
    GraphIntegrityException,
    LogicViolationException,
    SecurityBreachException,
)


class Neo4jKGAdapter:
    """
    Lightweight adapter over GovernedNeo4jSession - GOVERNANCE-HARDENED.

    Provides a simple `influence` signal based on outgoing relations
    (CITES, CO_CITATION, REFERS_TO) per node, normalized to [0,1].
    
    CONSTITUTIONAL COMPLIANCE:
    - Uses session_factory instead of raw driver
    - All queries require correlation_id + actor_id
    - All operations audited
    """

    def __init__(self, session_factory: Callable[[], GovernedNeo4jSession]):
        """
        Initialize adapter with governed session factory.
        
        Args:
            session_factory: Factory function returning GovernedNeo4jSession
            
        Raises:
            LogicViolationException: If session_factory is None
        """
        if session_factory is None:
            raise LogicViolationException(
                message="session_factory is required - raw driver injection forbidden",
                correlation_id="init",
                details={"component": "Neo4jKGAdapter"},
            )
        self._session_factory = session_factory

    def close(self) -> None:
        """No-op after governance hardening - connections managed by pool."""
        pass

    async def influence(
        self,
        evidences: List[Dict],
        correlation_id: str,
        actor_id: str,
    ) -> List[float]:
        """
        Calculate influence scores for evidence nodes.
        
        GOVERNANCE-PROTECTED: Requires active governance context.
        
        Args:
            evidences: List of evidence dictionaries with doc_id
            correlation_id: Request correlation ID (REQUIRED)
            actor_id: Actor performing the operation (REQUIRED)
            
        Returns:
            List of normalized influence scores [0,1]
            
        Raises:
            SecurityBreachException: If governance context invalid
            GraphIntegrityException: If query fails
        """
        # STEP 1: Validate governance context
        ctx = GovernanceContextManager.require_context()
        if ctx.correlation_id != correlation_id:
            raise SecurityBreachException(
                message="correlation_id mismatch",
                correlation_id=correlation_id,
                details={"expected": ctx.correlation_id, "provided": correlation_id},
            )
        
        ids = [e.get("doc_id", "") for e in evidences]
        if not ids:
            return []
        
        # STEP 2: Audit read operation
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "actor_id": actor_id,
            "operation": "influence_query",
            "component": "Neo4jKGAdapter",
            "evidence_count": len(ids),
        }
        _append_governance_audit(audit_entry)
        
        # STEP 3: Execute query through governed session
        try:
            q = (
                "MATCH (e:Article) WHERE e.doc_id IN $ids "
                "OPTIONAL MATCH (e)-[r:CITES|CO_CITATION|REFERS_TO]->() "
                "RETURN e.doc_id AS id, count(r) AS deg"
            )
            
            session = self._session_factory()
            rows = session._execute_authorized(q, {"ids": ids})
            
            m = {r["id"]: r["deg"] for r in rows}
            vals = [float(m.get(i, 0.0)) for i in ids]
            
            if not vals:
                return []
            
            lo, hi = min(vals), max(vals)
            return [(v - lo) / (hi - lo) if hi > lo else 0.0 for v in vals]
            
        except Exception as e:
            raise GraphIntegrityException(
                message="Influence query failed",
                correlation_id=correlation_id,
                details={"error": str(e), "component": "Neo4jKGAdapter"},
            ) from e

