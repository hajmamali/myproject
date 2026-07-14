"""
Orchestrator Tests - Task 1.1 Acceptance Criteria
=================================================

Tests for ValidationOrchestrator core functionality.
"""

import pytest
from pathlib import Path

from mahoun.preproduction import (
    ValidationOrchestrator,
    DomainValidator,
    ValidationResult,
    ValidationStatus,
    Finding,
    FindingSeverity,
)
from mahoun.preproduction.evidence_collector import EvidenceCollector


class MockValidator(DomainValidator):
    """Mock validator for testing"""
    
    def __init__(self, name: str, evidence_collector, *, should_fail: bool = False):
        super().__init__(name, evidence_collector)
        self.should_fail = should_fail
    
    def validate(self) -> ValidationResult:
        """Mock validation"""
        self._start_time = 0.0
        self._end_time = 0.001
        
        if self.should_fail:
            self.add_finding(
                severity=FindingSeverity.P0_CRITICAL,
                message=f"{self.name} failed intentionally",
                evidence={"test": True}
            )
        
        return self._build_result(additional_evidence={"mock": True})
    
    def get_dependencies(self) -> list[str]:
        """No dependencies"""
        return []


class TestOrchestratorBasic:
    """Basic orchestrator functionality"""
    
    def test_orchestrator_creates_successfully(self, tmp_path):
        """Test orchestrator instantiation"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="test",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(
            manifest=manifest,
            workspace_root=tmp_path
        )
        
        assert orchestrator.manifest.version == "1.0"
        assert orchestrator.workspace_root == tmp_path
    
    def test_validator_registration(self, tmp_path):
        """Test validator registration and graph building"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="test",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(manifest=manifest, workspace_root=tmp_path)
        evidence_collector = EvidenceCollector(workspace_root=tmp_path)
        
        validator = MockValidator("test_validator", evidence_collector)
        orchestrator.register_validator(validator)
        
        assert "test_validator" in orchestrator.validators
        assert "test_validator" in orchestrator.graph.nodes
    
    def test_single_validator_execution(self, tmp_path):
        """Test running a single validator"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="test",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(manifest=manifest, workspace_root=tmp_path)
        evidence_collector = EvidenceCollector(workspace_root=tmp_path)
        
        validator = MockValidator("test_validator", evidence_collector)
        orchestrator.register_validator(validator)
        
        result = orchestrator.run_validation(profile="test", fail_fast=False)
        
        assert result.overall_status == ValidationStatus.PASS
        assert len(result.results) == 1
        assert result.results[0].validator_id == "test_validator"
    
    def test_failing_validator(self, tmp_path):
        """Test validator that reports P0 failure"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="test",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(manifest=manifest, workspace_root=tmp_path)
        evidence_collector = EvidenceCollector(workspace_root=tmp_path)
        
        validator = MockValidator("failing_validator", evidence_collector, should_fail=True)
        orchestrator.register_validator(validator)
        
        result = orchestrator.run_validation(profile="test", fail_fast=False)
        
        assert result.overall_status == ValidationStatus.FAIL
        assert len(result.blockers) == 1
        assert result.blockers[0].severity == FindingSeverity.P0_CRITICAL
        assert not result.is_production_ready


class TestDependencyGraph:
    """Dependency graph and execution order tests"""
    
    def test_topological_sort_no_dependencies(self):
        """Test topological sort with independent validators"""
        from mahoun.preproduction.orchestrator import ValidationGraph
        
        graph = ValidationGraph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_node("C")
        
        order = graph.topological_sort()
        
        # All should be present
        assert set(order) == {"A", "B", "C"}
        assert len(order) == 3
    
    def test_topological_sort_with_dependencies(self):
        """Test topological sort respects dependencies"""
        from mahoun.preproduction.orchestrator import ValidationGraph
        
        graph = ValidationGraph()
        graph.add_edge("B", "A")  # B depends on A
        graph.add_edge("C", "A")  # C depends on A
        
        order = graph.topological_sort()
        
        # A must come before B and C
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
    
    def test_circular_dependency_detection(self):
        """Test circular dependency raises error"""
        from mahoun.preproduction.orchestrator import ValidationGraph
        
        graph = ValidationGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")  # Circular!
        
        with pytest.raises(ValueError, match="Circular dependency"):
            graph.topological_sort()
    
    def test_execution_groups(self):
        """Test parallel execution groups"""
        from mahoun.preproduction.orchestrator import ValidationGraph
        
        graph = ValidationGraph()
        graph.add_node("A")
        graph.add_node("B")
        graph.add_edge("C", "A")  # C depends on A
        graph.add_edge("C", "B")  # C depends on B
        
        groups = graph.get_execution_groups()
        
        # First group: A and B (parallel)
        # Second group: C (after A and B)
        assert len(groups) == 2
        assert set(groups[0]) == {"A", "B"}
        assert groups[1] == ["C"]


class TestComplianceScoring:
    """Compliance score calculation tests"""
    
    def test_perfect_score(self, tmp_path):
        """Test 100% compliance (no findings)"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="test",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(manifest=manifest, workspace_root=tmp_path)
        evidence_collector = EvidenceCollector(workspace_root=tmp_path)
        
        validator = MockValidator("perfect_validator", evidence_collector)
        orchestrator.register_validator(validator)
        
        result = orchestrator.run_validation(profile="test")
        
        assert result.compliance_score == 1.0
        assert result.is_production_ready
    
    def test_score_with_p0_blocker(self, tmp_path):
        """Test compliance score drops with P0 findings"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="test",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(manifest=manifest, workspace_root=tmp_path)
        evidence_collector = EvidenceCollector(workspace_root=tmp_path)
        
        validator = MockValidator("failing_validator", evidence_collector, should_fail=True)
        orchestrator.register_validator(validator)
        
        result = orchestrator.run_validation(profile="test")
        
        # P0 finding deducts 0.10
        assert result.compliance_score == 0.90
        assert not result.is_production_ready  # Has blocker


class TestReportGeneration:
    """Report generation tests"""
    
    def test_markdown_report_generation(self, tmp_path):
        """Test report contains expected sections"""
        from mahoun.preproduction.models import ValidationManifest
        
        manifest = ValidationManifest(
            version="1.0",
            profile="production",
            validators=[],
        )
        
        orchestrator = ValidationOrchestrator(manifest=manifest, workspace_root=tmp_path)
        evidence_collector = EvidenceCollector(workspace_root=tmp_path)
        
        validator = MockValidator("test_validator", evidence_collector)
        orchestrator.register_validator(validator)
        
        result = orchestrator.run_validation(profile="production")
        report = orchestrator.generate_report(result)
        
        assert "# Pre-Production Validation Report" in report
        assert "**Profile**: production" in report
        assert "**Compliance Score**:" in report
        assert "## Validator Results" in report
        assert "test_validator" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
