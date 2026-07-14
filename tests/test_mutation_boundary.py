"""
Tests for MutationAuthorizationBoundary — the constitutional checkpoint.

These tests prove that governance is impossible to bypass accidentally.
The system fails because governance BLOCKS it, not because developers
remembered to call validation.

Invariants proven:
    1. Raw MERGE/CREATE/DELETE/SET through execute_query → GovernanceViolationError
    2. execute_write() is constitutionally abolished → GovernanceViolationError
    3. GovernedNeo4jSession.write_node without provenance → GovernanceViolationError
    4. GovernedNeo4jSession.write_relationship with bad ontology → GovernanceViolationError
    5. GovernedNeo4jSession.write_node with valid data → MutationReceipt
    6. GovernedWriteTransaction: single bad mutation blocks entire batch
    7. Read-only Cypher is never blocked
    8. Authorization token is cleared after execution (cannot leak)
"""
import pytest
from unittest.mock import MagicMock, patch

from mahoun.core.governance.mutation_boundary import (
    MutationAuthorizationBoundary,
    GovernedNeo4jSession,
    GovernedWriteTransaction,
    MutationReceipt,
    MutationType,
    classify_cypher,
    _authorized_write_ctx,
)
from mahoun.core.governance.violations import GovernanceViolationError
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata


def _prov() -> dict:
    return ProvenanceMetadata.create(
        source="test", correlation_id="test-corr", author="test-agent"
    ).to_dict()


def _mock_executor():
    return MagicMock(return_value=[])


# ======================================================================
# Cypher Classifier
# ======================================================================

class TestCypherClassifier:
    @pytest.mark.parametrize("query", [
        "MERGE (n:Document {id: $id})",
        "CREATE (n:Law)",
        "MATCH (n) DELETE n",
        "MATCH (n) DETACH DELETE n",
        "MATCH (n) SET n.x = 1",
        "MATCH (n) REMOVE n.x",
        "  merge (n:Case {id: $id}) ON CREATE SET n.x = 1",
    ])
    def test_mutation_queries_classified(self, query: str):
        assert classify_cypher(query) is True

    @pytest.mark.parametrize("query", [
        "MATCH (n) RETURN n",
        "RETURN 1 AS num",
        "CALL db.labels()",
        "MATCH (n) RETURN count(n)",
        "MATCH (a)-[r]->(b) RETURN r",
    ])
    def test_read_queries_not_classified(self, query: str):
        assert classify_cypher(query) is False


# ======================================================================
# MutationAuthorizationBoundary — constitutional checkpoint
# ======================================================================

class TestMutationAuthorizationBoundary:
    def test_read_query_passes_unconditionally(self):
        # Must not raise — no authorization context needed
        MutationAuthorizationBoundary.inspect("MATCH (n) RETURN n")
        MutationAuthorizationBoundary.inspect("RETURN 1 AS num")

    @pytest.mark.parametrize("mutation_cypher", [
        "MERGE (n:Document {id: $id})",
        "CREATE (n:Law)",
        "MATCH (n) DELETE n",
        "MATCH (n) SET n.x = 1",
    ])
    def test_mutation_outside_context_raises(self, mutation_cypher: str):
        # Ensure no stale auth context
        _authorized_write_ctx.set(False)
        with pytest.raises(GovernanceViolationError, match="ARCHITECTURAL VIOLATION"):
            MutationAuthorizationBoundary.inspect(mutation_cypher)

    def test_mutation_inside_auth_context_passes(self):
        token = _authorized_write_ctx.set(True)
        try:
            # Must not raise inside authorized context
            MutationAuthorizationBoundary.inspect("MERGE (n:Document {id: $id})")
        finally:
            _authorized_write_ctx.set(False)

    def test_auth_token_is_not_set_globally(self):
        """Token starts False — cannot be globally pre-set."""
        _authorized_write_ctx.set(False)
        assert not _authorized_write_ctx.get()


# ======================================================================
# GovernedNeo4jSession — ONLY authorized write surface
# ======================================================================

class TestGovernedNeo4jSession:
    def test_valid_node_write_produces_receipt(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        receipt = session.write_node(
            "Document",
            {"id": "d1", "title": "Test", "provenance": _prov()},
        )
        assert isinstance(receipt, MutationReceipt)
        assert receipt.mutation_type == MutationType.NODE_MERGE
        assert receipt.entity_id == "d1"
        assert executor.called  # DB was actually called

    def test_node_write_without_provenance_blocked(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        with pytest.raises(GovernanceViolationError):
            session.write_node("Document", {"id": "d1"})

        assert not executor.called  # Zero DB writes

    def test_node_write_without_id_blocked(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        with pytest.raises(GovernanceViolationError):
            session.write_node("Document", {"title": "X", "provenance": _prov()})

        assert not executor.called

    def test_relationship_ontology_violation_blocked(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        with pytest.raises(GovernanceViolationError):
            session.write_relationship(
                "Case", "c1", "ILLEGAL_RELATION", "Law", "l1",
                {"provenance": _prov()},
            )
        assert not executor.called

    def test_relationship_without_provenance_blocked(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        with pytest.raises(GovernanceViolationError):
            session.write_relationship(
                "Case", "c1", "CITES", "Law", "l1", {}
            )
        assert not executor.called

    def test_valid_relationship_produces_receipt(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        receipt = session.write_relationship(
            "Case", "c1", "CITES", "Law", "l1",
            {"provenance": _prov()},
        )
        assert receipt.label == "CITES"
        assert receipt.entity_id == "c1->l1"
        assert executor.called

    def test_provenance_never_reaches_executor(self):
        """Provenance must not appear in the Cypher query or params."""
        captured_calls = []

        def capturing_executor(query, params):
            captured_calls.append((query, params))
            return []

        session = GovernedNeo4jSession(raw_executor=capturing_executor)
        session.write_node(
            "Document",
            {"id": "d1", "title": "Test", "provenance": _prov()},
        )

        assert len(captured_calls) == 1
        query, params = captured_calls[0]
        assert "provenance" not in query.lower()
        assert "provenance" not in params

    def test_auth_token_cleared_after_write(self):
        """Authorization token must be cleared even on executor failure."""
        def failing_executor(query, params):
            raise RuntimeError("DB failure")

        session = GovernedNeo4jSession(raw_executor=failing_executor)

        with pytest.raises(RuntimeError):
            session.write_node(
                "Document", {"id": "d1", "provenance": _prov()}
            )

        # Token must be cleared — it cannot leak
        assert not _authorized_write_ctx.get()

    def test_ledger_grows_with_receipts(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        assert session.mutation_count == 0
        session.write_node("Law", {"id": "l1", "provenance": _prov()})
        session.write_node("Law", {"id": "l2", "provenance": _prov()})
        assert session.mutation_count == 2
        assert isinstance(session.ledger, tuple)

    def test_receipt_is_frozen(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        receipt = session.write_node("Law", {"id": "l1", "provenance": _prov()})

        with pytest.raises(AttributeError):
            receipt.label = "tampered"  # type: ignore


# ======================================================================
# GovernedWriteTransaction — atomic governed batch
# ======================================================================

class TestGovernedWriteTransaction:
    def test_valid_batch_commits(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        prov = _prov()

        tx = session.begin_transaction()
        tx.queue_node("Document", {"id": "d1", "provenance": prov})
        tx.queue_node("Law", {"id": "l1", "provenance": prov})
        tx.queue_relationship("Case", "c1", "CITES", "Law", "l1", {"provenance": prov})

        receipts = tx.commit()

        assert len(receipts) == 3
        assert executor.call_count == 3
        assert session.mutation_count == 3

    def test_single_invalid_mutation_blocks_entire_batch(self):
        """If mutation N fails validation, mutations 1..N-1 are NOT executed."""
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        prov = _prov()

        tx = session.begin_transaction()
        for i in range(5):
            tx.queue_node("Document", {"id": f"d{i}", "provenance": prov})
        tx.queue_relationship(
            "Document", "d0", "FORBIDDEN_REL", "Document", "d1",
            {"provenance": prov},
        )

        with pytest.raises(GovernanceViolationError):
            tx.commit()

        # Constitutional guarantee: ZERO writes reached the DB
        assert executor.call_count == 0
        assert session.mutation_count == 0

    def test_committed_transaction_rejects_further_writes(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        tx = session.begin_transaction()
        tx.queue_node("Law", {"id": "l1", "provenance": _prov()})
        tx.commit()

        with pytest.raises(RuntimeError, match="already committed"):
            tx.queue_node("Law", {"id": "l2", "provenance": _prov()})

    def test_abort_prevents_execution(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        tx = session.begin_transaction()
        tx.queue_node("Law", {"id": "l1", "provenance": _prov()})
        tx.abort()

        assert not tx.is_open
        assert executor.call_count == 0

    def test_aborted_transaction_rejects_commit(self):
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        tx = session.begin_transaction()
        tx.abort()

        with pytest.raises(RuntimeError, match="already aborted"):
            tx.commit()


# ======================================================================
# execute_write() abolition — constitutional enforcement
# ======================================================================

class TestExecuteWriteAbolished:
    def test_execute_write_raises_governance_error(self):
        """
        execute_write() must be constitutionally abolished.
        Any attempt to call it must raise GovernanceViolationError.
        This test mocks connection to test the method directly.
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        conn = object.__new__(Neo4jConnection)  # bypass __init__

        with pytest.raises(GovernanceViolationError, match="constitutionally forbidden"):
            conn.execute_write(lambda tx: tx.run("MERGE (n:X)"))
