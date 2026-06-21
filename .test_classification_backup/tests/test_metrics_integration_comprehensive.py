"""
Comprehensive Integration Tests - Enterprise Grade
==================================================

End-to-end integration tests covering:
- Full lifecycle workflows
- Component interaction
- Backward compatibility
- Real-world scenarios
"""

import pytest
import time
import threading

from mahoun.metrics import (
    MetricsCollector,
    MetricsStore,
    SystemMetricsProvider,
    MetricsSnapshot,
    get_metrics_collector,
    reset_global_collector,
    register_counter,
    register_gauge
)


class TestFullLifecycleWorkflow:
    """Test complete lifecycle from registration to export."""
    
    def test_complete_workflow(self):
        """Test full workflow: register -> collect -> snapshot -> export."""
        collector = MetricsCollector()
        
        # 1. Register application metrics
        requests_counter = collector.register_counter("http_requests_total", 
                                                      labels={"method": "GET"})
        latency_gauge = collector.register_gauge("http_latency_seconds")
        
        # 2. Simulate application activity
        requests_counter.inc(100)
        latency_gauge.set(0.045)
        
        # 3. Collect system metrics explicitly
        collector.collect_system_metrics()
        
        # 4. Create snapshot
        snapshot_dict = collector.snapshot()
        
        # Verify application metrics
        assert snapshot_dict["counters"]["http_requests_total"]["value"] == 100
        assert snapshot_dict["gauges"]["http_latency_seconds"]["value"] == 0.045
        
        # 5. Create immutable audit snapshot
        audit_snapshot = collector.create_immutable_snapshot()
        
        assert audit_snapshot.verify_integrity()
        assert audit_snapshot.timestamp is not None
        
        # 6. Export to Prometheus
        prom_output = collector.to_prometheus()
        
        assert "http_requests_total" in prom_output
        assert "http_latency_seconds" in prom_output
        
        # 7. Serialize for storage
        json_output = audit_snapshot.to_json()
        
        # 8. Deserialize and verify
        restored = MetricsSnapshot.from_json(json_output)
        assert restored.content_hash == audit_snapshot.content_hash
    
    def test_reset_and_restart_workflow(self):
        """Test reset and restart cycle."""
        collector = MetricsCollector()
        
        # Phase 1: Initial metrics
        collector.register_counter("phase1").inc(100)
        collector.collect_system_metrics()
        
        snapshot1 = collector.snapshot()
        assert len(snapshot1["counters"]) >= 1
        
        # Phase 2: Reset
        collector.reset()
        
        snapshot2 = collector.snapshot()
        assert len(snapshot2["counters"]) == 0
        assert len(snapshot2["gauges"]) == 0
        
        # Phase 3: New metrics
        collector.register_counter("phase2").inc(200)
        
        snapshot3 = collector.snapshot()
        assert "phase1" not in snapshot3["counters"]
        assert "phase2" in snapshot3["counters"]
        assert snapshot3["counters"]["phase2"]["value"] == 200


class TestBackwardCompatibility:
    """Ensure backward compatibility with existing code."""
    
    def test_old_api_still_works(self):
        """Old API patterns should still work."""
        reset_global_collector()
        
        # Old pattern: module-level functions
        counter = register_counter("old_counter")
        gauge = register_gauge("old_gauge")
        
        counter.inc(10)
        gauge.set(20.0)
        
        # Old pattern: get global collector
        collector = get_metrics_collector()
        
        # Old pattern: get_all_metrics
        metrics = collector.get_all_metrics()
        
        assert metrics["counters"]["old_counter"]["value"] == 10
        assert metrics["gauges"]["old_gauge"]["value"] == 20.0


class TestConcurrentUsage:
    """Test concurrent usage scenarios."""
    
    def test_multi_threaded_collection(self):
        """Test metrics collection from multiple threads."""
        collector = MetricsCollector()
        errors = []
        
        def worker(thread_id: int):
            try:
                counter = collector.register_counter(f"thread_{thread_id}_counter")
                gauge = collector.register_gauge(f"thread_{thread_id}_gauge")
                
                for i in range(100):
                    counter.inc(1)
                    gauge.set(float(i))
                    
                    if i % 10 == 0:
                        collector.snapshot()
            except Exception as e:
                errors.append((thread_id, e))
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        
        # Verify all metrics exist
        snapshot = collector.snapshot()
        assert len(snapshot["counters"]) == 10
        assert len(snapshot["gauges"]) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
