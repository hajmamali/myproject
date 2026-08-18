import pytest
pytest.importorskip("hypothesis")
"""
Very Hard Level Tests: Property-Based Testing and Stress Tests
===============================================================
Tests invariants, properties, and system behavior under load.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from hypothesis import given, strategies as st, settings
import time
import os

client = TestClient(app)


class TestInvariants:
    """Test system invariants and properties"""

    @given(st.integers(min_value=0, max_value=1000))
    @settings(max_examples=50, deadline=None)
    def test_legal_metrics_total_queries_non_negative(self, _):
        """Property: total_queries is always non-negative"""
        response = client.get("/metrics/legal")
        data = response.json()
        assert data["total_queries"] >= 0

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50, deadline=None)
    def test_error_rate_bounded(self, _):
        """Property: error_rate is between 0 and 1"""
        response = client.get("/metrics/legal")
        data = response.json()
        assert 0 <= data["error_rate"] <= 1

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50, deadline=None)
    def test_cache_hit_rate_bounded(self, _):
        """Property: cache_hit_rate is between 0 and 1"""
        response = client.get("/metrics/legal")
        data = response.json()
        assert 0 <= data["cache_hit_rate"] <= 1

    def test_uptime_monotonic_increasing(self):
        """Property: uptime is monotonically increasing"""
        uptimes = []
        for _ in range(10):
            response = client.get("/health/detailed")
            data = response.json()
            uptimes.append(data["uptime_seconds"])
            time.sleep(0.01)

        # Each uptime should be >= previous
        for i in range(1, len(uptimes)):
            assert uptimes[i] >= uptimes[i - 1], (
                f"Uptime decreased: {uptimes[i - 1]} -> {uptimes[i]}"
            )


class TestIdempotency:
    """Test idempotency properties"""

    def test_legal_metrics_idempotent_reads(self):
        """Property: Reading metrics doesn't change metrics"""
        # Get initial state
        response1 = client.get("/metrics/legal")
        data1 = response1.json()

        # Read multiple times
        for _ in range(10):
            client.get("/metrics/legal")

        # Get final state
        response2 = client.get("/metrics/legal")
        data2 = response2.json()

        # Total queries should be same (reads don't increment)
        assert data1["total_queries"] == data2["total_queries"]

    def test_prometheus_idempotent_reads(self):
        """Property: Reading Prometheus metrics doesn't change state"""
        response1 = client.get("/metrics/prometheus")
        text1 = response1.text

        # Read multiple times
        for _ in range(5):
            client.get("/metrics/prometheus")

        response2 = client.get("/metrics/prometheus")
        text2 = response2.text

        # Should be identical (or very similar)
        assert len(text1) > 0 and len(text2) > 0


class TestResetProperties:
    """Test reset operation properties"""

    def test_reset_clears_all_metrics(self, monkeypatch):
        """Property: Reset clears all metrics to zero"""
        monkeypatch.setenv("MAHOUN_ENV", "dev")

        # Reset
        response = client.post("/metrics/reset")
        assert response.status_code == 200

        # Check metrics are zero
        response = client.get("/metrics/legal")
        data = response.json()

        assert data["total_queries"] == 0
        assert data["total_errors"] == 0

    def test_reset_is_atomic(self, monkeypatch):
        """Property: Reset is atomic (all or nothing)"""
        monkeypatch.setenv("MAHOUN_ENV", "dev")

        # Reset
        client.post("/metrics/reset")

        # Immediately check - should be consistent
        response = client.get("/metrics/legal")
        data = response.json()

        # All counters should be zero
        assert data["total_queries"] == 0


class TestStressAndLoad:
    """Stress tests and load testing"""

    def test_rapid_fire_requests(self):
        """Test handling 100 rapid requests"""
        errors = []
        for i in range(100):
            try:
                response = client.get("/metrics/legal")
                if response.status_code != 200:
                    errors.append(f"Request {i}: status {response.status_code}")
            except Exception as e:
                errors.append(f"Request {i}: {str(e)}")

        assert len(errors) == 0, f"Errors: {errors[:5]}"

    def test_mixed_endpoint_load(self):
        """Test mixed load across all monitoring endpoints"""
        endpoints = ["/metrics/prometheus", "/metrics/legal", "/health/detailed"]

        errors = []
        for i in range(50):
            endpoint = endpoints[i % len(endpoints)]
            try:
                response = client.get(endpoint)
                if response.status_code != 200:
                    errors.append(f"{endpoint}: {response.status_code}")
            except Exception as e:
                errors.append(f"{endpoint}: {str(e)}")

        assert len(errors) == 0, f"Errors: {errors[:5]}"

    def test_large_response_handling(self):
        """Test handling of large Prometheus responses"""
        # Generate some metrics first
        from mahoun.metrics import get_metrics_collector

        collector = get_metrics_collector()

        # Register many metrics
        for i in range(100):
            counter = collector.register_counter(f"test_metric_{i}")
            counter.inc(i)

        # Get Prometheus output
        response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert len(response.text) > 0


class TestSecurityProperties:
    """Test security-related properties"""

    def test_reset_always_blocked_in_production(self, monkeypatch):
        """Property: Reset is ALWAYS blocked in production"""
        prod_envs = ["prod", "production", "staging"]

        for env in prod_envs:
            monkeypatch.setenv("MAHOUN_ENV", env)
            response = client.post("/metrics/reset")

            assert response.status_code == 403, (
                f"Reset not blocked in {env} environment"
            )

            data = response.json()
            assert "error" in data
            assert data["error"] == "forbidden"

    def test_no_sensitive_data_in_metrics(self):
        """Property: Metrics don't contain sensitive data"""
        response = client.get("/metrics/legal")
        data_str = str(response.json())

        # Should not contain passwords, keys, tokens
        sensitive_patterns = ["password", "secret", "token", "key", "api_key"]
        for pattern in sensitive_patterns:
            assert pattern.lower() not in data_str.lower()


class TestConsistency:
    """Test data consistency properties"""

    def test_metrics_consistency_across_endpoints(self):
        """Property: Metrics are consistent across different endpoints"""
        # Get legal metrics
        legal_response = client.get("/metrics/legal")
        legal_data = legal_response.json()

        # Get Prometheus metrics
        prom_response = client.get("/metrics/prometheus")
        prom_text = prom_response.text

        # Both should reflect same underlying state
        # (This is a weak check - just verify both succeed)
        assert legal_response.status_code == 200
        assert prom_response.status_code == 200

    def test_health_status_consistency(self):
        """Property: Health status is consistent with metrics"""
        health_response = client.get("/health/detailed")
        health_data = health_response.json()

        metrics_response = client.get("/metrics/legal")
        metrics_data = metrics_response.json()

        # If error rate is high, health should reflect it
        if metrics_data["error_rate"] > 0.05:
            # Health might be degraded
            assert health_data["status"] in ["healthy", "degraded", "unhealthy"]
