"""
Runtime Guardrails Enforcement Tests
=====================================

CRITICAL: These tests verify that runtime invariant guards are enforced correctly
and cannot be bypassed. Zero-hallucination guarantee depends on these guards.

Test Coverage:
- G1: EvidenceStepHasEvidence
- G2: EvidenceReferencesResolve
- G3: NonResurrection
- G4: ContradictionVisibility
- G5: ResolutionOrder
- Guard modes (OFF, WARN, STRICT, AUDIT)
- Non-bypassable enforcement

NO SIMPLIFICATION ALLOWED - Full enforcement validation required.
"""

import pytest
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mahoun.guardrails.runtime_invariants import (
    G1_EvidenceStepHasEvidence,
    G2_EvidenceReferencesResolve,
    G3_NonResurrection,
    G4_ContradictionVisibility,
    G5_ResolutionOrder,
    register_node,
    clear_registry,
    get_registry,
)
from mahoun.guardrails.exceptions import InvariantViolation
from mahoun.guardrails.modes import GuardMode
from mahoun.reasoning.evidence_linked_verdict import VerdictStep, EvidenceReference
from mahoun.graph.ultra_graph_builder import GraphNode


class TestG1_EvidenceStepHasEvidence:
    """Test G1: Each verdict step must have at least one evidence reference"""
    
    def setup_method(self):
        """Setup before each test"""
        clear_registry()
        # Save original guard mode
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        clear_registry()
        # Restore original guard mode
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_g1_passes_with_evidence(self):
        """G1 should pass when step has evidence"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        step = VerdictStep(
            statement="Test statement",
            evidence=[
                EvidenceReference(
                    node_id="node_1",
                    node_type="Fact",
                    justification="Test justification",
                    confidence=0.9
                )
            ]
        )
        
        # Should not raise
        G1_EvidenceStepHasEvidence(step, 0)
    
    def test_g1_fails_without_evidence_strict_mode(self):
        """G1 should raise InvariantViolation in STRICT mode when no evidence"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        step = VerdictStep(
            statement="Test statement",
            evidence=[]  # NO EVIDENCE
        )
        
        with pytest.raises(InvariantViolation) as exc_info:
            G1_EvidenceStepHasEvidence(step, 0)
        
        assert exc_info.value.invariant_name == "G1_EvidenceStepHasEvidence"
        assert "evidence_count" in exc_info.value.details
        assert exc_info.value.details["evidence_count"] == 0
    
    def test_g1_warns_without_evidence_warn_mode(self):
        """G1 should only warn in WARN mode when no evidence"""
        os.environ['MAHOUN_GUARD_MODE'] = 'WARN'
        
        step = VerdictStep(
            statement="Test statement",
            evidence=[]
        )
        
        # Should not raise, only warn
        G1_EvidenceStepHasEvidence(step, 0)
    
    def test_g1_silent_in_off_mode(self):
        """G1 should be silent in OFF mode"""
        os.environ['MAHOUN_GUARD_MODE'] = 'OFF'
        
        step = VerdictStep(
            statement="Test statement",
            evidence=[]
        )
        
        # Should not raise or warn
        G1_EvidenceStepHasEvidence(step, 0)
    
    def test_g1_multiple_evidence_passes(self):
        """G1 should pass with multiple evidence references"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        step = VerdictStep(
            statement="Test statement",
            evidence=[
                EvidenceReference("node_1", "Fact", justification="J1", confidence=0.9),
                EvidenceReference("node_2", "Rule", justification="J2", confidence=0.8),
                EvidenceReference("node_3", "Precedent", justification="J3", confidence=0.7),
            ]
        )
        
        # Should not raise
        G1_EvidenceStepHasEvidence(step, 0)


class TestG2_EvidenceReferencesResolve:
    """Test G2: Evidence references must resolve to real nodes"""
    
    def setup_method(self):
        """Setup before each test"""
        clear_registry()
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        clear_registry()
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_g2_passes_when_node_exists(self):
        """G2 should pass when referenced node exists in registry"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        # Register node
        node = GraphNode(
            id="node_1",
            label="Test Node",
            node_type="Fact",
            properties={}
        )
        register_node("node_1", node)
        
        evidence = EvidenceReference(
            node_id="node_1",
            node_type="Fact",
            justification="Test",
            confidence=0.9
        )
        
        registry = get_registry()
        
        # Should not raise
        G2_EvidenceReferencesResolve(evidence, registry)
    
    def test_g2_fails_when_node_missing_strict_mode(self):
        """G2 should raise InvariantViolation when node doesn't exist"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        evidence = EvidenceReference(
            node_id="nonexistent_node",
            node_type="Fact",
            justification="Test",
            confidence=0.9
        )
        
        registry = get_registry()
        
        with pytest.raises(InvariantViolation) as exc_info:
            G2_EvidenceReferencesResolve(evidence, registry)
        
        assert exc_info.value.invariant_name == "G2_EvidenceReferencesResolve"
        assert "node_id" in exc_info.value.details
        assert exc_info.value.details["node_id"] == "nonexistent_node"
    
    def test_g2_multiple_nodes_all_exist(self):
        """G2 should pass when all referenced nodes exist"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        # Register multiple nodes
        for i in range(3):
            node = GraphNode(
                id=f"node_{i}",
                label=f"Node {i}",
                node_type="Fact",
                properties={}
            )
            register_node(f"node_{i}", node)
        
        registry = get_registry()
        
        # Check all evidence references
        for i in range(3):
            evidence = EvidenceReference(
                node_id=f"node_{i}",
                node_type="Fact",
                justification=f"Test {i}",
                confidence=0.9
            )
            # Should not raise
            G2_EvidenceReferencesResolve(evidence, registry)
    
    def test_g2_fails_with_empty_node_id(self):
        """G2 should fail when node_id is empty"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        evidence = EvidenceReference(
            node_id="",  # EMPTY
            node_type="Fact",
            justification="Test",
            confidence=0.9
        )
        
        registry = get_registry()
        
        with pytest.raises(InvariantViolation):
            G2_EvidenceReferencesResolve(evidence, registry)


class TestG3_NonResurrection:
    """Test G3: Excluded nodes must not appear in resolved_nodes or verdict steps"""
    
    def setup_method(self):
        """Setup before each test"""
        clear_registry()
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        clear_registry()
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_g3_passes_when_no_resurrection(self):
        """G3 should pass when excluded nodes don't appear"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        excluded_nodes = {"excluded_1", "excluded_2"}
        
        resolved_nodes = {
            "node_1": GraphNode("node_1", "Node 1", "Fact", {}),
            "node_2": GraphNode("node_2", "Node 2", "Rule", {}),
        }
        
        verdict_steps = [
            VerdictStep(
                statement="Step 1",
                evidence=[
                    EvidenceReference("node_1", "Fact", "J1", 0.9),
                    EvidenceReference("node_2", "Rule", "J2", 0.8),
                ]
            )
        ]
        
        # Should not raise
        G3_NonResurrection(excluded_nodes, resolved_nodes, verdict_steps)
    
    def test_g3_fails_when_excluded_in_resolved_nodes(self):
        """G3 should fail when excluded node appears in resolved_nodes"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        excluded_nodes = {"excluded_1"}
        
        resolved_nodes = {
            "node_1": GraphNode("node_1", "Node 1", "Fact", {}),
            "excluded_1": GraphNode("excluded_1", "Excluded", "Rule", {}),  # RESURRECTION!
        }
        
        verdict_steps = []
        
        with pytest.raises(InvariantViolation) as exc_info:
            G3_NonResurrection(excluded_nodes, resolved_nodes, verdict_steps)
        
        assert exc_info.value.invariant_name == "G3_NonResurrection"
        assert "excluded_in_resolved" in exc_info.value.details
        assert "excluded_1" in exc_info.value.details["excluded_in_resolved"]
    
    def test_g3_fails_when_excluded_in_verdict_steps(self):
        """G3 should fail when excluded node appears in verdict steps"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        excluded_nodes = {"excluded_1"}
        
        resolved_nodes = {
            "node_1": GraphNode("node_1", "Node 1", "Fact", {}),
        }
        
        verdict_steps = [
            VerdictStep(
                statement="Step 1",
                evidence=[
                    EvidenceReference("node_1", "Fact", "J1", 0.9),
                    EvidenceReference("excluded_1", "Rule", "J2", 0.8),  # RESURRECTION!
                ]
            )
        ]
        
        with pytest.raises(InvariantViolation) as exc_info:
            G3_NonResurrection(excluded_nodes, resolved_nodes, verdict_steps)
        
        assert exc_info.value.invariant_name == "G3_NonResurrection"
        assert "excluded_in_steps" in exc_info.value.details
        assert "excluded_1" in exc_info.value.details["excluded_in_steps"]
    
    def test_g3_fails_when_excluded_in_both(self):
        """G3 should fail when excluded node appears in both places"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        excluded_nodes = {"excluded_1"}
        
        resolved_nodes = {
            "excluded_1": GraphNode("excluded_1", "Excluded", "Rule", {}),
        }
        
        verdict_steps = [
            VerdictStep(
                statement="Step 1",
                evidence=[
                    EvidenceReference("excluded_1", "Rule", "J1", 0.9),
                ]
            )
        ]
        
        with pytest.raises(InvariantViolation) as exc_info:
            G3_NonResurrection(excluded_nodes, resolved_nodes, verdict_steps)
        
        assert exc_info.value.invariant_name == "G3_NonResurrection"
        assert exc_info.value.details["total_violations"] >= 1


class TestG4_ContradictionVisibility:
    """Test G4: Unresolved contradictions must result in UNDETERMINED verdict"""
    
    def setup_method(self):
        """Setup before each test"""
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_g4_passes_with_no_conflicts(self):
        """G4 should pass when no unresolved conflicts"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        unresolved_conflicts = []
        final_verdict = "Plaintiff wins"
        
        # Should not raise
        G4_ContradictionVisibility(unresolved_conflicts, final_verdict)
    
    def test_g4_passes_with_conflicts_and_undetermined(self):
        """G4 should pass when conflicts exist and verdict is UNDETERMINED"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        unresolved_conflicts = ["Conflict 1", "Conflict 2"]
        final_verdict = "UNDETERMINED"
        
        # Should not raise
        G4_ContradictionVisibility(unresolved_conflicts, final_verdict)
    
    def test_g4_passes_with_conflicts_and_none_verdict(self):
        """G4 should pass when conflicts exist and verdict is None"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        unresolved_conflicts = ["Conflict 1"]
        final_verdict = None
        
        # Should not raise
        G4_ContradictionVisibility(unresolved_conflicts, final_verdict)
    
    def test_g4_fails_with_conflicts_and_determined_verdict(self):
        """G4 should fail when conflicts exist but verdict is determined"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        unresolved_conflicts = ["Conflict 1", "Conflict 2"]
        final_verdict = "Plaintiff wins"  # DETERMINED despite conflicts!
        
        with pytest.raises(InvariantViolation) as exc_info:
            G4_ContradictionVisibility(unresolved_conflicts, final_verdict)
        
        assert exc_info.value.invariant_name == "G4_ContradictionVisibility"
        assert "unresolved_conflicts_count" in exc_info.value.details
        assert exc_info.value.details["unresolved_conflicts_count"] == 2
    
    def test_g4_case_insensitive_undetermined(self):
        """G4 should accept case-insensitive UNDETERMINED"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        unresolved_conflicts = ["Conflict 1"]
        
        # All these should pass
        for verdict in ["UNDETERMINED", "undetermined", "Undetermined", "verdict is undetermined"]:
            G4_ContradictionVisibility(unresolved_conflicts, verdict)


class TestG5_ResolutionOrder:
    """Test G5: Verdict steps must be built from resolved_nodes only"""
    
    def setup_method(self):
        """Setup before each test"""
        clear_registry()
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        clear_registry()
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_g5_passes_when_all_nodes_resolved(self):
        """G5 should pass when all step nodes are in resolved_nodes"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        resolved_nodes = {
            "node_1": GraphNode("node_1", "Node 1", "Fact", {}),
            "node_2": GraphNode("node_2", "Node 2", "Rule", {}),
        }
        
        case_nodes = {
            "fact_1": GraphNode("fact_1", "Fact 1", "Fact", {}),
        }
        
        verdict_steps = [
            VerdictStep(
                statement="Step 1",
                evidence=[
                    EvidenceReference("node_1", "Fact", "J1", 0.9),
                    EvidenceReference("node_2", "Rule", "J2", 0.8),
                    EvidenceReference("fact_1", "Fact", "J3", 0.7),
                ]
            )
        ]
        
        # Should not raise
        G5_ResolutionOrder(verdict_steps, resolved_nodes, case_nodes)
    
    def test_g5_fails_when_node_not_in_resolved(self):
        """G5 should fail when step references unresolved node"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        resolved_nodes = {
            "node_1": GraphNode("node_1", "Node 1", "Fact", {}),
        }
        
        case_nodes = {}
        
        verdict_steps = [
            VerdictStep(
                statement="Step 1",
                evidence=[
                    EvidenceReference("node_1", "Fact", "J1", 0.9),
                    EvidenceReference("unresolved_node", "Rule", "J2", 0.8),  # NOT RESOLVED!
                ]
            )
        ]
        
        with pytest.raises(InvariantViolation) as exc_info:
            G5_ResolutionOrder(verdict_steps, resolved_nodes, case_nodes)
        
        assert exc_info.value.invariant_name == "G5_ResolutionOrder"
        assert "missing_in_resolved" in exc_info.value.details
        assert "unresolved_node" in exc_info.value.details["missing_in_resolved"]
    
    def test_g5_accepts_case_nodes(self):
        """G5 should accept nodes from case_nodes (facts)"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        resolved_nodes = {}
        
        case_nodes = {
            "fact_1": GraphNode("fact_1", "Fact 1", "Fact", {}),
            "fact_2": GraphNode("fact_2", "Fact 2", "Fact", {}),
        }
        
        verdict_steps = [
            VerdictStep(
                statement="Step 1",
                evidence=[
                    EvidenceReference("fact_1", "Fact", "J1", 0.9),
                    EvidenceReference("fact_2", "Fact", "J2", 0.8),
                ]
            )
        ]
        
        # Should not raise
        G5_ResolutionOrder(verdict_steps, resolved_nodes, case_nodes)


class TestGuardModes:
    """Test guard mode behavior across all guards"""
    
    def setup_method(self):
        """Setup before each test"""
        clear_registry()
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        clear_registry()
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_strict_mode_raises_exceptions(self):
        """STRICT mode should raise InvariantViolation"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        step = VerdictStep(statement="Test", evidence=[])
        
        with pytest.raises(InvariantViolation):
            G1_EvidenceStepHasEvidence(step, 0)
    
    def test_audit_mode_raises_exceptions(self):
        """AUDIT mode should raise InvariantViolation (with extra logging)"""
        os.environ['MAHOUN_GUARD_MODE'] = 'AUDIT'
        
        step = VerdictStep(statement="Test", evidence=[])
        
        with pytest.raises(InvariantViolation):
            G1_EvidenceStepHasEvidence(step, 0)
    
    def test_warn_mode_no_exception(self):
        """WARN mode should not raise exception"""
        os.environ['MAHOUN_GUARD_MODE'] = 'WARN'
        
        step = VerdictStep(statement="Test", evidence=[])
        
        # Should not raise
        G1_EvidenceStepHasEvidence(step, 0)
    
    def test_off_mode_no_exception(self):
        """OFF mode should not raise exception"""
        os.environ['MAHOUN_GUARD_MODE'] = 'OFF'
        
        step = VerdictStep(statement="Test", evidence=[])
        
        # Should not raise
        G1_EvidenceStepHasEvidence(step, 0)


class TestNonBypassableEnforcement:
    """Test that critical guards cannot be bypassed"""
    
    def setup_method(self):
        """Setup before each test"""
        clear_registry()
        self.original_mode = os.environ.get('MAHOUN_GUARD_MODE')
    
    def teardown_method(self):
        """Cleanup after each test"""
        clear_registry()
        if self.original_mode:
            os.environ['MAHOUN_GUARD_MODE'] = self.original_mode
        elif 'MAHOUN_GUARD_MODE' in os.environ:
            del os.environ['MAHOUN_GUARD_MODE']
    
    def test_critical_guards_enforced_in_strict(self):
        """Critical guards must be enforced in STRICT mode"""
        os.environ['MAHOUN_GUARD_MODE'] = 'STRICT'
        
        # All critical guards should raise on violation
        step_no_evidence = VerdictStep(statement="Test", evidence=[])
        
        with pytest.raises(InvariantViolation):
            G1_EvidenceStepHasEvidence(step_no_evidence, 0)
    
    def test_guard_decorator_prevents_bypass(self):
        """@guard decorator should prevent bypassing critical guards"""
        # This test verifies the decorator is applied
        # The actual enforcement is tested in individual guard tests
        
        from mahoun.guardrails.runtime_invariants import G1_EvidenceStepHasEvidence
        
        # Check that guard has the decorator applied
        assert hasattr(G1_EvidenceStepHasEvidence, '__wrapped__') or \
               hasattr(G1_EvidenceStepHasEvidence, '_guard_critical'), \
               "G1 should have @guard decorator applied"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
