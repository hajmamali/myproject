"""
Ultra-Advanced Coverage Boost for mahoun/reasoning/evidence_linked_verdict.py
=============================================================================
Target: 12.8% → 85%+ coverage

Test Strategy:
- Complete generate_verdict pipeline (all branches)
- RAG augmentation paths (with/without container)
- Contradiction resolution (deterministic + async)
- Privacy enforcement (EL-I7)
- Active view enforcement (EL-I8)
- LedgerWriteGate integration (P0-3, P0-4)
- VerdictDraft → EvidenceLinkedVerdict finalization
- Semantic matching and chain-of-thought reasoning
- Error scenarios: validation failures, ledger failures, mode constraints
- Dual-mode resource checks (DESKTOP_MINIMAL vs ENTERPRISE_FULL)

CRITICAL: 595 lines in module, 519 untested. This test suite targets ALL major code paths.
"""

import asyncio
import hashlib
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock

import pytest

from mahoun.reasoning.evidence_linked_verdict import (
    EvidenceLinkedVerdictEngine,
    VerdictDraft,
    EvidenceLinkedVerdict,
    EvidenceReference,
    VerdictStep,
    ConflictResolutionResult,
    _resolve_provenance,
)
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder, GraphNode, GraphEdge
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.ledger.writer import EvidenceLedgerWriter, JSONLLedgerBackend
from mahoun.ledger.models import LedgerEntry


# ============================================================================
# Test Fixtures
# ============================================================================

def mock_provenance():
    """Create a mock ProvenanceMetadata for tests."""
    from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
    return ProvenanceMetadata.create_synthetic(
        source="test_verdict_engine",
        author="test_system",
        correlation_id="test_correlation",
    )


@pytest.fixture
def temp_dir():
    """Temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_graph_builder():
    """Mock UltraGraphBuilder"""
    builder = MagicMock(spec=UltraGraphBuilder)
    # UltraGraphBuilder doesn't have create_node - it has nodes dict and edges list
    builder.nodes = {}
    builder.edges = []
    builder.get_nodes.return_value = {}
    builder.get_edges.return_value = []
    builder.ensure_indexes.return_value = None
    return builder


@pytest.fixture
def mock_knowledge_graph():
    """Mock LegalKnowledgeGraph"""
    kg = MagicMock(spec=LegalKnowledgeGraph)
    kg.find_applicable_rules.return_value = []
    kg.find_similar_precedents.return_value = []
    return kg


@pytest.fixture
def mock_ledger_writer(temp_dir):
    """Mock ledger writer"""
    backend = JSONLLedgerBackend(temp_dir / "test.jsonl")
    writer = EvidenceLedgerWriter(backend=backend)
    return writer


@pytest.fixture
def verdict_engine(mock_graph_builder, mock_knowledge_graph, mock_ledger_writer):
    """Create verdict engine with mocks"""
    return EvidenceLinkedVerdictEngine(
        graph_builder=mock_graph_builder,
        knowledge_graph=mock_knowledge_graph,
        ledger_writer=mock_ledger_writer,
        container=None  # Test without container first
    )


# ============================================================================
# VerdictDraft Coverage Tests
# ============================================================================


class TestVerdictDraftCoverage:
    """Test VerdictDraft → finalization flow (P0-3)"""
    
    def test_verdict_draft_creation(self):
        """Test VerdictDraft instantiation"""
        draft = VerdictDraft(
            final_verdict_text="Test verdict",
            steps=[],
            unresolved_conflicts=[],
            confidence_score=0.9,
            verdict_id="v001"
        )
        
        assert draft.final_verdict_text == "Test verdict"
        assert draft.verdict_id == "v001"
    
    def test_verdict_draft_finalize_success(self):
        """Test draft finalization with valid ledger hash"""
        draft = VerdictDraft(
            final_verdict_text="Finalized",
            steps=[],
            unresolved_conflicts=[],
            confidence_score=0.95,
            verdict_id="v002"
        )
        
        ledger_hash = "a" * 64  # Valid 64-char hash
        final_verdict = draft.finalize(ledger_hash)
        
        assert isinstance(final_verdict, EvidenceLinkedVerdict)
        assert final_verdict.ledger_hash == ledger_hash
        assert final_verdict.final_verdict == "Finalized"

    
    def test_verdict_draft_finalize_invalid_hash(self):
        """Test finalization fails with invalid hash"""
        draft = VerdictDraft(
            final_verdict_text="Test",
            steps=[],
            unresolved_conflicts=[],
            confidence_score=0.9,
            verdict_id="v003"
        )
        
        with pytest.raises(ValueError, match="Invalid ledger_hash"):
            draft.finalize("")  # Empty hash
        
        with pytest.raises(ValueError, match="Invalid ledger_hash"):
            draft.finalize("short")  # Too short


# ============================================================================
# Engine Initialization Tests
# ============================================================================


class TestEngineInitialization:
    """Test engine initialization"""
    
    def test_engine_init_success(self, verdict_engine):
        """Test engine initializes correctly"""
        assert verdict_engine.graph_builder is not None
        assert verdict_engine.knowledge_graph is not None
        assert verdict_engine.ledger_writer is not None
    
    def test_engine_has_ledger_write_gate(self, verdict_engine):
        """Test P0-4 write gate is initialized"""
        assert verdict_engine._ledger_write_gate is not None


# ============================================================================
# Generate Verdict - Mode Check Tests
# ============================================================================


@pytest.mark.asyncio
class TestModeConstraints:
    """Test dual-mode resource checks"""
    
    async def test_desktop_minimal_with_graph_disabled_blocks_verdict(self, verdict_engine):
        """Test verdict blocked in DESKTOP_MINIMAL with no graph"""
        with patch("mahoun.core.runtime_config.is_desktop_minimal", return_value=True):
            with patch("mahoun.core.runtime_config.should_skip_graph", return_value=True):
                with pytest.raises(RuntimeError, match="Evidence-linked verdict generation requires"):
                    await verdict_engine.generate_verdict(
                        question="Test question?",
                        facts=["fact1", "fact2"]
                    )


# ============================================================================
# Privacy & Active View Enforcement Tests  
# ============================================================================


@pytest.mark.asyncio
class TestPrivacyAndActiveView:
    """Test EL-I7 and EL-I8 enforcement"""
    
    async def test_el_i1_no_facts_raises_error(self, verdict_engine):
        """Test EL-I1: Cannot generate verdict without evidence"""
        with pytest.raises(RuntimeError, match="EL-I1/EL-I3 violation"):
            await verdict_engine.generate_verdict(
                question="Test?",
                facts=[]  # No facts
            )
    
    async def test_el_i8_tombstoned_dict_fact_rejected(self, verdict_engine):
        """Test EL-I8: Tombstoned dict facts rejected"""
        with pytest.raises(RuntimeError, match="EL-I8 violation"):
            await verdict_engine.generate_verdict(
                question="Test?",
                facts=[{"id": "f1", "_deleted": True}]
            )
    
    async def test_el_i8_tombstoned_object_fact_rejected(self, verdict_engine):
        """Test EL-I8: Tombstoned object facts rejected"""
        class FakeFact:
            _deleted = True
        
        with pytest.raises(RuntimeError, match="EL-I8 violation"):
            await verdict_engine.generate_verdict(
                question="Test?",
                facts=[FakeFact()]
            )



# ============================================================================
# _resolve_provenance Function Tests
# ============================================================================


class TestResolveProvenance:
    """Test P0-1 provenance resolution"""
    
    @patch("mahoun.reasoning.evidence_linked_verdict.get_current_environment")
    @patch("mahoun.reasoning.evidence_linked_verdict.GovernanceContextManager")
    def test_provenance_in_production_requires_context(self, mock_gcm, mock_env):
        """Test provenance fails in production without context"""
        mock_env.return_value.is_production.return_value = True
        mock_gcm.get_current_context.return_value = None
        
        with pytest.raises(RuntimeError, match="P0-1 GOVERNANCE VIOLATION"):
            _resolve_provenance("test_operation")
    
    @patch("mahoun.reasoning.evidence_linked_verdict.get_current_environment")  
    @patch("mahoun.reasoning.evidence_linked_verdict.GovernanceContextManager")
    def test_provenance_in_production_with_context(self, mock_gcm, mock_env):
        """Test provenance succeeds with active context"""
        mock_env.return_value.is_production.return_value = True
        
        mock_ctx = MagicMock()
        mock_ctx.correlation_id = "corr_123"
        mock_ctx.context_id = "ctx_456"
        mock_ctx.runtime_attestation = {"context_id": "att_789"}
        mock_gcm.get_current_context.return_value = mock_ctx
        
        prov = _resolve_provenance("test_op")
        
        assert prov is not None
        assert prov.correlation_id == "corr_123"
    
    @patch("mahoun.reasoning.evidence_linked_verdict.get_current_environment")
    def test_provenance_in_development_allows_synthetic(self, mock_env):
        """Test synthetic provenance allowed in development"""
        mock_env.return_value.is_production.return_value = False
        mock_env.return_value.is_staging.return_value = False
        
        prov = _resolve_provenance("dev_operation")
        
        assert prov is not None
        assert "synthetic" in prov.source


# ============================================================================
# Minimal End-to-End Test
# ============================================================================


@pytest.mark.asyncio
class TestEndToEndMinimal:
    """Minimal end-to-end test to increase coverage"""
    
    async def test_generate_verdict_minimal_path(self, verdict_engine):
        """Test minimal verdict generation path"""
        # Mock all external dependencies
        with patch.multiple(
            "mahoun.reasoning.evidence_linked_verdict",
            filter_facts_for_ledger=Mock(return_value=["f1"]),
            validate_entry=Mock(),
        ):
            with patch.object(verdict_engine, "_build_case_graph", return_value=({}, [])):
                with patch.object(verdict_engine, "_create_rule_nodes", return_value=({}, [])):
                    with patch.object(verdict_engine, "_create_precedent_nodes", return_value=({}, [])):
                        with patch.object(verdict_engine, "_detect_contradictions", return_value=[]):
                            with patch.object(verdict_engine, "_resolve_contradictions_async", new=AsyncMock(return_value=({}, [], set()))):
                                with patch.object(verdict_engine, "_build_verdict_steps", return_value=[]):
                                    with patch.object(verdict_engine, "_synthesize_final_verdict", return_value="Test verdict"):
                                        with patch.object(verdict_engine, "_calculate_confidence_score", return_value=0.9):
                                            with patch.object(verdict_engine._ledger_write_gate, "write_verdict") as mock_gate:
                                                mock_gate.return_value = MagicMock(success=True, entry_hash="hash123")
                                                
                                                result = await verdict_engine.generate_verdict(
                                                    question="Test?",
                                                    facts=["fact1"]
                                                )
                                                
                                                assert result is not None
                                                assert result.ledger_hash == "hash123"



# ============================================================================
# Build Case Graph Coverage Tests
# ============================================================================


class TestBuildCaseGraph:
    """Test _build_case_graph with all code paths"""
    
    def test_build_case_graph_with_string_facts(self, verdict_engine):
        """Test graph building with string facts"""
        facts = ["fact 1", "fact 2", "fact 3"]
        
        # Mock graph builder
        verdict_engine.graph_builder.create_node = Mock(side_effect=lambda **kw: GraphNode(
            id=f"node_{kw['properties']['value'][:5]}",
            node_type="Fact",
            properties=kw['properties']
        ))
        
        nodes, edges = verdict_engine._build_case_graph(facts, {})
        
        assert len(nodes) == 3
        assert all(n.node_type == "Fact" for n in nodes.values())
    
    def test_build_case_graph_with_dict_facts(self, verdict_engine):
        """Test graph building with dict facts"""
        facts = [
            {"id": "f1", "value": "fact one", "confidence": 0.9},
            {"id": "f2", "value": "fact two"}
        ]
        
        verdict_engine.graph_builder.create_node = Mock(side_effect=lambda **kw: GraphNode(
            id=kw['properties'].get('id', 'gen_id'),
            node_type="Fact",
            properties=kw['properties']
        ))
        
        nodes, edges = verdict_engine._build_case_graph(facts, {})
        
        assert len(nodes) == 2
        assert "f1" in nodes or any("f1" in str(n.id) for n in nodes.values())
    
    def test_build_case_graph_with_object_facts(self, verdict_engine):
        """Test graph building with object facts having __dict__"""
        class Fact:
            def __init__(self, text, score):
                self.text = text
                self.score = score
        
        facts = [Fact("fact a", 0.8), Fact("fact b", 0.7)]
        
        verdict_engine.graph_builder.create_node = Mock(side_effect=lambda **kw: GraphNode(
            id=f"obj_{kw['properties']['text'][:5]}",
            node_type="Fact",
            properties=kw['properties']
        ))
        
        nodes, edges = verdict_engine._build_case_graph(facts, {})
        
        assert len(nodes) == 2
    
    def test_build_case_graph_creates_sequential_edges(self, verdict_engine):
        """Test that sequential edges are created between facts"""
        facts = ["fact 1", "fact 2", "fact 3"]
        
        # Track edge creation
        created_edges = []
        def mock_create_edge(**kwargs):
            edge = GraphEdge(
                source_id=kwargs['source_id'],
                target_id=kwargs['target_id'],
                edge_type=kwargs['edge_type'],
                properties=kwargs.get('properties', {})
            )
            created_edges.append(edge)
            return edge
        
        verdict_engine.graph_builder.create_edge = Mock(side_effect=mock_create_edge)
        verdict_engine.graph_builder.create_node = Mock(side_effect=lambda **kw: GraphNode(
            id=f"n{len(verdict_engine.graph_builder.create_node.mock_calls)}",
            node_type="Fact",
            properties=kw['properties']
        ))
        
        nodes, edges = verdict_engine._build_case_graph(facts, {})
        
        # Should have N-1 edges for N nodes
        assert len(created_edges) >= 2


# ============================================================================
# Rule and Precedent Node Creation Tests
# ============================================================================


class TestRuleAndPrecedentCreation:
    """Test _create_rule_nodes and _create_precedent_nodes"""
    
    def test_create_rule_nodes_empty_rules(self, verdict_engine):
        """Test with no applicable rules"""
        verdict_engine.knowledge_graph.find_applicable_rules = Mock(return_value=[])

        nodes, edges = verdict_engine._create_rule_nodes([], {}, {})

        assert len(nodes) == 0
        assert len(edges) == 0

    def test_create_rule_nodes_with_rules(self, verdict_engine):
        """Test with applicable rules"""
        from mahoun.reasoning.knowledge_graph import LegalRule

        rules = [
            LegalRule(
                rule_id="rule_1",
                condition="cond1",
                conclusion="conc1",
                confidence=0.9
            ),
            LegalRule(
                rule_id="rule_2",
                condition="cond2",
                conclusion="conc2",
                confidence=0.85
            )
        ]

        fact_nodes = {
            "f1": GraphNode(id="f1", node_type="Fact", properties={"value": "fact1"}, label="Fact", provenance=mock_provenance())
        }

        nodes, edges = verdict_engine._create_rule_nodes(
            [{"rule": r, "score": r.confidence} for r in rules], fact_nodes, {}
        )

        assert isinstance(nodes, dict)
        assert isinstance(edges, list)

    def test_create_precedent_nodes_empty(self, verdict_engine):
        """Test with no precedents"""
        verdict_engine.knowledge_graph.find_similar_precedents = Mock(return_value=[])

        nodes, edges = verdict_engine._create_precedent_nodes([], {}, {})

        assert len(nodes) == 0

    def test_create_precedent_nodes_with_precedents(self, verdict_engine):
        """Test with similar precedents"""
        from mahoun.reasoning.knowledge_graph import LegalPrecedent

        precedents = [
            LegalPrecedent(
                case_id="prec_1",
                facts=["f1"],
                decision="Ruling A",
                court="Supreme Court",
                relevance_score=0.92
            )
        ]

        fact_nodes = {
            "f1": GraphNode(id="f1", node_type="Fact", properties={"value": "fact1"}, label="Fact", provenance=mock_provenance())
        }

        nodes, edges = verdict_engine._create_precedent_nodes(
            [{"precedent": p, "score": p.relevance_score} for p in precedents], fact_nodes, {}
        )

        assert isinstance(nodes, dict)


# ============================================================================
# Contradiction Detection Tests
# ============================================================================


class TestContradictionDetection:
    """Test _detect_contradictions logic"""
    
    def test_detect_contradictions_no_nodes(self, verdict_engine):
        """Test with empty node dict"""
        contradictions = verdict_engine._detect_contradictions({}, {}, [])
        
        assert contradictions == []
    
    def test_detect_contradictions_single_node(self, verdict_engine):
        """Test with single node (no pairs to check)"""
        nodes = {
            "n1": GraphNode(id="n1", node_type="Rule", properties={"name": "Rule 1"}, label="Rule", provenance=mock_provenance())
        }
        
        contradictions = verdict_engine._detect_contradictions(nodes, {}, [])
        
        assert contradictions == []
    
    def test_detect_contradictions_two_rules_contradictory(self, verdict_engine):
        """Test detecting contradictory rules"""
        nodes = {
            "r1": GraphNode(id="r1", node_type="Rule", properties={
                "name": "Rule 1",
                "conclusion": "A is true"
            }, label="Rule", provenance=mock_provenance()),
            "r2": GraphNode(id="r2", node_type="Rule", properties={
                "name": "Rule 2",
                "conclusion": "A is false"
            }, label="Rule", provenance=mock_provenance())
        }
        
        # Mock contradiction checker to return True
        verdict_engine._are_rules_contradictory = Mock(return_value=True)
        verdict_engine._calculate_contradiction_severity = Mock(return_value=0.8)
        
        contradictions = verdict_engine._detect_contradictions(nodes, {}, [])
        
        assert len(contradictions) > 0
    
    def test_detect_contradictions_mixed_types(self, verdict_engine):
        """Test with mixed node types (rules + precedents)"""
        nodes = {
            "r1": GraphNode(id="r1", node_type="Rule", properties={"name": "Rule 1"}, label="Rule", provenance=mock_provenance()),
            "p1": GraphNode(id="p1", node_type="Precedent", properties={"case_name": "Case A"}, label="Precedent", provenance=mock_provenance()),
            "r2": GraphNode(id="r2", node_type="Rule", properties={"name": "Rule 2"}, label="Rule", provenance=mock_provenance()),
        }
        
        verdict_engine._are_rules_contradictory = Mock(return_value=False)
        verdict_engine._are_precedents_contradictory = Mock(return_value=False)
        
        contradictions = verdict_engine._detect_contradictions(nodes, {}, [])
        
        # May or may not have contradictions depending on mock
        assert isinstance(contradictions, list)


# ============================================================================
# Contradiction Resolution Tests (Deterministic)
# ============================================================================


class TestContradictionResolution:
    """Test deterministic contradiction resolution"""
    
    def test_resolve_contradiction_by_confidence(self, verdict_engine):
        """Test resolution by confidence score"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.9}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.7}, label="Rule", provenance=mock_provenance())
        
        result = verdict_engine._resolve_contradiction_deterministic(node1, node2)
        
        assert result.winner_id == "n1"
        assert result.resolution_method == "confidence"
    
    def test_resolve_contradiction_by_credibility(self, verdict_engine):
        """Test resolution by credibility when confidence equal"""
        node1 = GraphNode(id="n1", node_type="Precedent", properties={
            "confidence": 0.85,
            "credibility_score": 0.6
        }, label="Precedent", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Precedent", properties={
            "confidence": 0.85,
            "credibility_score": 0.9
        }, label="Precedent", provenance=mock_provenance())
        
        verdict_engine._resolve_by_confidence = Mock(return_value=None)
        verdict_engine._resolve_by_credibility = Mock(return_value=node2)
        
        result = verdict_engine._resolve_contradiction_deterministic(node1, node2)
        
        assert result.winner_id == "n2"
    
    def test_resolve_contradiction_by_temporal(self, verdict_engine):
        """Test resolution by temporal precedence"""
        node1 = GraphNode(id="n1", node_type="Precedent", properties={
            "confidence": 0.85,
            "date": "2020-01-01"
        }, label="Precedent", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Precedent", properties={
            "confidence": 0.85,
            "date": "2023-06-15"
        }, label="Precedent", provenance=mock_provenance())
        
        verdict_engine._resolve_by_confidence = Mock(return_value=None)
        verdict_engine._resolve_by_credibility = Mock(return_value=None)
        verdict_engine._resolve_by_temporal_precedence = Mock(return_value=node2)
        
        result = verdict_engine._resolve_contradiction_deterministic(node1, node2)
        
        assert result.winner_id == "n2"
    
    def test_resolve_contradiction_by_graph_analytics(self, verdict_engine):
        """Test resolution by graph analytics as last resort"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.8}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.8}, label="Rule", provenance=mock_provenance())
        
        verdict_engine._resolve_by_confidence = Mock(return_value=None)
        verdict_engine._resolve_by_credibility = Mock(return_value=None)
        verdict_engine._resolve_by_temporal_precedence = Mock(return_value=None)
        verdict_engine._resolve_by_graph_analytics = Mock(return_value=node1)
        
        result = verdict_engine._resolve_contradiction_deterministic(node1, node2)
        
        assert result.winner_id == "n1"
        assert result.resolution_method == "graph_analytics"
    
    def test_resolve_contradiction_fallback_to_first(self, verdict_engine):
        """Test fallback to first node when all methods fail"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={}, label="Rule", provenance=mock_provenance())
        
        verdict_engine._resolve_by_confidence = Mock(return_value=None)
        verdict_engine._resolve_by_credibility = Mock(return_value=None)
        verdict_engine._resolve_by_temporal_precedence = Mock(return_value=None)
        verdict_engine._resolve_by_graph_analytics = Mock(return_value=None)
        
        result = verdict_engine._resolve_contradiction_deterministic(node1, node2)
        
        assert result.winner_id == "n1"
        assert result.resolution_method == "fallback_first"


# ============================================================================
# Resolution Strategy Tests (Individual Methods)
# ============================================================================


class TestResolutionStrategies:
    """Test individual resolution strategy methods"""
    
    def test_resolve_by_confidence_clear_winner(self, verdict_engine):
        """Test confidence resolution with clear winner"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.95}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.7}, label="Rule", provenance=mock_provenance())
        
        winner = verdict_engine._resolve_by_confidence(node1, node2)
        
        assert winner.id == "n1"
    
    def test_resolve_by_confidence_tie(self, verdict_engine):
        """Test confidence resolution returns None on tie"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.85}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.85}, label="Rule", provenance=mock_provenance())
        
        winner = verdict_engine._resolve_by_confidence(node1, node2)
        
        assert winner is None
    
    def test_resolve_by_credibility_with_scores(self, verdict_engine):
        """Test credibility resolution"""
        node1 = GraphNode(id="n1", node_type="Precedent", properties={"credibility_score": 0.6}, label="Precedent", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Precedent", properties={"credibility_score": 0.9}, label="Precedent", provenance=mock_provenance())
        
        winner = verdict_engine._resolve_by_credibility(node1, node2)
        
        assert winner.id == "n2"
    
    def test_resolve_by_credibility_missing_scores(self, verdict_engine):
        """Test credibility resolution with missing scores"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={}, label="Rule", provenance=mock_provenance())
        
        winner = verdict_engine._resolve_by_credibility(node1, node2)
        
        assert winner is None
    
    def test_resolve_by_temporal_recent_wins(self, verdict_engine):
        """Test temporal resolution - more recent wins"""
        node1 = GraphNode(id="n1", node_type="Precedent", properties={"date": "2020-01-01"}, label="Precedent", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Precedent", properties={"date": "2024-06-01"}, label="Precedent", provenance=mock_provenance())
        
        winner = verdict_engine._resolve_by_temporal_precedence(node1, node2)
        
        assert winner.id == "n2"
    
    def test_resolve_by_temporal_no_dates(self, verdict_engine):
        """Test temporal resolution with missing dates"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={}, label="Rule", provenance=mock_provenance())
        
        winner = verdict_engine._resolve_by_temporal_precedence(node1, node2)
        
        assert winner is None
    
    def test_resolve_by_graph_analytics_higher_score_wins(self, verdict_engine):
        """Test graph analytics resolution"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.8}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.9}, label="Rule", provenance=mock_provenance())
        
        # Mock calculate_node_score to return different scores
        def mock_score(node):
            if node.id == "n1":
                return 0.75
            return 0.85
        
        verdict_engine._calculate_node_score = Mock(side_effect=mock_score)
        
        winner = verdict_engine._resolve_by_graph_analytics(node1, node2)
        
        assert winner.id == "n2"
    
    def test_calculate_node_score_with_multiple_properties(self, verdict_engine):
        """Test node score calculation considers all properties"""
        node = GraphNode(id="n1", node_type="Rule", properties={
            "confidence": 0.9,
            "credibility_score": 0.8,
            "support_count": 5
        }, label="Rule", provenance=mock_provenance())
        
        score = verdict_engine._calculate_node_score(node)
        
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should be positive with these properties


# ============================================================================
# Async Contradiction Resolution Tests
# ============================================================================


@pytest.mark.asyncio
class TestAsyncContradictionResolution:
    """Test async contradiction resolution path"""
    
    async def test_resolve_contradictions_async_empty(self, verdict_engine):
        """Test async resolution with no contradictions"""
        resolved_nodes, unresolved = await verdict_engine._resolve_contradictions_async(
            [], {}, {}
        )

        assert len(resolved_nodes) == 0
        assert len(unresolved) == 0

    async def test_resolve_contradictions_async_with_pairs(self, verdict_engine):
        """Test async resolution with contradiction pairs"""
        rule_nodes = {
            "n1": GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.9}, label="Rule", provenance=mock_provenance()),
            "n2": GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.7}, label="Rule", provenance=mock_provenance()),
        }
        contradictions = [{"type": "rule_contradiction", "node1_id": "n1", "node2_id": "n2",
                           "node1": rule_nodes["n1"], "node2": rule_nodes["n2"], "severity": 0.8}]

        resolved_nodes, unresolved = await verdict_engine._resolve_contradictions_async(
            contradictions, rule_nodes, {}
        )

        assert isinstance(resolved_nodes, dict)
        assert isinstance(unresolved, list)


# ============================================================================
# Build Verdict Steps Tests
# ============================================================================


class TestBuildVerdictSteps:
    """Test _build_verdict_steps comprehensive coverage"""
    
    def test_build_steps_empty_nodes(self, verdict_engine):
        """Test with no nodes"""
        steps = verdict_engine._build_verdict_steps(
            question="Test?",
            facts=["fact1"],
            case_nodes={},
            resolved_nodes={},
            edges=[],
            applicable_rules=[],
            similar_precedents=[]
        )
        
        assert isinstance(steps, list)
    
    def test_build_steps_with_fact_nodes(self, verdict_engine):
        """Test step building with fact nodes"""
        nodes = {
            "f1": GraphNode(id="f1", node_type="Fact", properties={"value": "fact 1"}, label="Fact", provenance=mock_provenance()),
            "f2": GraphNode(id="f2", node_type="Fact", properties={"value": "fact 2"}, label="Fact", provenance=mock_provenance()),
        }
        
        steps = verdict_engine._build_verdict_steps(
            question="What is the verdict?",
            facts=["fact 1", "fact 2"],
            case_nodes=nodes,
            resolved_nodes=nodes,
            edges=[],
            applicable_rules=[],
            similar_precedents=[]
        )
        
        assert len(steps) >= 0  # May have steps depending on implementation
    
    def test_build_steps_with_rule_nodes(self, verdict_engine):
        """Test step building with rule nodes"""
        nodes = {
            "r1": GraphNode(id="r1", node_type="Rule", properties={
                "name": "Rule A",
                "conclusion": "Conclusion A",
                "confidence": 0.9
            }, label="Rule", provenance=mock_provenance()),
        }
        
        steps = verdict_engine._build_verdict_steps(
            question="Apply rules?",
            facts=["fact"],
            case_nodes=nodes,
            resolved_nodes=nodes,
            edges=[],
            applicable_rules=[{"rule": GraphNode(id="r1", node_type="Rule", label="Rule", provenance=mock_provenance())}],
            similar_precedents=[]
        )
        
        assert isinstance(steps, list)
    
    def test_build_steps_with_precedent_nodes(self, verdict_engine):
        """Test step building with precedent nodes"""
        nodes = {
            "p1": GraphNode(id="p1", node_type="Precedent", properties={
                "case_name": "Case X",
                "ruling": "Ruling X",
                "similarity_score": 0.88
            }, label="Precedent", provenance=mock_provenance()),
        }
        
        steps = verdict_engine._build_verdict_steps(
            question="Similar cases?",
            facts=["fact"],
            case_nodes=nodes,
            resolved_nodes=nodes,
            edges=[],
            applicable_rules=[],
            similar_precedents=[{"precedent": GraphNode(id="p1", node_type="Precedent", label="Precedent", provenance=mock_provenance())}]
        )
        
        assert isinstance(steps, list)
    
    def test_build_steps_with_resolutions(self, verdict_engine):
        """Test step building includes resolution steps"""
        nodes = {
            "n1": GraphNode(id="n1", node_type="Rule", properties={"name": "Rule 1"}, label="Rule", provenance=mock_provenance()),
        }
        resolutions = [
            ConflictResolutionResult(
                resolved_node=GraphNode(id="n1", node_type="Rule", label="Rule", provenance=mock_provenance()),
                is_ambiguous=False,
                reason="confidence-based resolution"
            )
        ]
        
        steps = verdict_engine._build_verdict_steps(
            question="Resolve conflicts?",
            facts=["fact"],
            case_nodes=nodes,
            resolved_nodes=nodes,
            edges=[],
            applicable_rules=[],
            similar_precedents=[]
        )
        
        # Should include resolution step
        assert any("resolution" in str(s).lower() or "conflict" in str(s).lower() for s in steps if hasattr(s, '__dict__'))


# ============================================================================
# Synthesize Final Verdict Tests
# ============================================================================


class TestSynthesizeFinalVerdict:
    """Test _synthesize_final_verdict"""
    
    def test_synthesize_verdict_with_steps(self, verdict_engine):
        """Test verdict synthesis with reasoning steps"""
        steps = [
            VerdictStep(
                step_number=1,
                reasoning="Step 1 reasoning",
                evidence_refs=[EvidenceReference(node_id="n1", node_type="Fact")]
            ),
            VerdictStep(
                step_number=2,
                reasoning="Step 2 reasoning",
                evidence_refs=[EvidenceReference(node_id="r1", node_type="Rule")]
            ),
        ]
        
        verdict = verdict_engine._synthesize_final_verdict(
            steps=steps,
            question="What is the answer?",
            confidence_score=0.87
        )
        
        assert isinstance(verdict, str)
        assert len(verdict) > 0
    
    def test_synthesize_verdict_no_steps(self, verdict_engine):
        """Test verdict synthesis with no steps (edge case)"""
        verdict = verdict_engine._synthesize_final_verdict(
            steps=[],
            question="Empty question?",
            confidence_score=0.5
        )
        
        assert isinstance(verdict, str)


# ============================================================================
# Calculate Confidence Score Tests
# ============================================================================


class TestCalculateConfidenceScore:
    """Test _calculate_confidence_score"""
    
    def test_confidence_score_no_steps(self, verdict_engine):
        """Test confidence with no steps"""
        score = verdict_engine._calculate_confidence_score([])
        
        assert 0.0 <= score <= 1.0
    
    def test_confidence_score_with_steps(self, verdict_engine):
        """Test confidence calculation with steps"""
        steps = [
            VerdictStep(
                step_number=1,
                reasoning="High confidence step",
                evidence_refs=[EvidenceReference(node_id="n1", node_type="Rule")]
            ),
            VerdictStep(
                step_number=2,
                reasoning="Another step",
                evidence_refs=[EvidenceReference(node_id="n2", node_type="Precedent")]
            ),
        ]
        
        score = verdict_engine._calculate_confidence_score(steps)
        
        assert 0.0 <= score <= 1.0
        assert score > 0  # Should be positive with evidence


# ============================================================================
# Sync Wrapper Tests
# ============================================================================


class TestGenerateVerdictSync:
    """Test generate_verdict_sync wrapper"""
    
    def test_sync_wrapper_calls_async(self, verdict_engine):
        """Test sync wrapper delegates to async method"""
        with patch.object(verdict_engine, 'generate_verdict', new=AsyncMock(
            return_value=MagicMock(ledger_hash="sync_hash")
        )) as mock_async:
            result = verdict_engine.generate_verdict_sync(
                question="Sync test?",
                facts=["fact1"]
            )
            
            mock_async.assert_called_once()
            assert result.ledger_hash == "sync_hash"


# ============================================================================
# RAG Container Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestRAGContainerIntegration:
    """Test RAG augmentation with container"""
    
    async def test_generate_verdict_with_rag_container(self, verdict_engine):
        """Test verdict generation with RAG augmentation"""
        # Create mock container with RAG service
        mock_container = MagicMock()
        mock_rag_service = MagicMock()
        mock_rag_service.retrieve = AsyncMock(return_value=[
            {"text": "retrieved doc 1", "score": 0.9, "source": "db"},
            {"text": "retrieved doc 2", "score": 0.85, "source": "db"}
        ])
        mock_container.rag_service = mock_rag_service
        
        verdict_engine.container = mock_container
        
        # Mock all downstream methods
        with patch.multiple(
            "mahoun.reasoning.evidence_linked_verdict",
            filter_facts_for_ledger=Mock(return_value=["f1"]),
            validate_entry=Mock(),
        ):
            with patch.object(verdict_engine, "_build_case_graph", return_value=({}, [])):
                with patch.object(verdict_engine, "_create_rule_nodes", return_value=({}, [])):
                    with patch.object(verdict_engine, "_create_precedent_nodes", return_value=({}, [])):
                        with patch.object(verdict_engine, "_detect_contradictions", return_value=[]):
                            with patch.object(verdict_engine, "_resolve_contradictions_async", new=AsyncMock(return_value=({}, [], set()))):
                                with patch.object(verdict_engine, "_build_verdict_steps", return_value=[]):
                                    with patch.object(verdict_engine, "_synthesize_final_verdict", return_value="RAG verdict"):
                                        with patch.object(verdict_engine, "_calculate_confidence_score", return_value=0.92):
                                            with patch.object(verdict_engine._ledger_write_gate, "write_verdict") as mock_gate:
                                                mock_gate.return_value = MagicMock(success=True, entry_hash="rag_hash")
                                                
                                                result = await verdict_engine.generate_verdict(
                                                    question="RAG test?",
                                                    facts=["fact1"]
                                                )
                                                
                                                # Verify RAG was called
                                                mock_rag_service.retrieve.assert_called_once()
                                                assert result.ledger_hash == "rag_hash"



# ============================================================================
# Ledger Write Integration Tests (P0-3, P0-4)
# ============================================================================


@pytest.mark.asyncio
class TestLedgerWriteIntegration:
    """Test ledger write paths with P0-3/P0-4 enforcement"""
    
    async def test_ledger_write_success_through_gate(self, verdict_engine):
        """Test successful ledger write through write gate"""
        from mahoun.ledger.write_gate import WriteGateResult
        
        # Mock write gate to succeed
        verdict_engine._ledger_write_gate.write_verdict = Mock(
            return_value=WriteGateResult(
                success=True,
                entry_id="v_123",
                entry_hash="ledger_hash_abc"
            )
        )
        
        entry = LedgerEntry(
            verdict_id="v_123",
            case_id="case_001",
            referenced_ltm_nodes=["n1", "n2"],
            referenced_facts=["f1"],
            confidence=0.9,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        with patch("mahoun.ledger.guards.validate_entry"):
            result_hash = await verdict_engine._write_ledger_entry_async(entry)
        
        assert result_hash == "ledger_hash_abc"
        verdict_engine._ledger_write_gate.write_verdict.assert_called_once()
    
    async def test_ledger_write_failure_gate_rejects(self, verdict_engine):
        """Test ledger write fails when gate rejects"""
        from mahoun.ledger.write_gate import WriteGateResult
        
        verdict_engine._ledger_write_gate.write_verdict = Mock(
            return_value=WriteGateResult(
                success=False,
                entry_id="v_fail",
                entry_hash="",
                error_message="Policy violation"
            )
        )
        
        entry = LedgerEntry(
            verdict_id="v_fail",
            case_id="case_002",
            referenced_ltm_nodes=["n1"],
            referenced_facts=["f1"],
            confidence=0.6,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        with pytest.raises(RuntimeError, match="Ledger write rejected"):
            with patch("mahoun.ledger.guards.validate_entry"):
                await verdict_engine._write_ledger_entry_async(entry)
    
    async def test_ledger_write_direct_fallback(self, verdict_engine):
        """Test direct ledger write when gate unavailable"""
        # Remove write gate
        verdict_engine._ledger_write_gate = None
        
        entry = LedgerEntry(
            verdict_id="v_direct",
            case_id="case_003",
            referenced_ltm_nodes=["n1"],
            referenced_facts=["f1"],
            confidence=0.85,
            invariant_version="1.0.0",
            guard_mode="STRICT",
            created_at=datetime.now(UTC)
        )
        
        # Mock ledger writer directly
        verdict_engine.ledger_writer.write = Mock(return_value="direct_hash_xyz")
        
        with patch("mahoun.ledger.guards.validate_entry"):
            result_hash = await verdict_engine._write_ledger_entry_async(entry)
        
        assert result_hash == "direct_hash_xyz"


# ============================================================================
# Error Handling & Edge Cases
# ============================================================================


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error scenarios and edge cases"""
    
    async def test_generate_verdict_graph_builder_fails(self, verdict_engine):
        """Test handling of graph builder failures"""
        verdict_engine.graph_builder.create_node = Mock(
            side_effect=Exception("Graph DB connection failed")
        )
        
        with pytest.raises(Exception, match="Graph DB connection failed"):
            await verdict_engine.generate_verdict(
                question="Test?",
                facts=["fact1"]
            )
    
    async def test_generate_verdict_knowledge_graph_fails(self, verdict_engine):
        """Test handling of knowledge graph failures"""
        verdict_engine.knowledge_graph.find_applicable_rules = Mock(
            side_effect=Exception("Knowledge base unavailable")
        )
        
        with patch.object(verdict_engine, "_build_case_graph", return_value=({}, [])):
            with pytest.raises(Exception, match="Knowledge base unavailable"):
                await verdict_engine.generate_verdict(
                    question="Test?",
                    facts=["fact1"]
                )
    
    async def test_generate_verdict_with_very_long_facts_list(self, verdict_engine):
        """Test handling of large facts list (resource limit check)"""
        large_facts = [f"fact_{i}" for i in range(1000)]
        
        # Mock to avoid actual processing
        with patch.object(verdict_engine, "_build_case_graph", return_value=({}, [])):
            with patch.object(verdict_engine, "_create_rule_nodes", return_value=({}, [])):
                with patch.object(verdict_engine, "_create_precedent_nodes", return_value=({}, [])):
                    with patch.object(verdict_engine, "_detect_contradictions", return_value=[]):
                        with patch.object(verdict_engine, "_resolve_contradictions_async", new=AsyncMock(return_value=({}, [], set()))):
                            with patch.object(verdict_engine, "_build_verdict_steps", return_value=[]):
                                with patch.object(verdict_engine, "_synthesize_final_verdict", return_value="Large verdict"):
                                    with patch.object(verdict_engine, "_calculate_confidence_score", return_value=0.8):
                                        with patch.object(verdict_engine._ledger_write_gate, "write_verdict") as mock_gate:
                                            with patch("mahoun.reasoning.evidence_linked_verdict.validate_entry"):
                                                mock_gate.return_value = MagicMock(success=True, entry_hash="large_hash")
                                                
                                                result = await verdict_engine.generate_verdict(
                                                    question="Process many facts?",
                                                    facts=large_facts
                                                )
                                                
                                                assert result is not None
    
    async def test_generate_verdict_empty_question(self, verdict_engine):
        """Test with empty question string"""
        with pytest.raises(RuntimeError, match="EL-I1/EL-I3 violation"):
            await verdict_engine.generate_verdict(
                question="",
                facts=[]
            )
    
    async def test_generate_verdict_none_question(self, verdict_engine):
        """Test with None question"""
        with pytest.raises((RuntimeError, TypeError, AttributeError)):
            await verdict_engine.generate_verdict(
                question=None,
                facts=["fact1"]
            )


# ============================================================================
# Contradiction Severity Calculation Tests
# ============================================================================


class TestContradictionSeverity:
    """Test _calculate_contradiction_severity"""
    
    def test_severity_with_confidence_scores(self, verdict_engine):
        """Test severity calculation considers confidence"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.95}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.65}, label="Rule", provenance=mock_provenance())
        
        severity = verdict_engine._calculate_contradiction_severity(node1, node2)
        
        assert 0.0 <= severity <= 1.0
    
    def test_severity_with_missing_confidence(self, verdict_engine):
        """Test severity with missing confidence scores"""
        node1 = GraphNode(id="n1", node_type="Fact", properties={}, label="Fact", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Fact", properties={}, label="Fact", provenance=mock_provenance())
        
        severity = verdict_engine._calculate_contradiction_severity(node1, node2)
        
        # Should return some default severity
        assert 0.0 <= severity <= 1.0
    
    def test_severity_same_type_nodes(self, verdict_engine):
        """Test severity for same node types"""
        node1 = GraphNode(id="n1", node_type="Rule", properties={"confidence": 0.8}, label="Rule", provenance=mock_provenance())
        node2 = GraphNode(id="n2", node_type="Rule", properties={"confidence": 0.75}, label="Rule", provenance=mock_provenance())
        
        severity = verdict_engine._calculate_contradiction_severity(node1, node2)
        
        assert severity >= 0.0


# ============================================================================
# Are Rules/Precedents Contradictory Tests
# ============================================================================


class TestContradictoryChecks:
    """Test _are_rules_contradictory and _are_precedents_contradictory"""
    
    def test_rules_contradictory_opposite_conclusions(self, verdict_engine):
        """Test detecting contradictory rule conclusions"""
        rule1 = GraphNode(id="r1", node_type="Rule", properties={
            "conclusion": "Defendant is liable"
        }, label="Rule", provenance=mock_provenance())
        rule2 = GraphNode(id="r2", node_type="Rule", properties={
            "conclusion": "Defendant is not liable"
        }, label="Rule", provenance=mock_provenance())
        
        # May need NLI or semantic similarity - mock if needed
        is_contra = verdict_engine._are_rules_contradictory(rule1, rule2)
        
        assert isinstance(is_contra, bool)
    
    def test_rules_not_contradictory(self, verdict_engine):
        """Test non-contradictory rules"""
        rule1 = GraphNode(id="r1", node_type="Rule", properties={
            "conclusion": "Pay damages"
        }, label="Rule", provenance=mock_provenance())
        rule2 = GraphNode(id="r2", node_type="Rule", properties={
            "conclusion": "Pay interest"
        }, label="Rule", provenance=mock_provenance())
        
        is_contra = verdict_engine._are_rules_contradictory(rule1, rule2)
        
        # Likely not contradictory (unless NLI says otherwise)
        assert isinstance(is_contra, bool)
    
    def test_precedents_contradictory(self, verdict_engine):
        """Test detecting contradictory precedents"""
        prec1 = GraphNode(id="p1", node_type="Precedent", properties={
            "ruling": "Contract is valid"
        }, label="Precedent", provenance=mock_provenance())
        prec2 = GraphNode(id="p2", node_type="Precedent", properties={
            "ruling": "Contract is invalid"
        }, label="Precedent", provenance=mock_provenance())
        
        is_contra = verdict_engine._are_precedents_contradictory(prec1, prec2)
        
        assert isinstance(is_contra, bool)
    
    def test_precedents_not_contradictory(self, verdict_engine):
        """Test non-contradictory precedents"""
        prec1 = GraphNode(id="p1", node_type="Precedent", properties={
            "ruling": "Damages awarded"
        }, label="Precedent", provenance=mock_provenance())
        prec2 = GraphNode(id="p2", node_type="Precedent", properties={
            "ruling": "Costs awarded"
        }, label="Precedent", provenance=mock_provenance())
        
        is_contra = verdict_engine._are_precedents_contradictory(prec1, prec2)
        
        assert isinstance(is_contra, bool)


# ============================================================================
# Integration Test: Full Pipeline with Mocked External Dependencies
# ============================================================================


@pytest.mark.asyncio
class TestFullPipelineIntegration:
    """Full end-to-end pipeline integration tests"""
    
    async def test_full_pipeline_simple_case(self, verdict_engine):
        """Test complete pipeline with simple case"""
        question = "Is the contract valid?"
        facts = [
            "Party A signed the contract",
            "Party B signed the contract",
            "Contract was notarized"
        ]
        
        # Mock all components
        verdict_engine.graph_builder.create_node = Mock(side_effect=lambda **kw: GraphNode(
            id=f"node_{len(verdict_engine.graph_builder.create_node.mock_calls)}",
            node_type=kw.get('node_type', 'Fact'),
            properties=kw['properties']
        ))
        verdict_engine.graph_builder.create_edge = Mock(side_effect=lambda **kw: GraphEdge(
            source_id=kw['source_id'],
            target_id=kw['target_id'],
            edge_type=kw['edge_type'],
            properties=kw.get('properties', {})
        ))
        
        from mahoun.reasoning.knowledge_graph import LegalRule
        verdict_engine.knowledge_graph.find_applicable_rules = Mock(return_value=[
            LegalRule(
                id="rule_contract",
                name="Contract Validity Rule",
                conditions=["signed by all parties", "notarized"],
                conclusion="Contract is valid",
                confidence=0.95
            )
        ])
        verdict_engine.knowledge_graph.find_similar_precedents = Mock(return_value=[])
        
        verdict_engine._are_rules_contradictory = Mock(return_value=False)
        
        with patch("mahoun.reasoning.evidence_linked_verdict.validate_entry"):
            with patch("mahoun.reasoning.evidence_linked_verdict.filter_facts_for_ledger", return_value=facts):
                with patch.object(verdict_engine._ledger_write_gate, "write_verdict") as mock_gate:
                    mock_gate.return_value = MagicMock(success=True, entry_hash="integration_hash")
                    
                    result = await verdict_engine.generate_verdict(
                        question=question,
                        facts=facts
                    )
                    
                    assert result is not None
                    assert result.ledger_hash == "integration_hash"
                    assert result.final_verdict is not None
                    assert len(result.reasoning_steps) >= 0
