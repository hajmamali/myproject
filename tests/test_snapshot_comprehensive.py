"""
Comprehensive Tests for MetricsSnapshot - Audit Grade
=====================================================

Ruthless testing of MetricsSnapshot with focus on:
- Immutability guarantees
- Integrity verification
- Audit compliance
- Serialization/deserialization
- Schema versioning
"""

import pytest
import json
import hashlib
import time
from datetime import datetime, timezone
from types import MappingProxyType

from mahoun.metrics.snapshot import (
    MetricsSnapshot,
    METRICS_SCHEMA_VERSION,
    compare_snapshots,
    validate_snapshot_chain
)
from mahoun.metrics.store import MetricsStore


class TestMetricsSnapshotImmutability:
    """Ruthless immutability tests."""
    
    def test_frozen_dataclass(self):
        """Snapshot attributes should be immutable."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            snapshot.timestamp = "modified"
        
        with pytest.raises(AttributeError):
            snapshot.content_hash = "modified"
    
    def test_counters_immutability(self):
        """Counters dict should be immutable."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Should be MappingProxyType
        assert isinstance(snapshot.counters, MappingProxyType)
        
        # Should not be able to modify
        with pytest.raises(TypeError):
            snapshot.counters["test"] = {"value": 999}
        
        with pytest.raises(TypeError):
            snapshot.counters["new_counter"] = {"value": 1}
    
    def test_gauges_immutability(self):
        """Gauges dict should be immutable."""
        store = MetricsStore()
        store.register_gauge("test").set(42.0)
        
        snapshot = MetricsSnapshot.create(store)
        
        assert isinstance(snapshot.gauges, MappingProxyType)
        
        with pytest.raises(TypeError):
            snapshot.gauges["test"] = {"value": 999.0}
    
    def test_histograms_immutability(self):
        """Histograms dict should be immutable."""
        store = MetricsStore()
        hist = store.register_histogram("test")
        hist.observe(10.0)
        
        snapshot = MetricsSnapshot.create(store)
        
        assert isinstance(snapshot.histograms, MappingProxyType)
        
        with pytest.raises(TypeError):
            snapshot.histograms["test"] = {"count": 999}
    
    def test_nested_data_independence(self):
        """Modifying nested data should not affect snapshot."""
        store = MetricsStore()
        store.register_counter("test", labels={"env": "prod"}).inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Get the counter data (this is a copy)
        counter_data = dict(snapshot.counters)["test"]
        
        # Modify the copy
        counter_data["value"] = 999
        counter_data["labels"]["env"] = "dev"
        
        # Original snapshot should be unchanged
        original_data = dict(snapshot.counters)["test"]
        assert original_data["value"] == 10
        assert original_data["labels"]["env"] == "prod"


class TestMetricsSnapshotIntegrity:
    """Test integrity verification."""
    
    def test_content_hash_determinism(self):
        """Same data should produce same hash."""
        store = MetricsStore()
        store.register_counter("test").inc(42)
        
        snapshot1 = MetricsSnapshot.create(store)
        snapshot2 = MetricsSnapshot.create(store)
        
        # Hashes should be identical (same data)
        assert snapshot1.content_hash == snapshot2.content_hash
    
    def test_content_hash_sensitivity(self):
        """Different data should produce different hash."""
        store = MetricsStore()
        counter = store.register_counter("test")
        
        counter.inc(10)
        snapshot1 = MetricsSnapshot.create(store)
        
        counter.inc(1)  # Change value
        snapshot2 = MetricsSnapshot.create(store)
        
        # Hashes should be different
        assert snapshot1.content_hash != snapshot2.content_hash
    
    def test_verify_integrity_valid(self):
        """Valid snapshot should pass integrity check."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        assert snapshot.verify_integrity() is True
    
    def test_verify_integrity_tampered(self):
        """Tampered snapshot should fail integrity check."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Create a tampered snapshot by manually constructing it
        tampered = MetricsSnapshot(
            timestamp=snapshot.timestamp,
            schema_version=snapshot.schema_version,
            content_hash="0" * 64,  # Invalid hash
            counters=snapshot.counters,
            gauges=snapshot.gauges,
            histograms=snapshot.histograms
        )
        
        assert tampered.verify_integrity() is False
    
    def test_content_hash_format(self):
        """Content hash should be valid SHA256."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Should be 64 hex characters
        assert len(snapshot.content_hash) == 64
        assert all(c in "0123456789abcdef" for c in snapshot.content_hash)


class TestMetricsSnapshotAuditCompliance:
    """Test audit compliance features."""
    
    def test_timestamp_format(self):
        """Timestamp should be ISO8601 UTC."""
        store = MetricsStore()
        snapshot = MetricsSnapshot.create(store)
        
        # Should be parseable as ISO8601
        dt = datetime.fromisoformat(snapshot.timestamp.replace('Z', '+00:00'))
        
        # Should be recent (within last second)
        now = datetime.now(timezone.utc)
        delta = (now - dt).total_seconds()
        assert abs(delta) < 2.0, f"Timestamp too old: {delta}s"
    
    def test_schema_version_present(self):
        """Schema version should be present."""
        store = MetricsStore()
        snapshot = MetricsSnapshot.create(store)
        
        assert snapshot.schema_version == METRICS_SCHEMA_VERSION
        assert snapshot.schema_version == "1.0.0"
    
    def test_metadata_completeness(self):
        """All audit metadata should be present."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Check all required fields
        assert snapshot.timestamp is not None
        assert snapshot.schema_version is not None
        assert snapshot.content_hash is not None
        assert snapshot.counters is not None
        assert snapshot.gauges is not None
        assert snapshot.histograms is not None
    
    def test_to_dict_structure(self):
        """to_dict should have proper audit structure."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        data = snapshot.to_dict()
        
        # Check structure
        assert "metadata" in data
        assert "metrics" in data
        
        # Check metadata
        assert "timestamp" in data["metadata"]
        assert "schema_version" in data["metadata"]
        assert "content_hash" in data["metadata"]
        
        # Check metrics
        assert "counters" in data["metrics"]
        assert "gauges" in data["metrics"]
        assert "histograms" in data["metrics"]


class TestMetricsSnapshotSerialization:
    """Test serialization and deserialization."""
    
    def test_to_json_and_back(self):
        """Snapshot should survive JSON round-trip."""
        store = MetricsStore()
        store.register_counter("test").inc(42)
        store.register_gauge("gauge").set(3.14)
        
        original = MetricsSnapshot.create(store)
        
        # Serialize
        json_str = original.to_json()
        
        # Deserialize
        restored = MetricsSnapshot.from_json(json_str)
        
        # Should be equal
        assert restored.timestamp == original.timestamp
        assert restored.schema_version == original.schema_version
        assert restored.content_hash == original.content_hash
        assert dict(restored.counters) == dict(original.counters)
        assert dict(restored.gauges) == dict(original.gauges)
    
    def test_to_json_pretty(self):
        """to_json with indent should be readable."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        json_str = snapshot.to_json(indent=2)
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert "metadata" in data
        
        # Should have newlines (pretty-printed)
        assert "\n" in json_str
    
    def test_from_dict_validation(self):
        """from_dict should validate structure."""
        # Missing metadata
        with pytest.raises(ValueError, match="Invalid"):
            MetricsSnapshot.from_dict({"metrics": {}})
        
        # Missing metrics
        with pytest.raises(ValueError, match="Invalid"):
            MetricsSnapshot.from_dict({"metadata": {}})
    
    def test_from_json_invalid(self):
        """from_json should reject invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            MetricsSnapshot.from_json("not json")
    
    def test_serialization_determinism(self):
        """Same snapshot should serialize to same JSON."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        json1 = snapshot.to_json()
        json2 = snapshot.to_json()
        
        assert json1 == json2


class TestMetricsSnapshotMetrics:
    """Test metric counting and statistics."""
    
    def test_get_metric_count(self):
        """get_metric_count should be accurate."""
        store = MetricsStore()
        
        store.register_counter("c1")
        store.register_counter("c2")
        store.register_gauge("g1")
        store.register_histogram("h1")
        
        snapshot = MetricsSnapshot.create(store)
        counts = snapshot.get_metric_count()
        
        assert counts == {"counters": 2, "gauges": 1, "histograms": 1}
    
    def test_get_total_metric_count(self):
        """get_total_metric_count should sum all types."""
        store = MetricsStore()
        
        store.register_counter("c1")
        store.register_gauge("g1")
        store.register_histogram("h1")
        
        snapshot = MetricsSnapshot.create(store)
        
        assert snapshot.get_total_metric_count() == 3
    
    def test_empty_snapshot_counts(self):
        """Empty snapshot should have zero counts."""
        store = MetricsStore()
        snapshot = MetricsSnapshot.create(store)
        
        counts = snapshot.get_metric_count()
        assert counts == {"counters": 0, "gauges": 0, "histograms": 0}
        
        assert snapshot.get_total_metric_count() == 0


class TestMetricsSnapshotStringRepresentation:
    """Test string representations."""
    
    def test_str(self):
        """__str__ should be human-readable."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        str_repr = str(snapshot)
        
        assert "MetricsSnapshot" in str_repr
        assert "timestamp=" in str_repr
        assert "counters=1" in str_repr
    
    def test_repr(self):
        """__repr__ should be detailed."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        repr_str = repr(snapshot)
        
        assert "MetricsSnapshot" in repr_str
        assert "schema_version" in repr_str
        assert "content_hash" in repr_str


class TestCompareSnapshots:
    """Test snapshot comparison utility."""
    
    def test_compare_identical_snapshots(self):
        """Identical snapshots should be detected."""
        store = MetricsStore()
        store.register_counter("test").inc(10)
        
        snapshot1 = MetricsSnapshot.create(store)
        snapshot2 = MetricsSnapshot.create(store)
        
        comparison = compare_snapshots(snapshot1, snapshot2)
        
        # Content should be identical
        assert comparison["content_hash_diff"] is False
        assert comparison["identical"] is True
    
    def test_compare_different_snapshots(self):
        """Different snapshots should be detected."""
        store = MetricsStore()
        counter = store.register_counter("test")
        
        counter.inc(10)
        snapshot1 = MetricsSnapshot.create(store)
        
        counter.inc(5)
        snapshot2 = MetricsSnapshot.create(store)
        
        comparison = compare_snapshots(snapshot1, snapshot2)
        
        assert comparison["content_hash_diff"] is True
        assert comparison["identical"] is False


class TestValidateSnapshotChain:
    """Test snapshot chain validation."""
    
    def test_valid_chain(self):
        """Valid chain should pass validation."""
        store = MetricsStore()
        counter = store.register_counter("test")
        
        snapshots = []
        for i in range(5):
            counter.inc(1)
            time.sleep(0.01)  # Ensure different timestamps
            snapshots.append(MetricsSnapshot.create(store))
        
        result = validate_snapshot_chain(snapshots)
        
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["snapshot_count"] == 5
    
    def test_empty_chain(self):
        """Empty chain should be valid."""
        result = validate_snapshot_chain([])
        
        assert result["valid"] is True
        assert result["issues"] == []
    
    def test_single_snapshot_chain(self):
        """Single snapshot should be valid."""
        store = MetricsStore()
        snapshot = MetricsSnapshot.create(store)
        
        result = validate_snapshot_chain([snapshot])
        
        assert result["valid"] is True


class TestMetricsSnapshotEdgeCases:
    """Edge cases and error conditions."""
    
    def test_create_from_none_store(self):
        """Creating from None store should fail."""
        with pytest.raises(ValueError, match="cannot be None"):
            MetricsSnapshot.create(None)
    
    def test_empty_store_snapshot(self):
        """Empty store should produce valid snapshot."""
        store = MetricsStore()
        snapshot = MetricsSnapshot.create(store)
        
        assert len(snapshot.counters) == 0
        assert len(snapshot.gauges) == 0
        assert len(snapshot.histograms) == 0
        assert snapshot.verify_integrity() is True
    
    def test_large_snapshot(self):
        """Large snapshot should work."""
        store = MetricsStore()
        
        # Create 1000 metrics
        for i in range(1000):
            store.register_counter(f"counter_{i}").inc(i)
        
        snapshot = MetricsSnapshot.create(store)
        
        assert len(snapshot.counters) == 1000
        assert snapshot.verify_integrity() is True
    
    def test_snapshot_with_unicode(self):
        """Snapshot with Unicode labels should work."""
        store = MetricsStore()
        store.register_counter("test", labels={"name": "مهون", "env": "تست"}).inc(10)
        
        snapshot = MetricsSnapshot.create(store)
        
        # Should serialize/deserialize correctly
        json_str = snapshot.to_json()
        restored = MetricsSnapshot.from_json(json_str)
        
        assert dict(restored.counters) == dict(snapshot.counters)


class TestMetricsSnapshotPerformance:
    """Performance tests."""
    
    def test_snapshot_creation_performance(self):
        """Snapshot creation should be fast."""
        store = MetricsStore()
        
        # Pre-populate
        for i in range(1000):
            store.register_counter(f"c_{i}").inc(i)
        
        times = []
        for _ in range(10):
            start = time.time()
            MetricsSnapshot.create(store)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n  Avg snapshot creation: {avg_time*1000:.2f}ms")
        
        assert avg_time < 0.5, f"Too slow: {avg_time}s"
    
    def test_integrity_verification_performance(self):
        """Integrity verification should be fast."""
        store = MetricsStore()
        
        for i in range(1000):
            store.register_counter(f"c_{i}").inc(i)
        
        snapshot = MetricsSnapshot.create(store)
        
        times = []
        for _ in range(10):
            start = time.time()
            snapshot.verify_integrity()
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        
        print(f"\n  Avg integrity check: {avg_time*1000:.2f}ms")
        
        assert avg_time < 0.5, f"Too slow: {avg_time}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
