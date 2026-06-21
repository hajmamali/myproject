"""
Comprehensive Tests for SystemMetricsProvider - Enterprise Grade
================================================================

Ruthless testing of SystemMetricsProvider with focus on:
- Stateless behavior verification
- Graceful degradation without psutil
- Error isolation
- Performance characteristics
- Deterministic behavior
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from mahoun.metrics.system_provider import (
    SystemMetricsProvider,
    collect_system_metrics,
    is_system_metrics_available,
    PSUTIL_AVAILABLE
)


class TestSystemMetricsProviderStateless:
    """Verify stateless behavior."""
    
    def test_no_internal_state_mutation(self):
        """Provider should not store collected metrics."""
        provider = SystemMetricsProvider()
        
        # Collect multiple times
        metrics1 = provider.collect()
        metrics2 = provider.collect()
        
        # Results may differ (system state changes) but provider has no state
        # We verify this by checking that __dict__ doesn't grow
        initial_dict = dict(provider.__dict__)
        
        for _ in range(10):
            provider.collect()
        
        final_dict = dict(provider.__dict__)
        
        # Only _start_time and _psutil_available should exist
        assert set(initial_dict.keys()) == set(final_dict.keys())
        assert initial_dict["_start_time"] == final_dict["_start_time"]
        assert initial_dict["_psutil_available"] == final_dict["_psutil_available"]
    
    def test_thread_safety_without_locks(self):
        """Provider should be thread-safe without explicit locking."""
        provider = SystemMetricsProvider()
        results = []
        errors = []
        
        def collect_metrics(thread_id: int):
            try:
                for _ in range(100):
                    metrics = provider.collect()
                    results.append((thread_id, metrics))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Launch 20 threads
        threads = [threading.Thread(target=collect_metrics, args=(i,)) for i in range(20)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 2000  # 20 threads * 100 collections


class TestSystemMetricsProviderGracefulDegradation:
    """Test behavior when psutil is unavailable."""
    
    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_with_psutil_available(self):
        """When psutil is available, should collect metrics."""
        provider = SystemMetricsProvider()
        
        assert provider.is_available()
        
        metrics = provider.collect()
        
        # Should have at least some metrics
        assert isinstance(metrics, dict)
        
        # Check expected metric names
        expected_names = provider.get_metric_names()
        assert "mahoun_system_cpu_percent" in expected_names
        assert "mahoun_system_memory_bytes" in expected_names
        assert "mahoun_system_uptime_seconds" in expected_names
    
    def test_without_psutil_mock(self):
        """When psutil is unavailable, should return empty dict."""
        # Mock psutil as unavailable
        with patch('mahoun.metrics.system_provider.PSUTIL_AVAILABLE', False):
            with patch('mahoun.metrics.system_provider.psutil', None):
                provider = SystemMetricsProvider()
                
                assert not provider.is_available()
                
                metrics = provider.collect()
                
                # Should return empty dict
                assert metrics == {}
                
                # Metric names should be empty
                assert provider.get_metric_names() == []
    
    def test_partial_failure_isolation(self):
        """If one metric fails, others should still be collected."""
        provider = SystemMetricsProvider()
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        # Mock psutil.cpu_percent to fail
        with patch('psutil.cpu_percent', side_effect=Exception("CPU error")):
            metrics = provider.collect()
            
            # CPU metric should be missing
            assert "mahoun_system_cpu_percent" not in metrics
            
            # But other metrics should still be present
            # (if psutil is available)
            if PSUTIL_AVAILABLE:
                # At least uptime should work (doesn't depend on psutil calls)
                assert "mahoun_system_uptime_seconds" in metrics


class TestSystemMetricsProviderErrorIsolation:
    """Test error handling and isolation."""
    
    def test_cpu_collection_failure(self):
        """CPU collection failure should not crash provider."""
        provider = SystemMetricsProvider()
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        with patch('psutil.cpu_percent', side_effect=RuntimeError("CPU fail")):
            metrics = provider.collect()
            
            # Should return dict (possibly empty or partial)
            assert isinstance(metrics, dict)
            assert "mahoun_system_cpu_percent" not in metrics
    
    def test_memory_collection_failure(self):
        """Memory collection failure should not crash provider."""
        provider = SystemMetricsProvider()
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        with patch('psutil.virtual_memory', side_effect=RuntimeError("Memory fail")):
            metrics = provider.collect()
            
            assert isinstance(metrics, dict)
            assert "mahoun_system_memory_bytes" not in metrics
    
    def test_uptime_calculation_robustness(self):
        """Uptime should handle clock adjustments."""
        # Start time in the future (simulates clock adjustment)
        future_time = time.time() + 1000
        provider = SystemMetricsProvider(start_time=future_time)
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        metrics = provider.collect()
        
        # Uptime should be 0 (not negative)
        if "mahoun_system_uptime_seconds" in metrics:
            assert metrics["mahoun_system_uptime_seconds"] >= 0.0


class TestSystemMetricsProviderDeterminism:
    """Test deterministic behavior."""
    
    def test_uptime_increases_monotonically(self):
        """Uptime should increase over time."""
        provider = SystemMetricsProvider()
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        metrics1 = provider.collect()
        time.sleep(0.1)
        metrics2 = provider.collect()
        
        if "mahoun_system_uptime_seconds" in metrics1 and "mahoun_system_uptime_seconds" in metrics2:
            uptime1 = metrics1["mahoun_system_uptime_seconds"]
            uptime2 = metrics2["mahoun_system_uptime_seconds"]
            
            assert uptime2 > uptime1, "Uptime should increase"
            assert uptime2 - uptime1 >= 0.1, "Uptime delta should match sleep time"
    
    def test_metric_names_consistency(self):
        """get_metric_names should return consistent results."""
        provider = SystemMetricsProvider()
        
        names1 = provider.get_metric_names()
        names2 = provider.get_metric_names()
        
        assert names1 == names2
    
    def test_collection_info_consistency(self):
        """get_collection_info should return consistent results."""
        provider = SystemMetricsProvider(start_time=12345.0)
        
        info1 = provider.get_collection_info()
        info2 = provider.get_collection_info()
        
        assert info1 == info2
        assert info1["start_time"] == 12345.0


class TestSystemMetricsProviderPerformance:
    """Performance tests."""
    
    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_collection_performance(self):
        """Collection should complete in reasonable time."""
        provider = SystemMetricsProvider()
        
        times = []
        for _ in range(10):
            start = time.time()
            provider.collect()
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"\n  Avg collection time: {avg_time*1000:.2f}ms")
        print(f"  Max collection time: {max_time*1000:.2f}ms")
        
        # Should be reasonably fast (CPU measurement adds ~10ms)
        assert avg_time < 0.5, f"Average too slow: {avg_time}s"
        assert max_time < 1.0, f"Max too slow: {max_time}s"
    
    def test_concurrent_collection_performance(self):
        """Concurrent collections should not block each other."""
        provider = SystemMetricsProvider()
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        def collect_many():
            for _ in range(10):
                provider.collect()
        
        start = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(collect_many) for _ in range(10)]
            for future in futures:
                future.result()
        
        total_time = time.time() - start
        
        print(f"\n  Total time for 100 collections (10 threads): {total_time:.2f}s")
        
        # Should complete in reasonable time
        assert total_time < 20.0, f"Too slow: {total_time}s"


class TestSystemMetricsProviderAPI:
    """Test public API."""
    
    def test_is_available(self):
        """is_available should reflect psutil availability."""
        provider = SystemMetricsProvider()
        
        available = provider.is_available()
        
        assert isinstance(available, bool)
        assert available == PSUTIL_AVAILABLE
    
    def test_get_metric_names(self):
        """get_metric_names should return list of strings."""
        provider = SystemMetricsProvider()
        
        names = provider.get_metric_names()
        
        assert isinstance(names, list)
        
        if provider.is_available():
            assert len(names) > 0
            assert all(isinstance(name, str) for name in names)
        else:
            assert names == []
    
    def test_get_collection_info(self):
        """get_collection_info should return complete info."""
        start_time = 12345.0
        provider = SystemMetricsProvider(start_time=start_time)
        
        info = provider.get_collection_info()
        
        assert isinstance(info, dict)
        assert "psutil_available" in info
        assert "metric_count" in info
        assert "metric_names" in info
        assert "start_time" in info
        
        assert info["start_time"] == start_time
        assert isinstance(info["psutil_available"], bool)
        assert isinstance(info["metric_count"], int)
        assert isinstance(info["metric_names"], list)
    
    def test_repr(self):
        """__repr__ should be informative."""
        provider = SystemMetricsProvider(start_time=12345.0)
        
        repr_str = repr(provider)
        
        assert "SystemMetricsProvider" in repr_str
        assert "12345.0" in repr_str
        
        if provider.is_available():
            assert "available" in repr_str
        else:
            assert "unavailable" in repr_str


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""
    
    def test_collect_system_metrics_function(self):
        """collect_system_metrics should work."""
        metrics = collect_system_metrics()
        
        assert isinstance(metrics, dict)
    
    def test_collect_system_metrics_with_start_time(self):
        """collect_system_metrics should accept start_time."""
        metrics = collect_system_metrics(start_time=12345.0)
        
        assert isinstance(metrics, dict)
        
        if PSUTIL_AVAILABLE and "mahoun_system_uptime_seconds" in metrics:
            # Uptime should be large (current time - 12345.0)
            assert metrics["mahoun_system_uptime_seconds"] > 0
    
    def test_is_system_metrics_available_function(self):
        """is_system_metrics_available should return bool."""
        available = is_system_metrics_available()
        
        assert isinstance(available, bool)
        assert available == PSUTIL_AVAILABLE


class TestSystemMetricsProviderEdgeCases:
    """Edge cases and corner cases."""
    
    def test_start_time_none(self):
        """start_time=None should use current time."""
        provider = SystemMetricsProvider(start_time=None)
        
        # Should not crash
        info = provider.get_collection_info()
        
        # Start time should be recent
        assert info["start_time"] > time.time() - 1.0
    
    def test_start_time_zero(self):
        """start_time=0 should work."""
        provider = SystemMetricsProvider(start_time=0.0)
        
        if not provider.is_available():
            pytest.skip("psutil not available")
        
        metrics = provider.collect()
        
        if "mahoun_system_uptime_seconds" in metrics:
            # Uptime should be very large (current time - 0)
            assert metrics["mahoun_system_uptime_seconds"] > 1000000
    
    def test_multiple_providers_independence(self):
        """Multiple providers should be independent."""
        provider1 = SystemMetricsProvider(start_time=1000.0)
        provider2 = SystemMetricsProvider(start_time=2000.0)
        
        info1 = provider1.get_collection_info()
        info2 = provider2.get_collection_info()
        
        assert info1["start_time"] == 1000.0
        assert info2["start_time"] == 2000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
