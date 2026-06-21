"""
Graph Feedback Collection System - GOVERNANCE-HARDENED
=================================

v2 Enterprise: Aggregates usage and quality signals for graph edges.

Data Sources:
- Relationship properties (usage_count, success_count, last_used_at)
- Future: retrieval logs, RAG flows, uncertainty scores

CONSTITUTIONAL COMPLIANCE:
- NO raw driver access
- ALL operations require correlation_id + actor_id
- ALL operations use GovernedNeo4jSession
"""

import logging
from typing import Any, Callable, Dict, Optional
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


class GraphFeedbackCollector:
    """
    Collects and aggregates feedback signals for graph optimization - GOVERNANCE-HARDENED.
    
    v2.0 Implementation:
    - Reads from existing relationship properties
    - Returns usage metrics per edge
    
    CONSTITUTIONAL COMPLIANCE:
    - Uses session_factory instead of raw driver
    - All queries require correlation_id + actor_id
    - All operations audited
    
    Future enhancements (planned):
    - Integration with retrieval/ logs
    - Integration with rag/ and flows/ quality signals
    - Integration with uncertainty/ and guardrails/ relevance scores
    """
    
    def __init__(
        self,
        session_factory: Callable[[], GovernedNeo4jSession],
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize feedback collector with governed session factory.
        
        Args:
            session_factory: Factory function returning GovernedNeo4jSession
            logger: Optional logger
            
        Raises:
            LogicViolationException: If session_factory is None
        """
        if session_factory is None:
            raise LogicViolationException(
                message="session_factory is required - raw driver injection forbidden",
                correlation_id="init",
                details={"component": "GraphFeedbackCollector"},
            )
        self._session_factory = session_factory
        self.logger = logger or logging.getLogger(__name__)
    
    async def aggregate_edge_feedback(
        self,
        correlation_id: str,
        actor_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate feedback signals for all edges.
        
        GOVERNANCE-PROTECTED: Requires active governance context.
        
        Args:
            correlation_id: Request correlation ID (REQUIRED)
            actor_id: Actor performing the operation (REQUIRED)
        
        Returns:
            Dict mapping edge_id to feedback metrics:
            {
                "edge_id_123": {
                    "usage_count": int,
                    "success_count": int,
                    "last_used_at": datetime | None,
                    "avg_score": float | None,
                }
            }
        
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
        
        self.logger.debug("Aggregating edge feedback metrics")
        
        # STEP 2: Audit read operation
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "actor_id": actor_id,
            "operation": "aggregate_edge_feedback",
            "component": "GraphFeedbackCollector",
        }
        _append_governance_audit(audit_entry)
        
        cypher = """
        MATCH ()-[r]->()
        WHERE r.usage_count IS NOT NULL OR r.success_count IS NOT NULL
        RETURN 
            id(r) as edge_id,
            coalesce(r.usage_count, 0) as usage_count,
            coalesce(r.success_count, 0) as success_count,
            r.last_used_at as last_used_at,
            r.avg_score as avg_score
        """
        
        feedback_map: Dict[str, Any] = {}
        try:
            session = self._session_factory()
            result = session._execute_authorized(cypher, {})
            
            for record in result:
                edge_id = str(record["edge_id"])
                feedback_map[edge_id] = {
                    "usage_count": record["usage_count"],
                    "success_count": record["success_count"],
                    "last_used_at": record["last_used_at"],
                    "avg_score": record["avg_score"],
                }
            
            self.logger.info(f"Aggregated feedback for {len(feedback_map)} edges")
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate edge feedback: {e}", exc_info=True)
            raise GraphIntegrityException(
                message="Edge feedback aggregation failed",
                correlation_id=correlation_id,
                details={"error": str(e), "component": "GraphFeedbackCollector"},
            ) from e
        
        return feedback_map
    
    def collect_from_retrieval_logs(self) -> Dict[str, Dict[str, Any]]:
        """
        Will aggregate:
        - Path traversal counts from ultra_hybrid_search
        - Edge usage from graph_hop operations
        - Relevance scores from retrievers
        """
        self.logger.debug("Retrieval log integration not yet implemented")
        return {}
    
    def collect_from_rag_flows(self) -> Dict[str, Dict[str, Any]]:
        """
        Will aggregate:
        - Context quality scores
        - Answer relevance metrics
        - Edge contribution to successful retrievals
        """
        self.logger.debug("RAG flow integration not yet implemented")
        return {}
    
    def collect_from_quality_systems(self) -> Dict[str, Dict[str, Any]]:
        """
        Will aggregate:
        - Hallucination flags
        - Relevance scores
        - Confidence metrics
        """
        self.logger.debug("Quality system integration not yet implemented")
        return {}
