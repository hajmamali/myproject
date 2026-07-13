"""
MAHOUN AI Runtime Health System - Comprehensive Test Suite
==========================================================

Tests for mahoun/ai/health.py - Advanced health monitoring system
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mahoun.ai.health import (
    AIRuntimeHealthChecker,
    HealthStatus,
    ComponentType,
    HealthCheckResult,
    SystemMetrics
)


class TestHealthCheckResult:
    """Test HealthCheckResult data model"""
    
    def test_health_check_result_creation(self):
        """Test creating health check result"""
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="All systems operational",
            timestamp="2026-07-04T12:00:00Z",
            latency_ms=50.5,
            details={"version": "1.0"},
            metrics={"cpu": 25.0}
        )
        
        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All systems operational"
        assert result.latency_ms == 50.5
        assert result.details["version"] == "1.0"
        assert result.metrics["cpu"] == 25.0


class TestSystemMetrics:
    """Test SystemMetrics data model"""
    
    def test_system_metrics_creation(self):
        """Test creating system metrics"""
        metrics = SystemMetrics(
            cpu_percent=45.5,
            memory_used_mb=2048.0,
            memory_available_mb=6144.0,
            memory_percent=25.0,
            disk_used_gb=50.0,
            disk_available_gb=200.0,
            disk_percent=20.0,
            model_count=5,
            cache_size_mb=512.0,
            uptime_seconds=3600.0
        )
        
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_used_mb == 2048.0
        assert metrics.model_count == 5
        assert metrics.uptime_seconds == 3600.0


class TestAIRuntimeHealthChecker:
    """Test AIRuntimeHealthChecker main functionality"""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        models_dir = tempfile.mkdtemp()
        data_dir = tempfile.mkdtemp()
        
        yield Path(models_dir), Path(data_dir)
        
        # Cleanup
        shutil.rmtree(models_dir, ignore_errors=True)
        shutil.rmtree(data_dir, ignore_errors=True)
    
    @pytest.fixture
    def health_checker(self, temp_dirs):
        """Create health checker instance"""
        models_dir, data_dir = temp_dirs
        return AIRuntimeHealthChecker(
            models_dir=models_dir,
            data_dir=data_dir,
            enable_detailed_metrics=True
        )
    
    def test_health_checker_initialization(self, temp_dirs):
        """Test health checker initializes correctly"""
        models_dir, data_dir = temp_dirs
        
        checker = AIRuntimeHealthChecker(
            models_dir=models_dir,
            data_dir=data_dir
        )
        
        assert checker.models_dir == models_dir
        assert checker.data_dir == data_dir
        assert checker.enable_detailed_metrics is True
        assert checker._cache_ttl == 5.0
    
    @pytest.mark.asyncio
    async def test_check_health_basic(self, health_checker):
        """Test basic health check execution"""
        result = await health_checker.check_health(include_details=False)
        
        # Verify response structure
        assert "status" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "version" in result
        assert "checks" in result
        assert "system" in result
        assert "latency_ms" in result
        
        # Verify status is valid
        assert result["status"] in ["healthy", "degraded", "unhealthy", "unknown"]
        
        # Verify version
        assert result["version"] == "2.0.0-NEXUS"
    
    @pytest.mark.asyncio
    async def test_check_health_with_details(self, health_checker):
        """Test health check with detailed metrics"""
        result = await health_checker.check_health(include_details=True)
        
        # Should have details section
        assert "details" in result
        
        # Should have component checks
        assert "checks" in result
        for component, check_data in result["checks"].items():
            assert "status" in check_data
            assert "message" in check_data
            assert "latency_ms" in check_data
            if "metrics" in check_data:
                assert isinstance(check_data["metrics"], dict)
    
    @pytest.mark.asyncio
    async def test_model_runtime_check_no_models(self, health_checker):
        """Test model runtime check when no models present"""
        result = await health_checker._check_model_runtime()
        
        assert result.component == ComponentType.MODEL_RUNTIME.value
        # Should be DEGRADED (no models) not UNHEALTHY
        assert result.status in [HealthStatus.DEGRADED, HealthStatus.HEALTHY]
        assert result.latency_ms >= 0
    
    @pytest.mark.asyncio
    async def test_model_runtime_check_with_models(self, health_checker, temp_dirs):
        """Test model runtime check with GGUF models present"""
        models_dir, _ = temp_dirs
        
        # Create mock GGUF model files
        model1 = models_dir / "model1.gguf"
        model2 = models_dir / "model2.gguf"
        model1.write_bytes(b"fake_model_data" * 1000)  # Some data
        model2.write_bytes(b"fake_model_data" * 1000)
        
        result = await health_checker._check_model_runtime()
        
        assert result.component == ComponentType.MODEL_RUNTIME.value
        assert result.status == HealthStatus.HEALTHY
        assert "2 models available" in result.message
        assert result.metrics["model_count"] == 2.0
        assert result.metrics["accessible_count"] == 2.0
    
    @pytest.mark.asyncio
    async def test_embedding_service_check(self, health_checker):
        """Test embedding service health check"""
        result = await health_checker._check_embedding_service()
        
        assert result.component == ComponentType.EMBEDDING_SERVICE.value
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNKNOWN]
        assert result.latency_ms >= 0
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_memory_resources_check_healthy(self, mock_memory, health_checker):
        """Test memory check when resources are healthy"""
        # Mock healthy memory state (60% used)
        mock_memory.return_value = Mock(
            percent=60.0,
            available=4 * 1024 ** 3,  # 4 GB available
            total=10 * 1024 ** 3,  # 10 GB total
            used=6 * 1024 ** 3  # 6 GB used
        )
        
        result = await health_checker._check_memory_resources()
        
        assert result.component == ComponentType.MEMORY_MANAGER.value
        assert result.status == HealthStatus.HEALTHY
        assert "Memory healthy" in result.message
        assert result.metrics["memory_percent"] == 60.0
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_memory_resources_check_degraded(self, mock_memory, health_checker):
        """Test memory check when resources are degraded"""
        # Mock degraded memory state (90% used)
        mock_memory.return_value = Mock(
            percent=90.0,
            available=1 * 1024 ** 3,  # 1 GB available
            total=10 * 1024 ** 3,
            used=9 * 1024 ** 3
        )
        
        result = await health_checker._check_memory_resources()
        
        assert result.component == ComponentType.MEMORY_MANAGER.value
        assert result.status == HealthStatus.DEGRADED
        assert "High memory usage" in result.message
        assert result.metrics["memory_percent"] == 90.0
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_memory_resources_check_unhealthy(self, mock_memory, health_checker):
        """Test memory check when resources are critical"""
        # Mock critical memory state (97% used)
        mock_memory.return_value = Mock(
            percent=97.0,
            available=300 * 1024 ** 2,  # 300 MB available
            total=10 * 1024 ** 3,
            used=9.7 * 1024 ** 3
        )
        
        result = await health_checker._check_memory_resources()
        
        assert result.component == ComponentType.MEMORY_MANAGER.value
        assert result.status == HealthStatus.UNHEALTHY
        assert "Critical memory pressure" in result.message
    
    @pytest.mark.asyncio
    async def test_governance_validator_check(self, health_checker):
        """Test governance validator health check"""
        result = await health_checker._check_governance_validator()
        
        assert result.component == ComponentType.GOVERNANCE_VALIDATOR.value
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]
        assert result.latency_ms >= 0
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {
        'TRANSFORMERS_OFFLINE': '1',
        'HF_DATASETS_OFFLINE': '1',
        'MAHOUN_ENABLE_NETWORK': 'false'
    })
    async def test_network_isolation_check_compliant(self, health_checker):
        """Test network isolation check when air-gap compliant"""
        result = await health_checker._check_network_isolation()
        
        assert result.component == ComponentType.NETWORK_ISOLATION.value
        assert result.status == HealthStatus.HEALTHY
        assert "Air-gap compliance verified" in result.message
        assert result.metrics["offline_compliant"] == 1.0
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {
        'TRANSFORMERS_OFFLINE': '0',
        'MAHOUN_ENABLE_NETWORK': 'true'
    }, clear=True)
    async def test_network_isolation_check_non_compliant(self, health_checker):
        """Test network isolation check when not air-gap compliant"""
        result = await health_checker._check_network_isolation()
        
        assert result.component == ComponentType.NETWORK_ISOLATION.value
        assert result.status == HealthStatus.DEGRADED
        assert "Air-gap configuration incomplete" in result.message
        assert result.metrics["offline_compliant"] == 0.0
    
    @pytest.mark.asyncio
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def test_collect_system_metrics(self, mock_disk, mock_memory, mock_cpu, health_checker):
        """Test system metrics collection"""
        # Mock system resources
        mock_cpu.return_value = 35.5
        mock_memory.return_value = Mock(
            used=2 * 1024 ** 3,
            available=6 * 1024 ** 3,
            percent=25.0,
            total=8 * 1024 ** 3
        )
        mock_disk.return_value = Mock(
            used=50 * 1024 ** 3,
            free=150 * 1024 ** 3,
            percent=25.0
        )
        
        metrics = await health_checker._collect_system_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_percent == 35.5
        assert metrics.memory_percent == 25.0
        assert metrics.disk_percent == 25.0
        assert metrics.uptime_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_readiness_check(self, health_checker):
        """Test Kubernetes-style readiness check"""
        result = await health_checker.readiness_check()
        
        assert "ready" in result
        assert isinstance(result["ready"], bool)
        assert "timestamp" in result
        assert "components" in result
        assert "models" in result["components"]
        assert "memory" in result["components"]
    
    @pytest.mark.asyncio
    async def test_liveness_check(self, health_checker):
        """Test Kubernetes-style liveness check"""
        result = await health_checker.liveness_check()
        
        assert result["alive"] is True
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0
    
    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, health_checker):
        """Test health check handles exceptions gracefully"""
        # Patch one check to raise exception
        with patch.object(health_checker, '_check_model_runtime', side_effect=Exception("Test error")):
            result = await health_checker.check_health()
            
            # Should still complete with overall UNHEALTHY status
            assert result["status"] == "unhealthy"
            assert "checks" in result


@pytest.mark.integration
class TestHealthSystemIntegration:
    """Integration tests for health system"""
    
    @pytest.mark.asyncio
    async def test_full_health_check_cycle(self, tmp_path):
        """Test complete health check cycle with real filesystem"""
        models_dir = tmp_path / "models"
        data_dir = tmp_path / "data"
        models_dir.mkdir()
        data_dir.mkdir()
        
        # Create some test models
        (models_dir / "test-7b.gguf").write_bytes(b"x" * 1024 * 100)  # 100KB
        (models_dir / "test-13b.gguf").write_bytes(b"x" * 1024 * 200)  # 200KB
        
        # Create embeddings dir
        embeddings_dir = models_dir / "embeddings"
        embeddings_dir.mkdir()
        (embeddings_dir / "pytorch_model.bin").write_bytes(b"x" * 1024)
        
        checker = AIRuntimeHealthChecker(
            models_dir=models_dir,
            data_dir=data_dir
        )
        
        # Run comprehensive health check
        result = await checker.check_health(include_details=True)
        
        # Verify complete response
        assert result["status"] in ["healthy", "degraded"]
        assert len(result["checks"]) >= 4  # At least 4 component checks
        assert result["system"]["model_count"] == 2
        
        # Verify all expected checks are present
        expected_components = [
            ComponentType.MODEL_RUNTIME.value,
            ComponentType.EMBEDDING_SERVICE.value,
            ComponentType.MEMORY_MANAGER.value,
            ComponentType.GOVERNANCE_VALIDATOR.value,
            ComponentType.NETWORK_ISOLATION.value
        ]
        
        for component in expected_components:
            assert component in result["checks"], f"Missing check for {component}"
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, tmp_path):
        """Test multiple concurrent health checks"""
        models_dir = tmp_path / "models"
        data_dir = tmp_path / "data"
        models_dir.mkdir()
        data_dir.mkdir()
        
        checker = AIRuntimeHealthChecker(
            models_dir=models_dir,
            data_dir=data_dir
        )
        
        # Run 5 concurrent health checks
        results = await asyncio.gather(*[
            checker.check_health() for _ in range(5)
        ])
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert "status" in result
            assert result["status"] in ["healthy", "degraded", "unhealthy", "unknown"]


@pytest.mark.performance
class TestHealthSystemPerformance:
    """Performance tests for health system"""
    
    @pytest.mark.asyncio
    async def test_health_check_latency(self, tmp_path):
        """Test health check completes within acceptable latency"""
        models_dir = tmp_path / "models"
        data_dir = tmp_path / "data"
        models_dir.mkdir()
        data_dir.mkdir()
        
        checker = AIRuntimeHealthChecker(
            models_dir=models_dir,
            data_dir=data_dir
        )
        
        import time
        start = time.perf_counter()
        result = await checker.check_health()
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Health check should complete in under 500ms
        assert duration_ms < 500, f"Health check took {duration_ms:.2f}ms (expected <500ms)"
        
        # Reported latency should match
        assert abs(result["latency_ms"] - duration_ms) < 50  # Within 50ms tolerance


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
