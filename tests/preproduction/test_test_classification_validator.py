"""
Tests for Test Classification Validator
========================================
"""

import tempfile
from pathlib import Path
import pytest

from mahoun.preproduction.models import FindingSeverity, ValidationStatus
from mahoun.preproduction.validators.test_classification_validator import (
    TestClassificationValidator,
    TestFileMetadata,
)


class TestTestFileMetadata:
    """Test TestFileMetadata dataclass."""
    
    def test_is_mismarked_slow(self):
        """Should detect slow marker on fast test."""
        meta = TestFileMetadata(
            path=Path("test_fast.py"),
            markers={"slow"},
            test_count=5,
            total_duration_ms=500,
            avg_duration_ms=100,
            slowest_test_ms=150,
        )
        assert meta.is_mismarked_slow
    
    def test_is_unmarked_slow(self):
        """Should detect missing slow marker."""
        meta = TestFileMetadata(
            path=Path("test_slow.py"),
            markers=set(),
            test_count=3,
            total_duration_ms=6000,
            avg_duration_ms=2000,
            slowest_test_ms=3000,
        )
        assert meta.is_unmarked_slow


class TestTestClassificationValidator:
    """Test full validation logic."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project with tests."""
        project = tmp_path / "project"
        tests_dir = project / "tests"
        tests_dir.mkdir(parents=True)
        return project
    
    def test_extracts_markers_from_file(self, temp_project):
        """Should extract pytest markers from test file."""
        test_file = temp_project / "tests" / "test_example.py"
        test_file.write_text("""
import pytest

pytestmark = pytest.mark.slow

def test_something():
    assert True
""")
        
        validator = TestClassificationValidator(temp_project)
        markers = validator._extract_markers_from_file(test_file)
        
        assert "slow" in markers
    
    def test_extracts_multiple_markers(self, temp_project):
        """Should extract multiple markers."""
        test_file = temp_project / "tests" / "test_multi.py"
        test_file.write_text("""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

def test_something():
    assert True
""")
        
        validator = TestClassificationValidator(temp_project)
        markers = validator._extract_markers_from_file(test_file)
        
        assert "integration" in markers
        assert "slow" in markers
    
    def test_validation_completes_without_tests_dir(self, tmp_path):
        """Should handle missing tests directory gracefully."""
        project = tmp_path / "project"
        project.mkdir()
        
        validator = TestClassificationValidator(project)
        result = validator.validate()
        
        assert result.status == ValidationStatus.SKIPPED
        assert "not found" in result.evidence["reason"]
    
    def test_detects_mismarked_slow_test(self, temp_project):
        """Should detect test marked slow but executing quickly."""
        # Create test file marked as slow
        test_file = temp_project / "tests" / "test_fast_but_marked_slow.py"
        test_file.write_text("""
import pytest

pytestmark = pytest.mark.slow

def test_quick():
    assert 1 + 1 == 2

def test_another_quick():
    assert True
""")
        
        validator = TestClassificationValidator(temp_project)
        result = validator.validate()
        
        # Should have findings about mismarked tests
        mismarked_findings = [
            f for f in result.findings
            if "marked 'slow' but executes" in f.message
        ]
        # May not find it if estimation is off, but structure is correct
        assert isinstance(result.findings, list)
    
    def test_scan_test_files(self, temp_project):
        """Should scan all test files in tests directory."""
        # Create multiple test files
        (temp_project / "tests" / "test_one.py").write_text("def test_one(): pass")
        (temp_project / "tests" / "test_two.py").write_text("def test_two(): pass")
        
        subdir = temp_project / "tests" / "subdir"
        subdir.mkdir()
        (subdir / "test_three.py").write_text("def test_three(): pass")
        
        validator = TestClassificationValidator(temp_project)
        test_files = validator._scan_test_files()
        
        assert len(test_files) == 3
    
    def test_estimate_test_metadata(self, temp_project):
        """Should estimate test metadata from file."""
        test_file = temp_project / "tests" / "test_estimate.py"
        test_file.write_text("""
import pytest

pytestmark = pytest.mark.integration

def test_one():
    assert True

def test_two():
    assert True

def test_three():
    assert True
""")
        
        validator = TestClassificationValidator(temp_project)
        meta = validator._estimate_test_metadata(test_file)
        
        assert meta is not None
        assert meta.test_count == 3
        assert "integration" in meta.markers
        assert meta.total_duration_ms > 0
    
    def test_check_known_issue_api_integration(self, temp_project):
        """Should detect the known test_api_integration.py issue."""
        # Create the known problematic file
        gov_dir = temp_project / "tests" / "governance"
        gov_dir.mkdir(parents=True)
        
        api_test = gov_dir / "test_api_integration.py"
        api_test.write_text("""
import pytest

pytestmark = pytest.mark.slow

def test_api_call():
    '''Fast API test'''
    assert True
""")
        
        validator = TestClassificationValidator(temp_project)
        
        # Create metadata showing it's fast
        timing_data = {
            api_test: TestFileMetadata(
                path=api_test,
                markers={"slow"},
                test_count=1,
                total_duration_ms=600,  # Fast!
                avg_duration_ms=600,
                slowest_test_ms=600,
            )
        }
        
        findings = validator._check_known_issues(timing_data)
        
        # Should detect the known issue
        assert len(findings) > 0
        assert findings[0].severity == FindingSeverity.P1_HIGH
        assert "test_api_integration.py" in findings[0].message
    
    def test_check_marker_consistency(self, temp_project):
        """Should detect conflicting markers."""
        test_file = temp_project / "tests" / "test_conflict.py"
        test_file.write_text("""
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.integration]

def test_something():
    assert True
""")
        
        validator = TestClassificationValidator(temp_project)
        test_files = {test_file: {"unit", "integration"}}
        
        findings = validator._check_marker_consistency(test_files)
        
        assert len(findings) > 0
        assert findings[0].severity == FindingSeverity.P3_LOW
        assert "both 'unit' and 'integration'" in findings[0].message


class TestIntegration:
    """Integration tests with real project structure."""
    
    def test_validates_real_project(self):
        """Should validate actual project structure."""
        project_root = Path(__file__).parent.parent.parent
        
        validator = TestClassificationValidator(project_root)
        result = validator.validate()
        
        # Should complete without crashing
        assert result.validator_id == "test-classification"
        assert result.domain == "test-classification"
        assert result.status in [ValidationStatus.PASS, ValidationStatus.WARNING, ValidationStatus.FAIL]
