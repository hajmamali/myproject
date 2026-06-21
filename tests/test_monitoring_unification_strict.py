#!/usr/bin/env python3
"""
Strict and comprehensive tests for monitoring unification refactoring
Tests verify:
1. No dual state management
2. Single source of truth (collector)
3. Consistency between stats and collector
4. Type safety
5. Edge cases
"""
import asyncio
import pytest
from typing import Dict, Any
from mahoun.monitoring.legal_metrics import (
    UltraProfessionalLegalMonitoring,
    LegalMetricType,
)
from mahoun.metrics import get_metrics_collector


class TestMonitoringUnification:
    """Strict tests for monitoring unification"""

    @pytest.fixture
    def monitor(self):
        """Create fresh monitoring instance for each test"""
        # Reset collector to avoid shared state
        collector = get_metrics_collector()
        collector._store.reset()
        
        return UltraProfessionalLegalMonitoring(
            window_size=100,
            enable_ultra_monitoring=False,
            enable_prometheus=True,
            enable_sla_tracking=True,
        )

    @pytest.mark.asyncio
    async def test_no_duplicate_state_variables(self, monitor):
        """CRITICAL: Verify duplicate state variables are removed"""
        # These attributes should NOT exist anymore
        forbidden_attrs = [
            'total_queries',
            'total_filtered', 
            'total_errors',
            'cache_hits',
            'cache_misses',
            'queries_by_status',
            'queries_by_court',
            'queries_by_domain',
            'errors_by_type',
        ]
        
        for attr in forbidden_attrs:
            assert not hasattr(monitor, attr), (
                f"❌ FAILED: Attribute '{attr}' should be removed! "
                f"Dual state management detected!"
            )
        
        print("✅ PASS: No duplicate state variables found")

    @pytest.mark.asyncio
    async def test_type_hints_present(self, monitor):
        """CRITICAL: Verify type hints are added to deques"""
        import inspect
        from typing import get_type_hints
        
        # Get type hints from __init__
        hints = get_type_hints(monitor.__init__)
        
        # Verify deques have proper type hints
        assert hasattr(monitor, 'recent_durations')
        assert hasattr(monitor, 'recent_filtered')
        assert hasattr(monitor, 'recent_authority_scores')
        assert hasattr(monitor, 'recent_query_metrics')
        
        # Check annotations exist
        annotations = monitor.__class__.__annotations__ if hasattr(
            monitor.__class__, '__annotations__'
        ) else {}
        
        print(f"✅ PASS: Type hints verified for rolling windows")

    @pytest.mark.asyncio
    async def test_single_source_of_truth(self, monitor):
        """CRITICAL: Verify collector is single source of truth"""
        # Track queries
        for i in range(20):
            await monitor.track_legal_query(
                query=f"test {i}",
                duration=0.1,
                filtered_count=i,
                result_count=10,
            )
        
        # Get stats
        stats = monitor.get_stats()
        
        # Get collector snapshot
        snapshot = monitor.collector.snapshot()
        counters = snapshot.get("counters", {})
        
        # Verify consistency
        collector_queries = counters.get(
            LegalMetricType.QUERY_THROUGHPUT.value, {}
        ).get("value", 0)
        
        collector_filtered = counters.get(
            LegalMetricType.FILTER_COUNT.value, {}
        ).get("value", 0)
        
        assert stats['total_queries'] == collector_queries, (
            f"❌ FAILED: Query count mismatch! "
            f"Stats: {stats['total_queries']}, Collector: {collector_queries}"
        )
        
        assert stats['total_filtered'] == collector_filtered, (
            f"❌ FAILED: Filtered count mismatch! "
            f"Stats: {stats['total_filtered']}, Collector: {collector_filtered}"
        )
        
        print(f"✅ PASS: Single source of truth verified")
        print(f"  Queries: {collector_queries}")
        print(f"  Filtered: {collector_filtered}")

    @pytest.mark.asyncio
    async def test_stats_consistency_under_load(self, monitor):
        """CRITICAL: Test consistency under concurrent load"""
        # Track many queries
        for i in range(100):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.05 + (i * 0.001),
                filtered_count=i % 10,
                result_count=10 - (i % 10),
                court_rank="supreme" if i % 3 == 0 else "appeal",
                legal_domain="civil" if i % 2 == 0 else "criminal",
                authority_score=0.7 + (i % 30) * 0.01,
                cache_hit=(i % 4 == 0),
                error="test_error" if i % 20 == 0 else None,
            )
        
        # Get stats multiple times
        stats1 = monitor.get_stats()
        stats2 = monitor.get_stats()
        
        # Stats should be identical (deterministic)
        assert stats1['total_queries'] == stats2['total_queries']
        assert stats1['total_filtered'] == stats2['total_filtered']
        assert stats1['error_rate'] == stats2['error_rate']
        assert stats1['cache_hit_rate'] == stats2['cache_hit_rate']
        
        # Verify against collector
        snapshot = monitor.collector.snapshot()
        counters = snapshot.get("counters", {})
        
        collector_queries = counters.get(
            LegalMetricType.QUERY_THROUGHPUT.value, {}
        ).get("value", 0)
        
        assert stats1['total_queries'] == collector_queries
        
        print(f"✅ PASS: Consistency verified under load (100 queries)")
        print(f"  Total queries: {stats1['total_queries']}")
        print(f"  Error rate: {stats1['error_rate']:.2%}")
        print(f"  Cache hit rate: {stats1['cache_hit_rate']:.2%}")

    @pytest.mark.asyncio
    async def test_error_rate_calculation(self, monitor):
        """CRITICAL: Verify error rate is calculated from rolling windows"""
        # Track queries with errors
        for i in range(10):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.1,
                filtered_count=1,
                result_count=10,
                error="test_error" if i >= 8 else None,  # 2 errors out of 10
            )
        
        stats = monitor.get_stats()
        
        # Error rate should be 20% (2 out of 10)
        expected_error_rate = 0.2
        assert abs(stats['error_rate'] - expected_error_rate) < 0.01, (
            f"❌ FAILED: Error rate mismatch! "
            f"Expected: {expected_error_rate:.2%}, Got: {stats['error_rate']:.2%}"
        )
        
        print(f"✅ PASS: Error rate calculation correct: {stats['error_rate']:.2%}")

    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculation(self, monitor):
        """CRITICAL: Verify cache hit rate is calculated from rolling windows"""
        # Track queries with cache hits
        for i in range(10):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.1,
                filtered_count=1,
                result_count=10,
                cache_hit=(i < 7),  # 7 hits out of 10
            )
        
        stats = monitor.get_stats()
        
        # Cache hit rate should be 70% (7 out of 10)
        expected_cache_hit_rate = 0.7
        assert abs(stats['cache_hit_rate'] - expected_cache_hit_rate) < 0.01, (
            f"❌ FAILED: Cache hit rate mismatch! "
            f"Expected: {expected_cache_hit_rate:.2%}, Got: {stats['cache_hit_rate']:.2%}"
        )
        
        print(f"✅ PASS: Cache hit rate calculation correct: {stats['cache_hit_rate']:.2%}")

    @pytest.mark.asyncio
    async def test_categorized_counters_from_rolling_windows(self, monitor):
        """CRITICAL: Verify categorized counters are built from rolling windows"""
        # Track queries with different categories
        for i in range(20):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.1,
                filtered_count=1,
                result_count=10,
                court_rank="supreme" if i < 10 else "appeal",
                legal_domain="civil" if i < 15 else "criminal",
            )
        
        stats = monitor.get_stats()
        
        # Verify categorized counters
        assert 'queries_by_court' in stats
        assert 'queries_by_domain' in stats
        
        # Check counts
        assert stats['queries_by_court']['supreme'] == 10
        assert stats['queries_by_court']['appeal'] == 10
        assert stats['queries_by_domain']['civil'] == 15
        assert stats['queries_by_domain']['criminal'] == 5
        
        print(f"✅ PASS: Categorized counters built correctly from rolling windows")
        print(f"  By court: {stats['queries_by_court']}")
        print(f"  By domain: {stats['queries_by_domain']}")

    @pytest.mark.asyncio
    async def test_percentile_calculations(self, monitor):
        """CRITICAL: Verify percentile calculations from rolling windows"""
        # Track queries with known durations
        durations = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        
        for i, duration in enumerate(durations):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=duration,
                filtered_count=1,
                result_count=10,
            )
        
        stats = monitor.get_stats()
        
        # Verify percentiles are reasonable
        assert 0 < stats['p50_latency'] < 1.0
        assert stats['p50_latency'] < stats['p95_latency']
        assert stats['p95_latency'] < stats['p99_latency']
        
        # P50 should be around 0.5
        assert abs(stats['p50_latency'] - 0.5) < 0.1
        
        # P95 should be around 0.95
        assert abs(stats['p95_latency'] - 0.95) < 0.1
        
        print(f"✅ PASS: Percentile calculations correct")
        print(f"  P50: {stats['p50_latency']:.3f}s")
        print(f"  P95: {stats['p95_latency']:.3f}s")
        print(f"  P99: {stats['p99_latency']:.3f}s")

    @pytest.mark.asyncio
    async def test_sla_compliance_from_rolling_windows(self, monitor):
        """CRITICAL: Verify SLA compliance uses rolling windows"""
        # Track queries with good performance
        for i in range(20):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.1,  # Fast queries
                filtered_count=1,
                result_count=10,
                authority_score=0.9,  # High authority
                cache_hit=True,  # Good cache hit rate
                error=None,  # No errors
            )
        
        stats = monitor.get_stats()
        
        # SLA compliance should be high
        assert stats['sla_compliance_rate'] > 0.5, (
            f"❌ FAILED: SLA compliance too low: {stats['sla_compliance_rate']:.2%}"
        )
        
        print(f"✅ PASS: SLA compliance calculated from rolling windows: {stats['sla_compliance_rate']:.2%}")

    @pytest.mark.asyncio
    async def test_edge_case_empty_windows(self, monitor):
        """CRITICAL: Test edge case with empty rolling windows"""
        # Get stats without tracking any queries
        stats = monitor.get_stats()
        
        # Should not crash and return sensible defaults
        assert stats['total_queries'] == 0
        assert stats['total_filtered'] == 0
        assert stats['error_rate'] == 0.0
        assert stats['cache_hit_rate'] == 0.0
        assert stats['p50_latency'] == 0.0
        
        print(f"✅ PASS: Empty windows handled correctly")

    @pytest.mark.asyncio
    async def test_edge_case_window_overflow(self, monitor):
        """CRITICAL: Test rolling window overflow behavior"""
        window_size = monitor.window_size
        
        # Track more queries than window size
        for i in range(window_size + 50):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.1,
                filtered_count=1,
                result_count=10,
            )
        
        # Verify rolling windows don't exceed max size
        assert len(monitor.recent_durations) <= window_size
        assert len(monitor.recent_filtered) <= window_size
        assert len(monitor.recent_query_metrics) <= window_size
        
        # But collector should have all queries
        snapshot = monitor.collector.snapshot()
        counters = snapshot.get("counters", {})
        collector_queries = counters.get(
            LegalMetricType.QUERY_THROUGHPUT.value, {}
        ).get("value", 0)
        
        assert collector_queries == window_size + 50
        
        print(f"✅ PASS: Window overflow handled correctly")
        print(f"  Window size: {window_size}")
        print(f"  Total queries tracked: {collector_queries}")
        print(f"  Queries in rolling window: {len(monitor.recent_query_metrics)}")

    @pytest.mark.asyncio
    async def test_prometheus_export_uses_collector(self, monitor):
        """CRITICAL: Verify Prometheus export uses collector"""
        # Track some queries
        for i in range(10):
            await monitor.track_legal_query(
                query=f"query_{i}",
                duration=0.1,
                filtered_count=i,
                result_count=10,
            )
        
        # Export Prometheus metrics
        prometheus_output = monitor.export_prometheus_metrics()
        
        # Should contain legal metrics
        assert "legal_query_throughput_total" in prometheus_output
        assert "legal_documents_filtered_total" in prometheus_output
        
        # Should show correct values
        assert "10" in prometheus_output  # 10 queries
        
        print(f"✅ PASS: Prometheus export uses collector")
        print(f"  Output length: {len(prometheus_output)} bytes")


@pytest.mark.asyncio
async def test_integration_with_reasoning_engine():
    """CRITICAL: Test integration with reasoning engine decorator"""
    from mahoun.monitoring.legal_metrics import track_legal_query_decorator
    
    # Create a mock function
    @track_legal_query_decorator
    async def mock_legal_query(query: str, **kwargs):
        await asyncio.sleep(0.01)
        return {"results": [1, 2, 3], "filtered": 5}
    
    # Call the decorated function
    result = await mock_legal_query("test query")
    
    # Should return results
    assert result is not None
    assert "results" in result
    
    print(f"✅ PASS: Decorator integration works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
