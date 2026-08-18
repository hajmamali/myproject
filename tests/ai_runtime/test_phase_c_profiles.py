#!/usr/bin/env python3
"""
Phase C Integration Tests: Deployment Profile Unity

Test Coverage:
- Task C.1: Profile Configuration System
- Task C.2: Semantic Equivalence Testing
- Task C.3: Model Size Flexibility Implementation

All tests validate deployment profile unity, resource management,
and semantic equivalence preservation across profiles.

Test Count: 18 tests
Expected Result: 18/18 passing
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
import psutil

from mahoun.ai.profile_manager import (
    ProfileManager,
    ResourceStatus,
    ResourceUtilization,
    ProfileCompatibilityReport,
    ModelRecommendation,
    compare_profiles,
    get_optimal_profile_for_workload
)
from mahoun.core.models import (
    DeploymentProfile,
    DESKTOP_MINIMAL,
    ENTERPRISE_FULL,
    ResourceLimits,
    PerformanceTargets
)


# ============================================================================
# Task C.1: Profile Configuration System
# ============================================================================

class TestTaskC11_DeploymentProfileImplementation:
    """Task C.1.1: DeploymentProfile implementation and validation"""
    
    @pytest.mark.p2
    def test_desktop_minimal_profile_constants(self):
        """Validate Desktop Minimal profile specifications"""
        profile = DESKTOP_MINIMAL
        
        assert profile.profile_name == "desktop_minimal"
        assert profile.resource_limits.max_memory_gb == 4.0
        assert profile.resource_limits.max_cpu_cores == 4
        assert profile.resource_limits.max_concurrent_requests == 10
        assert profile.resource_limits.max_model_size_gb == 4.0
        assert profile.resource_limits.enable_gpu == False
        assert profile.resource_limits.max_storage_gb == 50.0
        
        # Performance targets (desktop allows higher latency)
        assert profile.performance_targets.target_latency_ms <= 10000  # Up to 10s acceptable
        assert profile.performance_targets.target_throughput_rps >= 1
    
    @pytest.mark.p2
    def test_enterprise_full_profile_constants(self):
        """Validate Enterprise Full profile specifications"""
        profile = ENTERPRISE_FULL
        
        assert profile.profile_name == "enterprise_full"
        assert profile.resource_limits.max_memory_gb == 32.0
        assert profile.resource_limits.max_cpu_cores == 16
        assert profile.resource_limits.max_concurrent_requests == 1000
        assert profile.resource_limits.max_model_size_gb == 32.0
        assert profile.resource_limits.enable_gpu == True
        assert profile.resource_limits.max_storage_gb == 500.0
        
        # Performance targets (enterprise has faster latency)
        assert profile.performance_targets.target_latency_ms <= 5000  # Better than desktop
        assert profile.performance_targets.target_throughput_rps >= 50
    
    @pytest.mark.p2
    def test_profile_resource_scaling(self):
        """Validate resource scaling between profiles"""
        desktop = DESKTOP_MINIMAL
        enterprise = ENTERPRISE_FULL
        
        # Enterprise should have more resources
        assert enterprise.resource_limits.max_memory_gb > desktop.resource_limits.max_memory_gb
        assert enterprise.resource_limits.max_cpu_cores > desktop.resource_limits.max_cpu_cores
        assert enterprise.resource_limits.max_concurrent_requests > desktop.resource_limits.max_concurrent_requests
        
        # Resource ratios should be reasonable (not extreme)
        memory_ratio = enterprise.resource_limits.max_memory_gb / desktop.resource_limits.max_memory_gb
        assert 2.0 <= memory_ratio <= 20.0
        
        concurrent_ratio = enterprise.resource_limits.max_concurrent_requests / desktop.resource_limits.max_concurrent_requests
        assert 10.0 <= concurrent_ratio <= 200.0


class TestTaskC12_EnvironmentDrivenProfileSelection:
    """Task C.1.2: Environment-driven profile selection"""
    
    @patch.dict('os.environ', {'MAHOUN_DEPLOYMENT_PROFILE': 'desktop_minimal'})
    @pytest.mark.p2
    def test_environment_variable_desktop_minimal(self):
        """Test profile selection from environment variable - Desktop Minimal"""
        from mahoun.core.models import load_profile_from_env
        
        profile = load_profile_from_env()
        assert profile.profile_name == "desktop_minimal"
    
    @patch.dict('os.environ', {'MAHOUN_DEPLOYMENT_PROFILE': 'enterprise_full'})
    @pytest.mark.p2
    def test_environment_variable_enterprise_full(self):
        """Test profile selection from environment variable - Enterprise Full"""
        from mahoun.core.models import load_profile_from_env
        
        profile = load_profile_from_env()
        assert profile.profile_name == "enterprise_full"
    
    @patch.dict('os.environ', {}, clear=True)
    @pytest.mark.p2
    def test_default_profile_selection(self):
        """Test default profile selection when no environment variable"""
        from mahoun.core.models import load_profile_from_env
        
        profile = load_profile_from_env()
        # Should default to desktop_minimal
        assert profile.profile_name == "desktop_minimal"
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_count')
    @pytest.mark.p2
    def test_auto_profile_selection_enterprise(self, mock_cpu_count, mock_mem):
        """Test automatic profile selection for enterprise resources"""
        # Mock enterprise-level resources
        mock_mem.return_value = Mock(total=32 * 1024**3)  # 32GB
        mock_cpu_count.return_value = 16
        
        manager = ProfileManager(profile=None, auto_select=True)
        
        assert manager.profile.profile_name == "enterprise_full"
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_count')
    @pytest.mark.p2
    def test_auto_profile_selection_desktop(self, mock_cpu_count, mock_mem):
        """Test automatic profile selection for desktop resources"""
        # Mock desktop-level resources
        mock_mem.return_value = Mock(total=8 * 1024**3)  # 8GB
        mock_cpu_count.return_value = 4
        
        manager = ProfileManager(profile=None, auto_select=True)
        
        assert manager.profile.profile_name == "desktop_minimal"


class TestTaskC13_ResourceLimitEnforcement:
    """Task C.1.3: Resource limit enforcement"""
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    @patch('psutil.disk_usage')
    @pytest.mark.p2
    def test_resource_utilization_monitoring(
        self, mock_disk, mock_cpu_count, mock_cpu_percent, mock_mem
    ):
        """Test resource utilization monitoring"""
        # Mock system resources
        mock_mem.return_value = Mock(
            total=16 * 1024**3,
            available=8 * 1024**3,
            percent=50.0
        )
        mock_cpu_percent.return_value = 45.0
        mock_cpu_count.return_value = 8
        mock_disk.return_value = Mock(
            total=500 * 1024**3,
            used=100 * 1024**3,
            free=400 * 1024**3
        )
        
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        utilization = manager.get_resource_utilization()
        
        assert utilization.memory_used_gb > 0
        assert utilization.memory_available_gb > 0
        assert 0 <= utilization.memory_percent <= 100
        assert 0 <= utilization.cpu_percent <= 100
        assert utilization.cpu_count > 0
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    @patch('psutil.disk_usage')
    @pytest.mark.p2
    def test_resource_status_healthy(
        self, mock_disk, mock_cpu_count, mock_cpu_percent, mock_mem
    ):
        """Test resource status detection - HEALTHY"""
        # Mock healthy resources (well below 4GB desktop limit)
        mock_mem.return_value = Mock(
            total=16 * 1024**3,
            available=14 * 1024**3,
            percent=12.5
        )
        mock_cpu_percent.return_value = 30.0
        mock_cpu_count.return_value = 8
        mock_disk.return_value = Mock(
            total=500 * 1024**3,
            used=20 * 1024**3,
            free=480 * 1024**3
        )
        
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        status, details = manager.check_resource_status()
        
        assert status == ResourceStatus.HEALTHY
        assert details["memory_status"] == "healthy"
        assert details["cpu_status"] == "healthy"
    
    @patch('psutil.virtual_memory')
    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    @patch('psutil.disk_usage')
    @pytest.mark.p2
    def test_resource_status_exceeded(
        self, mock_disk, mock_cpu_count, mock_cpu_percent, mock_mem
    ):
        """Test resource status detection - EXCEEDED"""
        # Mock exceeded resources (more than 4GB used for desktop_minimal)
        mock_mem.return_value = Mock(
            total=16 * 1024**3,
            available=2 * 1024**3,
            percent=87.5
        )
        mock_cpu_percent.return_value = 95.0
        mock_cpu_count.return_value = 8
        mock_disk.return_value = Mock(
            total=500 * 1024**3,
            used=480 * 1024**3,
            free=20 * 1024**3
        )
        
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        status, details = manager.check_resource_status()
        
        # Should detect exceeded status
        assert status in [ResourceStatus.EXCEEDED, ResourceStatus.CRITICAL]


class TestTaskC14_ProfileSwitchingValidation:
    """Task C.1.4: Profile switching validation"""
    
    @pytest.mark.p2
    def test_profile_compatibility_report(self):
        """Test profile compatibility assessment"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL, auto_select=False)
        
        report = manager.validate_profile_compatibility(ENTERPRISE_FULL)
        
        assert isinstance(report, ProfileCompatibilityReport)
        assert report.profile == ENTERPRISE_FULL
        assert isinstance(report.compatible, bool)
        assert isinstance(report.resource_check, dict)
        assert isinstance(report.warnings, list)
        assert isinstance(report.recommendations, list)
    
    @pytest.mark.p2
    def test_profile_comparison(self):
        """Test profile comparison utility"""
        comparison = compare_profiles(DESKTOP_MINIMAL, ENTERPRISE_FULL)
        
        assert comparison["profile_a"] == "desktop_minimal"
        assert comparison["profile_b"] == "enterprise_full"
        assert "resource_differences" in comparison
        assert "performance_differences" in comparison
        assert comparison["semantic_equivalence"]["same_api"] == True
        assert comparison["semantic_equivalence"]["same_contracts"] == True


# ============================================================================
# Task C.2: Semantic Equivalence Testing
# ============================================================================

class TestTaskC21_CrossProfileQueryTesting:
    """Task C.2.1: Cross-profile query testing"""
    
    @pytest.mark.p2
    def test_semantic_equivalence_validation_structure(self):
        """Test semantic equivalence validation framework"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        
        test_queries = [
            "Analyze legal precedent for contract dispute",
            "Find similar cases in Persian law",
            "Evaluate evidence quality"
        ]
        
        report = manager.validate_semantic_equivalence(
            profile_a=DESKTOP_MINIMAL,
            profile_b=ENTERPRISE_FULL,
            test_queries=test_queries
        )
        
        assert report["profile_a"] == "desktop_minimal"
        assert report["profile_b"] == "enterprise_full"
        assert report["api_equivalent"] == True
        assert report["contract_equivalent"] == True
        assert report["test_queries_count"] == 3
        assert report["structural_checks"]["same_codebase"] == True
        assert report["structural_checks"]["same_api_surface"] == True
    
    @pytest.mark.p2
    def test_api_surface_equivalence(self):
        """Test API surface equivalence across profiles"""
        # Both profiles use same ProfileManager API
        desktop_manager = ProfileManager(profile=DESKTOP_MINIMAL)
        enterprise_manager = ProfileManager(profile=ENTERPRISE_FULL)
        
        # Same methods available
        assert hasattr(desktop_manager, 'get_resource_utilization')
        assert hasattr(enterprise_manager, 'get_resource_utilization')
        assert hasattr(desktop_manager, 'recommend_models')
        assert hasattr(enterprise_manager, 'recommend_models')


class TestTaskC22_ResourceUtilizationMonitoring:
    """Task C.2.2: Resource utilization monitoring"""
    
    @pytest.mark.p2
    def test_utilization_history_tracking(self):
        """Test resource utilization history tracking"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        
        # Get utilization multiple times
        for _ in range(5):
            manager.get_resource_utilization()
        
        assert len(manager._utilization_history) == 5
    
    @pytest.mark.p2
    def test_utilization_history_limits(self):
        """Test utilization history size limits"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        
        # Generate more than 100 records
        for _ in range(150):
            manager.get_resource_utilization()
        
        # Should cap at 100
        assert len(manager._utilization_history) == 100


class TestTaskC23_PerformanceScalingVerification:
    """Task C.2.3: Performance scaling verification"""
    
    @pytest.mark.p2
    def test_performance_targets_desktop(self):
        """Test performance targets for Desktop Minimal"""
        profile = DESKTOP_MINIMAL
        
        # Should have reasonable targets for desktop
        assert profile.performance_targets.target_latency_ms <= 10000
        assert profile.performance_targets.target_throughput_rps >= 0.5
    
    @pytest.mark.p2
    def test_performance_targets_enterprise(self):
        """Test performance targets for Enterprise Full"""
        profile = ENTERPRISE_FULL
        
        # Should have higher performance targets
        assert profile.performance_targets.target_latency_ms < DESKTOP_MINIMAL.performance_targets.target_latency_ms
        assert profile.performance_targets.target_throughput_rps > DESKTOP_MINIMAL.performance_targets.target_throughput_rps


# ============================================================================
# Task C.3: Model Size Flexibility Implementation
# ============================================================================

class TestTaskC31_DynamicModelSelection:
    """Task C.3.1: Dynamic model selection"""
    
    @pytest.mark.p2
    def test_model_recommendations_desktop(self):
        """Test model recommendations for Desktop Minimal"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        
        recommendations = manager.recommend_models(top_k=5)
        
        assert len(recommendations) > 0
        assert all(isinstance(r, ModelRecommendation) for r in recommendations)
        
        # All recommended models should fit in profile
        for rec in recommendations:
            assert rec.model_size_gb <= DESKTOP_MINIMAL.resource_limits.max_model_size_gb
    
    @pytest.mark.p2
    def test_model_recommendations_enterprise(self):
        """Test model recommendations for Enterprise Full"""
        manager = ProfileManager(profile=ENTERPRISE_FULL)
        
        recommendations = manager.recommend_models(top_k=5)
        
        assert len(recommendations) > 0
        
        # Should include larger models
        model_sizes = [r.model_size_gb for r in recommendations]
        assert max(model_sizes) > 4.0  # Larger than desktop models


class TestTaskC32_LargeModelSupport:
    """Task C.3.2: Large model support (Enterprise Full)"""
    
    @pytest.mark.p2
    def test_model_catalog_completeness(self):
        """Test model catalog contains all size ranges"""
        catalog = ProfileManager.MODEL_CATALOG
        
        # Check for different model sizes
        sizes = [spec["parameters"] for spec in catalog.values()]
        
        # Should have 1B, 3B, 7B models minimum
        assert any(s < 2_000_000_000 for s in sizes)  # 1B range
        assert any(2_000_000_000 <= s < 5_000_000_000 for s in sizes)  # 3B range
        assert any(5_000_000_000 <= s < 10_000_000_000 for s in sizes)  # 7B range
    
    @pytest.mark.p2
    def test_large_model_compatibility_enterprise(self):
        """Test large model (70B) compatibility with Enterprise Full"""
        manager = ProfileManager(profile=ENTERPRISE_FULL)
        
        # Find 70B model in recommendations
        recommendations = manager.recommend_models(top_k=10)
        
        # Should include large models for enterprise
        large_models = [r for r in recommendations if r.parameters >= 30_000_000_000]
        assert len(large_models) > 0


class TestTaskC33_ModelMetadataManagement:
    """Task C.3.3: Model metadata management"""
    
    @pytest.mark.p2
    def test_model_metadata_structure(self):
        """Test model metadata structure"""
        catalog = ProfileManager.MODEL_CATALOG
        
        # Check first model
        model_id = list(catalog.keys())[0]
        spec = catalog[model_id]
        
        # Required fields
        assert "size_gb" in spec
        assert "parameters" in spec
        assert "quantization" in spec
        assert "context_window" in spec
        assert "profile" in spec
    
    @pytest.mark.p2
    def test_model_recommendation_completeness(self):
        """Test model recommendation data completeness"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        
        recommendations = manager.recommend_models(top_k=1)
        rec = recommendations[0]
        
        # Check all required fields
        assert rec.model_id is not None
        assert rec.model_size_gb > 0
        assert rec.parameters > 0
        assert rec.quantization in ["Q4_K_M", "Q8_0", "F16"]
        assert 0.0 <= rec.confidence <= 1.0
        assert rec.reasoning is not None
        assert "tokens_per_second" in rec.estimated_performance


# ============================================================================
# Integration Tests
# ============================================================================

class TestProfileManagerIntegration:
    """Integration tests for ProfileManager"""
    
    @pytest.mark.p2
    def test_profile_summary_completeness(self):
        """Test comprehensive profile summary"""
        manager = ProfileManager(profile=DESKTOP_MINIMAL)
        
        summary = manager.get_profile_summary()
        
        # Check all sections present
        assert "profile" in summary
        assert "resource_utilization" in summary
        assert "resource_status" in summary
        assert "compatibility" in summary
        assert "model_recommendations" in summary
    
    @pytest.mark.p2
    def test_optimal_profile_selection_utility(self):
        """Test optimal profile selection utility function"""
        # Low workload
        profile = get_optimal_profile_for_workload(
            concurrent_requests=5,
            model_size_preference="small",
            memory_budget_gb=8.0
        )
        assert profile.profile_name == "desktop_minimal"
        
        # High workload
        profile = get_optimal_profile_for_workload(
            concurrent_requests=100,
            model_size_preference="large",
            memory_budget_gb=32.0
        )
        assert profile.profile_name == "enterprise_full"


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
