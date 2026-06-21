"""Error path tests for reasoning components

Tests error handling and edge cases when required dependencies are missing
or invalid inputs are provided.

CRITICAL: These tests verify the platform's robustness in high-stakes scenarios
where missing dependencies or invalid inputs could lead to incorrect verdicts.
"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from mahoun.reasoning.evidence_linked_verdict import (
    EvidenceLinkedVerdictEngine,
    EvidenceLinkedVerdict,
)
from mahoun.reasoning.reasoning_engine import DeepLegalReasoningEngine
from mahoun.reasoning.chain_of_thought import ChainOfThoughtReasoner
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.ledger.writer import EvidenceLedgerWriter


class TestReasoningWithoutGraph:
    """Test reasoning engine behavior when graph is missing or None
    
    CRITICAL: In regulated industries (healthcare, legal, finance), reasoning
    without proper graph infrastructure could lead to hallucinated verdicts.
    These tests ensure the system fails safely.
    """
    
    def test_evidence_linked_verdict_requires_graph_builder(self):
        """EvidenceLinkedVerdictEngine MUST reject None graph_builder
        
        RATIONALE: Without graph_builder, the engine cannot create case graphs
        from facts, violating the zero-hallucination guarantee (I1 invariant).
        """
        kg = LegalKnowledgeGraph()
        ledger = EvidenceLedgerWriter()
        
        # CRITICAL: Must raise TypeError when graph_builder is None
        with pytest.raises(TypeError):
            EvidenceLinkedVerdictEngine(
                graph_builder=None,  # type: ignore
                knowledge_graph=kg,
                ledger_writer=ledger
            )
    
    def test_evidence_linked_verdict_requires_knowledge_graph(self):
        """EvidenceLinkedVerdictEngine MUST reject None knowledge_graph
        
        RATIONALE: Without knowledge_graph, the engine cannot find applicable
        rules or precedents, making all verdicts ungrounded.
        """
        graph_builder = UltraGraphBuilder()
        ledger = EvidenceLedgerWriter()
        
        # CRITICAL: Must raise TypeError when knowledge_graph is None
        with pytest.raises(TypeError):
            EvidenceLinkedVerdictEngine(
                graph_builder=graph_builder,
                knowledge_graph=None,  # type: ignore
                ledger_writer=ledger
            )
    
    def test_evidence_linked_verdict_requires_ledger_writer(self):
        """EvidenceLinkedVerdictEngine MUST reject None ledger_writer
        
        RATIONALE: Without ledger_writer, verdicts cannot be audited,
        violating regulatory compliance requirements.
        """
        kg = LegalKnowledgeGraph()
        graph_builder = UltraGraphBuilder()
        
        # CRITICAL: Must raise TypeError when ledger_writer is None
        with pytest.raises(TypeError):
            EvidenceLinkedVerdictEngine(
                graph_builder=graph_builder,
                knowledge_graph=kg,
                ledger_writer=None  # type: ignore
            )
    
    def test_chain_of_thought_requires_knowledge_graph(self):
        """ChainOfThoughtReasoner MUST reject None knowledge_graph
        
        RATIONALE: Chain of thought reasoning requires legal rules and
        precedents from the knowledge graph to generate valid reasoning steps.
        """
        # CRITICAL: Must raise TypeError when knowledge_graph is None
        with pytest.raises(TypeError):
            ChainOfThoughtReasoner(knowledge_graph=None)  # type: ignore
    
    def test_deep_reasoning_engine_initializes_own_graph(self):
        """DeepLegalReasoningEngine MUST initialize its own graph infrastructure
        
        RATIONALE: High-level API should be user-friendly and handle
        infrastructure setup automatically while maintaining safety.
        """
        # Should not raise error - creates its own graph
        engine = DeepLegalReasoningEngine()
        
        # VERIFY: All required components are initialized
        assert hasattr(engine, 'graph_builder')
        assert engine.graph_builder is not None
        assert isinstance(engine.graph_builder, UltraGraphBuilder)
        
        assert hasattr(engine, 'knowledge_graph')
        assert engine.knowledge_graph is not None
        assert isinstance(engine.knowledge_graph, LegalKnowledgeGraph)
        
        assert hasattr(engine, 'chain_reasoner')
        assert engine.chain_reasoner is not None
        assert isinstance(engine.chain_reasoner, ChainOfThoughtReasoner)
        
        assert hasattr(engine, 'causal_engine')
        assert engine.causal_engine is not None
    
    def test_reasoning_with_empty_knowledge_graph(self):
        """Reasoning MUST handle empty knowledge graph gracefully
        
        RATIONALE: In early deployment or specialized domains, the knowledge
        graph may be empty. System should degrade gracefully, not crash.
        
        EXPECTED: Low confidence verdict with explicit acknowledgment of
        missing rules/precedents.
        """
        # Create empty knowledge graph (no rules, no precedents)
        kg = LegalKnowledgeGraph()
        graph_builder = UltraGraphBuilder()
        ledger = EvidenceLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=kg,
            ledger_writer=ledger
        )
        
        # CRITICAL: Should not crash with empty knowledge graph
        verdict = asyncio.run(engine.generate_verdict(
            question="آیا قرارداد نقض شده است؟",
            facts=["طرف الف تعهدات خود را انجام نداد", "طرف ب خسارت دید"]
        ))
        
        # VERIFY: Returns valid verdict structure
        assert isinstance(verdict, EvidenceLinkedVerdict)
        assert verdict.final_verdict is not None
        assert len(verdict.final_verdict) > 0
        
        # VERIFY: Verdict acknowledges lack of rules/precedents
        assert "قوانین" in verdict.final_verdict or "سوابق" in verdict.final_verdict or "گراف" in verdict.final_verdict
        
        # VERIFY: Confidence is low (no rules/precedents to support verdict)
        assert verdict.confidence_score >= 0.0
        assert verdict.confidence_score <= 0.5  # Should be low confidence
        
        # VERIFY: At least one step exists (fact identification)
        assert len(verdict.steps) > 0
        
        # VERIFY: Each step has evidence (even if just facts)
        for step in verdict.steps:
            assert len(step.evidence) > 0
    
    def test_reasoning_with_no_facts(self):
        """Reasoning MUST handle empty facts list gracefully
        
        RATIONALE: User may accidentally submit empty facts. System should
        not crash but should return low-confidence verdict.
        """
        kg = LegalKnowledgeGraph()
        graph_builder = UltraGraphBuilder()
        ledger = EvidenceLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=kg,
            ledger_writer=ledger
        )
        
        # CRITICAL: Should handle empty facts without crashing
        verdict = asyncio.run(engine.generate_verdict(
            question="آیا قرارداد نقض شده است؟",
            facts=[]  # Empty facts
        ))
        
        # VERIFY: Returns valid verdict
        assert isinstance(verdict, EvidenceLinkedVerdict)
        assert verdict.final_verdict is not None
        
        # VERIFY: Confidence is zero or very low
        assert verdict.confidence_score >= 0.0
        assert verdict.confidence_score <= 0.1
        
        # VERIFY: At least one step exists (placeholder)
        assert len(verdict.steps) > 0
    
    def test_reasoning_with_invalid_fact_types(self):
        """Reasoning MUST handle invalid fact types gracefully
        
        RATIONALE: API consumers may pass wrong data types. System should
        validate inputs and provide clear error messages.
        """
        kg = LegalKnowledgeGraph()
        graph_builder = UltraGraphBuilder()
        ledger = EvidenceLedgerWriter()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=graph_builder,
            knowledge_graph=kg,
            ledger_writer=ledger
        )
        
        # Test with None facts
        with pytest.raises((TypeError, AttributeError, ValueError)):
            asyncio.run(engine.generate_verdict(
                question="Test?",
                facts=None  # type: ignore
            ))
        
        # Test with non-list facts
        with pytest.raises((TypeError, AttributeError)):
            asyncio.run(engine.generate_verdict(
                question="Test?",
                facts="not a list"  # type: ignore
            ))
    
    def test_deep_reasoning_without_facts(self):
        """DeepLegalReasoningEngine MUST extract facts from context if not provided
        
        RATIONALE: High-level API should be forgiving and extract facts
        automatically from context when possible.
        """
        engine = DeepLegalReasoningEngine()
        
        # Should extract facts from context automatically
        result = engine.deep_reason(
            question="آیا قرارداد نقض شده است؟",
            context="طرف الف تعهدات خود را انجام نداد. طرف ب خسارت دید. قرارداد در تاریخ ۱۴۰۰/۰۱/۰۱ منعقد شد.",
            facts=None  # No facts provided
        )
        
        # VERIFY: Facts were extracted from context
        assert len(result.facts) > 0
        assert result.final_answer is not None
        
        # VERIFY: Reasoning chain exists
        assert len(result.reasoning_chain) > 0
    
    def test_deep_reasoning_with_empty_context(self):
        """DeepLegalReasoningEngine MUST handle empty context gracefully
        
        RATIONALE: User may provide empty context. System should not crash
        but should return low-confidence result.
        """
        engine = DeepLegalReasoningEngine()
        
        # Should handle empty context
        result = engine.deep_reason(
            question="آیا قرارداد نقض شده است؟",
            context="",  # Empty context
            facts=["Fact 1"]
        )
        
        # VERIFY: Returns valid result
        assert result.final_answer is not None
        assert result.confidence >= 0.0
        
        # VERIFY: Low confidence due to lack of context
        assert result.confidence <= 0.7
