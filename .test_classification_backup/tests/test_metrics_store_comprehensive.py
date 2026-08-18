"""
Comprehensive Tests for MetricsStore - Enterprise Grade
========================================================

Ruthless testing of MetricsStore with focus on:
- Thread safety under extreme concurrency
- Edge cases and error conditions
- Determinism and atomicity
- Performance under stress
- Memory safety and leak detection
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from mahoun.metrics.store import MetricsStore
from mahoun.metrics.metrics import Counter, Gauge, Histogram


class TestMetricsStoreThreadSafety:
    """Ruthless thread safety tests."""
    
    def test_concurrent_counter_registration(self):
        """Test 100 threads registering same counter simultaneously."""
        store = MetricsStore()
        results = []
        errors = []
        
        def register_counter(thread_id: int):
            try:
                counter = store.register_counter("shared_counter")
                counter.inc(1)
                results.append((thread_id, counter))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Launch 100 threads
        threads = []
        for i in range(100):
            t = threading.Thread(target=register_counter, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all
        for t in threads:
            t.join()
        
        # Verify
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 100
        
        # All threads should get the SAME counter instance
        counter_ids = [id(counter) for _, counter in results]
        assert len(set(counter_ids)) == 1, "All threads must get same counter instance"
        
        # Final value should be exactly 100
        final_counter = store.get_counter("shared_counter")
        assert final_counter.value == 100, f"Expected 100, got {final_counter.value}"
    
    def test_concurrent_mixed_operations(self):
        """Test mixed read/write operations from multiple threads."""
        store = MetricsStore()
        operations_count = 1000
        thread_count = 20
        
        def worker(worker_id: int):
            for i in range(operations_count // thread_count):
                # Register
                counter = store.register_counter(f"counter_{worker_id}")
                gauge = store.register_gauge(f"gauge_{worker_id}")
                
                # Modify
                counter.inc(1)
                gauge.set(float(i))
                
                # Read
                store.get_counter(f"counter_{worker_id}")
                store.snapshot()
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker, i) for i in range(thread_count)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions
        
        # Verify all metrics exist
        snapshot = store.snapshot()
        assert len(snapshot["counters"]) == thread_count
        assert len(snapshot["gauges"]) == thread_count
    
    def test_concurrent_reset_and_register(self):
        """Test reset while other threads are registering metrics."""
        store = MetricsStore()
        stop_flag = threading.Event()
        errors = []
        
        def continuous_register():
            counter = 0
            while not stop_flag.is_set():
                try:
                    c = store.register_counter(f"counter_{counter}")
                    c.inc(1)
                    counter += 1
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(e)
        
        def periodic_reset():
            for _ in range(10):
                time.sleep(0.01)
                try:
                    store.reset()
                except Exception as e:
                    errors.append(e)
        
        # Start workers
        register_threads = [threading.Thread(target=continuous_register) for _ in range(5)]
        reset_thread = threading.Thread(target=periodic_reset)
        
        for t in register_threads:
            t.start()
        reset_thread.start()
        
        # Wait for reset to finish
        reset_thread.join()
        stop_flag.set()
        
        for t in register_threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Errors: {errors}"


class TestMetricsStoreEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_name_rejection(self):
        """Empty names should be rejected."""
        store = MetricsStore()
        
        with pytest.raises(ValueError, match="non-empty string"):
            store.register_counter("")
        
        with pytest.raises(ValueError, match="non-empty string"):
            store.register_gauge("")
        
        with pytest.raises(ValueError, match="non-empty string"):
            store.register_histogram("")
    
    def test_none_name_rejection(self):
        """None names should be rejected."""
        store = MetricsStore()
        
        with pytest.raises((ValueError, AttributeError)):
            store.register_counter(None)
    
    def test_invalid_labels_type(self):
        """Invalid label types should be rejected."""
        store = MetricsStore()
        
        with pytest.raises(TypeError, match="dictionary"):
            store.register_counter("test", labels="invalid")
        
        with pytest.raises(TypeError, match="dictionary"):
            store.register_gauge("test", labels=123)
    
    def test_invalid_histogram_buckets(self):
        """Invalid histogram buckets should be rejected."""
        store = MetricsStore()
        
        # Non-list buckets
        with pytest.raises(TypeError, match="list"):
            store.register_histogram("test", buckets="invalid")
        
        # Non-numeric buckets
        with pytest.raises(ValueError, match="numbers"):
            store.register_histogram("test", buckets=["a", "b"])
        
        # Unsorted buckets
        with pytest.raises(ValueError, match="ascending"):
            store.register_histogram("test", buckets=[5.0, 1.0, 3.0])
    
    def test_get_nonexistent_metrics(self):
        """Getting non-existent metrics should return None."""
        store = MetricsStore()
        
        assert store.get_counter("nonexistent") is None
        assert store.get_gauge("nonexistent") is None
        assert store.get_histogram("nonexistent") is None
    
    def test_snapshot_immutability(self):
        """Snapshot should be independent of store state."""
        store = MetricsStore()
        
        counter = store.register_counter("test")
        counter.inc(10)
        
        snapshot1 = store.snapshot()
        
        # Modify store
        counter.inc(5)
        
        # Snapshot should be unchanged
        assert snapshot1["counters"]["test"]["value"] == 10
        
        # New snapshot should reflect changes
        snapshot2 = store.snapshot()
        assert snapshot2["counters"]["test"]["value"] == 15


class TestMetricsStoreDeterminism:
    """Test deterministic behavior."""
    
    def test_reset_determinism(self):
        """Reset should always produce same empty state."""
        store = MetricsStore()
        
        # Add metrics
        store.register_counter("c1").inc(10)
        store.register_gauge("g1").set(20.0)
        store.register_histogram("h1").observe(30.0)
        
        # Reset
        store.reset()
        
        # Check empty state
        snapshot1 = store.snapshot()
        assert len(snapshot1["counters"]) == 0
        assert len(snapshot1["gauges"]) == 0
        assert len(snapshot1["histograms"]) == 0
        
        # Reset again
        store.reset()
        snapshot2 = store.snapshot()
        
        # Should be identical
        assert snapshot1 == snapshot2
    
    def test_registration_idempotence(self):
        """Registering same metric multiple times returns same instance."""
        store = MetricsStore()
        
        counter1 = store.register_counter("test")
        counter2 = store.register_counter("test")
        counter3 = store.register_counter("test")
        
        # All should be the SAME object
        assert counter1 is counter2
        assert counter2 is counter3
        
        # Modifications affect all references
        counter1.inc(5)
        assert counter2.value == 5
        assert counter3.value == 5
    
    def test_snapshot_determinism(self):
        """Same state should produce identical snapshots."""
        store = MetricsStore()
        
        counter = store.register_counter("test")
        counter.inc(42)
        
        snapshot1 = store.snapshot()
        snapshot2 = store.snapshot()
        
        # Should be equal (but not same object)
        assert snapshot1 == snapshot2
        assert snapshot1 is not snapshot2


class TestMetricsStorePerformance:
    """Performance and stress tests."""
    
    def test_large_number_of_metrics(self):
        """Test with 10,000 metrics."""
        store = MetricsStore()
        
        start = time.time()
        
        # Register 10k metrics
        for i in range(10000):
            store.register_counter(f"counter_{i}").inc(i)
        
        registration_time = time.time() - start
        
        # Snapshot
        start = time.time()
        snapshot = store.snapshot()
        snapshot_time = time.time() - start
        
        # Verify
        assert len(snapshot["counters"]) == 10000
        
        print(f"\n  Registration: {registration_time:.3f}s")
        print(f"  Snapshot: {snapshot_time:.3f}s")
        
        # Should be reasonably fast
        assert registration_time < 5.0, "Registration too slow"
        assert snapshot_time < 2.0, "Snapshot too slow"
    
    def test_snapshot_performance_under_load(self):
        """Test snapshot performance with concurrent modifications."""
        store = MetricsStore()
        
        # Pre-populate
        for i in range(1000):
            store.register_counter(f"c_{i}").inc(i)
        
        stop_flag = threading.Event()
        snapshot_times = []
        
        def continuous_modify():
            counter = 0
            while not stop_flag.is_set():
                store.register_counter(f"c_{counter % 1000}").inc(1)
                counter += 1
        
        def take_snapshots():
            for _ in range(100):
                start = time.time()
                store.snapshot()
                snapshot_times.append(time.time() - start)
                time.sleep(0.01)
        
        # Start workers
        modify_threads = [threading.Thread(target=continuous_modify) for _ in range(4)]
        snapshot_thread = threading.Thread(target=take_snapshots)
        
        for t in modify_threads:
            t.start()
        snapshot_thread.start()
        
        snapshot_thread.join()
        stop_flag.set()
        
        for t in modify_threads:
            t.join()
        
        # Analyze performance
        avg_time = sum(snapshot_times) / len(snapshot_times)
        max_time = max(snapshot_times)
        
        print(f"\n  Avg snapshot time: {avg_time*1000:.2f}ms")
        print(f"  Max snapshot time: {max_time*1000:.2f}ms")
        
        # Should be fast even under load
        assert avg_time < 0.1, f"Average snapshot too slow: {avg_time}s"
        assert max_time < 0.5, f"Max snapshot too slow: {max_time}s"


class TestMetricsStoreMemorySafety:
    """Memory safety and leak detection."""
    
    def test_no_memory_leak_on_repeated_reset(self):
        """Repeated reset should not leak memory."""
        store = MetricsStore()
        
        for iteration in range(100):
            # Add metrics
            for i in range(100):
                store.register_counter(f"c_{i}").inc(i)
                store.register_gauge(f"g_{i}").set(float(i))
            
            # Reset
            store.reset()
            
            # Verify empty
            counts = store._get_metric_counts()
            assert counts["counters"] == 0
            assert counts["gauges"] == 0
    
    def test_snapshot_independence(self):
        """Snapshots should not share mutable state."""
        store = MetricsStore()
        
        counter = store.register_counter("test", labels={"env": "prod"})
        counter.inc(10)
        
        snapshot1 = store.snapshot()
        snapshot2 = store.snapshot()
        
        # Modify snapshot1's labels (should not affect snapshot2)
        snapshot1["counters"]["test"]["labels"]["env"] = "dev"
        
        # snapshot2 should be unchanged
        assert snapshot2["counters"]["test"]["labels"]["env"] == "prod"


class TestMetricsStoreIntrospection:
    """Test introspection methods."""
    
    def test_get_metric_counts(self):
        """Test _get_metric_counts accuracy."""
        store = MetricsStore()
        
        # Empty
        counts = store._get_metric_counts()
        assert counts == {"counters": 0, "gauges": 0, "histograms": 0}
        
        # Add metrics
        store.register_counter("c1")
        store.register_counter("c2")
        store.register_gauge("g1")
        store.register_histogram("h1")
        
        counts = store._get_metric_counts()
        assert counts == {"counters": 2, "gauges": 1, "histograms": 1}
    
    def test_get_metric_names(self):
        """Test _get_metric_names accuracy."""
        store = MetricsStore()
        
        store.register_counter("counter_a")
        store.register_counter("counter_b")
        store.register_gauge("gauge_x")
        
        names = store._get_metric_names()
        
        assert set(names["counters"]) == {"counter_a", "counter_b"}
        assert set(names["gauges"]) == {"gauge_x"}
        assert names["histograms"] == []
    
    def test_repr(self):
        """Test __repr__ output."""
        store = MetricsStore()
        
        store.register_counter("c1")
        store.register_gauge("g1")
        
        repr_str = repr(store)
        
        assert "MetricsStore" in repr_str
        assert "counters=1" in repr_str
        assert "gauges=1" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
