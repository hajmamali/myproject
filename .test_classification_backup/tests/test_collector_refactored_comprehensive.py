"""
Comprehensive Tests for MetricsCollector (Refactored) - Enterprise Grade
========================================================================

Ruthless testing of refactored MetricsCollector with focus on:
- Explicit lifecycle management
- Pure operations (no hidden side effects)
- Deterministic reset behavior
- Backward compatibility
- Integration with Store and SystemProvider
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from mahoun.metrics.collector import (
    MetricsCollector,
    get_metrics_collector,
    reset_global_collector,
    register_counter,
    register_gauge,
    register_histogram
)
from mahoun.metrics.store import MetricsStore
from mahoun.metrics.system_provider import SystemMetricsProvider
from mahoun.config import ObservabilityConfig


class TestMetricsCollectorExplicitLifecycle:
    """Test explicit lifecycle management - NO hidden side effects."""
    
    def test_snapshot_is_pure(self):
        """snapshot() should NOT auto-collect system metrics."""
        collector = MetricsCollector()
        
        # Register a counter
        collector.register_counter("test").inc(10)
        
        # Snapshot should NOT include system metrics
        snapshot1 = collector.snapshot()
        
        # Should only have our counter
        assert "test" in snapshot1["counters"]
        assert "mahoun_system_cpu_percent" not in snapshot1["gauges"]
        assert "mahoun_system_memory_bytes" not in snapshot1["gauges"]
        
        # Multiple snapshots should be identical (pure)
        snapshot2 = collector.snapshot()
        assert snapshot1 == snapshot2
    
    def test_get_all_metrics_is_pure(self):
        """get_all_metrics() should NOT auto-collect system metrics."""
        collector = MetricsCollector()
        
        collector.register_counter("test").inc(5)
        
        metrics1 = collector.get_all_metrics()
        
        # Should NOT have system metrics
        assert "mahoun_system_cpu_percent" not in metrics1["gauges"]
        
        # Should be deterministic
        metrics2 = collector.get_all_metrics()
        assert metrics1 == metrics2
    
    def test_to_prometheus_is_pure(self):
        """to_prometheus() should NOT auto-collect system metrics."""
        collector = MetricsCollector()
        
        collector.register_counter("test").inc(10)
        
        prom1 = collector.to_prometheus()
        
        # Should NOT contain system metrics
        assert "mahoun_system_cpu_percent" not in prom1
        assert "mahoun_system_memory_bytes" not in prom1
        
        # Should be deterministic
        prom2 = collector.to_prometheus()
        assert prom1 == prom2
    
    def test_explicit_system_metrics_collection(self):
        """System metrics must be collected EXPLICITLY."""
        collector = MetricsCollector()
        
        # Before explicit collection
        snapshot1 = collector.snapshot()
        assert "mahoun_system_cpu_percent" not in snapshot1["gauges"]
        
        # Explicitly collect
        collector.collect_system_metrics()
        
        # Now should have system metrics (if psutil available)
        snapshot2 = collector.snapshot()
        
        # May or may not have metrics depending on psutil
        # But the point is it required explicit call
        assert snapshot1 != snapshot2 or not collector._system_provider.is_available()
    
    def test_reset_is_deterministic(self):
        """reset() should produce deterministic empty state."""
        collector = MetricsCollector()
        
        # Add metrics
        collector.register_counter("c1").inc(10)
        collector.register_gauge("g1").set(20.0)
        collector.collect_system_metrics()
        
        # Reset
        collector.reset()
        
        # Should be completely empty
        snapshot1 = collector.snapshot()
        assert len(snapshot1["counters"]) == 0
        assert len(snapshot1["gauges"]) == 0
        assert len(snapshot1["histograms"]) == 0
        
        # System metrics should NOT reappear
        snapshot2 = collector.snapshot()
        assert snapshot1 == snapshot2
        
        # Even after multiple snapshots
        for _ in range(5):
            snapshot_n = collector.snapshot()
            assert snapshot_n == snapshot1


class TestMetricsCollectorDependencyInjection:
    """Test dependency injection for testability."""
    
    def test_custom_config(self):
        """Should accept custom config."""
        config = ObservabilityConfig(metrics_enabled=False)
        collector = MetricsCollector(config=config)
        
        info = collector.get_collector_info()
        assert info["metrics_enabled"] is False
    
    def test_custom_store(self):
        """Should accept custom store."""
        store = MetricsStore()
        store.register_counter("pre_existing").inc(42)
        
        collector = MetricsCollector(store=store)
        
        # Should use the provided store
        snapshot = collector.snapshot()
        assert snapshot["counters"]["pre_existing"]["value"] == 42
    
    def test_custom_system_provider(self):
        """Should accept custom system provider."""
        mock_provider = Mock(spec=SystemMetricsProvider)
        mock_provider.is_available.return_value = True
        mock_provider.collect.return_value = {"mock_metric": 123.0}
        
        collector = MetricsCollector(system_provider=mock_provider)
        
        # Collect system metrics
        collector.collect_system_metrics()
        
        # Should use mock provider
        mock_provider.collect.assert_called_once()
        
        snapshot = collector.snapshot()
        assert "mock_metric" in snapshot["gauges"]
        assert snapshot["gauges"]["mock_metric"]["value"] == 123.0
    
    def test_none_system_provider(self):
        """Should handle None system provider gracefully."""
        collector = MetricsCollector(system_provider=None)
        
        # Should not crash
        collector.collect_system_metrics()
        
        info = collector.get_collector_info()
        assert info["system_provider_available"] is False


class TestMetricsCollectorBackwardCompatibility:
    """Test backward compatibility with old API."""
    
    def test_register_counter_api(self):
        """register_counter should work as before."""
        collector = MetricsCollector()
        
        counter = collector.register_counter("test")
        counter.inc(10)
        
        assert collector.get_counter("test").value == 10
    
    def test_register_gauge_api(self):
        """register_gauge should work as before."""
        collector = MetricsCollector()
        
        gauge = collector.register_gauge("test")
        gauge.set(42.0)
        
        assert collector.get_gauge("test").value == 42.0
    
    def test_register_histogram_api(self):
        """register_histogram should work as before."""
        collector = MetricsCollector()
        
        hist = collector.register_histogram("test")
        hist.observe(10.0)
        
        assert collector.get_histogram("test") is not None
    
    def test_get_counter_api(self):
        """get_counter should work as before."""
        collector = MetricsCollector()
        
        collector.register_counter("test").inc(5)
        
        counter = collector.get_counter("test")
        assert counter is not None
        assert counter.value == 5
        
        # Non-existent should return None
        assert collector.get_counter("nonexistent") is None
    
    def test_get_all_metrics_api(self):
        """get_all_metrics should work as before."""
        collector = MetricsCollector()
        
        collector.register_counter("c1").inc(10)
        collector.register_gauge("g1").set(20.0)
        
        metrics = collector.get_all_metrics()
        
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert metrics["counters"]["c1"]["value"] == 10
        assert metrics["gauges"]["g1"]["value"] == 20.0
    
    def test_update_system_metrics_deprecated(self):
        """update_system_metrics should still work but warn."""
        collector = MetricsCollector()
        
        with pytest.warns(UserWarning, match="deprecated"):
            collector.update_system_metrics()


class TestMetricsCollectorGlobalSingleton:
    """Test global singleton pattern."""
    
    def test_get_metrics_collector_singleton(self):
        """get_metrics_collector should return singleton."""
        reset_global_collector()  # Clean slate
        
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        # Should be same instance
        assert collector1 is collector2
    
    def test_global_collector_state_persistence(self):
        """Global collector should persist state."""
        reset_global_collector()
        
        collector1 = get_metrics_collector()
        collector1.register_counter("test").inc(10)
        
        collector2 = get_metrics_collector()
        
        # Should see the same counter
        assert collector2.get_counter("test").value == 10
    
    def test_reset_global_collector(self):
        """reset_global_collector should create new instance."""
        reset_global_collector()
        
        collector1 = get_metrics_collector()
        collector1.register_counter("test").inc(10)
        
        reset_global_collector()
        
        collector2 = get_metrics_collector()
        
        # Should be different instance
        assert collector1 is not collector2
        
        # Should not have old metrics
        assert collector2.get_counter("test") is None
    
    def test_convenience_functions(self):
        """Module-level convenience functions should work."""
        reset_global_collector()
        
        counter = register_counter("test_counter")
        gauge = register_gauge("test_gauge")
        hist = register_histogram("test_histogram")
        
        counter.inc(5)
        gauge.set(10.0)
        hist.observe(15.0)
        
        # Should be accessible via global collector
        collector = get_metrics_collector()
        assert collector.get_counter("test_counter").value == 5
        assert collector.get_gauge("test_gauge").value == 10.0
        assert collector.get_histogram("test_histogram") is not None


class TestMetricsCollectorThreadSafety:
    """Test thread safety."""
    
    def test_concurrent_registration(self):
        """Concurrent registration should be safe."""
        collector = MetricsCollector()
        errors = []
        
        def worker(thread_id: int):
            try:
                for i in range(100):
                    counter = collector.register_counter(f"counter_{thread_id}")
                    counter.inc(1)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        
        # Each counter should have value 100
        for i in range(10):
            counter = collector.get_counter(f"counter_{i}")
            assert counter.value == 100
    
    def test_concurrent_snapshot(self):
        """Concurrent snapshots should be safe."""
        collector = MetricsCollector()
        
        # Pre-populate
        for i in range(100):
            collector.register_counter(f"c_{i}").inc(i)
        
        results = []
        errors = []
        
        def take_snapshot(thread_id: int):
            try:
                for _ in range(10):
                    snapshot = collector.snapshot()
                    results.append((thread_id, snapshot))
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=take_snapshot, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 100  # 10 threads * 10 snapshots


class TestMetricsCollectorPrometheusExport:
    """Test Prometheus export functionality."""
    
    def test_prometheus_format_basic(self):
        """Prometheus export should have correct format."""
        collector = MetricsCollector()
        
        collector.register_counter("test_counter").inc(10)
        collector.register_gauge("test_gauge").set(42.0)
        
        prom = collector.to_prometheus()
        
        assert "test_counter" in prom
        assert "test_gauge" in prom
        assert "10" in prom
        assert "42" in prom or "42.0" in prom
    
    def test_prometheus_with_labels(self):
        """Prometheus export should handle labels."""
        collector = MetricsCollector()
        
        collector.register_counter("requests", labels={"method": "GET", "status": "200"}).inc(100)
        
        prom = collector.to_prometheus()
        
        assert "requests" in prom
        assert "method" in prom
        assert "GET" in prom
        assert "status" in prom
        assert "200" in prom
    
    def test_prometheus_disabled_metrics(self):
        """Prometheus export when metrics disabled."""
        config = ObservabilityConfig(metrics_enabled=False)
        collector = MetricsCollector(config=config)
        
        prom = collector.to_prometheus()
        
        assert "disabled" in prom.lower()


class TestMetricsCollectorImmutableSnapshot:
    """Test immutable snapshot creation."""
    
    def test_create_immutable_snapshot(self):
        """Should create MetricsSnapshot with audit metadata."""
        collector = MetricsCollector()
        
        collector.register_counter("test").inc(10)
        
        snapshot = collector.create_immutable_snapshot()
        
        # Should have audit metadata
        assert snapshot.timestamp is not None
        assert snapshot.schema_version is not None
        assert snapshot.content_hash is not None
        
        # Should have metrics
        assert len(snapshot.counters) == 1
        assert snapshot.counters["test"]["value"] == 10
        
        # Should pass integrity check
        assert snapshot.verify_integrity() is True


class TestMetricsCollectorIntrospection:
    """Test introspection methods."""
    
    def test_get_collector_info(self):
        """get_collector_info should return complete info."""
        collector = MetricsCollector()
        
        info = collector.get_collector_info()
        
        assert "metrics_enabled" in info
        assert "system_provider_available" in info
        assert "metric_counts" in info
        assert "architecture" in info
        
        assert info["architecture"] == "refactored"
        assert isinstance(info["metrics_enabled"], bool)
        assert isinstance(info["metric_counts"], dict)
    
    def test_repr(self):
        """__repr__ should be informative."""
        collector = MetricsCollector()
        
        repr_str = repr(collector)
        
        assert "MetricsCollector" in repr_str
        assert "enabled=" in repr_str
        assert "system_available=" in repr_str


class TestMetricsCollectorEdgeCases:
    """Edge cases and error conditions."""
    
    def test_metrics_disabled(self):
        """Operations should handle disabled metrics gracefully."""
        config = ObservabilityConfig(metrics_enabled=False)
        collector = MetricsCollector(config=config)
        
        # Should not crash
        snapshot = collector.snapshot()
        assert snapshot == {"counters": {}, "gauges": {}, "histograms": {}}
        
        prom = collector.to_prometheus()
        assert "disabled" in prom.lower()
    
    def test_system_provider_unavailable(self):
        """Should handle unavailable system provider."""
        mock_provider = Mock(spec=SystemMetricsProvider)
        mock_provider.is_available.return_value = False
        mock_provider.collect.return_value = {}
        
        collector = MetricsCollector(system_provider=mock_provider)
        
        # Should not crash
        collector.collect_system_metrics()
        
        snapshot = collector.snapshot()
        # Should not have system metrics
        assert "mahoun_system_cpu_percent" not in snapshot["gauges"]
    
    def test_system_provider_error(self):
        """Should handle system provider errors gracefully."""
        mock_provider = Mock(spec=SystemMetricsProvider)
        mock_provider.is_available.return_value = True
        mock_provider.collect.side_effect = Exception("Provider error")
        
        collector = MetricsCollector(system_provider=mock_provider)
        
        # Should not crash
        collector.collect_system_metrics()
        
        # Should still be able to snapshot
        snapshot = collector.snapshot()
        assert isinstance(snapshot, dict)


class TestMetricsCollectorPerformance:
    """Performance tests."""
    
    def test_registration_performance(self):
        """Registration should be fast."""
        collector = MetricsCollector()
        
        start = time.time()
        
        for i in range(1000):
            collector.register_counter(f"c_{i}").inc(i)
        
        elapsed = time.time() - start
        
        print(f"\n  1000 registrations: {elapsed:.3f}s")
        
        assert elapsed < 2.0, f"Too slow: {elapsed}s"
    
    def test_snapshot_performance(self):
        """Snapshot should be fast."""
        collector = MetricsCollector()
        
        # Pre-populate
        for i in range(1000):
            collector.register_counter(f"c_{i}").inc(i)
        
        times = []
        for _ in range(10):
            start = time.time()
            collector.snapshot()
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n  Avg snapshot time: {avg_time*1000:.2f}ms")
        
        assert avg_time < 0.5, f"Too slow: {avg_time}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
