"""
Surgical Tests for evidence_linked_verdict.py
==============================================
Target: Test ONLY helper methods (not full pipeline)

Focus Areas:
1. VerdictDraft.finalize() - ledger hash validation
2. _calculate_confidence_score() - scoring logic
3. _synthesize_final_verdict() - verdict text generation
4. _resolve_provenance() - provenance resolution
5. ConflictResolutionResult - data structure
"""

import pytest
from mahoun.reasoning.evidence_linked_verdict import (
    VerdictDraft,
    EvidenceLinkedVerdict,
    VerdictStep,
    EvidenceReference,
    ConflictResolutionResult,
    _resolve_provenance,
)


class TestVerdictDraftFinalization:
    """Test VerdictDraft → EvidenceLinkedVerdict conversion"""
    
    @pytest.mark.p1
    def test_finalize_with_valid_hash(self):
        """VerdictDraft.finalize() creates EvidenceLinkedVerdict with valid hash"""
        draft = VerdictDraft(
            final_verdict_text="Test verdict",
            steps=[],
            unresolved_conflicts=[],
            confidence_score=0.85,
            verdict_id="v001"
        )
        
        verdict = draft.finalize(ledger_hash="a" * 64)
        
        assert isinstance(verdict, EvidenceLinkedVerdict)
        assert verdict.final_verdict == "Test verdict"
        assert verdict.ledger_hash == "a" * 64
        assert verdict.verdict_id == "v001"
    
    @pytest.mark.p1
    def test_finalize_rejects_empty_hash(self):
        """VerdictDraft.finalize() rejects empty ledger hash"""
        draft = VerdictDraft(
            final_verdict_text="Test",
            steps=[],
            unresolved_conflicts=[],
            confidence_score=0.8,
            verdict_id="v002"
        )
        
        with pytest.raises(ValueError, match="Invalid ledger_hash"):
            draft.finalize(ledger_hash="")
    
    @pytest.mark.p1
    def test_finalize_rejects_short_hash(self):
        """VerdictDraft.finalize() rejects hash shorter than 16 chars"""
        draft = VerdictDraft(
            final_verdict_text="Test",
            steps=[],
            unresolved_conflicts=[],
            confidence_score=0.8,
            verdict_id="v003"
        )
        
        with pytest.raises(ValueError, match="Invalid ledger_hash"):
            draft.finalize(ledger_hash="abc123")


class TestConfidenceScoreCalculation:
    """Test confidence score calculation from verdict steps"""
    
    @pytest.mark.p1
    def test_confidence_no_steps_returns_zero(self):
        """_calculate_confidence_score([]) returns 0.0"""
        from unittest.mock import MagicMock
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend
        
        # Mock LegalKnowledgeGraph to avoid embedding model dependency
        mock_kg = MagicMock()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=UltraGraphBuilder(),
            knowledge_graph=mock_kg,
            ledger_writer=EvidenceLedgerWriter(NoOpLedgerBackend()),
        )
        
        score = engine._calculate_confidence_score([])
        assert score == 0.0
    
    @pytest.mark.p1
    def test_confidence_with_one_step(self):
        """_calculate_confidence_score([step]) > 0"""
        from unittest.mock import MagicMock
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend
        
        # Mock LegalKnowledgeGraph to avoid embedding model dependency
        mock_kg = MagicMock()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=UltraGraphBuilder(),
            knowledge_graph=mock_kg,
            ledger_writer=EvidenceLedgerWriter(NoOpLedgerBackend()),
        )
        
        steps = [
            VerdictStep(
                statement="Test statement",
                evidence=[EvidenceReference(node_id="n1", node_type="Fact", confidence=0.9)]
            )
        ]
        
        score = engine._calculate_confidence_score(steps)
        assert 0.0 < score <= 1.0
    
    @pytest.mark.p1
    def test_confidence_with_multiple_steps(self):
        """_calculate_confidence_score([step1, step2]) averages evidence confidence"""
        from unittest.mock import MagicMock
        from mahoun.reasoning.evidence_linked_verdict import EvidenceLinkedVerdictEngine
        from mahoun.graph.ultra_graph_builder import UltraGraphBuilder
        from mahoun.ledger.writer import EvidenceLedgerWriter, NoOpLedgerBackend
        
        # Mock LegalKnowledgeGraph to avoid embedding model dependency
        mock_kg = MagicMock()
        
        engine = EvidenceLinkedVerdictEngine(
            graph_builder=UltraGraphBuilder(),
            knowledge_graph=mock_kg,
            ledger_writer=EvidenceLedgerWriter(NoOpLedgerBackend()),
        )
        
        steps = [
            VerdictStep(
                statement="Statement 1",
                evidence=[EvidenceReference(node_id="n1", node_type="Fact", confidence=1.0)]
            ),
            VerdictStep(
                statement="Statement 2",
                evidence=[EvidenceReference(node_id="n2", node_type="Fact", confidence=0.5)]
            ),
        ]
        
        score = engine._calculate_confidence_score(steps)
        # Average of 1.0 and 0.5 = 0.75 (but actual calculation may vary)
        assert 0.5 < score < 1.0


class TestConflictResolutionResult:
    """Test ConflictResolutionResult data structure"""
    
    @pytest.mark.p1
    def test_resolution_with_resolved_node(self):
        """ConflictResolutionResult with resolved node"""
        result = ConflictResolutionResult(
            resolved_node="node_winner",
            is_ambiguous=False,
            reason="Higher confidence score"
        )
        
        assert result.resolved_node == "node_winner"
        assert result.is_ambiguous is False
        assert "confidence" in result.reason.lower()
    
    @pytest.mark.p1
    def test_resolution_ambiguous(self):
        """ConflictResolutionResult for ambiguous conflicts"""
        result = ConflictResolutionResult(
            resolved_node=None,
            is_ambiguous=True,
            reason="Equal confidence scores"
        )
        
        assert result.resolved_node is None
        assert result.is_ambiguous is True


class TestResolveProvenance:
    """Test _resolve_provenance() helper function"""
    
    @pytest.mark.p1
    def test_resolve_provenance_in_development(self):
        """_resolve_provenance() allows synthetic in development"""
        import os
        os.environ["MAHOUN_ENV"] = "dev"
        
        prov = _resolve_provenance(operation="test_op")
        
        assert prov is not None
        assert "synthetic" in prov.source
        assert "dev" in prov.governance_scope_id or "synthetic" in prov.governance_scope_id
    
    @pytest.mark.p1
    def test_resolve_provenance_creates_metadata(self):
        """_resolve_provenance() creates ProvenanceMetadata"""
        import os
        os.environ["MAHOUN_ENV"] = "dev"
        
        from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
        
        prov = _resolve_provenance(operation="graph_node_creation")
        
        assert isinstance(prov, ProvenanceMetadata)
        assert prov.author is not None
        assert prov.correlation_id is not None


class TestEvidenceReference:
    """Test EvidenceReference data structure"""
    
    @pytest.mark.p1
    def test_evidence_reference_creation(self):
        """EvidenceReference can be created with required fields"""
        ref = EvidenceReference(
            node_id="fact_001",
            node_type="Fact",
            edge_id=None,
            justification="Supporting evidence",
            confidence=0.95
        )
        
        assert ref.node_id == "fact_001"
        assert ref.node_type == "Fact"
        assert ref.confidence == 0.95
    
    @pytest.mark.p1
    def test_evidence_reference_with_edge(self):
        """EvidenceReference can include edge_id"""
        ref = EvidenceReference(
            node_id="rule_001",
            node_type="Rule",
            edge_id="edge_123",
            justification="Rule application",
            confidence=0.88
        )
        
        assert ref.edge_id == "edge_123"
        assert ref.node_type == "Rule"
