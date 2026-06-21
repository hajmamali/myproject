"""
Tests for Phase Operations
===========================

Property-based and unit tests for phase operations.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from scripts.phase_operations import (
    Phase1Operations,
    Phase2Operations,
    Phase3Operations,
    Phase7Operations,
    PhaseOperationError,
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace with mahoun structure."""
    mahoun_dir = tmp_path / "mahoun"
    mahoun_dir.mkdir()
    
    # Create core directory
    core_dir = mahoun_dir / "core"
    core_dir.mkdir()
    (core_dir / "__init__.py").write_text("")
    
    # Create sample health_cache.py
    (core_dir / "health_cache.py").write_text(
        '"""Health cache module."""\n\n'
        'class HealthCache:\n'
        '    """Health cache implementation."""\n'
        '    pass\n'
    )
    
    # Create sample metrics module
    metrics_dir = core_dir / "metrics"
    metrics_dir.mkdir()
    (metrics_dir / "__init__.py").write_text(
        '"""Metrics module."""\n\n'
        '__all__ = ["MetricsCollector"]\n'
    )
    
    # Create sample monitoring module
    monitoring_dir = core_dir / "monitoring"
    monitoring_dir.mkdir()
    (monitoring_dir / "__init__.py").write_text(
        '"""Monitoring module."""\n\n'
        '__all__ = ["Monitor"]\n'
    )
    
    # Change to temp directory
    import os
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    
    yield tmp_path
    
    # Restore original directory
    os.chdir(original_cwd)


class TestPhase1Operations:
    """Test Phase 1: Create directories."""
    
    def test_create_infrastructure_dir(self, temp_workspace):
        """Test creating infrastructure directory."""
        result = Phase1Operations.create_infrastructure_dir(dry_run=False)
        
        assert result is True
        assert (temp_workspace / "mahoun/infrastructure").exists()
        assert (temp_workspace / "mahoun/infrastructure/__init__.py").exists()
    
    def test_create_infrastructure_dir_dry_run(self, temp_workspace):
        """Test dry run doesn't create directory."""
        result = Phase1Operations.create_infrastructure_dir(dry_run=True)
        
        assert result is True
        assert not (temp_workspace / "mahoun/infrastructure").exists()
    
    def test_create_monitoring_dir(self, temp_workspace):
        """Test creating monitoring subdirectory."""
        # First create parent
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        
        result = Phase1Operations.create_monitoring_dir(dry_run=False)
        
        assert result is True
        assert (temp_workspace / "mahoun/infrastructure/monitoring").exists()
        assert (temp_workspace / "mahoun/infrastructure/monitoring/__init__.py").exists()
    
    def test_create_observability_dir(self, temp_workspace):
        """Test creating observability subdirectory."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        
        result = Phase1Operations.create_observability_dir(dry_run=False)
        
        assert result is True
        assert (temp_workspace / "mahoun/infrastructure/observability").exists()


class TestPhase2Operations:
    """Test Phase 2: Copy files."""
    
    def test_copy_health_cache(self, temp_workspace):
        """Test copying health_cache.py."""
        # Setup infrastructure
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_monitoring_dir(dry_run=False)
        
        # Copy file
        success, dest = Phase2Operations.copy_health_cache(dry_run=False)
        
        assert success is True
        assert dest is not None
        assert dest.exists()
        assert "HealthCache" in dest.read_text()
    
    def test_copy_health_cache_dry_run(self, temp_workspace):
        """Test dry run doesn't copy file."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_monitoring_dir(dry_run=False)
        
        success, dest = Phase2Operations.copy_health_cache(dry_run=True)
        
        assert success is True
        assert dest is None
        assert not (temp_workspace / "mahoun/infrastructure/monitoring/health_cache.py").exists()
    
    def test_copy_metrics_module(self, temp_workspace):
        """Test copying metrics module."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_observability_dir(dry_run=False)
        
        success, dest = Phase2Operations.copy_metrics_module(dry_run=False)
        
        assert success is True
        assert dest is not None
        assert dest.exists()
        assert (dest / "__init__.py").exists()
    
    def test_copy_monitoring_module(self, temp_workspace):
        """Test copying monitoring module."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_observability_dir(dry_run=False)
        
        success, dest = Phase2Operations.copy_monitoring_module(dry_run=False)
        
        assert success is True
        assert dest is not None
        assert dest.exists()


class TestPhase3Operations:
    """Test Phase 3: Add deprecation warnings."""
    
    def test_add_deprecation_to_health_cache(self, temp_workspace):
        """Test adding deprecation warning."""
        # Setup
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_monitoring_dir(dry_run=False)
        Phase2Operations.copy_health_cache(dry_run=False)
        
        # Add deprecation
        result = Phase3Operations.add_deprecation_to_health_cache(dry_run=False)
        
        assert result is True
        
        # Check content
        content = (temp_workspace / "mahoun/core/health_cache.py").read_text()
        assert "DEPRECATED" in content
        assert "warnings.warn" in content
        assert "mahoun.infrastructure.monitoring.health_cache" in content
        
        # Check backup exists
        assert (temp_workspace / "mahoun/core/health_cache.py.backup").exists()
    
    def test_add_deprecation_dry_run(self, temp_workspace):
        """Test dry run doesn't modify file."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_monitoring_dir(dry_run=False)
        Phase2Operations.copy_health_cache(dry_run=False)
        
        original_content = (temp_workspace / "mahoun/core/health_cache.py").read_text()
        
        result = Phase3Operations.add_deprecation_to_health_cache(dry_run=True)
        
        assert result is True
        assert (temp_workspace / "mahoun/core/health_cache.py").read_text() == original_content
    
    def test_add_deprecation_to_metrics(self, temp_workspace):
        """Test adding deprecation to metrics module."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_observability_dir(dry_run=False)
        Phase2Operations.copy_metrics_module(dry_run=False)
        
        result = Phase3Operations.add_deprecation_to_metrics(dry_run=False)
        
        assert result is True
        content = (temp_workspace / "mahoun/core/metrics/__init__.py").read_text()
        assert "DEPRECATED" in content


class TestPhase7Operations:
    """Test Phase 7: Remove deprecated files."""
    
    def test_remove_health_cache(self, temp_workspace):
        """Test removing deprecated file."""
        # Setup
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_monitoring_dir(dry_run=False)
        Phase2Operations.copy_health_cache(dry_run=False)
        
        # Remove
        result = Phase7Operations.remove_health_cache(dry_run=False)
        
        assert result is True
        assert not (temp_workspace / "mahoun/core/health_cache.py").exists()
        assert (temp_workspace / "mahoun/core/archive/health_cache.py").exists()
    
    def test_remove_health_cache_dry_run(self, temp_workspace):
        """Test dry run doesn't remove file."""
        result = Phase7Operations.remove_health_cache(dry_run=True)
        
        assert result is True
        assert (temp_workspace / "mahoun/core/health_cache.py").exists()
    
    def test_remove_metrics_module(self, temp_workspace):
        """Test removing metrics module."""
        Phase1Operations.create_infrastructure_dir(dry_run=False)
        Phase1Operations.create_observability_dir(dry_run=False)
        Phase2Operations.copy_metrics_module(dry_run=False)
        
        result = Phase7Operations.remove_metrics_module(dry_run=False)
        
        assert result is True
        assert not (temp_workspace / "mahoun/core/metrics").exists()
        assert (temp_workspace / "mahoun/core/archive/metrics").exists()


class TestPhaseOperationsIntegration:
    """Integration tests for complete phase workflows."""
    
    def test_phase_1_to_3_workflow(self, temp_workspace):
        """Test complete workflow from Phase 1 to 3."""
        # Phase 1: Create directories
        assert Phase1Operations.create_infrastructure_dir(dry_run=False)
        assert Phase1Operations.create_monitoring_dir(dry_run=False)
        assert Phase1Operations.create_observability_dir(dry_run=False)
        
        # Phase 2: Copy files
        success, _ = Phase2Operations.copy_health_cache(dry_run=False)
        assert success
        
        success, _ = Phase2Operations.copy_metrics_module(dry_run=False)
        assert success
        
        # Phase 3: Add deprecations
        assert Phase3Operations.add_deprecation_to_health_cache(dry_run=False)
        assert Phase3Operations.add_deprecation_to_metrics(dry_run=False)
        
        # Verify both old and new locations exist
        assert (temp_workspace / "mahoun/core/health_cache.py").exists()
        assert (temp_workspace / "mahoun/infrastructure/monitoring/health_cache.py").exists()
        
        # Verify deprecation warning in old location
        old_content = (temp_workspace / "mahoun/core/health_cache.py").read_text()
        assert "DEPRECATED" in old_content
        assert "warnings.warn" in old_content
    
    def test_idempotency(self, temp_workspace):
        """Test operations are idempotent."""
        # Run Phase 1 twice
        assert Phase1Operations.create_infrastructure_dir(dry_run=False)
        assert Phase1Operations.create_infrastructure_dir(dry_run=False)
        
        # Run Phase 2 twice
        Phase1Operations.create_monitoring_dir(dry_run=False)
        success1, _ = Phase2Operations.copy_health_cache(dry_run=False)
        success2, _ = Phase2Operations.copy_health_cache(dry_run=False)
        
        assert success1 and success2
