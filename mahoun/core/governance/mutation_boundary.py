"""
MAHOUN Mutation Authorization Boundary
========================================

Classification: KERNEL / CONSTITUTIONAL / NON-BYPASSABLE

This module implements the hard governance boundary at the Neo4j write layer.

Architecture:
    ALL Cypher → MutationAuthorizationBoundary.inspect()
                        │
                  READ query?  ──YES──→ pass through
                        │NO
                  Called from GovernedNeo4jSession? ──YES──→ pass through
                        │NO
                        ▼
                GovernanceViolationError (fail-closed, unconditionally)

Invariants:
    1. No mutation Cypher (MERGE/CREATE/DELETE/SET) may execute without
       passing through GovernedNeo4jSession.
    2. GovernedNeo4jSession validates provenance and ontology via
       ValidatorPipeline BEFORE building Cypher.
    3. Every successful mutation produces an immutable MutationReceipt.
    4. No audit mode. No soft mode. No compatibility mode.
       Governance IS execution authority.

The system fails because governance BLOCKS it —
not because developers remembered to call validation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import contextvars
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Tuple

if TYPE_CHECKING:
    from mahoun.core.governance.protocols import RawQueryExecutor

from mahoun.core.governance.validator_pipeline import ValidatorPipeline, PipelineResult
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError, GovernanceViolation, ViolationSeverity, ViolationCategory

logger = logging.getLogger(__name__)

# ============================================================================
# IMMUTABLE GOVERNANCE AUDIT LOG (P0 requirement)
# ============================================================================

import os

_GOVERNANCE_AUDIT_PATH = "logs/governance.audit"
_REMOTE_LEDGER_MOCK_PATH = "logs/remote_immutable.ledger"


def _append_governance_audit(entry: dict[str, Any]) -> None:
    """
    Append an immutable, fsynced entry to the governance audit log.
    
    HARDENING V2: Dual-write strategy. 
    1. Local log (logs/governance.audit)
    2. Simulated Remote Immutable Ledger (logs/remote_immutable.ledger)

    This MUST succeed BEFORE any graph mutation is committed.
    Failure here causes the mutation to be rejected (fail-closed).
    """
    try:
        os.makedirs(os.path.dirname(_GOVERNANCE_AUDIT_PATH) or ".", exist_ok=True)
        line = json.dumps(entry, default=str, sort_keys=True) + "\n"
        
        # 1. Write to local audit
        with open(_GOVERNANCE_AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
            
        # 2. Write to REMOTE IMMUTABLE LEDGER (Simulated)
        # In production, this would be an API call to a tamper-proof service
        with open(_REMOTE_LEDGER_MOCK_PATH, "a", encoding="utf-8") as f:
            # Entry is signed with a simulated HSM key in real production
            entry_with_sig = {**entry, "hsm_signature": hashlib.sha256(line.encode()).hexdigest()}
            f.write(json.dumps(entry_with_sig, default=str, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
            
    except Exception as exc:
        # Fail-closed: audit append failure MUST block mutation
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.AUDIT_FAILURE,
                severity=ViolationSeverity.CRITICAL,
                message="GOVERNANCE AUDIT APPEND FAILED — mutation aborted",
                details={"error": str(exc), "audit_path": _GOVERNANCE_AUDIT_PATH},
                source="GovernedNeo4jSession._append_governance_audit",
            )
        ) from exc

# ---------------------------------------------------------------------------
# Cypher Lexer & Mutation Intent Classifier
# ---------------------------------------------------------------------------

class CypherLexer:
    """
    Robust tokenizer for Cypher queries that strips comments and handles
    whitespace-agnostic keyword detection.

    Architectural Mandate:
    Regex word-boundary checks are insufficient for kernel-level security.
    This lexer ensures that mutation intent is detected even if obfuscated
    by comments or unusual formatting.
    """
    
    # Keywords that signal a state-mutation operation.
    MUTATION_KEYWORDS = frozenset({
        "MERGE", "CREATE", "DELETE", "SET", "REMOVE", "DROP", "DETACH"
    })
    
    # Procedures that are strictly forbidden outside governed sessions
    # (or completely forbidden if they bypass governance entirely).
    FORBIDDEN_PROCEDURES = frozenset({
        "apoc", "dbms", "plugin", "custom"
    })

    @staticmethod
    def strip_comments(query: str) -> str:
        """Remove single-line (//) and multi-line (/* ... */) comments."""
        # Remove multi-line comments
        query = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
        # Remove single-line comments
        query = re.sub(r"//.*$", "", query, flags=re.MULTILINE)
        return query

    @classmethod
    def analyze_intent(cls, query: str) -> Tuple[bool, List[str]]:
        """
        Analyze Cypher query for mutation intent and forbidden procedures.
        
        HARDENING V2: Unicode Normalization
        Performs NFKC normalization to collapse Unicode variants (like ＳＥＴ)
        into their standard ASCII equivalents before tokenization.
        
        Returns:
            (is_mutation, violations)
        """
        # Step 1: Normalize Unicode (NFKC handles full-width, compatibility forms, etc.)
        normalized_query = unicodedata.normalize('NFKC', query)
        
        # Step 2: Strip comments from normalized query
        clean_query = cls.strip_comments(normalized_query)
        
        # Step 3: Tokenize by splitting on non-word characters while preserving dots for procedures
        tokens = re.findall(r"[\w\.]+", clean_query)
        
        is_mutation = False
        violations = []
        
        for token in tokens:
            upper_token = token.upper()
            
            # 1. Check for mutation keywords
            if upper_token in cls.MUTATION_KEYWORDS:
                is_mutation = True
                
            # 2. Check for forbidden procedure calls (e.g., CALL apoc.algo.path)
            if "." in token:
                prefix = token.split(".")[0].lower()
                if prefix in cls.FORBIDDEN_PROCEDURES:
                    violations.append(f"Forbidden procedure call: {token}")
        
        return is_mutation, violations


def classify_cypher(query: str) -> bool:
    """
    Return True if the query contains mutation intent or violations.
    Used by MutationAuthorizationBoundary.inspect().
    """
    is_mutation, violations = CypherLexer.analyze_intent(query)
    
    if violations:
        # Forbidden procedures trigger immediate mutation-class failure
        return True
        
    return is_mutation


# Queries that are always allowed regardless of caller
# (DDL health checks and schema reads only)
_WHITELIST_PATTERN = re.compile(
    r"^\s*RETURN\s+1|"
    r"^\s*CALL\s+db\.|"
    r"^\s*MATCH\b(?!.*\b(MERGE|CREATE|DELETE|SET|REMOVE)\b)",
    re.IGNORECASE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# Mutation Receipt
# ---------------------------------------------------------------------------

class MutationType(str, Enum):
    NODE_CREATE = "NODE_CREATE"
    NODE_MERGE = "NODE_MERGE"
    RELATIONSHIP_CREATE = "RELATIONSHIP_CREATE"
    RELATIONSHIP_MERGE = "RELATIONSHIP_MERGE"
    NODE_DELETE = "NODE_DELETE"


@dataclass(frozen=True)
class MutationReceipt:
    """Immutable forensic record for every governed graph mutation."""
    receipt_id: str
    mutation_type: MutationType
    label: str
    entity_id: str
    timestamp: str
    correlation_id: str
    content_hash: str
    pipeline_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "mutation_type": self.mutation_type.value,
            "label": self.label,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "content_hash": self.content_hash,
            "pipeline_hash": self.pipeline_hash,
        }


def _make_receipt(
    mutation_type: MutationType,
    label: str,
    entity_id: str,
    correlation_id: str,
    payload: Dict[str, Any],
    pipeline_hash: str,
) -> MutationReceipt:
    ts = datetime.now(timezone.utc).isoformat()
    canonical = json.dumps(payload, sort_keys=True, default=str)
    content_hash = hashlib.sha256(canonical.encode()).hexdigest()
    # Structural hash ONLY. Timestamp is recorded but NOT part of the execution identity.
    receipt_id = hashlib.sha256(
        f"{entity_id}:{content_hash}".encode()
    ).hexdigest()[:24]
    return MutationReceipt(
        receipt_id=receipt_id,
        mutation_type=mutation_type,
        label=label,
        entity_id=entity_id,
        timestamp=ts,
        correlation_id=correlation_id,
        content_hash=content_hash,
        pipeline_hash=pipeline_hash,
    )


# ---------------------------------------------------------------------------
# Mutation Authorization Boundary (constitutional checkpoint)
# ---------------------------------------------------------------------------

# ContextVar: safe for asyncio, completely isolates coroutines even on the same OS thread.
_authorized_write_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_authorized_write_ctx", default=False
)


def _is_authorized() -> bool:
    """True only when executing inside GovernedNeo4jSession."""
    return _authorized_write_ctx.get()


class MutationAuthorizationBoundary:
    """
    Constitutional checkpoint for ALL Cypher execution.

    This is NOT a helper. This is the execution authority.

    Called by Neo4jConnection._raw_execute() on EVERY query.
    Raises GovernanceViolationError unconditionally if:
        - The query contains mutation intent (MERGE/CREATE/DELETE/SET/REMOVE)
        - AND the caller is not inside an active GovernedNeo4jSession context

    Read-only queries always pass through.
    """

    @staticmethod
    def inspect(query: str) -> None:
        """
        Inspect a Cypher query for mutation intent.

        Raises:
            GovernanceViolationError: If mutation detected outside governed context.
        """
        if not classify_cypher(query):
            return  # Read-only — pass through

        if _is_authorized():
            return  # Inside GovernedNeo4jSession — pass through

        # Mutation outside governed context — CONSTITUTIONAL VIOLATION
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.ARCHITECTURE_BOUNDARY,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "ARCHITECTURAL VIOLATION: Mutation Cypher detected outside "
                    "GovernedNeo4jSession. Direct execution of MERGE/CREATE/"
                    "DELETE/SET is constitutionally forbidden. "
                    "All mutations must flow through GovernedNeo4jSession."
                ),
                details={"query_preview": query[:120]},
                source="MutationAuthorizationBoundary",
            )
        )


# ---------------------------------------------------------------------------
# GovernedNeo4jSession — the ONLY authorized write surface
# ---------------------------------------------------------------------------

class GovernedNeo4jSession:
    """
    The ONLY surface through which mutation Cypher may reach Neo4j.

    Callers do NOT get raw session access.
    They call typed write methods (write_node, write_relationship).
    Each call:
        1. Validates provenance via ValidatorPipeline (fail-closed)
        2. Validates ontology via ValidatorPipeline (fail-closed)
        3. Sets the thread-local authorization flag
        4. Executes the pre-built Cypher
        5. Clears the authorization flag
        6. Appends an immutable MutationReceipt to the ledger

    There is no path to execute raw mutation Cypher from outside this class.
    """

    def __init__(
        self,
        raw_executor: "RawQueryExecutor",  # Must be Neo4jConnection._raw_execute
        pipeline: Optional[ValidatorPipeline] = None,
        correlation_id: str = "",
        actor_id: str = "",
    ) -> None:
        # CRITICAL P0: Reject mutation surface creation if no GovernanceContext
        ctx = GovernanceContextManager.require_context()
        self._raw_executor = raw_executor
        self._pipeline = pipeline or ValidatorPipeline()

        # I3: correlation_id must be explicit — no silent "system" fallback
        resolved_correlation = correlation_id or ctx.correlation_id
        if not resolved_correlation or not resolved_correlation.strip():
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        "GovernedNeo4jSession requires an explicit correlation_id. "
                        "Silent fallback to 'system' is forbidden. "
                        "Every mutation must belong to an explicit execution chain."
                    ),
                    details={"correlation_id_provided": repr(correlation_id)},
                    source="GovernedNeo4jSession.__init__",
                )
            )
        self._correlation_id = resolved_correlation

        # I7: actor_id must be non-empty and non-whitespace
        resolved_actor = actor_id or getattr(ctx, "actor_id", "")
        if not resolved_actor or not resolved_actor.strip():
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        "GovernedNeo4jSession requires a non-empty actor_id. "
                        "Empty or whitespace actor_id corrupts the audit trail. "
                        "Every mutation must carry a verified actor identity."
                    ),
                    details={"actor_id_provided": repr(actor_id)},
                    source="GovernedNeo4jSession.__init__",
                )
            )
        self._actor_id = resolved_actor.strip()
        self._governance_scope_id = ctx.context_id
        self._ledger: List[MutationReceipt] = []

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    def write_node(
        self,
        label: str,
        node_data: Dict[str, Any],
        merge: bool = True,
    ) -> MutationReceipt:
        """
        Write a node through the governed boundary.

        Requires:
            - node_data["id"] — unique identifier
            - node_data["provenance"] — provenance metadata dict (or will be injected)

        CRITICAL ORDER (P0 TRANSACTIONAL GOVERNANCE ORDERING):
            1. governance validation (context + pipeline)
            2. provenance generation
            3. immutable audit append (must succeed or mutation aborts)
            4. graph mutation commit
            5. attestation finalization

        Raises:
            GovernanceViolationError: fail-closed on any violation.
        """
        # STEP 0: Node label allowlist enforcement (I4)
        # Import here to avoid circular import at module level.
        from mahoun.core.governance.validator_pipeline import validate_node_label
        validate_node_label(label, self._correlation_id)

        # STEP 1: Governance validation (already enforced at __init__ via require_context)
        ctx = GovernanceContextManager.require_context()

        # Ensure provenance is complete before validation.
        provenance_entry = node_data.get("provenance")
        source = "graph_mutation:write_node"
        if isinstance(provenance_entry, dict) and provenance_entry.get("source"):
            source = provenance_entry.get("source")

        generated_provenance = GovernanceContextManager.require_provenance(
            source=source,
            author=self._actor_id,
        ).to_dict()
        node_data["provenance"] = generated_provenance

        result = self._pipeline.validate_node_write(
            node_data, self._correlation_id
        )

        # STEP 1.5: Confidence-based quarantine routing
        confidence = node_data.get("confidence", 1.0)
        if isinstance(confidence, (int, float)) and confidence < 1.0:
            if not label.startswith("Quarantined"):
                original_label = label
                label = f"Quarantined{label}"
                logger.warning(
                    "[MAB] QUARANTINE: Node '%s' routed to quarantine label '%s' "
                    "(confidence=%.2f < 1.0, original_label='%s')",
                    node_data.get("id", "?"), label, confidence, original_label,
                )

        # STEP 2: Provenance generation (must succeed before audit/mutation)
        provenance = GovernanceContextManager.require_provenance(
            source=source,
            author=self._actor_id,
        )

        # Phase 2: Build Cypher (provenance stays out of graph properties)
        cypher_props = {k: v for k, v in node_data.items() if k != "provenance"}
        assignments = ", ".join(f"n.{k} = ${k}" for k in cypher_props)

        if merge:
            query = (
                f"MERGE (n:{label} {{id: $id}}) "
                f"ON CREATE SET n.created_at = datetime() "
                f"SET {assignments}, n.updated_at = datetime()"
            )
            m_type = MutationType.NODE_MERGE
        else:
            query = (
                f"CREATE (n:{label}) "
                f"SET {assignments}, n.created_at = datetime()"
            )
            m_type = MutationType.NODE_CREATE

        # STEP 3: Immutable audit append — FAILS CLOSED if this raises
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self._correlation_id,
            "governance_scope_id": self._governance_scope_id,
            "actor_id": self._actor_id,
            "provenance_hash": getattr(provenance, "provenance_hash", str(provenance)),
            "operation": "write_node",
            "label": label,
            "entity_id": str(node_data.get("id", "")),
            "query_preview": query[:200],
            "params_keys": list(cypher_props.keys()),
        }
        _append_governance_audit(audit_entry)

        # STEP 4: Execute under authorization (mutation only after audit success)
        self._execute_authorized(query, cypher_props)

        # Phase 4: Receipt
        receipt = _make_receipt(
            mutation_type=m_type,
            label=label,
            entity_id=str(node_data.get("id", "")),
            correlation_id=self._correlation_id,
            payload=node_data,
            pipeline_hash=result.pipeline_hash,
        )
        self._ledger.append(receipt)
        logger.info(
            "[MAB] Node write authorized: %s/%s receipt=%s",
            label, node_data.get("id"), receipt.receipt_id,
        )
        return receipt

    def write_relationship(
        self,
        source_type: str,
        source_id: str,
        relationship_type: str,
        target_type: str,
        target_id: str,
        rel_data: Dict[str, Any],
        merge: bool = True,
    ) -> MutationReceipt:
        """
        Write a relationship through the governed boundary.

        Requires:
            - rel_data["provenance"] — provenance metadata dict
            - relationship_type must be in OntologyEnforcer ruleset

        CRITICAL ORDER (P0 TRANSACTIONAL GOVERNANCE ORDERING):
            1. governance validation
            2. provenance generation
            3. immutable audit append (must succeed)
            4. graph mutation
            5. attestation

        Raises:
            GovernanceViolationError: fail-closed on any violation.
        """
        # STEP 1: Governance validation
        ctx = GovernanceContextManager.require_context()

        # Ensure provenance entry is complete before validation.
        provenance_entry = rel_data.get("provenance")
        source = "graph_mutation:write_relationship"
        if isinstance(provenance_entry, dict) and provenance_entry.get("source"):
            source = provenance_entry.get("source")

        generated_provenance = GovernanceContextManager.require_provenance(
            source=source,
            author=self._actor_id,
        ).to_dict()
        rel_data["provenance"] = generated_provenance

        result = self._pipeline.validate_relationship_write(
            source_type=source_type,
            relationship_type=relationship_type,
            target_type=target_type,
            relationship_data=rel_data,
            correlation_id=self._correlation_id,
        )

        # STEP 2: Provenance generation
        provenance = GovernanceContextManager.require_provenance(
            source=source,
            author=self._actor_id,
        )

        # Phase 2: Build Cypher
        cypher_props = {k: v for k, v in rel_data.items() if k != "provenance"}
        assignments = ", ".join(f"r.{k} = ${k}" for k in cypher_props)
        set_clause = f"SET {assignments}" if assignments else ""

        if merge:
            query = (
                f"MATCH (a:{source_type} {{id: $__src}}) "
                f"MATCH (b:{target_type} {{id: $__tgt}}) "
                f"MERGE (a)-[r:{relationship_type}]->(b) "
                f"ON CREATE SET r.created_at = datetime() "
                f"{set_clause}"
            )
            m_type = MutationType.RELATIONSHIP_MERGE
        else:
            query = (
                f"MATCH (a:{source_type} {{id: $__src}}) "
                f"MATCH (b:{target_type} {{id: $__tgt}}) "
                f"CREATE (a)-[r:{relationship_type}]->(b) "
                f"SET r.created_at = datetime() {set_clause}"
            )
            m_type = MutationType.RELATIONSHIP_CREATE

        params = {"__src": source_id, "__tgt": target_id, **cypher_props}

        # STEP 3: Immutable audit append — must succeed or abort
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self._correlation_id,
            "governance_scope_id": self._governance_scope_id,
            "actor_id": self._actor_id,
            "provenance_hash": getattr(provenance, "provenance_hash", str(provenance)),
            "operation": "write_relationship",
            "relationship_type": relationship_type,
            "source": f"{source_type}/{source_id}",
            "target": f"{target_type}/{target_id}",
            "query_preview": query[:200],
        }
        _append_governance_audit(audit_entry)

        # STEP 4: Execute under authorization
        self._execute_authorized(query, params)

        # Phase 4: Receipt
        receipt = _make_receipt(
            mutation_type=m_type,
            label=relationship_type,
            entity_id=f"{source_id}->{target_id}",
            correlation_id=self._correlation_id,
            payload=rel_data,
            pipeline_hash=result.pipeline_hash,
        )
        self._ledger.append(receipt)
        logger.info(
            "[MAB] Relationship write authorized: %s-[%s]->%s receipt=%s",
            source_type, relationship_type, target_type, receipt.receipt_id,
        )
        return receipt

    def delete_node(
        self,
        label: str,
        node_id: str,
        soft_delete: bool = True,
        deleted_reason: str = "governance_delete",
        source_event_id: str = "",
    ) -> MutationReceipt:
        """
        Delete a node through the governed boundary.

        Philosophy (Soft-Delete First):
            MahouN is built on Provenance, Auditability, Receipts, Ledger,
            Forensics, and Governance. Physical deletion destroys forensic
            history and breaks the audit chain. Soft delete is therefore the
            default and preferred path for all governed entities.

        Args:
            label:            Node label (e.g., "Chunk", "Verdict")
            node_id:          Unique identifier of the node
            soft_delete:      True  → Tombstone (sets _deleted=True, preserves node)
                              False → DETACH DELETE (irreversible — use only for
                                      transient/cache nodes, never for legal evidence)
            deleted_reason:   Human-readable reason recorded in the tombstone
            source_event_id:  Outbox/event ID that triggered this delete (for lineage)

        Tombstone properties written (soft_delete=True):
            _deleted        = true
            _deleted_at     = datetime()   (ISO timestamp)
            _deleted_reason = $reason
            _deleted_by     = <actor_id>
            _source_event   = $event_id    (empty string if not provided)

        G3 Invariant:
            Deleted entities CANNOT be resurrected unless formally re-admitted.
            Soft delete respects this by keeping the tombstone in the graph so
            that all receipts and provenances that reference the node remain valid.

        Returns:
            MutationReceipt with mutation_type=NODE_DELETE

        Raises:
            GovernanceViolationError: fail-closed on any violation.
        """
        # STEP 1: Governance validation
        ctx = GovernanceContextManager.require_context()

        # STEP 2: Provenance generation
        provenance = GovernanceContextManager.require_provenance(
            source="graph_mutation:delete_node",
            author=self._actor_id,
        )

        if soft_delete:
            # Tombstone — node stays, but is permanently marked _deleted
            query = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"SET n._deleted = true, "
                f"    n._deleted_at = datetime(), "
                f"    n._deleted_reason = $_deleted_reason, "
                f"    n._deleted_by = $_deleted_by, "
                f"    n._source_event = $_source_event, "
                f"    n.updated_at = datetime()"
            )
            params: Dict[str, Any] = {
                "id": node_id,
                "_deleted_reason": deleted_reason,
                "_deleted_by": self._actor_id,
                "_source_event": source_event_id,
            }
        else:
            # Hard delete — physically removes node and all its relationships.
            # ONLY for transient/cache nodes. NOT appropriate for legal evidence,
            # verdicts, facts, or any entity with provenance lineage.
            query = f"MATCH (n:{label} {{id: $id}}) DETACH DELETE n"
            params = {"id": node_id}

        # STEP 3: Immutable audit append — FAILS CLOSED if this raises
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self._correlation_id,
            "governance_scope_id": self._governance_scope_id,
            "actor_id": self._actor_id,
            "provenance_hash": getattr(provenance, "provenance_hash", str(provenance)),
            "operation": "delete_node",
            "mode": "soft_tombstone" if soft_delete else "hard_detach_delete",
            "label": label,
            "entity_id": node_id,
            "deleted_reason": deleted_reason,
            "source_event_id": source_event_id,
            "query_preview": query[:200],
        }
        _append_governance_audit(audit_entry)

        # STEP 4: Execute under authorization token
        self._execute_authorized(query, params)

        # STEP 5: Mint immutable receipt
        receipt_payload: Dict[str, Any] = {
            "id": node_id,
            "label": label,
            "mode": "soft_tombstone" if soft_delete else "hard_detach_delete",
            "deleted_reason": deleted_reason,
            "source_event_id": source_event_id,
        }
        receipt = _make_receipt(
            mutation_type=MutationType.NODE_DELETE,
            label=label,
            entity_id=node_id,
            correlation_id=self._correlation_id,
            payload=receipt_payload,
            pipeline_hash=ValidatorPipeline._compute_hash(receipt_payload),
        )
        self._ledger.append(receipt)
        logger.info(
            "[MAB] Node delete authorized: %s/%s mode=%s receipt=%s",
            label, node_id,
            "soft_tombstone" if soft_delete else "hard_detach_delete",
            receipt.receipt_id,
        )
        return receipt

    # ------------------------------------------------------------------
    # Batch / Transaction
    # ------------------------------------------------------------------

    def begin_transaction(self) -> "GovernedWriteTransaction":

        """Begin an atomic governed transaction.

        Validates ALL queued mutations before executing ANY.
        """
        return GovernedWriteTransaction(session=self)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    @property
    def ledger(self) -> Tuple[MutationReceipt, ...]:
        """Immutable view of all mutation receipts."""
        return tuple(self._ledger)

    @property
    def mutation_count(self) -> int:
        return len(self._ledger)

    # ------------------------------------------------------------------
    # Internal — authorization token management
    # ------------------------------------------------------------------

    def _execute_authorized(self, query: str, params: Dict[str, Any]) -> List[Any]:
        """Execute mutation Cypher under the authorization token.

        Sets contextvar flag → executes → resets flag.
        The token is managed contextually — it cannot leak across async boundaries.
        """
        token = _authorized_write_ctx.set(True)
        try:
            return self._raw_executor(query, params)
        finally:
            _authorized_write_ctx.reset(token)


# ---------------------------------------------------------------------------
# GovernedWriteTransaction — validate-all-then-execute-all
# ---------------------------------------------------------------------------

class GovernedWriteTransaction:
    """Atomic governed transaction.

    Phase 1 — Validation: every queued mutation validated via pipeline.
               If ANY fails → abort entire transaction → zero DB writes.
    Phase 2 — Execution: all validated mutations executed sequentially.

    This is the only safe way to perform multi-mutation batch writes.
    """

    def __init__(self, session: GovernedNeo4jSession) -> None:
        self._session = session
        self._committed = False
        self._aborted = False
        # Each pending item: (validate_fn, execute_fn, meta)
        self._pending: List[Tuple[Any, Any, Dict[str, Any]]] = []

    def queue_node(
        self,
        label: str,
        node_data: Dict[str, Any],
        merge: bool = True,
    ) -> None:
        self._check_open()
        GovernanceContextManager.require_context()

        def validate():
            return self._session._pipeline.validate_node_write(
                node_data, self._session._correlation_id
            )

        def execute():
            cypher_props = {k: v for k, v in node_data.items() if k != "provenance"}
            assignments = ", ".join(f"n.{k} = ${k}" for k in cypher_props)
            op = "MERGE" if merge else "CREATE"
            if merge:
                query = (
                    f"{op} (n:{label} {{id: $id}}) "
                    f"ON CREATE SET n.created_at = datetime() "
                    f"SET {assignments}, n.updated_at = datetime()"
                )
            else:
                query = f"{op} (n:{label}) SET {assignments}, n.created_at = datetime()"
            self._session._execute_authorized(query, cypher_props)

        self._pending.append((
            validate, execute,
            {"type": "node", "label": label, "data": node_data,
             "m_type": MutationType.NODE_MERGE if merge else MutationType.NODE_CREATE},
        ))

    def queue_relationship(
        self,
        source_type: str,
        source_id: str,
        relationship_type: str,
        target_type: str,
        target_id: str,
        rel_data: Dict[str, Any],
        merge: bool = True,
    ) -> None:
        self._check_open()
        GovernanceContextManager.require_context()

        def validate():
            return self._session._pipeline.validate_relationship_write(
                source_type=source_type,
                relationship_type=relationship_type,
                target_type=target_type,
                relationship_data=rel_data,
                correlation_id=self._session._correlation_id,
            )

        def execute():
            cypher_props = {k: v for k, v in rel_data.items() if k != "provenance"}
            assignments = ", ".join(f"r.{k} = ${k}" for k in cypher_props)
            set_clause = f"SET {assignments}" if assignments else ""
            op = "MERGE" if merge else "CREATE"
            if merge:
                query = (
                    f"MATCH (a:{source_type} {{id: $__src}}) "
                    f"MATCH (b:{target_type} {{id: $__tgt}}) "
                    f"{op} (a)-[r:{relationship_type}]->(b) "
                    f"ON CREATE SET r.created_at = datetime() {set_clause}"
                )
            else:
                query = (
                    f"MATCH (a:{source_type} {{id: $__src}}) "
                    f"MATCH (b:{target_type} {{id: $__tgt}}) "
                    f"{op} (a)-[r:{relationship_type}]->(b) "
                    f"SET r.created_at = datetime() {set_clause}"
                )
            params = {"__src": source_id, "__tgt": target_id, **cypher_props}
            self._session._execute_authorized(query, params)

        self._pending.append((
            validate, execute,
            {
                "type": "relationship", "label": relationship_type,
                "data": rel_data,
                "m_type": MutationType.RELATIONSHIP_MERGE if merge else MutationType.RELATIONSHIP_CREATE,
                "entity_id": f"{source_id}->{target_id}",
            },
        ))

    def commit(self) -> Tuple[MutationReceipt, ...]:
        """Validate ALL, then execute ALL. Atomic fail-closed semantics."""
        self._check_open()
        GovernanceContextManager.require_context()

        # Phase 1: Validate every pending mutation
        pipeline_results = []
        for validate_fn, _, _ in self._pending:
            pipeline_results.append(validate_fn())  # raises on violation

        logger.info("[TX] %d mutations validated. Executing.", len(self._pending))

        # Phase 2: Execute and mint receipts
        receipts: List[MutationReceipt] = []
        for i, (_, execute_fn, meta) in enumerate(self._pending):
            execute_fn()
            receipt = _make_receipt(
                mutation_type=meta["m_type"],
                label=meta["label"],
                entity_id=meta.get("entity_id", str(meta["data"].get("id", ""))),
                correlation_id=self._session._correlation_id,
                payload=meta["data"],
                pipeline_hash=pipeline_results[i].pipeline_hash,
            )
            receipts.append(receipt)
            self._session._ledger.append(receipt)

        self._committed = True
        return tuple(receipts)

    def abort(self) -> None:
        self._aborted = True
        self._pending.clear()

    @property
    def is_open(self) -> bool:
        return not self._committed and not self._aborted

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def _check_open(self) -> None:
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._aborted:
            raise RuntimeError("Transaction already aborted")
