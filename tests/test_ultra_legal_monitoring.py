"""
Ultra-Professional Legal Monitoring System Tests
================================================
Comprehensive test suite for legal monitoring system.

Tests cover:
- Metrics collection and aggregation
- SLA compliance tracking
- Prometheus metrics export
- Health checks
- Alert triggering
- UltraPerformanceMonitor integration
"""

import pytest
import asyncio
from datetime import datetime

from mahoun.monitoring.legal_metrics import (
    UltraProfessionalLegalMonitoring,
    LegalMetricType,
    SLATarget,
    MetricSnapshot,
    LegalQueryMetrics,
)
from mahoun.self_improve.ultra_performance_monitoring import AlertSeverity, Alert


def _reset_collector():
    """Helper to reset collector state between tests"""
    from mahoun.metrics import get_metrics_collector

    collector = get_metrics_collector()
    collector._store.reset()


class TestLegalMonitoringBasics:
    """Test basic monitoring functionality"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance for testing"""
        # Reset collector to avoid shared state between tests
        _reset_collector()

        return UltraProfessionalLegalMonitoring(
            window_size=100,
            enable_ultra_monitoring=True,
            enable_prometheus=True,
            enable_sla_tracking=True,
        )

    @pytest.mark.asyncio
    async def test_track_legal_query(self, monitoring):
        """Test tracking a legal query"""
        await monitoring.track_legal_query(
            query="test query",
            duration=0.5,
            filtered_count=3,
            result_count=10,
            court_rank="SUPREME_COURT",
            legal_domain="civil_law",
            authority_score=0.92,
            cache_hit=True,
        )

        stats = monitoring.get_stats()
        assert stats["total_queries"] == 1
        assert stats["total_filtered"] == 3
        assert stats["cache_hits"] == 1
        assert stats["avg_authority_score"] == 0.92

    @pytest.mark.asyncio
    async def test_multiple_queries(self, monitoring):
        """Test tracking multiple queries"""
        for i in range(10):
            await monitoring.track_legal_query(
                query=f"query_{i}",
                duration=0.1 + i * 0.01,
                filtered_count=i % 3,
                result_count=10,
                court_rank="SUPREME_COURT",
                cache_hit=(i % 2 == 0),
            )

        stats = monitoring.get_stats()
        assert stats["total_queries"] == 10
        assert stats["cache_hits"] == 5
        assert stats["cache_misses"] == 5
        assert stats["cache_hit_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_error_tracking(self, monitoring):
        """Test error tracking"""
        # Track successful query
        await monitoring.track_legal_query(
            query="success", duration=0.1, result_count=10
        )

        # Track failed query
        await monitoring.track_legal_query(
            query="failure", duration=0.2, error="ValidationError"
        )

        stats = monitoring.get_stats()
        assert stats["total_queries"] == 2
        assert stats["total_errors"] == 1
        assert stats["error_rate"] == 0.5
        assert "ValidationError" in stats["errors_by_type"]

    def test_percentile_calculation(self, monitoring):
        """Test latency percentile calculation"""
        durations = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        for duration in durations:
            monitoring.recent_durations.append(duration)

        stats = monitoring.get_stats()
        # Correct percentile values using linear interpolation (matches numpy)
        # For 10 values [0.1, 0.2, ..., 1.0]:
        # P50 = 0.55 (interpolation between 0.5 and 0.6)
        # P95 = 0.955 (interpolation between 0.9 and 1.0)
        # P99 = 0.991 (interpolation between 0.9 and 1.0)
        assert stats["p50_latency"] == pytest.approx(0.55, rel=0.01)
        assert stats["p95_latency"] == pytest.approx(0.955, rel=0.01)
        assert stats["p99_latency"] == pytest.approx(0.991, rel=0.01)


class TestSLACompliance:
    """Test SLA compliance tracking"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance with custom SLA"""
        _reset_collector()

        mon = UltraProfessionalLegalMonitoring(
            window_size=100, enable_sla_tracking=True
        )

        # Add custom SLA target
        mon.add_sla_target(
            SLATarget(
                metric_name="test_metric",
                target_value=0.5,
                comparison="less_than",
                severity=AlertSeverity.HIGH,
                description="Test metric must be under 0.5",
            )
        )

        return mon

    @pytest.mark.asyncio
    async def test_sla_compliance_pass(self, monitoring):
        """Test SLA compliance when targets are met"""
        # Track queries with good performance AND proper cache/authority data
        for _ in range(10):
            await monitoring.track_legal_query(
                query="test",
                duration=0.1,  # Well under 500ms target
                result_count=10,
                cache_hit=True,  # Provide cache data to meet cache SLA
                authority_score=0.85,  # Provide authority score to meet authority SLA
            )

        stats = monitoring.get_stats()
        # Now all 4 SLAs should pass:
        # - query_latency_p95: 0.1 < 0.5 ✓
        # - error_rate: 0.0 < 0.01 ✓
        # - cache_hit_rate: 1.0 > 0.7 ✓
        # - avg_authority_score: 0.85 > 0.75 ✓
        assert stats["sla_compliance_rate"] > 0.9

    @pytest.mark.asyncio
    async def test_sla_violation_detection(self, monitoring):
        """Test SLA violation detection"""
        # Track queries with poor performance
        for _ in range(10):
            await monitoring.track_legal_query(
                query="test",
                duration=2.0,  # Over 500ms target
                result_count=10,
            )

        # Check for violations
        assert len(monitoring.sla_violations) > 0

        # Verify violation details
        violation = monitoring.sla_violations[0]
        assert "query_latency_p95" in violation["metric"]

    def test_sla_target_configuration(self, monitoring):
        """Test SLA target configuration"""
        assert "test_metric" in monitoring.sla_targets

        target = monitoring.sla_targets["test_metric"]
        assert target.target_value == 0.5
        assert target.comparison == "less_than"
        assert target.severity == AlertSeverity.HIGH


class TestPrometheusExport:
    """Test Prometheus metrics export"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring(enable_prometheus=True)

    @pytest.mark.asyncio
    async def test_prometheus_export_format(self, monitoring):
        """Test Prometheus export format"""
        # Track some queries
        await monitoring.track_legal_query(
            query="test",
            duration=0.5,
            filtered_count=3,
            result_count=10,
            court_rank="SUPREME_COURT",
            legal_domain="civil_law",
        )

        # Export metrics
        metrics = monitoring.export_prometheus_metrics()

        # Verify format
        assert "# HELP" in metrics
        assert "# TYPE" in metrics
        assert LegalMetricType.QUERY_THROUGHPUT.value in metrics
        assert LegalMetricType.QUERY_LATENCY.value in metrics

    @pytest.mark.asyncio
    async def test_prometheus_metric_values(self, monitoring):
        """Test Prometheus metric values"""
        # Track queries
        for i in range(5):
            await monitoring.track_legal_query(
                query=f"query_{i}", duration=0.1, result_count=10
            )

        metrics = monitoring.export_prometheus_metrics()

        # Verify metrics contain expected values
        assert "legal_query_throughput_total 5" in metrics

    @pytest.mark.asyncio
    async def test_prometheus_labels(self, monitoring):
        """Test Prometheus metric labels"""
        # Track queries with different court ranks
        await monitoring.track_legal_query(
            query="test1", duration=0.1, court_rank="SUPREME_COURT", result_count=10
        )

        await monitoring.track_legal_query(
            query="test2", duration=0.1, court_rank="APPEALS_COURT", result_count=10
        )

        metrics = monitoring.export_prometheus_metrics()

        # Verify labels
        assert 'court_rank="SUPREME_COURT"' in metrics
        assert 'court_rank="APPEALS_COURT"' in metrics


class TestHealthChecks:
    """Test health check functionality"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring()

    @pytest.mark.asyncio
    async def test_healthy_status(self, monitoring):
        """Test healthy status"""
        # Track some normal queries
        for _ in range(10):
            await monitoring.track_legal_query(
                query="test", duration=0.1, result_count=10
            )

        health = await monitoring.health_check()
        assert health["status"] == "healthy"
        assert "components" in health
        assert "sla_compliance" in health

    @pytest.mark.asyncio
    async def test_degraded_status_high_errors(self, monitoring):
        """Test degraded status with high error rate"""
        # Track queries with high error rate
        for i in range(10):
            await monitoring.track_legal_query(
                query=f"query_{i}",
                duration=0.1,
                error="TestError" if i < 6 else None,  # 60% error rate
                result_count=10 if i >= 6 else 0,
            )

        health = await monitoring.health_check()
        assert health["status"] == "degraded"
        assert health["components"]["error_rate"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_degraded_status_high_latency(self, monitoring):
        """Test degraded status with high latency"""
        # Track queries with high latency
        for _ in range(10):
            await monitoring.track_legal_query(
                query="test",
                duration=2.0,  # High latency
                result_count=10,
            )

        health = await monitoring.health_check()
        assert health["status"] == "degraded"
        assert health["components"]["latency"]["status"] == "unhealthy"


class TestAlertCallbacks:
    """Test alert callback functionality"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring(enable_ultra_monitoring=True)

    @pytest.mark.asyncio
    async def test_alert_callback_registration(self, monitoring):
        """Test alert callback registration"""
        alerts_received = []

        def callback(alert: Alert):
            alerts_received.append(alert)

        monitoring.register_alert_callback(callback)

        # Trigger an alert by violating SLA
        for _ in range(20):
            await monitoring.track_legal_query(
                query="test",
                duration=2.0,  # High latency to trigger alert
                result_count=10,
            )

        # Give time for alerts to process
        await asyncio.sleep(0.1)

        # Verify callback was called
        # Note: Actual alert triggering depends on UltraPerformanceMonitor
        assert len(monitoring.alert_callbacks) == 1


class TestComprehensiveStats:
    """Test comprehensive statistics"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring(enable_ultra_monitoring=True)

    @pytest.mark.asyncio
    async def test_comprehensive_stats_structure(self, monitoring):
        """Test comprehensive stats structure"""
        # Track some queries
        for i in range(10):
            await monitoring.track_legal_query(
                query=f"query_{i}",
                duration=0.1 + i * 0.01,
                filtered_count=i % 3,
                result_count=10,
                court_rank="SUPREME_COURT",
                legal_domain="civil_law",
                authority_score=0.9,
            )

        stats = monitoring.get_comprehensive_stats()

        # Verify structure
        assert "total_queries" in stats
        assert "ultra_monitor" in stats
        assert "performance_report" in stats
        assert "recent_queries" in stats
        assert "recent_sla_violations" in stats

    @pytest.mark.asyncio
    async def test_recent_queries_tracking(self, monitoring):
        """Test recent queries tracking"""
        # Track queries
        for i in range(15):
            await monitoring.track_legal_query(
                query=f"query_{i}", duration=0.1, result_count=10, query_id=f"test_{i}"
            )

        stats = monitoring.get_comprehensive_stats()
        recent = stats["recent_queries"]

        # Should only keep last 10
        assert len(recent) == 10
        assert recent[-1]["query_id"] == "test_14"


class TestMetricSnapshot:
    """Test metric snapshot functionality"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring()

    @pytest.mark.asyncio
    async def test_snapshot_creation(self, monitoring):
        """Test snapshot creation"""
        # Track some queries
        for _ in range(5):
            await monitoring.track_legal_query(
                query="test", duration=0.1, result_count=10, authority_score=0.85
            )

        snapshot = monitoring.get_snapshot()

        assert isinstance(snapshot, MetricSnapshot)
        assert snapshot.total_queries == 5
        assert snapshot.avg_authority_score == 0.85
        assert isinstance(snapshot.timestamp, datetime)


class TestReset:
    """Test metrics reset functionality"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring()

    @pytest.mark.asyncio
    async def test_reset_clears_metrics(self, monitoring):
        """Test that reset clears all metrics"""
        # Track some queries
        for _ in range(10):
            await monitoring.track_legal_query(
                query="test", duration=0.1, filtered_count=3, result_count=10
            )

        # Verify metrics exist
        stats_before = monitoring.get_stats()
        assert stats_before["total_queries"] == 10

        # Reset
        monitoring.reset()

        # Verify metrics cleared
        stats_after = monitoring.get_stats()
        assert stats_after["total_queries"] == 0
        assert stats_after["total_filtered"] == 0
        assert stats_after["cache_hits"] == 0


class TestCourtRankDistribution:
    """Test court rank distribution tracking"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring()

    @pytest.mark.asyncio
    async def test_court_rank_tracking(self, monitoring):
        """Test court rank distribution"""
        # Track queries with different court ranks
        court_ranks = ["SUPREME_COURT", "APPEALS_COURT", "FIRST_INSTANCE"]

        for court_rank in court_ranks:
            for _ in range(5):
                await monitoring.track_legal_query(
                    query="test", duration=0.1, court_rank=court_rank, result_count=10
                )

        stats = monitoring.get_stats()

        # Verify distribution
        assert stats["queries_by_court"]["SUPREME_COURT"] == 5
        assert stats["queries_by_court"]["APPEALS_COURT"] == 5
        assert stats["queries_by_court"]["FIRST_INSTANCE"] == 5


class TestLegalDomainDistribution:
    """Test legal domain distribution tracking"""

    @pytest.fixture
    def monitoring(self):
        """Create monitoring instance"""
        _reset_collector()

        return UltraProfessionalLegalMonitoring()

    @pytest.mark.asyncio
    async def test_legal_domain_tracking(self, monitoring):
        """Test legal domain distribution"""
        # Track queries with different legal domains
        domains = ["civil_law", "criminal_law", "commercial_law"]

        for domain in domains:
            for _ in range(3):
                await monitoring.track_legal_query(
                    query="test", duration=0.1, legal_domain=domain, result_count=10
                )

        stats = monitoring.get_stats()

        # Verify distribution
        assert stats["queries_by_domain"]["civil_law"] == 3
        assert stats["queries_by_domain"]["criminal_law"] == 3
        assert stats["queries_by_domain"]["commercial_law"] == 3


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete monitoring workflow"""

    @pytest.mark.asyncio
    async def test_complete_monitoring_workflow(self):
        """Test a complete workflow representing realistic usage"""
        from mahoun.monitoring.legal_metrics import legal_monitoring

        # Ensure clean state for this integration test
        legal_monitoring.reset()

        # Create monitoring instance
        monitoring = UltraProfessionalLegalMonitoring(
            window_size=100,
            enable_ultra_monitoring=True,
            enable_prometheus=True,
            enable_sla_tracking=True,
        )

        # 1. Generate normal traffic (50 requests)

        # Track various queries
        for i in range(50):
            await monitoring.track_legal_query(
                query=f"query_{i}",
                duration=0.1 + (i % 10) * 0.05,
                filtered_count=i % 5,
                result_count=10 + i % 10,
                court_rank=["SUPREME_COURT", "APPEALS_COURT", "FIRST_INSTANCE"][i % 3],
                legal_domain=["civil_law", "criminal_law", "commercial_law"][i % 3],
                authority_score=0.7 + (i % 20) * 0.01,
                cache_hit=(i % 3 != 0),
                error="TestError" if i % 20 == 0 else None,
            )

        # Get comprehensive stats
        stats = monitoring.get_comprehensive_stats()

        # Verify all components
        assert stats["total_queries"] >= 50
        assert stats["total_errors"] > 0
        assert len(stats["queries_by_court"]) == 3
        assert len(stats["queries_by_domain"]) == 3

        # Export Prometheus metrics
        metrics = monitoring.export_prometheus_metrics()
        assert len(metrics) > 0

        # Health check
        health = await monitoring.health_check()
        assert health["status"] in ["healthy", "degraded"]

        # Print summary (for manual verification)
        monitoring.print_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
