"""
Tests for Coverage Validator
============================

Test suite for ultra-advanced coverage analysis and gap prioritization.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mahoun.preproduction.validators.coverage_validator import (
    CoverageValidator,
    ModuleCoverage,
    CoverageGap,
)
from mahoun.preproduction.models import ValidationStatus, FindingSeverity


@pytest.fixture
def mock_evidence_collector():
    """Mock evidence collector."""
    collector = Mock()
    collector.collect_file_lines = Mock(return_value={})
    collector.collect_ast_analysis = Mock(return_value={})
    collector.collect_command_output = Mock(return_value={})
    return collector


@pytest.fixture
def sample_coverage_data():
    """Sample coverage.json data."""
    return {
        "meta": {"version": "7.2.0"},
        "files": {
            "/workspace/mahoun/core/exceptions.py": {
                "summary": {
                    "num_statements": 100,
                    "missing_lines": 20,
                    "excluded_lines": 5,
                    "num_branches": 10,
                    "num_partial_branches": 2,
                    "percent_covered": 80.0,
                }
            },
            "/workspace/mahoun/security/api_keys.py": {
                "summary": {
                    "num_statements": 200,
                    "missing_lines": 110,
                    "excluded_lines": 0,
                    "num_branches": 20,
                    "num_partial_branches": 5,
                    "percent_covered": 45.0,
                }
            },
            "/workspace/mahoun/ledger/writer.py": {
                "summary": {
                    "num_statements": 150,
                    "missing_lines": 48,
                    "excluded_lines": 2,
                    "num_branches": 15,
                    "num_partial_branches": 3,
                    "percent_covered": 68.0,
                }
            },
        },
        "totals": {
            "num_statements": 450,
            "missing_lines": 178,
            "percent_covered": 60.4,
        }
    }


@pytest.fixture
def sample_baseline_content():
    """Sample TEST_COVERAGE_BASELINE.md content."""
    return """
# Test Coverage Baseline

## Priority Modules

Priority Order:
  1. mahoun/security/api_keys.py: 45% → 80%
  2. mahoun/security/rbac.py: 52% → 85%
  3. mahoun/ledger/writer.py: 68% → 90%
  4. mahoun/reasoning/evidence_linked_verdict.py: 71% → 85%
  5. mahoun/graph/neo4j/operations.py: 34% → 75%
"""


class TestModuleCoverage:
    """Test ModuleCoverage dataclass."""
    
    def test_missing_percent_calculation(self):
        """Test missing percentage calculation."""
        module = ModuleCoverage(
            module_path="test.py",
            statements=100,
            missing=25,
            excluded=5,
            coverage_percent=75.0,
        )
        
        assert module.missing_percent == 25.0
    
    def test_missing_percent_zero_statements(self):
        """Test missing percent when no statements."""
        module = ModuleCoverage(
            module_path="test.py",
            statements=0,
            missing=0,
            excluded=0,
            coverage_percent=0.0,
        )
        
        assert module.missing_percent == 0.0
    
    def test_is_critical_detection(self):
        """Test critical module detection."""
        critical = ModuleCoverage(
            module_path="mahoun/core/exceptions.py",
            statements=100,
            missing=20,
            excluded=0,
        )
        assert critical.is_critical
        
        non_critical = ModuleCoverage(
            module_path="mahoun/pipelines/utils.py",
            statements=50,
            missing=10,
            excluded=0,
        )
        assert not non_critical.is_critical
    
    def test_all_critical_paths(self):
        """Test all critical path patterns."""
        critical_paths = [
            "mahoun/core/models.py",
            "mahoun/security/rbac.py",
            "mahoun/ledger/writer.py",
            "mahoun/reasoning/chain.py",
            "mahoun/graph/neo4j/connection.py",
            "mahoun/core/governance/boundary.py",
        ]
        
        for path in critical_paths:
            module = ModuleCoverage(path, 100, 10, 0)
            assert module.is_critical, f"{path} should be critical"


class TestCoverageValidator:
    """Test CoverageValidator."""
    
    def test_initialization(self, mock_evidence_collector, tmp_path):
        """Test validator initialization."""
        validator = CoverageValidator(
            evidence_collector=mock_evidence_collector,
            workspace_root=tmp_path
        )
        
        assert validator.name == "coverage-validator"
        assert validator.workspace_root == tmp_path
        assert validator.coverage_json_path == tmp_path / "coverage.json"
        assert validator.baseline_path == tmp_path / "TEST_COVERAGE_BASELINE.md"
    
    def test_dependencies(self, mock_evidence_collector, tmp_path):
        """Test validator dependencies."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        deps = validator.get_dependencies()
        
        assert "test-classification-validator" in deps
    
    def test_parse_coverage_json(self, mock_evidence_collector, tmp_path, sample_coverage_data):
        """Test parsing coverage.json."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        modules = validator._parse_coverage_json(sample_coverage_data)
        
        assert len(modules) == 3
        assert any("exceptions.py" in path for path in modules.keys())
        assert any("api_keys.py" in path for path in modules.keys())
        
        # Check api_keys.py details
        api_keys_module = next(m for path, m in modules.items() if "api_keys.py" in path)
        assert api_keys_module.statements == 200
        assert api_keys_module.missing == 110
        assert api_keys_module.coverage_percent == 45.0
    
    def test_parse_baseline_targets(self, mock_evidence_collector, tmp_path, sample_baseline_content):
        """Test parsing baseline targets from markdown."""
        # Write baseline file
        baseline_path = tmp_path / "TEST_COVERAGE_BASELINE.md"
        baseline_path.write_text(sample_baseline_content)
        
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        targets = validator._parse_baseline_targets()
        
        assert "mahoun/security/api_keys.py" in targets
        assert targets["mahoun/security/api_keys.py"] == 80.0
        assert targets["mahoun/ledger/writer.py"] == 90.0
    
    def test_parse_baseline_missing_file(self, mock_evidence_collector, tmp_path):
        """Test baseline parsing when file missing."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        targets = validator._parse_baseline_targets()
        
        # Should return default targets
        assert len(targets) > 0
        assert "mahoun/security/api_keys.py" in targets
        assert targets["mahoun/security/api_keys.py"] == 80.0
    
    def test_identify_coverage_gaps(self, mock_evidence_collector, tmp_path, sample_coverage_data):
        """Test identifying coverage gaps."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        modules = validator._parse_coverage_json(sample_coverage_data)
        
        # Get actual module paths from parsed data
        actual_paths = list(modules.keys())
        api_keys_path = next((p for p in actual_paths if "api_keys.py" in p), None)
        writer_path = next((p for p in actual_paths if "writer.py" in p), None)
        
        assert api_keys_path is not None, f"api_keys.py not found in {actual_paths}"
        assert writer_path is not None, f"writer.py not found in {actual_paths}"
        
        # Simplified baseline for test
        baseline = {
            api_keys_path: 80.0,  # Current: 45%, gap: 35%
            writer_path: 90.0,    # Current: 68%, gap: 22%
        }
        
        gaps = validator._identify_coverage_gaps(modules, baseline)
        
        assert len(gaps) >= 2
        
        # Check api_keys gap
        api_keys_gap = next(g for g in gaps if "api_keys.py" in g.module.module_path)
        assert api_keys_gap.current_coverage == 45.0
        assert api_keys_gap.target_coverage == 80.0
        assert api_keys_gap.gap_percent == 35.0
        assert api_keys_gap.priority_score > 0
    
    def test_gap_prioritization(self, mock_evidence_collector, tmp_path):
        """Test gap prioritization logic."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        # Create test modules
        critical_module = ModuleCoverage(
            module_path="mahoun/core/governance/boundary.py",
            statements=200,
            missing=100,
            excluded=0,
            coverage_percent=50.0,
        )
        
        non_critical_module = ModuleCoverage(
            module_path="mahoun/pipelines/utils.py",
            statements=50,
            missing=25,
            excluded=0,
            coverage_percent=50.0,
        )
        
        modules = {
            "mahoun/core/governance/boundary.py": critical_module,
            "mahoun/pipelines/utils.py": non_critical_module,
        }
        
        baseline = {
            "mahoun/core/governance/boundary.py": 90.0,  # Gap: 40%
            "mahoun/pipelines/utils.py": 80.0,           # Gap: 30%
        }
        
        gaps = validator._identify_coverage_gaps(modules, baseline)
        
        # Critical module gap should have higher priority
        critical_gap = next(g for g in gaps if "boundary.py" in g.module.module_path)
        non_critical_gap = next(g for g in gaps if "utils.py" in g.module.module_path)
        
        assert critical_gap.priority_score > non_critical_gap.priority_score
    
    def test_check_critical_paths(self, mock_evidence_collector, tmp_path):
        """Test critical path coverage checking."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        # Create test data with low coverage critical module
        modules = {
            "mahoun/security/api_keys.py": ModuleCoverage(
                module_path="mahoun/security/api_keys.py",
                statements=200,
                missing=110,
                excluded=0,
                coverage_percent=45.0,  # Below 75% minimum
            ),
            "mahoun/core/exceptions.py": ModuleCoverage(
                module_path="mahoun/core/exceptions.py",
                statements=100,
                missing=0,
                excluded=0,
                coverage_percent=100.0,  # Good
            ),
        }
        
        findings = validator._check_critical_paths(modules)
        
        # Should have P0 finding for low coverage critical module
        assert len(findings) > 0
        p0_findings = [f for f in findings if f.severity == FindingSeverity.P0_CRITICAL]
        assert len(p0_findings) > 0
        assert "critical modules below" in p0_findings[0].message.lower()
    
    def test_untested_critical_module(self, mock_evidence_collector, tmp_path):
        """Test detection of untested critical modules."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        modules = {
            "mahoun/core/governance/policies.py": ModuleCoverage(
                module_path="mahoun/core/governance/policies.py",
                statements=150,
                missing=150,
                excluded=0,
                coverage_percent=0.0,  # ZERO coverage
            ),
        }
        
        findings = validator._check_critical_paths(modules)
        
        # Should have P0 finding for untested module
        zero_coverage_findings = [
            f for f in findings 
            if "zero test coverage" in f.message.lower()
        ]
        assert len(zero_coverage_findings) > 0
        assert zero_coverage_findings[0].severity == FindingSeverity.P0_CRITICAL
    
    def test_calculate_overall_coverage(self, mock_evidence_collector, tmp_path, sample_coverage_data):
        """Test overall coverage calculation."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        overall = validator._calculate_overall_coverage(sample_coverage_data)
        
        assert overall == 60.4
    
    def test_estimate_tests_needed(self, mock_evidence_collector, tmp_path):
        """Test estimation of tests needed."""
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        gaps = [
            CoverageGap(
                module=ModuleCoverage("test1.py", 100, 50, 0, coverage_percent=50.0),
                current_coverage=50.0,
                target_coverage=90.0,
                gap_percent=40.0,
                priority_score=50.0,
            ),
            CoverageGap(
                module=ModuleCoverage("test2.py", 200, 100, 0, coverage_percent=50.0),
                current_coverage=50.0,
                target_coverage=90.0,
                gap_percent=40.0,
                priority_score=50.0,
            ),
        ]
        
        estimated = validator._estimate_tests_needed(gaps)
        
        # 150 missing statements / 50 = 3 tests
        assert estimated == 3
    
    @patch("mahoun.preproduction.validators.coverage_validator.subprocess.run")
    def test_generate_coverage_data_success(self, mock_run, mock_evidence_collector, tmp_path, sample_coverage_data):
        """Test successful coverage data generation."""
        # Mock subprocess success
        mock_run.return_value = MagicMock(returncode=0)
        
        # Mock coverage.json creation
        coverage_path = tmp_path / "coverage.json"
        coverage_path.write_text(json.dumps(sample_coverage_data))
        
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        result = validator._generate_coverage_data()
        
        assert result is not None
        assert "files" in result
    
    @patch("mahoun.preproduction.validators.coverage_validator.subprocess.run")
    def test_generate_coverage_data_timeout(self, mock_run, mock_evidence_collector, tmp_path):
        """Test coverage generation timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("pytest", 120)
        
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        result = validator._generate_coverage_data()
        
        # Should return None on timeout
        assert result is None
        # Finding is added via add_finding() which appends to self.findings
        # Check that a finding was added
        assert len(validator.findings) > 0
    
    def test_full_validation_with_mock_data(self, mock_evidence_collector, tmp_path, sample_coverage_data, sample_baseline_content):
        """Test full validation workflow with mocked data."""
        # Setup files
        coverage_path = tmp_path / "coverage.json"
        coverage_path.write_text(json.dumps(sample_coverage_data))
        
        baseline_path = tmp_path / "TEST_COVERAGE_BASELINE.md"
        baseline_path.write_text(sample_baseline_content)
        
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        # Mock subprocess to avoid actually running pytest
        with patch.object(validator, "_generate_coverage_data", return_value=sample_coverage_data):
            result = validator.validate()
        
        assert result.validator_id == "coverage-validator"
        assert result.status in (ValidationStatus.PASS, ValidationStatus.FAIL, ValidationStatus.WARNING)
        assert "overall_coverage_percent" in result.evidence
        assert result.evidence["overall_coverage_percent"] == 60.4


class TestCoverageGapDataclass:
    """Test CoverageGap dataclass."""
    
    def test_coverage_gap_creation(self):
        """Test creating coverage gap."""
        module = ModuleCoverage(
            module_path="test.py",
            statements=100,
            missing=40,
            excluded=0,
            coverage_percent=60.0,
        )
        
        gap = CoverageGap(
            module=module,
            current_coverage=60.0,
            target_coverage=90.0,
            gap_percent=30.0,
            priority_score=75.5,
        )
        
        assert gap.module == module
        assert gap.gap_percent == 30.0
        assert gap.priority_score == 75.5


class TestIntegrationScenarios:
    """Integration test scenarios."""
    
    def test_meets_target_coverage_passes(self, mock_evidence_collector, tmp_path):
        """Test that meeting target coverage passes."""
        # Mock data with good coverage
        good_coverage_data = {
            "files": {
                "/workspace/mahoun/core/test.py": {
                    "summary": {
                        "num_statements": 100,
                        "missing_lines": 5,
                        "excluded_lines": 0,
                        "percent_covered": 95.0,
                    }
                }
            },
            "totals": {
                "num_statements": 100,
                "missing_lines": 5,
                "percent_covered": 95.0,  # Above 61% target
            }
        }
        
        coverage_path = tmp_path / "coverage.json"
        coverage_path.write_text(json.dumps(good_coverage_data))
        
        validator = CoverageValidator(mock_evidence_collector, tmp_path)
        
        with patch.object(validator, "_generate_coverage_data", return_value=good_coverage_data):
            result = validator.validate()
        
        # Should pass or warn, not fail
        assert result.status in (ValidationStatus.PASS, ValidationStatus.WARNING)
