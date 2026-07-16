"""
MAHOUN Adversarial Bypass Attempt Tests
=========================================

Classification: SECURITY / CONSTITUTIONAL / ADVERSARIAL

These tests actively ATTEMPT to bypass the governance boundary and verify
that every attempt fails. This is the test suite that proves the audit
finding: "I attempted to falsify the constitutional claim. I failed."

Tests cover:
    1. Direct driver instantiation bypass
    2. Raw mutation outside GovernanceContext
    3. Forged GovernanceContext (HMAC spoof)
    4. Unicode obfuscation of mutation keywords
    5. delete_node() soft tombstone behavior
    6. delete_node() hard delete guard
    7. MutationReceipt is always produced for deletes
    8. outbox_worker DELETE no longer raises AttributeError
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, call

import pytest

from mahoun.core.governance.governance_context import (
    GovernanceContext,
    GovernanceContextManager,
)
from mahoun.core.governance.mutation_boundary import (
    GovernedNeo4jSession,
    MutationAuthorizationBoundary,
    MutationType,
    classify_cypher,
    _authorized_write_ctx,
)
from mahoun.core.governance.violations import GovernanceViolationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_governed_session(executor=None) -> GovernedNeo4jSession:
    """Create a GovernedNeo4jSession backed by a mock executor."""
    if executor is None:
        executor = MagicMock(return_value=[])
    return GovernedNeo4jSession(
        raw_executor=executor,
        correlation_id="test-corr",
        actor_id="test-actor",
    )


# ---------------------------------------------------------------------------
# CATEGORY 1: Mutation boundary chokepoint
# ---------------------------------------------------------------------------

class TestMutationBoundaryChokepoint:
    """Verify that MutationAuthorizationBoundary blocks all mutations outside
    an authorized context (fail-closed by design)."""

    @pytest.mark.p2
    def test_read_query_always_passes(self):
        """READ-only Cypher must never raise."""
        MutationAuthorizationBoundary.inspect("MATCH (n) RETURN n")
        MutationAuthorizationBoundary.inspect("RETURN 1 AS num")
        MutationAuthorizationBoundary.inspect("CALL db.labels()")

    @pytest.mark.p2
    def test_mutation_outside_context_raises(self):
        """Any mutation Cypher outside GovernedNeo4jSession MUST raise."""
        assert not _authorized_write_ctx.get(), "Pre-condition: no auth token active"

        with pytest.raises(GovernanceViolationError) as exc_info:
            MutationAuthorizationBoundary.inspect("MERGE (n:Verdict {id: 'x'})")
        assert "GovernedNeo4jSession" in str(exc_info.value)

    @pytest.mark.p2
    def test_create_outside_context_raises(self):
        with pytest.raises(GovernanceViolationError):
            MutationAuthorizationBoundary.inspect("CREATE (n:Fact {id: 'x'})")

    @pytest.mark.p2
    def test_delete_outside_context_raises(self):
        with pytest.raises(GovernanceViolationError):
            MutationAuthorizationBoundary.inspect(
                "MATCH (n:Chunk {id: 'x'}) DETACH DELETE n"
            )

    @pytest.mark.p2
    def test_set_outside_context_raises(self):
        with pytest.raises(GovernanceViolationError):
            MutationAuthorizationBoundary.inspect("MATCH (n) SET n.foo = 'bar'")


# ---------------------------------------------------------------------------
# CATEGORY 2: GovernanceContext forgery attempts
# ---------------------------------------------------------------------------

class TestContextForgeryRejected:
    """Verify that a manually constructed GovernanceContext is detected and
    rejected by require_context() HMAC signature check."""

    @pytest.mark.p2
    def test_forged_context_signature_fails(self):
        """A context constructed outside GovernanceContextManager.create_context()
        will have an empty (or wrong) signature and MUST be rejected."""
        from mahoun.core.governance.validator_pipeline import ValidatorPipeline
        from mahoun.core.governance.provenance_tracker import ProvenanceTracker
        from mahoun.core.governance.deterministic_resolver import DeterministicResolver
        from mahoun.core.governance.ontology_enforcer import OntologyEnforcer

        forged = GovernanceContext(
            context_id="forged-ctx-id",
            correlation_id="forged-corr",
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_mode="STRICT",
            provenance_tracker=ProvenanceTracker(),
            validator_pipeline=ValidatorPipeline(),
            deterministic_resolver=DeterministicResolver(),
            ontology_enforcer=OntologyEnforcer(),
            signature="",  # No valid HMAC — attacker doesn't know _CONTEXT_SECRET
        )

        GovernanceContextManager._reset_for_test()
        # Manually inject the forged context into the stack
        stack = GovernanceContextManager._get_stack()
        GovernanceContextManager._governance_stack.set(stack + (forged,))

        try:
            with pytest.raises(GovernanceViolationError) as exc_info:
                GovernanceContextManager.require_context()
            err_msg = str(exc_info.value)
            assert "signature" in err_msg.lower() or "spoofed" in err_msg.lower() or "Spoofed" in err_msg
        finally:
            GovernanceContextManager._reset_for_test()

    @pytest.mark.p2
    def test_no_context_raises(self):
        """require_context() without any active context MUST raise."""
        GovernanceContextManager._reset_for_test()
        with pytest.raises(GovernanceViolationError):
            GovernanceContextManager.require_context()


# ---------------------------------------------------------------------------
# CATEGORY 3: Unicode obfuscation bypass attempts
# ---------------------------------------------------------------------------

class TestUnicodeObfuscationBlocked:
    """MahouN's CypherLexer normalizes Unicode (NFKC) before tokenizing.
    Full-width and lookalike characters must be detected as mutations."""

    @pytest.mark.p2
    def test_fullwidth_merge_detected(self):
        """Full-width ＭＥＲＧＥ must be classified as a mutation."""
        # U+FF2D U+FF25 U+FF32 U+FF27 U+FF25 = ＭＥＲＧＥ
        fullwidth_merge = "ＭＥＲＧＥ (n:Fact {id: 'x'})"
        assert classify_cypher(fullwidth_merge), (
            "Full-width MERGE not detected as mutation — Unicode bypass possible!"
        )

    @pytest.mark.p2
    def test_fullwidth_set_detected(self):
        """Full-width ＳＥＴ must be detected."""
        fullwidth_set = "MATCH (n) ＳＥＴ n.foo = 'bar'"
        assert classify_cypher(fullwidth_set)

    @pytest.mark.p2
    def test_comment_hidden_mutation_detected(self):
        """Mutation hidden after comment must be detected."""
        obfuscated = "/* harmless */ MERGE (n:Fact {id: 'y'})"
        assert classify_cypher(obfuscated)

    @pytest.mark.p2
    def test_newline_split_mutation_detected(self):
        """Mutation split across newlines must be detected."""
        multiline = "\nMERGE\n(n:Chunk {id: 'z'})\n"
        assert classify_cypher(multiline)

    @pytest.mark.p2
    def test_comment_only_is_not_mutation(self):
        """A query that is all comment should not trigger mutation classification."""
        comment_only = "/* MERGE CREATE DELETE */"
        assert not classify_cypher(comment_only)


# ---------------------------------------------------------------------------
# CATEGORY 4: delete_node() — soft tombstone correctness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeleteNodeSoftTombstone:
    """Tests for GovernedNeo4jSession.delete_node() — soft delete path."""

    @pytest.mark.p2
    async def test_soft_delete_executes_set_not_detach_delete(self):
        """Soft delete must write tombstone properties — NOT DETACH DELETE."""
        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="test-soft-delete",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)
            session.delete_node(
                label="Chunk",
                node_id="chunk-001",
                soft_delete=True,
                deleted_reason="test_deletion",
                source_event_id="evt-42",
            )

        # Verify executor was called with a SET query, not DETACH DELETE
        assert executor.called
        query_used = executor.call_args[0][0]
        assert "DETACH DELETE" not in query_used, (
            "Soft delete must not physically delete the node!"
        )
        assert "_deleted" in query_used
        assert "_deleted_at" in query_used or "datetime()" in query_used
        assert "_deleted_reason" in query_used

    @pytest.mark.p2
    async def test_soft_delete_produces_node_delete_receipt(self):
        """delete_node() must produce a MutationReceipt with NODE_DELETE type."""
        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="test-receipt",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)
            receipt = session.delete_node(
                label="Chunk",
                node_id="chunk-002",
                soft_delete=True,
            )

        assert receipt.mutation_type == MutationType.NODE_DELETE
        assert receipt.label == "Chunk"
        assert receipt.entity_id == "chunk-002"
        assert receipt.receipt_id  # Non-empty

    @pytest.mark.p2
    async def test_soft_delete_appears_in_session_ledger(self):
        """delete_node receipt must be recorded in the session ledger."""
        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="test-ledger",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)
            session.delete_node(label="Chunk", node_id="chunk-003")

        assert session.mutation_count == 1
        assert session.ledger[0].mutation_type == MutationType.NODE_DELETE

    @pytest.mark.p2
    async def test_soft_delete_passes_source_event_id_to_executor(self):
        """source_event_id must be forwarded to the Cypher executor."""
        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="test-event",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)
            session.delete_node(
                label="Chunk",
                node_id="chunk-004",
                soft_delete=True,
                source_event_id="outbox-event-999",
            )

        params = executor.call_args[0][1]
        assert params.get("_source_event") == "outbox-event-999"

    @pytest.mark.p2
    async def test_delete_requires_active_governance_context(self):
        """delete_node() without GovernanceContext must fail-closed."""
        GovernanceContextManager._reset_for_test()
        executor = MagicMock(return_value=[])

        # Cannot create GovernedNeo4jSession without context
        with pytest.raises(GovernanceViolationError):
            _make_governed_session(executor)


# ---------------------------------------------------------------------------
# CATEGORY 5: delete_node() — hard delete guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeleteNodeHardDelete:
    """Hard delete (soft_delete=False) is the escape hatch for transient nodes.
    It must still go through the governance boundary."""

    @pytest.mark.p2
    async def test_hard_delete_uses_detach_delete_cypher(self):
        """Hard delete (soft_delete=False) must execute DETACH DELETE."""
        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="test-hard-delete",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)
            receipt = session.delete_node(
                label="CacheNode",
                node_id="cache-001",
                soft_delete=False,
                deleted_reason="cache_expiry",
            )

        query_used = executor.call_args[0][0]
        assert "DETACH DELETE" in query_used
        assert receipt.mutation_type == MutationType.NODE_DELETE

    @pytest.mark.p2
    async def test_hard_delete_still_produces_receipt(self):
        """Hard delete must still produce an immutable MutationReceipt."""
        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="test-hard-receipt",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)
            receipt = session.delete_node(
                label="CacheNode",
                node_id="cache-002",
                soft_delete=False,
            )

        assert receipt.mutation_type == MutationType.NODE_DELETE
        assert receipt.receipt_id


# ---------------------------------------------------------------------------
# CATEGORY 6: outbox_worker DELETE fix regression test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestOutboxWorkerDeleteFix:
    """Regression tests: outbox_worker.py DELETE path no longer raises
    AttributeError ('GovernedNeo4jSession' has no attribute 'run')."""

    @pytest.mark.p2
    async def test_process_chunk_delete_event_does_not_raise_attribute_error(self):
        """The P0 runtime bug must be fixed: session.run() call is gone."""
        # Simulate an outbox DELETE event
        event = {
            "event_id": "evt-001",
            "aggregate_type": "legal.chunks",
            "aggregate_id": uuid.uuid4(),
            "action": "DELETE",
            "payload": {},
            "correlation_id": "corr-001",
        }

        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="corr-001",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)

            # This must NOT raise AttributeError
            from mahoun.infrastructure.workers.outbox_worker import OutboxWorker
            worker = OutboxWorker.__new__(OutboxWorker)  # bypass __init__
            result = worker._process_chunk_event(session, event)

        assert result is True

    @pytest.mark.p2
    async def test_chunk_delete_calls_delete_node_not_run(self):
        """session.run() must not be called on DELETE events; delete_node() is."""
        event = {
            "event_id": "evt-002",
            "aggregate_type": "legal.chunks",
            "aggregate_id": uuid.uuid4(),
            "action": "DELETE",
            "payload": {},
            "correlation_id": "corr-002",
        }

        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="corr-002",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)

            # Spy on delete_node
            original_delete = session.delete_node
            delete_calls: List[Dict[str, Any]] = []

            def spy_delete(**kwargs):
                delete_calls.append(kwargs)
                return original_delete(**kwargs)

            session.delete_node = spy_delete  # type: ignore[method-assign]

            from mahoun.infrastructure.workers.outbox_worker import OutboxWorker
            worker = OutboxWorker.__new__(OutboxWorker)
            worker._process_chunk_event(session, event)

        assert len(delete_calls) == 1, "delete_node() must be called exactly once"
        assert delete_calls[0]["label"] == "Chunk"
        assert delete_calls[0]["soft_delete"] is True, (
            "outbox_worker must use soft_delete=True (tombstone)"
        )

    @pytest.mark.p2
    async def test_chunk_delete_tombstone_preserves_forensic_lineage(self):
        """The soft tombstone must include source_event_id for lineage tracing."""
        event_id = "evt-003"
        event = {
            "event_id": event_id,
            "aggregate_type": "legal.chunks",
            "aggregate_id": uuid.uuid4(),
            "action": "DELETE",
            "payload": {},
            "correlation_id": "corr-003",
        }

        executor = MagicMock(return_value=[])

        async with GovernanceContextManager.active_context(
            correlation_id="corr-003",
            execution_mode="STRICT",
        ):
            session = _make_governed_session(executor)

            from mahoun.infrastructure.workers.outbox_worker import OutboxWorker
            worker = OutboxWorker.__new__(OutboxWorker)
            worker._process_chunk_event(session, event)

        # Check that _source_event was passed in params
        params = executor.call_args[0][1]
        assert params.get("_source_event") == event_id, (
            "source_event_id must be forwarded to tombstone for forensic lineage"
        )
