"""
Test Deterministic Contradiction Resolution
============================================

Tests to verify that contradiction resolution is deterministic and
produces same output for same input, regardless of concurrency.
"""

import pytest
import asyncio
from unittest.mock import Mock

from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphNode
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend


class TestDeterministicResolution:
    """Test suite for deterministic contradiction resolution"""

    @pytest.fixture
    def engine(self):
        """Create verdict engine"""
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = EvidenceLedgerWriter(backend=NoOpLedgerBackend())
        return EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)

    @pytest.mark.asyncio
    async def test_same_input_produces_same_output(self, engine):
        """Test: Same input always produces same output (determinism)"""
        # Add rules with potential contradictions
        engine.knowledge_graph.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        engine.knowledge_graph.add_legal_rule("rule_2", "قرارداد", "آزادی", 0.85)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        # Generate verdict multiple times
        verdict1 = await engine.generate_verdict(question, facts)
        verdict2 = await engine.generate_verdict(question, facts)
        verdict3 = await engine.generate_verdict(question, facts)
        
        # Verify same output
        assert verdict1.final_verdict == verdict2.final_verdict
        assert verdict2.final_verdict == verdict3.final_verdict
        assert len(verdict1.steps) == len(verdict2.steps)
        assert len(verdict2.steps) == len(verdict3.steps)
        
        print("✓ Same input produces same output (determinism verified)")

    @pytest.mark.asyncio
    async def test_concurrent_calls_produce_same_output(self, engine):
        """Test: Concurrent calls produce same output (no race conditions)"""
        # Add rules
        engine.knowledge_graph.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        engine.knowledge_graph.add_legal_rule("rule_2", "قرارداد", "آزادی", 0.85)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        # Generate verdicts concurrently
        tasks = [
            engine.generate_verdict(question, facts)
            for _ in range(10)
        ]
        verdicts = await asyncio.gather(*tasks)
        
        # Verify all verdicts are identical
        first_verdict = verdicts[0]
        for verdict in verdicts[1:]:
            assert verdict.final_verdict == first_verdict.final_verdict
            assert len(verdict.steps) == len(first_verdict.steps)
        
        print("✓ Concurrent calls produce same output (no race conditions)")

    @pytest.mark.asyncio
    async def test_tie_breaking_is_deterministic(self, engine):
        """Test: Tie-breaking uses lexicographic node ID comparison"""
        # Create nodes with equal confidence (tie)
        node1 = GraphNode(
            id="rule_b",  # Lexicographically after "rule_a"
            label="Rule B",
            node_type="LegalRule",
            properties={"condition": "test", "conclusion": "result B"},
            confidence=0.9,
        )
        node2 = GraphNode(
            id="rule_a",  # Lexicographically before "rule_b"
            label="Rule A",
            node_type="LegalRule",
            properties={"condition": "test", "conclusion": "result A"},
            confidence=0.9,  # Same confidence as node1
        )
        
        # Resolve contradiction
        resolution = engine._resolve_contradiction_deterministic(node1, node2)
        
        # Should always choose "rule_a" (lexicographically first)
        assert resolution.id == "rule_a"
        
        # Verify it's deterministic (same result every time)
        for _ in range(10):
            resolution = engine._resolve_contradiction_deterministic(node1, node2)
            assert resolution.id == "rule_a"
        
        print("✓ Tie-breaking is deterministic (lexicographic node ID)")

    @pytest.mark.asyncio
    async def test_confidence_threshold_prevents_floating_point_issues(self, engine):
        """Test: Confidence threshold prevents floating-point rounding issues"""
        # Create nodes with very close confidence values
        node1 = GraphNode(
            id="rule_1",
            label="Rule 1",
            node_type="LegalRule",
            properties={},
            confidence=0.900001,  # Very close to 0.9
        )
        node2 = GraphNode(
            id="rule_2",
            label="Rule 2",
            node_type="LegalRule",
            properties={},
            confidence=0.900000,  # Very close to 0.9
        )
        
        # Resolve contradiction
        resolution = engine._resolve_contradiction_deterministic(node1, node2)
        
        # Should use tie-breaking (difference < threshold)
        # Lexicographically, "rule_1" < "rule_2"
        assert resolution.id == "rule_1"
        
        print("✓ Confidence threshold prevents floating-point issues")

    @pytest.mark.asyncio
    async def test_resolution_order_is_deterministic(self, engine):
        """Test: Contradictions are processed in deterministic order"""
        # Add multiple rules with contradictions
        engine.knowledge_graph.add_legal_rule("rule_c", "شرط", "نتیجه C", 0.8)
        engine.knowledge_graph.add_legal_rule("rule_a", "شرط", "نتیجه A", 0.85)
        engine.knowledge_graph.add_legal_rule("rule_b", "شرط", "نتیجه B", 0.9)
        
        question = "سوال تست"
        facts = ["شرط برقرار است"]
        
        # Generate verdict multiple times
        verdicts = []
        for _ in range(5):
            verdict = await engine.generate_verdict(question, facts)
            verdicts.append(verdict)
        
        # Verify all verdicts are identical
        first_verdict = verdicts[0]
        for verdict in verdicts[1:]:
            assert verdict.final_verdict == first_verdict.final_verdict
            # Verify step order is same
            for i, step in enumerate(verdict.steps):
                assert step.statement == first_verdict.steps[i].statement
        
        print("✓ Resolution order is deterministic")

    @pytest.mark.asyncio
    async def test_no_lock_needed_for_determinism(self, engine):
        """Test: Deterministic resolution works without locks"""
        # Verify no resolution lock exists
        assert not hasattr(engine, '_resolution_lock')
        
        # Add rules
        engine.knowledge_graph.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        # Generate verdict (should work without lock)
        verdict = await engine.generate_verdict(question, facts)
        
        assert verdict is not None
        assert verdict.final_verdict is not None
        
        print("✓ No lock needed for determinism")

    @pytest.mark.asyncio
    async def test_multiple_engine_instances_produce_same_output(self):
        """Test: Multiple engine instances produce same output (no shared state)"""
        # Create multiple engine instances
        engines = []
        for _ in range(3):
            builder = UltraGraphBuilder()
            kg = LegalKnowledgeGraph()
            ledger_writer = EvidenceLedgerWriter(backend=NoOpLedgerBackend())
            engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
            
            # Add same rules to each
            engine.knowledge_graph.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
            engine.knowledge_graph.add_legal_rule("rule_2", "قرارداد", "آزادی", 0.85)
            
            engines.append(engine)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        # Generate verdicts from different engines
        verdicts = []
        for engine in engines:
            verdict = await engine.generate_verdict(question, facts)
            verdicts.append(verdict)
        
        # Verify all verdicts are identical
        first_verdict = verdicts[0]
        for verdict in verdicts[1:]:
            assert verdict.final_verdict == first_verdict.final_verdict
            assert len(verdict.steps) == len(first_verdict.steps)
        
        print("✓ Multiple engine instances produce same output")

    @pytest.mark.asyncio
    async def test_date_based_resolution_is_deterministic(self, engine):
        """Test: Date-based resolution is deterministic"""
        # Create nodes with different dates
        node1 = GraphNode(
            id="precedent_1",
            label="Precedent 1",
            node_type="LegalPrecedent",
            properties={"date": "2023-01-01"},
            confidence=0.9,
        )
        node2 = GraphNode(
            id="precedent_2",
            label="Precedent 2",
            node_type="LegalPrecedent",
            properties={"date": "2024-01-01"},  # Newer
            confidence=0.9,
        )
        
        # Resolve contradiction (should choose newer)
        resolution = engine._resolve_contradiction_deterministic(node1, node2)
        
        # Should choose newer date
        assert resolution.id == "precedent_2"
        
        # Verify determinism
        for _ in range(10):
            resolution = engine._resolve_contradiction_deterministic(node1, node2)
            assert resolution.id == "precedent_2"
        
        print("✓ Date-based resolution is deterministic")

    @pytest.mark.asyncio
    async def test_credibility_based_resolution_is_deterministic(self, engine):
        """Test: Credibility-based resolution is deterministic"""
        # Create nodes with different credibility
        node1 = GraphNode(
            id="rule_1",
            label="Rule 1",
            node_type="LegalRule",
            properties={"credibility": 0.95},
            confidence=0.9,
        )
        node2 = GraphNode(
            id="rule_2",
            label="Rule 2",
            node_type="LegalRule",
            properties={"credibility": 0.85},
            confidence=0.9,
        )
        
        # Resolve contradiction (should choose higher credibility)
        resolution = engine._resolve_contradiction_deterministic(node1, node2)
        
        # Should choose higher credibility
        assert resolution.id == "rule_1"
        
        # Verify determinism
        for _ in range(10):
            resolution = engine._resolve_contradiction_deterministic(node1, node2)
            assert resolution.id == "rule_1"
        
        print("✓ Credibility-based resolution is deterministic")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
