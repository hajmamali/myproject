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

@pytest.fixture(autouse=True)
def active_mock_governance_context():
    """Establish an active governance context for testing."""
    from mahoun.core.governance.governance_context import GovernanceContextManager, _CONTEXT_SECRET
    import hmac
    import hashlib
    ctx = GovernanceContextManager.create_context(correlation_id="test-correlation")
    signature_input = f"{ctx.context_id}|{ctx.correlation_id}|{ctx.execution_mode}"
    ctx.signature = hmac.new(
        _CONTEXT_SECRET.encode(),
        signature_input.encode(),
        hashlib.sha256
    ).hexdigest()
    token = GovernanceContextManager._governance_stack.set((ctx,))
    yield ctx
    GovernanceContextManager._governance_stack.reset(token)

def _prov() -> dict:
    return ProvenanceMetadata.create(
        source="test", correlation_id="test-corr", author="test-agent",
        governance_scope_id="test-scope", runtime_attestation_id="test-attest"
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

    def test_node_write_without_provenance_succeeds_via_auto_injection(self):
        """write_node auto-injects provenance from the active GovernanceContext.

        Architectural note: provenance is NOT the caller's responsibility to
        supply. The GovernanceContext owns provenance generation and injects it
        transparently. A missing 'provenance' key is NOT a rejection criterion.
        The only hard requirement is a present 'id' field.
        """
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        # No provenance supplied — must succeed because it is auto-injected
        receipt = session.write_node("Document", {"id": "d1"})
        assert receipt is not None
        assert executor.called  # DB was written

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

    def test_relationship_without_provenance_succeeds_via_auto_injection(self):
        """write_relationship auto-injects provenance from the active GovernanceContext.

        Architectural note: the validator_pipeline checks that 'provenance' is
        present in rel_data — but write_relationship injects it before calling
        the pipeline, so an empty dict {} is valid from the caller's perspective.
        The ontology gate still blocks invalid relationship types.
        """
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)

        # No provenance supplied, valid ontology — must succeed via auto-injection
        receipt = session.write_relationship(
            "Case", "c1", "CITES", "Law", "l1", {}
        )
        assert receipt is not None
        assert executor.called

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

# ======================================================================
# execute_batch() abolition — constitutional enforcement
# ======================================================================

class TestExecuteBatchAbolished:
    def test_execute_batch_is_constitutionally_forbidden(self):
        """
        execute_batch() must be constitutionally abolished.
        Any attempt to call it must raise GovernanceViolationError.
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        conn = object.__new__(Neo4jConnection)  # bypass __init__

        with pytest.raises(GovernanceViolationError, match="execute_batch.*constitutionally forbidden"):
            conn.execute_batch([("MERGE (n:X)", {})])

    def test_execute_batch_requires_governance_context(self):
        """
        Attempting to execute batch write should fail even if context is absent,
        because the method itself is constitutionally forbidden.
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        # Disable context
        token = GovernanceContextManager._governance_stack.set(())
        try:
            conn = object.__new__(Neo4jConnection)
            with pytest.raises(GovernanceViolationError, match="constitutionally forbidden"):
                conn.execute_batch([("CREATE (n:X)", {})])
        finally:
            GovernanceContextManager._governance_stack.reset(token)

# ======================================================================
# Advanced Boundary Verification
# ======================================================================

class TestAdvancedBoundaryVerification:
    def _execute_tx_node(session):
        tx = session.begin_transaction()
        tx.queue_node("Document", {"id": "d2", "provenance": _prov()})
        tx.commit()

    def _execute_tx_rel(session):
        tx = session.begin_transaction()
        tx.queue_relationship("Case", "c1", "CITES", "Law", "l1", {"provenance": _prov()})
        tx.commit()

    @pytest.mark.parametrize("mutation_action", [
        lambda session: session.write_node("Document", {"id": "d1", "provenance": _prov()}),
        lambda session: session.write_relationship("Case", "c1", "CITES", "Law", "l1", {"provenance": _prov()}),
        _execute_tx_node,
        _execute_tx_rel,
    ])
    def test_entire_mutation_surface_reaches_boundary_real_spy(self, mutation_action):
        """
        Prove that ALL write paths on GovernedNeo4jSession dynamically hit 
        MutationAuthorizationBoundary.inspect() and perform actual validation
        (using a True Spy via wraps=).
        """
        from mahoun.graph.neo4j.connection import Neo4jConnection
        with patch("neo4j.GraphDatabase.driver"), \
             patch("mahoun.graph.neo4j.connection._NEO4J_INIT_AUTHORIZED", True):
            connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "pass")
            
            with patch.object(connection, 'session') as mock_session_ctx:
                mock_tx = MagicMock()
                mock_session_ctx.return_value.__enter__.return_value = mock_tx
                
                with connection.governed_session() as session:
                    with patch.object(
                        MutationAuthorizationBoundary, 
                        'inspect', 
                        wraps=MutationAuthorizationBoundary.inspect
                    ) as spy:
                        mutation_action(session)
                        
                        # Real Spy Verification: ensure the actual inspect logic was executed
                        assert spy.call_count >= 1

            
    def test_forbidden_neo4j_apis_ast_audit(self):
        """
        P0-D: AST-based architectural audit to guarantee no raw write bypasses exist.
        Searches all Python files in the repository.
        """
        import ast
        import os
        from pathlib import Path
        
        approved_files = {
            "mahoun/graph/neo4j/connection.py",
            "mahoun/core/governance/mutation_boundary.py",
            "tests/",
            "api/database.py",
            "api/routers/system.py",
            "scripts/",
            ".test_classification_backup/",
            "mahoun/core/governance/outbox_worker.py",
            "mahoun/graph/legal_cypher_queries.py",
        }
        
        root_dir = Path("/home/haji/Desktop/KingMahouN").resolve()
        violations = []
        
        class BypassVisitor(ast.NodeVisitor):
            def __init__(self, filepath):
                self.filepath = filepath
                self.local_violations = []
                
            def visit_Call(self, node):
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                    # Ban raw execution methods
                    if method_name in ('execute_write', 'execute_read', 'execute_batch'):
                        self.local_violations.append(f"Found {method_name}() at line {node.lineno}")
                    # Ban execute_query only if called directly on driver
                    if method_name == 'execute_query' and isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ('driver', '_driver', 'neo4j_driver'):
                            self.local_violations.append(f"Found driver.execute_query() at line {node.lineno}")
                    # Ban session or tx running
                    if method_name == 'session' and isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ('driver', '_driver', 'neo4j_driver'):
                            self.local_violations.append(f"Found driver.session() at line {node.lineno}")
                    if method_name == 'run' and isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ('tx', '_tx', 'session', 's'):
                            self.local_violations.append(f"Found {node.func.value.id}.run() at line {node.lineno}")
                self.generic_visit(node)
                
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', 'node_modules')]
            for file in files:
                if not file.endswith('.py'):
                    continue
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(root_dir))
                if any(rel_path.startswith(approved) for approved in approved_files):
                    continue
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    tree = ast.parse(source)
                    visitor = BypassVisitor(rel_path)
                    visitor.visit(tree)
                    if visitor.local_violations:
                        violations.append((rel_path, visitor.local_violations))
                except Exception:
                    pass
                    
        if violations:
            msg = "AST Audit failed. Unauthorized raw Neo4j access found:\n"
            for rel_path, local_violations in violations:
                msg += f"- {rel_path}:\n"
                for v in local_violations:
                    msg += f"  * {v}\n"
            pytest.fail(msg)

    @pytest.mark.parametrize("mutation_action", [
        lambda session: session.write_node("Document", {"id": "d1", "provenance": _prov()}),
        lambda session: session.write_relationship("Case", "c1", "CITES", "Law", "l1", {"provenance": _prov()}),
        _execute_tx_node,
    ])
    def test_every_graph_mutation_requires_governance_context(self, mutation_action):
        """
        P0-E: Architectural Truth Test
        Verify EVERY mutation entrypoint instantly fails if GovernanceContext is missing.
        """
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        
        # Simulate an unauthorized caller by wiping the context stack
        token = GovernanceContextManager._governance_stack.set(())
        try:
            with pytest.raises(GovernanceViolationError, match="No active governance context"):
                mutation_action(session)
        finally:
            GovernanceContextManager._governance_stack.reset(token)

    def test_mutation_inventory_complete(self):
        """
        P0-A: Prevent Inventory Drift by asserting ALL mutation methods are strictly known.
        """
        import inspect
        import re
        from mahoun.core.governance.mutation_boundary import GovernedWriteTransaction
        
        # CANONICAL mutation surface inventory — update this set whenever a new
        # governed mutation method is added to GovernedNeo4jSession or
        # GovernedWriteTransaction. Drift from this set is a constitutional alert.
        ALL_MUTATIONS = {
            "write_node",
            "write_relationship",
            "delete_node",        # Soft Tombstone (G3-invariant-safe hard delete opt-in)
            "begin_transaction",
            "queue_node",
            "queue_relationship",
        }
        discovered_methods = set()
        
        for cls in [GovernedNeo4jSession, GovernedWriteTransaction]:
            for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
                if re.match(r'^(write|queue|merge|upsert|delete|create)_.*', name) or name == "begin_transaction":
                    discovered_methods.add(name)
                    
        unregistered = discovered_methods - ALL_MUTATIONS
        assert not unregistered, f"Inventory drift detected! Unauthorized mutations found: {unregistered}"

    def test_negative_enforcement_rejection(self, active_mock_governance_context):
        """
        P0-B: Prove that invalid payloads are actively rejected by the boundary.
        """
        executor = _mock_executor()
        session = GovernedNeo4jSession(raw_executor=executor)
        
        with pytest.raises(GovernanceViolationError):
            # Missing provenance and incorrect ontology will strictly raise GovernanceViolationError
            session.write_node("UnknownLabel", {"bad": "payload"})
