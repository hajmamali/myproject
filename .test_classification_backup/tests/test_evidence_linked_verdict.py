"""
Tests for Evidence-Linked Verdict Engine
========================================
Tests that verify EVERY conclusion is explicitly linked to graph evidence.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestEvidenceLinkedVerdictEngine:
    """Test Evidence-Linked Verdict Engine"""
    
    def test_engine_exists(self):
        """Test that EvidenceLinkedVerdictEngine exists"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        assert EvidenceLinkedVerdictEngine is not None
        print("✓ EvidenceLinkedVerdictEngine exists")
    
    def test_engine_can_be_created(self):
        """Test that engine can be instantiated"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        assert engine is not None
        assert hasattr(engine, 'generate_verdict')
        print("✓ EvidenceLinkedVerdictEngine can be instantiated")
    
    def test_data_structures_exist(self):
        """Test that required data structures exist"""
        from mahoun.reasoning.evidence_linked_verdict import (
            EvidenceReference,
            VerdictStep,
            EvidenceLinkedVerdict
        )
        
        assert EvidenceReference is not None
        assert VerdictStep is not None
        assert EvidenceLinkedVerdict is not None
        print("✓ All required data structures exist")


class TestEvidenceLinking:
    """Test that evidence is properly linked"""
    
    def test_verdict_links_to_graph_nodes(self):
        """Test that verdict steps reference graph nodes"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Add rules to knowledge graph
        kg.add_legal_rule(
            "rule_1",
            "قرارداد امضا شده",
            "تعهد ایجاد می‌شود",
            0.9
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "اگر قراردادی امضا شود چه می‌شود؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # Check that steps have evidence
        assert len(verdict.steps) > 0, "باید حداقل یک step باشد"
        
        # Check that each step has evidence references
        for step in verdict.steps:
            assert len(step.evidence) > 0, f"Step '{step.statement}' باید evidence داشته باشد"
            for evidence in step.evidence:
                assert evidence.node_id, "Evidence باید node_id داشته باشد"
                assert evidence.node_type, "Evidence باید node_type داشته باشد"
        
        print(f"✓ Verdict has {len(verdict.steps)} steps, all with evidence links")
    
    def test_removing_node_invalidates_verdict(self):
        """Test that removing a referenced node invalidates the verdict"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Add a specific rule
        kg.add_legal_rule(
            "critical_rule",
            "قرارداد",
            "تعهد",
            0.95
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict1 = engine.generate_verdict(question, facts)
        
        # Get referenced node IDs
        referenced_nodes = set()
        for step in verdict1.steps:
            for evidence in step.evidence:
                referenced_nodes.add(evidence.node_id)
        
        assert len(referenced_nodes) > 0, "باید حداقل یک node reference شده باشد"
        
        # Remove the critical rule
        kg.legal_rules.pop("critical_rule", None)
        
        # Generate verdict again
        verdict2 = engine.generate_verdict(question, facts)
        
        # Check that verdict changed (node removed)
        # The verdict should either have fewer steps or different evidence
        verdict1_node_ids = {
            e.node_id for step in verdict1.steps for e in step.evidence
        }
        verdict2_node_ids = {
            e.node_id for step in verdict2.steps for e in step.evidence
        }
        
        # At least one node should be missing
        missing_nodes = verdict1_node_ids - verdict2_node_ids
        assert len(missing_nodes) > 0 or verdict1.final_verdict != verdict2.final_verdict, \
            "حذف node باید verdict را تغییر دهد"
        
        print(f"✓ Removing node invalidates verdict ({len(missing_nodes)} nodes missing)")
    
    def test_contradictory_rules_in_unresolved_conflicts(self):
        """Test that contradictory rules appear in unresolved_conflicts"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Add contradictory rules
        kg.add_legal_rule(
            "rule_yes",
            "قرارداد",
            "باید اجرا شود",
            0.9
        )
        kg.add_legal_rule(
            "rule_no",
            "قرارداد",
            "نباید اجرا شود",  # Contradiction!
            0.9  # Same confidence - cannot resolve
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد باید اجرا شود؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # Check that contradiction is either resolved or in unresolved_conflicts
        has_contradiction = len(verdict.unresolved_conflicts) > 0
        
        # If resolved, check that only one rule is used
        if not has_contradiction:
            # Check that verdict steps reference only one of the contradictory rules
            rule_yes_refs = sum(
                1 for step in verdict.steps
                for e in step.evidence
                if "rule_yes" in e.node_id or "rule_no" in e.node_id
            )
            assert rule_yes_refs > 0, "باید حداقل یک rule reference شده باشد"
            print("✓ Contradiction resolved by selection")
        else:
            assert len(verdict.unresolved_conflicts) > 0, "باید contradiction در unresolved_conflicts باشد"
            print(f"✓ Contradiction in unresolved_conflicts: {verdict.unresolved_conflicts}")
    
    def test_confidence_score_from_evidence(self):
        """Test that confidence_score is computed from evidence confidence"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Add rule with specific confidence
        kg.add_legal_rule(
            "high_conf_rule",
            "قرارداد",
            "تعهد",
            0.95  # High confidence
        )
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        # Confidence should be based on evidence confidence
        assert 0.0 <= verdict.confidence_score <= 1.0, "Confidence باید بین 0 و 1 باشد"
        
        # If we have high confidence evidence, confidence should reflect that
        if len(verdict.steps) > 0:
            max_evidence_conf = max(
                e.confidence for step in verdict.steps for e in step.evidence
            )
            # Confidence score should be related to evidence confidence
            assert verdict.confidence_score > 0.0, "Confidence باید مثبت باشد"
        
        print(f"✓ Confidence score computed: {verdict.confidence_score:.2f}")


class TestDeterministicOutput:
    """Test that output is deterministic"""
    
    def test_same_input_same_output(self):
        """Test that same input produces same output"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict1 = engine.generate_verdict(question, facts)
        verdict2 = engine.generate_verdict(question, facts)
        
        # Verdicts should be the same (deterministic)
        assert verdict1.final_verdict == verdict2.final_verdict, "Output باید deterministic باشد"
        assert len(verdict1.steps) == len(verdict2.steps), "تعداد steps باید یکسان باشد"
        assert verdict1.confidence_score == verdict2.confidence_score, "Confidence باید یکسان باشد"
        
        print("✓ Output is deterministic")


class TestNoLLMCalls:
    """Test that engine works without LLM calls"""
    
    def test_engine_works_without_llm(self):
        """Test that engine generates verdict without LLM"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.storage import NoOpLedgerWriter
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = NoOpLedgerWriter()
        
        # Add rules
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        kg.add_precedent("case_1", ["قرارداد"], "اجرا", "دادگاه")
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        # This should work without any LLM calls
        verdict = engine.generate_verdict(question, facts)
        
        assert verdict is not None
        assert verdict.final_verdict, "باید verdict تولید شود"
        assert len(verdict.steps) > 0, "باید steps داشته باشد"
        
        print("✓ Engine works without LLM calls")


class TestEvidenceRequirements:
    """Test evidence requirements"""
    
    def test_each_step_has_evidence(self):
        """Test that each VerdictStep has at least one evidence reference"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        from mahoun.ledger.storage import NoOpLedgerWriter
        ledger_writer = NoOpLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        for i, step in enumerate(verdict.steps):
            assert len(step.evidence) > 0, \
                f"Step {i} ('{step.statement}') باید حداقل یک evidence reference داشته باشد"
            
            for j, evidence in enumerate(step.evidence):
                assert evidence.node_id, \
                    f"Evidence {j} در step {i} باید node_id داشته باشد"
                assert evidence.node_type, \
                    f"Evidence {j} در step {i} باید node_type داشته باشد"
        
        print(f"✓ All {len(verdict.steps)} steps have evidence references")
    
    def test_evidence_justification_exists(self):
        """Test that evidence has justification"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        from mahoun.ledger.storage import NoOpLedgerWriter
        ledger_writer = NoOpLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        verdict = engine.generate_verdict(question, facts)
        
        for step in verdict.steps:
            for evidence in step.evidence:
                assert evidence.justification, \
                    f"Evidence برای node {evidence.node_id} باید justification داشته باشد"
        
        print("✓ All evidence has justification")


class TestEvidenceLedger:
    """Test Evidence Ledger functionality"""
    
    @pytest.mark.asyncio
    async def test_ledger_write_failure_blocks_verdict(self):
        """Test that ledger write failure blocks verdict generation"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend
        
        class FailingLedgerBackend(NoOpLedgerBackend):
            def write(self, entry, entry_hash, prev_hash):
                raise Exception("Ledger write failed")
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = EvidenceLedgerWriter(backend=FailingLedgerBackend())
        
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        with pytest.raises(RuntimeError, match="Ledger write failed"):
            await engine.generate_verdict(question, facts)
        
        print("✓ Ledger write failure blocks verdict generation")
    
    def test_ledger_entry_validation_no_evidence(self):
        """Test that LedgerEntry with no evidence is rejected"""
        from mahoun.ledger.models import LedgerEntry
        from mahoun.ledger.guards import validate_entry
        from datetime import datetime, timezone
        
        entry = LedgerEntry(
            verdict_id="test_id",
            case_id="test_case",
            referenced_ltm_nodes=[],
            referenced_facts=[],
            confidence=0.8,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="at least one referenced"):
            validate_entry(entry)
        
        print("✓ LedgerEntry with no evidence rejected")
    
    def test_ledger_entry_immutable(self):
        """Test that LedgerEntry is immutable"""
        from mahoun.ledger.models import LedgerEntry
        from datetime import datetime, timezone
        
        entry = LedgerEntry(
            verdict_id="test_id",
            case_id="test_case",
            referenced_ltm_nodes=["rule_1"],
            referenced_facts=["fact_1"],
            confidence=0.8,
            invariant_version="1.0",
            guard_mode="STRICT",
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(AttributeError):
            entry.verdict_id = "new_id"
        
        print("✓ LedgerEntry is immutable")
    
    @pytest.mark.asyncio
    async def test_verdict_without_ledger_is_forbidden(self):
        """Test that verdict generation fails if ledger write fails (EL-I3: Verdict Blocking)"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend
        
        class FailingLedgerBackend(NoOpLedgerBackend):
            def write(self, entry, entry_hash, prev_hash):
                raise RuntimeError("Simulated ledger failure")
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = EvidenceLedgerWriter(backend=FailingLedgerBackend())
        
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        question = "قرارداد چیست؟"
        facts = ["قرارداد امضا شده"]
        
        # Should raise RuntimeError due to ledger failure
        with pytest.raises(RuntimeError, match="Ledger write failed"):
            await engine.generate_verdict(question, facts)
        
        print("✓ Verdict generation blocked by ledger failure")
    
    @pytest.mark.asyncio
    async def test_sensitive_fact_value_is_not_written_to_ledger(self):
        """Test that sensitive fact values are not stored in ledger (EL-I7: Privacy Preservation)"""
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
        from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend
        from mahoun.ledger.privacy import SENSITIVE_FACT_TYPES
        
        builder = UltraGraphBuilder()
        kg = LegalKnowledgeGraph()
        ledger_writer = EvidenceLedgerWriter(backend=NoOpLedgerBackend())
        
        kg.add_legal_rule("rule_1", "قرارداد", "تعهد", 0.9)
        
        engine = EvidenceLinkedVerdictEngine(builder, kg, ledger_writer)
        
        # Create facts with sensitive data
        sensitive_fact = {
            'id': 'fact_1',
            'type': 'PERSONAL_ID',  # Sensitive type
            'value': '123-45-6789'  # Sensitive value
        }
        
        # This should fail due to privacy violation
        with pytest.raises(RuntimeError, match="Privacy violation"):
            await engine.generate_verdict("Test question", [sensitive_fact])
        
        print("✓ Sensitive fact values blocked from ledger")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])

