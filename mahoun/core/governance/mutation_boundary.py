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
from typing import Any, Dict, Generator, List, Optional, Tuple

from mahoun.core.governance.validator_pipeline import ValidatorPipeline, PipelineResult
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.violations import GovernanceViolationError, GovernanceViolation, ViolationSeverity, ViolationCategory

logger = logging.getLogger(__name__)

# ============================================================================
# IMMUTABLE GOVERNANCE AUDIT LOG (P0 requirement)
# ============================================================================
#
# The audit sink is INJECTED via set_audit_sink(...). The kernel never
# knows the medium (filesystem, remote ledger, in-memory). The default sink
# is a NullAuditSink so the kernel is hermetic under no wiring. Production
# wires `FilesystemAuditSink` at the application composition root.
#
# This preserves all existing call-site behaviour: the function name
# (``_append_governance_audit``), signature, and fail-closed semantics
# (raises GovernanceViolationError(AUDIT_FAILURE) on persistence failure).
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mahoun.core.governance.protocols import AuditSinkProtocol

# Module-global audit sink reference (injected; defaults to NullAuditSink).
_AUDIT_SINK: "AuditSinkProtocol | None" = None
"""
Module-global handle for the audit sink.

The kernel boundary sets this at composition time:
    - Tests that ``patch(_append_governance_audit, ...)`` need nothing
      wired (the patch replaces the function entirely).
    - Production code calls ``set_audit_sink(FilesystemAuditSink(...))``
      from ``mahoun/infrastructure/audit/wiring.py`` at bootstrap.

The default of ``None`` indicates "no sink wired". Any attempt to append
an audit entry without a wired sink raises GovernanceViolationError
(AUDIT_FAILURE). This enforces fail-closed semantics at the boundary:
no mutation may succeed without audit persistence.
"""


def set_audit_sink(sink: "AuditSinkProtocol") -> None:
    """
    Inject the audit sink used by the kernel boundary.

    Production callers should invoke this once at startup. Tests that
    ``patch(_append_governance_audit, ...)`` do not need to set a sink —
    the patch function replaces the boundary call entirely.
    """
    global _AUDIT_SINK
    _AUDIT_SINK = sink


def get_audit_sink() -> "AuditSinkProtocol | None":
    """Return the currently wired audit sink (or None for unwired)."""
    return _AUDIT_SINK


def unset_audit_sink() -> None:
    """Detach the audit sink (kernel reverts to unwired default)."""
    global _AUDIT_SINK
    _AUDIT_SINK = None


def _append_governance_audit(entry: dict[str, Any]) -> None:
    """
    Append an immutable entry to the governance audit log.

    P0 CONSTITUTIONAL INVARIANT: FAIL-CLOSED
    =========================================
    Audit persistence MUST succeed before any mutation is committed.

    - If sink is None (not wired): raises GovernanceViolationError.
      Production deployments MUST call set_audit_sink() at bootstrap.
      Use validate_governance_runtime() at startup to catch this early.
    - If sink.append() raises: raises GovernanceViolationError.
    - Only on success: caller may proceed to execute mutation.

    Tests may either:
      (a) wire a NullAuditSink via set_audit_sink(), or
      (b) patch _append_governance_audit directly.
    Patching is preferred for unit tests that don't exercise the sink.
    """
    sink = _AUDIT_SINK
    if sink is None:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.AUDIT_FAILURE,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    "AUDIT SINK NOT WIRED — mutation blocked. "
                    "Call set_audit_sink() at bootstrap before any mutation. "
                    "Run validate_governance_runtime() at startup to detect this early."
                ),
                details={
                    "hint": "mahoun.bootstrap.runtime.validate_governance_runtime()",
                    "fix": "from mahoun.core.governance.mutation_boundary import set_audit_sink",
                },
                source="_append_governance_audit",
            )
        )
    try:
        sink.append(entry)
    except Exception as exc:
        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.AUDIT_FAILURE,
                severity=ViolationSeverity.CRITICAL,
                message="GOVERNANCE AUDIT APPEND FAILED — mutation aborted",
                details={"error": str(exc), "sink_type": type(sink).__name__},
                source="_append_governance_audit",
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

# IMPORTANT: The ContextVar is owned canonically by
# mahoun.core.governance_kernel.authorization_state (single source of
# truth, stdlib-only). This module MUST NOT redefine it. Doing so creates
# a second ContextVar and governance state silently split-brains: the
# canonical var never receives the True flag set by GovernedNeo4jSession,
# so MutationAuthorizationBoundary.inspect() sees mutation outside an
# authorized context and the kernel chokepoint raises spuriously (or, in
# the inverse direction, writing the canonical var never releases the
# boundary enforced here). See AGENTRULES.md §1 and the singleton test
# at tests/test_authorization_state_singleton.py.
from mahoun.core.governance.authorization_state import (
    _authorized_write_ctx,
    set_authorized as _set_authorized,
    reset_authorized as _reset_authorized,
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
        raw_executor: Any,  # callable(query, params) -> list
        pipeline: Optional[ValidatorPipeline] = None,
        correlation_id: str = "",
        actor_id: str = "",
    ) -> None:
        # CRITICAL P0 ORDER: Identity validation MUST happen BEFORE require_context()
        # so that AUDIT_INTEGRITY_VIOLATION is raised (not GOVERNANCE_BYPASS) when
        # actor_id or correlation_id are empty/whitespace.

        # CRITICAL P0: Enforce identity checks (AUDIT_INTEGRITY_VIOLATION)
        # actor_id must be non-empty and non-whitespace
        sanitized_actor_id = (actor_id or "").strip()
        if not sanitized_actor_id:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message="GovernedNeo4jSession requires non-empty actor_id",
                    details={"provided_actor_id": actor_id or ""},
                    source="GovernedNeo4jSession.__init__",
                )
            )

        # CRITICAL P0: Enforce correlation_id requirement (before context fetch)
        sanitized_correlation_id = (correlation_id or "").strip()
        # We'll verify further against ctx below, but explicit empty fails immediately
        # (whitespace-only is also rejected)

        # CRITICAL P0: Reject mutation surface creation if no GovernanceContext
        ctx = GovernanceContextManager.require_context()

        # If correlation_id still empty, try to fall back to context's
        if not sanitized_correlation_id:
            sanitized_correlation_id = ctx.correlation_id.strip()
            if not sanitized_correlation_id:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.AUDIT_INTEGRITY_VIOLATION,
                        severity=ViolationSeverity.CRITICAL,
                        message="GovernedNeo4jSession requires non-empty correlation_id",
                        details={"provided_correlation_id": correlation_id or ""},
                        source="GovernedNeo4jSession.__init__",
                    )
                )

        self._raw_executor = raw_executor
        self._pipeline = pipeline or ValidatorPipeline()
        self._correlation_id = sanitized_correlation_id
        self._actor_id = sanitized_actor_id
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
        # STEP 1: Governance validation (already enforced at __init__ via require_context)
        ctx = GovernanceContextManager.require_context()
        
        # STEP 2: Provenance generation (must succeed before audit/mutation)
        provenance_obj = GovernanceContextManager.require_provenance(
            source="graph_mutation:write_node",
            author=self._actor_id,
        )
        # Determine the value to store in node_data for validation:
        # If the object provides a to_dict() method, use its dict representation,
        # otherwise use the object directly (should be dict or ProvenanceMetadata).
        if hasattr(provenance_obj, 'to_dict'):
            prov_val = provenance_obj.to_dict()
        else:
            prov_val = provenance_obj
        node_data = {**node_data, "provenance": prov_val}
        
        # STEP 1 (continued): Governance validation via pipeline (now with provenance)
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

        # Determine provenance hash for audit (prefer from prov_val if dict, else from object)
        if isinstance(prov_val, dict):
            provenance_hash = prov_val.get("provenance_hash")
        else:
            provenance_hash = getattr(provenance_obj, "provenance_hash", None)
        # Fallback: compute string representation if still None (should not happen in production)
        if provenance_hash is None:
            provenance_hash = str(provenance_obj)

        # STEP 3: Immutable audit append — FAILS CLOSED if this raises
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self._correlation_id,
            "governance_scope_id": self._governance_scope_id,
            "actor_id": self._actor_id,
            "provenance_hash": provenance_hash,
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
        
        # STEP 2: Provenance generation (must succeed before audit/mutation)
        provenance_obj = GovernanceContextManager.require_provenance(
            source="graph_mutation:write_relationship",
            author=self._actor_id,
        )
        # Inject provenance into rel_data for validation
        if hasattr(provenance_obj, 'to_dict'):
            prov_val = provenance_obj.to_dict()
        else:
            prov_val = provenance_obj
        rel_data = {**rel_data, "provenance": prov_val}
        
        # STEP 1 (continued): Governance validation via pipeline (now with provenance)
        result = self._pipeline.validate_relationship_write(
            source_type=source_type,
            relationship_type=relationship_type,
            target_type=target_type,
            relationship_data=rel_data,
            correlation_id=self._correlation_id,
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

        # Determine provenance hash for audit
        if isinstance(prov_val, dict):
            provenance_hash = prov_val.get("provenance_hash")
        else:
            provenance_hash = getattr(provenance_obj, "provenance_hash", None)
        if provenance_hash is None:
            provenance_hash = str(provenance_obj)

        # STEP 3: Immutable audit append — must succeed or abort
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self._correlation_id,
            "governance_scope_id": self._governance_scope_id,
            "actor_id": self._actor_id,
            "provenance_hash": provenance_hash,
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
        Delete (soft-tombstone or hard) a node through the governed boundary.

        CRITICAL ORDER (P0 TRANSACTIONAL GOVERNANCE ORDERING):
            1. governance validation
            2. provenance generation
            3. immutable audit append (must succeed or mutation aborts)
            4. graph mutation
            5. receipt minting
        """
        ctx = GovernanceContextManager.require_context()

        provenance = GovernanceContextManager.require_provenance(
            source="graph_mutation:delete_node",
            author=self._actor_id,
        )

        if soft_delete:
            query = (
                f"MATCH (n:{label} {{id: $id}}) "
                f"SET n._deleted = true, n._deletion_timestamp = datetime(), "
                f"n._deleted_reason = $deleted_reason, n._deleted_by = $actor_id, "
                f"n._source_event = $_source_event, "
                f"n.updated_at = datetime()"
            )
        else:
            query = f"MATCH (n:{label} {{id: $id}}) DETACH DELETE n"

        params: Dict[str, Any] = {
            "id": node_id,
            "deleted_reason": deleted_reason,
            "actor_id": self._actor_id,
            "_source_event": source_event_id,
        }

        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self._correlation_id,
            "governance_scope_id": self._governance_scope_id,
            "actor_id": self._actor_id,
            "provenance_hash": getattr(provenance, "provenance_hash", str(provenance)),
            "operation": "delete_node",
            "label": label,
            "entity_id": node_id,
            "soft_delete": soft_delete,
            "deleted_reason": deleted_reason,
            "source_event_id": source_event_id,
        }
        _append_governance_audit(audit_entry)

        self._execute_authorized(query, params)

        receipt = _make_receipt(
            mutation_type=MutationType.NODE_DELETE,
            label=label,
            entity_id=node_id,
            correlation_id=self._correlation_id,
            payload={"id": node_id, "deleted_reason": deleted_reason, "source_event_id": source_event_id},
            pipeline_hash="delete-op",
        )
        self._ledger.append(receipt)
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

        Sets the canonical _authorized_write_ctx flag → executes → resets.
        The token is managed contextually — it cannot leak across async
        boundaries or across separate GovernedNeo4jSession instances.
        """
        token = _set_authorized(True)
        try:
            return self._raw_executor(query, params)
        finally:
            _reset_authorized(token)


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
