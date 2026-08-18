"""
Test Ledger Atomicity - EL-I3 Enforcement
==========================================

Tests that verdict creation is atomic with ledger write.
If ledger write fails, verdict must NOT be created.

This enforces EL-I3 (Verdict Blocking) invariant.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from mahoun.reasoning.evidence_linked_verdict import (
    EvidenceLinkedVerdictEngine,
    EvidenceLinkedVerdict,
)
from mahoun.ledger.models import LedgerEntry
from mahoun.ledger.writer import EvidenceLedgerWriter


class TestLedgerAtomicity:
    """Test suite for ledger atomicity guarantees"""

    @pytest.fixture
    def mock_graph_builder(self):
        """Mock graph builder"""
        mock = Mock()
        return mock

    @pytest.fixture
    def mock_knowledge_graph(self):
        """Mock knowledge graph"""
        mock = Mock()
        mock.find_applicable_rules = Mock(return_value=[])
        mock.find_similar_precedents = Mock(return_value=[])
        return mock

    @pytest.fixture
    def mock_ledger_writer(self):
        """Mock ledger writer"""
        mock = Mock(spec=EvidenceLedgerWriter)
        mock.write = Mock(return_value="mock_ledger_hash_12345")
        return mock

    @pytest.fixture
    def engine(self, mock_graph_builder, mock_knowledge_graph, mock_ledger_writer):
        """Create verdict engine with mocks"""
        return EvidenceLinkedVerdictEngine(
            graph_builder=mock_graph_builder,
            knowledge_graph=mock_knowledge_graph,
            ledger_writer=mock_ledger_writer,
        )

    @pytest.mark.asyncio
    async def test_verdict_created_only_after_ledger_success(
        self, engine, mock_ledger_writer
    ):
        """
        Test: Verdict is created ONLY AFTER successful ledger write
        
        Expected behavior:
        1. Ledger write succeeds
        2. Verdict object is created
        3. Verdict has ledger_hash field populated
        """
        question = "Test question"
        facts = ["Fact 1", "Fact 2"]

        # Mock ledger write to succeed
        mock_ledger_writer.write.return_value = "test_hash_abc123"

        # Generate verdict
        verdict = await engine.generate_verdict(question, facts)

        # Assertions
        assert isinstance(verdict, EvidenceLinkedVerdict)
        assert verdict.verdict_id is not None
        assert verdict.ledger_hash == "test_hash_abc123"
        assert mock_ledger_writer.write.called

    @pytest.mark.asyncio
    async def test_verdict_not_created_if_ledger_fails(
        self, engine, mock_ledger_writer
    ):
        """
        Test: Verdict is NOT created if ledger write fails
        
        Expected behavior:
        1. Ledger write fails with exception
        2. Exception propagates to caller
        3. No verdict object is created
        
        This enforces EL-I3 (Verdict Blocking) invariant.
        """
        question = "Test question"
        facts = ["Fact 1", "Fact 2"]

        # Mock ledger write to fail
        mock_ledger_writer.write.side_effect = RuntimeError("Ledger write failed")

        # Attempt to generate verdict
        with pytest.raises(RuntimeError) as exc_info:
            await engine.generate_verdict(question, facts)

        # Assertions
        assert "Ledger write failed" in str(exc_info.value)
        assert "verdict blocked per EL-I3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ledger_write_called_before_verdict_creation(
        self, engine, mock_ledger_writer
    ):
        """
        Test: Ledger write is called BEFORE verdict object creation
        
        This test uses a side effect to verify ordering.
        """
        question = "Test question"
        facts = ["Fact 1"]

        call_order = []

        # Track call order
        def track_ledger_write(entry):
            call_order.append("ledger_write")
            return "hash_123"

        mock_ledger_writer.write.side_effect = track_ledger_write

        # Patch EvidenceLinkedVerdict creation to track order
        original_verdict_class = EvidenceLinkedVerdict

        def track_verdict_creation(*args, **kwargs):
            call_order.append("verdict_creation")
            return original_verdict_class(*args, **kwargs)

        with patch(
            "mahoun.reasoning.evidence_linked_verdict.EvidenceLinkedVerdict",
            side_effect=track_verdict_creation,
        ):
            verdict = await engine.generate_verdict(question, facts)

        # Verify order: ledger_write must come before verdict_creation
        assert call_order == ["ledger_write", "verdict_creation"]

    @pytest.mark.asyncio
    async def test_empty_facts_skips_ledger_write(self, engine, mock_ledger_writer):
        """
        Test: Empty facts case skips ledger write gracefully
        
        Expected behavior:
        1. No facts provided
        2. Ledger write is skipped
        3. Verdict is still created (with placeholder)
        4. ledger_hash is None
        """
        question = "Test question"
        facts = []

        # Generate verdict
        verdict = await engine.generate_verdict(question, facts)

        # Assertions
        assert isinstance(verdict, EvidenceLinkedVerdict)
        assert verdict.ledger_hash is None
        assert not mock_ledger_writer.write.called

    @pytest.mark.asyncio
    async def test_ledger_hash_proves_auditability(self, engine, mock_ledger_writer):
        """
        Test: Ledger hash in verdict proves audit trail exists
        
        Expected behavior:
        1. Verdict has ledger_hash field
        2. ledger_hash matches what ledger writer returned
        3. This proves EL-I6 (Audit Sufficiency)
        """
        question = "Test question"
        facts = ["Fact 1"]

        expected_hash = "proof_of_audit_trail_xyz789"
        mock_ledger_writer.write.return_value = expected_hash

        # Generate verdict
        verdict = await engine.generate_verdict(question, facts)

        # Assertions
        assert verdict.ledger_hash == expected_hash
        # This proves that the verdict has a corresponding ledger entry
        # Client can verify audit trail by checking ledger with this hash

    @pytest.mark.asyncio
    async def test_concurrent_verdicts_have_unique_ledger_entries(
        self, engine, mock_ledger_writer
    ):
        """
        Test: Concurrent verdict generation creates unique ledger entries
        
        Expected behavior:
        1. Multiple verdicts generated concurrently
        2. Each has unique verdict_id
        3. Each has unique ledger_hash
        4. Ledger lock ensures sequential writes
        """
        question = "Test question"
        facts = ["Fact 1"]

        # Mock ledger writer to return unique hashes
        call_count = [0]

        def unique_hash(entry):
            call_count[0] += 1
            return f"hash_{call_count[0]}"

        mock_ledger_writer.write.side_effect = unique_hash

        # Generate multiple verdicts concurrently
        tasks = [
            engine.generate_verdict(question, facts),
            engine.generate_verdict(question, facts),
            engine.generate_verdict(question, facts),
        ]
        verdicts = await asyncio.gather(*tasks)

        # Assertions
        assert len(verdicts) == 3
        verdict_ids = [v.verdict_id for v in verdicts]
        ledger_hashes = [v.ledger_hash for v in verdicts]

        # All verdict_ids must be unique
        assert len(set(verdict_ids)) == 3
        # All ledger_hashes must be unique
        assert len(set(ledger_hashes)) == 3
        # Ledger writer must be called 3 times
        assert mock_ledger_writer.write.call_count == 3


class TestLedgerAtomicityIntegration:
    """Integration tests with real ledger writer (NoOp backend)"""

    @pytest.fixture
    def real_ledger_writer(self):
        """Create real ledger writer with NoOp backend"""
        from mahoun.ledger.writer import create_ledger_writer

        return create_ledger_writer(backend_type="noop")

    @pytest.fixture
    def engine_with_real_ledger(
        self, mock_graph_builder, mock_knowledge_graph, real_ledger_writer
    ):
        """Create engine with real ledger writer"""
        return EvidenceLinkedVerdictEngine(
            graph_builder=mock_graph_builder,
            knowledge_graph=mock_knowledge_graph,
            ledger_writer=real_ledger_writer,
        )

    @pytest.fixture
    def mock_graph_builder(self):
        """Mock graph builder"""
        return Mock()

    @pytest.fixture
    def mock_knowledge_graph(self):
        """Mock knowledge graph"""
        mock = Mock()
        mock.find_applicable_rules = Mock(return_value=[])
        mock.find_similar_precedents = Mock(return_value=[])
        return mock

    @pytest.mark.asyncio
    async def test_real_ledger_write_atomicity(self, engine_with_real_ledger):
        """
        Test: Real ledger writer maintains atomicity
        
        This test uses NoOp backend (no persistence) but verifies
        that the atomicity logic works with real ledger writer.
        """
        question = "Test question"
        facts = ["Fact 1", "Fact 2"]

        # Generate verdict
        verdict = await engine_with_real_ledger.generate_verdict(question, facts)

        # Assertions
        assert isinstance(verdict, EvidenceLinkedVerdict)
        assert verdict.verdict_id is not None
        # NoOp backend returns hash, so ledger_hash should be populated
        assert verdict.ledger_hash is not None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
