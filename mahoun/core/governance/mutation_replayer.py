"""
MAHOUN Mutation Replayer — Task 11
====================================

Classification: KERNEL / AUDIT / FORENSIC

Purpose:
    Replay a sequence of MutationReceipt objects against an in-memory
    graph snapshot and verify that the reconstructed state hash matches
    the hash produced during the original mutation chain.

Algorithm:
    1. Accept N MutationReceipt objects (from a governed session's ledger).
    2. Apply each mutation (in receipt order) to an InMemoryGraphState.
    3. Compute a deterministic SHA-256 hash of the final state.
    4. Compare against the expected_state_hash (provided or derived from
       the last receipt's content_hash chain).
    5. Return ReplayResult — MATCH / MISMATCH / PARTIAL.

This module has ZERO external dependencies (stdlib only).
It must remain hermetic — no Neo4j, no network, no filesystem.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class ReplayStatus(str, Enum):
    """Result classification for a replay run."""
    MATCH   = "MATCH"    # Reconstructed hash == expected hash
    MISMATCH = "MISMATCH" # Hash divergence — audit integrity PARTIAL
    PARTIAL  = "PARTIAL"  # Some receipts could not be applied (missing data)
    EMPTY    = "EMPTY"    # No mutations to replay


@dataclass(frozen=True)
class ReplayResult:
    """Immutable result of a mutation replay verification run."""
    status: ReplayStatus
    mutation_count: int
    applied_count: int
    skipped_count: int
    reconstructed_hash: str
    expected_hash: str
    # Per-mutation replay trace (entity_id → final state hash)
    entity_hashes: Dict[str, str] = field(default_factory=dict)
    mismatched_entities: List[str] = field(default_factory=list)
    detail: str = ""

    @property
    def audit_integrity(self) -> str:
        """Human-readable audit integrity classification."""
        if self.status == ReplayStatus.MATCH:
            return "PROVEN"
        if self.status == ReplayStatus.PARTIAL:
            return "PARTIALLY PROVEN"
        return "NOT PROVEN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "audit_integrity": self.audit_integrity,
            "mutation_count": self.mutation_count,
            "applied_count": self.applied_count,
            "skipped_count": self.skipped_count,
            "reconstructed_hash": self.reconstructed_hash,
            "expected_hash": self.expected_hash,
            "mismatched_entities": self.mismatched_entities,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# In-memory graph state
# ---------------------------------------------------------------------------

class InMemoryGraphState:
    """
    Minimal in-memory representation of a Neo4j graph for replay purposes.

    Stores nodes and soft-delete tombstones.  Does NOT store relationships
    (relationship receipts carry no node property data to reconstruct from).

    Thread-safety: NOT thread-safe.  Each replayer runs on its own instance.
    """

    def __init__(self) -> None:
        # node_id → {"label": str, "data": dict, "_deleted": bool}
        self._nodes: Dict[str, Dict[str, Any]] = {}

    def apply_node_merge(self, entity_id: str, label: str,
                         content_hash: str) -> None:
        """MERGE — upsert node by entity_id."""
        if entity_id in self._nodes:
            self._nodes[entity_id]["label"] = label
            self._nodes[entity_id]["content_hash"] = content_hash
            self._nodes[entity_id]["_deleted"] = False
        else:
            self._nodes[entity_id] = {
                "label": label,
                "content_hash": content_hash,
                "_deleted": False,
            }

    def apply_node_create(self, entity_id: str, label: str,
                          content_hash: str) -> None:
        """CREATE — only if node does not already exist."""
        if entity_id not in self._nodes:
            self._nodes[entity_id] = {
                "label": label,
                "content_hash": content_hash,
                "_deleted": False,
            }

    def apply_node_delete(self, entity_id: str, soft: bool = True) -> None:
        """DELETE — soft tombstone (default) or hard remove."""
        if entity_id in self._nodes:
            if soft:
                self._nodes[entity_id]["_deleted"] = True
            else:
                del self._nodes[entity_id]

    def state_hash(self) -> str:
        """
        Deterministic SHA-256 of the entire graph state.

        Nodes are sorted by entity_id before hashing so that insertion
        order does not affect the hash.
        """
        canonical: List[Dict[str, Any]] = []
        for eid in sorted(self._nodes.keys()):
            node = self._nodes[eid].copy()
            node["entity_id"] = eid
            canonical.append(node)
        payload = json.dumps(canonical, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def entity_hash(self, entity_id: str) -> Optional[str]:
        """Hash of a single entity's current state (or None if not found)."""
        if entity_id not in self._nodes:
            return None
        node = self._nodes[entity_id].copy()
        node["entity_id"] = entity_id
        payload = json.dumps(node, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def active_node_count(self) -> int:
        return sum(1 for n in self._nodes.values() if not n.get("_deleted"))


# ---------------------------------------------------------------------------
# Mutation Replayer
# ---------------------------------------------------------------------------

class MutationReplayer:
    """
    Replays a sequence of MutationReceipts and verifies state hash integrity.

    PATCH P0-2: Temporal ordering validation enforced.
    Receipts must follow valid mutation sequences:
      - NODE_CREATE may only execute if node doesn't exist
      - NODE_MERGE may execute anytime
      - NODE_DELETE may only execute if node exists

    Usage:
        replayer = MutationReplayer()
        result = replayer.replay(receipts, expected_hash=session_state_hash)
        assert result.status == ReplayStatus.MATCH
    """

    def __init__(self, *, strict_temporal_validation: bool = False) -> None:
        """
        Initialize MutationReplayer.
        
        Args:
            strict_temporal_validation: If True, temporal ordering violations
                raise exceptions immediately rather than being logged as skipped.
                Use True for adversarial testing, False for production replay
                (where partial replays with skipped receipts are acceptable).
        """
        self._graph = InMemoryGraphState()
        # PATCH P0-2: Track entity lifecycle to enforce temporal constraints
        self._entity_lifecycle: Dict[str, List[str]] = {}  # entity_id -> [mutation_type_history]
        self._strict_temporal_validation = strict_temporal_validation

    def replay(
        self,
        receipts: Sequence[Any],  # Sequence[MutationReceipt]
        expected_hash: Optional[str] = None,
    ) -> ReplayResult:
        """
        Replay N mutations and verify the final state hash.

        Args:
            receipts: Ordered sequence of MutationReceipt objects from
                      GovernedNeo4jSession.ledger.
            expected_hash: Optional expected state hash.  If None, the
                           replayer computes the expected hash by deriving
                           it from the chain of receipt content_hashes
                           (chain-of-custody hash, not graph state hash).

        Returns:
            ReplayResult with status MATCH / MISMATCH / PARTIAL / EMPTY.
        """
        if not receipts:
            return ReplayResult(
                status=ReplayStatus.EMPTY,
                mutation_count=0,
                applied_count=0,
                skipped_count=0,
                reconstructed_hash="",
                expected_hash=expected_hash or "",
                detail="No mutations to replay.",
            )

        applied = 0
        skipped = 0
        entity_hashes: Dict[str, str] = {}

        for receipt in receipts:
            try:
                self._apply_receipt(receipt)
                applied += 1
                eh = self._graph.entity_hash(receipt.entity_id)
                if eh:
                    entity_hashes[receipt.entity_id] = eh
            except ValueError as temporal_exc:
                # PATCH P0-2: Distinguish temporal violations from other errors
                if self._strict_temporal_validation and "TEMPORAL ORDERING VIOLATION" in str(temporal_exc):
                    # In strict mode, temporal violations are fatal — re-raise immediately
                    raise
                # In lenient mode (production), log and skip
                logger.warning(
                    "MutationReplayer: could not apply receipt %s (%s): %s",
                    getattr(receipt, "receipt_id", "?"),
                    getattr(receipt, "entity_id", "?"),
                    temporal_exc,
                )
                skipped += 1
            except Exception as exc:
                # Other exceptions always logged and skipped (regardless of mode)
                logger.warning(
                    "MutationReplayer: could not apply receipt %s (%s): %s",
                    getattr(receipt, "receipt_id", "?"),
                    getattr(receipt, "entity_id", "?"),
                    exc,
                )
                skipped += 1

        reconstructed = self._graph.state_hash()

        # Derive expected hash if not provided:
        # chain-of-custody hash = sha256 of sorted receipt content_hashes
        if expected_hash is None:
            chain_input = json.dumps(
                sorted(getattr(r, "content_hash", "") for r in receipts)
            )
            expected_hash = hashlib.sha256(chain_input.encode()).hexdigest()

        # Determine status
        if skipped > 0 and applied == 0:
            status = ReplayStatus.PARTIAL
        elif skipped > 0:
            status = ReplayStatus.PARTIAL
        elif reconstructed == expected_hash:
            status = ReplayStatus.MATCH
        else:
            status = ReplayStatus.MISMATCH

        # Find mismatched entities (those whose receipt hash ≠ graph hash)
        mismatched: List[str] = []
        for receipt in receipts:
            eid = getattr(receipt, "entity_id", "")
            receipt_content = getattr(receipt, "content_hash", "")
            live = entity_hashes.get(eid, "")
            # A mismatch means the content_hash recorded at mutation time
            # no longer matches the reconstructed entity state.
            # For NODE_DELETE the entity may be tombstoned — that is expected.
            mutation_type = getattr(receipt, "mutation_type", None)
            mutation_val = getattr(mutation_type, "value", str(mutation_type))
            if mutation_val == "NODE_DELETE":
                continue  # tombstones do not carry property hash
            if receipt_content and live and receipt_content[:16] != live:
                mismatched.append(eid)

        detail_parts = [
            f"applied={applied}",
            f"skipped={skipped}",
            f"nodes_in_graph={self._graph.node_count}",
            f"active_nodes={self._graph.active_node_count}",
        ]
        if mismatched:
            detail_parts.append(f"mismatched_entities={mismatched}")

        return ReplayResult(
            status=status,
            mutation_count=len(receipts),
            applied_count=applied,
            skipped_count=skipped,
            reconstructed_hash=reconstructed,
            expected_hash=expected_hash,
            entity_hashes=entity_hashes,
            mismatched_entities=mismatched,
            detail="; ".join(detail_parts),
        )

    def _apply_receipt(self, receipt: Any) -> None:
        """Apply a single MutationReceipt to the in-memory graph.
        
        PATCH P0-2: Enforces temporal ordering constraints:
          - NODE_CREATE: Only if entity doesn't exist (prevents duplicate creates)
          - NODE_MERGE: Always allowed (idempotent by definition)
          - NODE_DELETE: Only if entity exists (prevents delete-before-create)
        """
        from mahoun.core.governance.mutation_boundary import MutationType

        mutation_type = getattr(receipt, "mutation_type", None)
        entity_id = getattr(receipt, "entity_id", "")
        label = getattr(receipt, "label", "Unknown")
        content_hash = getattr(receipt, "content_hash", "")

        if mutation_type is None:
            raise ValueError(f"Receipt has no mutation_type: {receipt!r}")

        mt_value = getattr(mutation_type, "value", str(mutation_type))

        # PATCH P0-2: Track mutation history for temporal validation
        if entity_id not in self._entity_lifecycle:
            self._entity_lifecycle[entity_id] = []
        
        history = self._entity_lifecycle[entity_id]
        node_exists = entity_id in self._graph._nodes and not self._graph._nodes[entity_id].get("_deleted", False)

        if mt_value in (MutationType.NODE_MERGE.value, "NODE_MERGE"):
            # MERGE is idempotent — always allowed
            self._graph.apply_node_merge(entity_id, label, content_hash)
            history.append("NODE_MERGE")

        elif mt_value in (MutationType.NODE_CREATE.value, "NODE_CREATE"):
            # PATCH P0-2: CREATE temporal constraint enforcement
            # Reject if node already exists (prevents duplicate creates)
            if node_exists:
                raise ValueError(
                    f"TEMPORAL ORDERING VIOLATION: NODE_CREATE for entity '{entity_id}' "
                    f"attempted but node already exists. History: {history}. "
                    f"This indicates either (1) duplicate CREATE receipts or "
                    f"(2) CREATE after MERGE without intervening DELETE."
                )
            
            # Reject if entity was previously created without deletion
            if "NODE_CREATE" in history and "NODE_DELETE" not in history[-len([h for h in history if h == "NODE_CREATE"]):]:
                raise ValueError(
                    f"TEMPORAL ORDERING VIOLATION: Duplicate NODE_CREATE for entity '{entity_id}'. "
                    f"History: {history}. A node may only be created once per lifecycle."
                )
            
            self._graph.apply_node_create(entity_id, label, content_hash)
            history.append("NODE_CREATE")

        elif mt_value in (MutationType.NODE_DELETE.value, "NODE_DELETE"):
            # PATCH P0-2: DELETE temporal constraint enforcement
            # Reject if node doesn't exist (prevents delete-before-create corruption)
            # Node must exist OR entity must have been created in this replay session
            entity_was_created = "NODE_CREATE" in history or "NODE_MERGE" in history
            
            if not node_exists and not entity_was_created:
                raise ValueError(
                    f"TEMPORAL ORDERING VIOLATION: NODE_DELETE for entity '{entity_id}' "
                    f"attempted but node does not exist and was never created in this replay session. "
                    f"History: {history}. This indicates DELETE before CREATE."
                )
            
            # Soft delete by default (MAHOUN constitution)
            self._graph.apply_node_delete(entity_id, soft=True)
            history.append("NODE_DELETE")

        elif mt_value in (
            MutationType.RELATIONSHIP_CREATE.value, "RELATIONSHIP_CREATE",
            MutationType.RELATIONSHIP_MERGE.value,  "RELATIONSHIP_MERGE",
        ):
            # Relationships don't carry node property data — skip state update
            # History tracking for relationships not implemented (not in scope for P0-2)
            pass

        else:
            raise ValueError(f"Unknown mutation type: {mt_value}")
