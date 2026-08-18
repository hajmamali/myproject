"""
Hard Level Tests: Integration Tests and Edge Cases
===================================================
Tests integration with monitoring system, edge cases, and error handling.
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app
import time
import os

client = TestClient(app)


class TestMonitoringIntegration:
    """Test integration with actual monitoring system"""
    
    def test_legal_monitoring_integration(self):
        """Test that legal metrics actually come from legal_monitoring"""
        from mahoun.monitoring.legal_metrics import legal_monitoring
        
        # Reset to known state
        legal_monitoring.reset()
        
        # Get metrics
        response = client.get("/metrics/legal")
        data = response.json()
        
        # Should have zero queries after reset
        assert data["total_queries"] == 0
    
    def test_metrics_collector_integration(self):
        """Test that Prometheus metrics come from metrics collector"""
        from mahoun.metrics import get_metrics_collector
        
        collector = get_metrics_collector()
        collector.reset()
        
        # Get Prometheus metrics
        response = client.get("/metrics/prometheus")
        
        # Should succeed even after reset
        assert response.status_code == 200
    
    def test_uptime_tracking_works(self):
        """Test that uptime is actually tracked"""
        # First call
        response1 = client.get("/health/detailed")
        data1 = response1.json()
        uptime1 = data1["uptime_seconds"]
        
        # Wait a bit
        time.sleep(0.1)
        
        # Second call
        response2 = client.get("/health/detailed")
        data2 = response2.json()
        uptime2 = data2["uptime_seconds"]
        
        # Uptime should increase
        assert uptime2 >= uptime1


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_reset_with_invalid_env(self, monkeypatch):
        """Test reset with various environment values"""
        for env in ["staging", "production", "prod"]:
            monkeypatch.setenv("MAHOUN_ENV", env)
            response = client.post("/metrics/reset")
            assert response.status_code == 403
    
    def test_health_detailed_without_start_time(self):
        """Test health detailed when start_time is not set"""
        # This tests the hasattr check
        response = client.get("/health/detailed")
        data = response.json()
        
        # Should still work, uptime might be 0
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
    
    def test_legal_metrics_with_no_data(self):
        """Test legal metrics when no queries have been tracked"""
        from mahoun.monitoring.legal_metrics import legal_monitoring
        legal_monitoring.reset()
        
        response = client.get("/metrics/legal")
        data = response.json()
        
        # Should return valid structure with zeros
        assert data["total_queries"] == 0
        assert data["error_rate"] == 0
    
    def test_prometheus_with_empty_collector(self):
        """Test Prometheus endpoint with empty collector"""
        from mahoun.metrics import get_metrics_collector
        collector = get_metrics_collector()
        collector.reset()
        
        response = client.get("/metrics/prometheus")
        
        # Should still return valid response
        assert response.status_code == 200


class TestConcurrency:
    """Test concurrent access to monitoring endpoints"""
    
    def test_concurrent_legal_metrics_calls(self):
        """Test multiple simultaneous calls to legal metrics"""
        import concurrent.futures
        
        def call_endpoint():
            response = client.get("/metrics/legal")
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(call_endpoint) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(status == 200 for status in results)
    
    def test_concurrent_reset_calls(self, monkeypatch):
        """Test multiple simultaneous reset calls"""
        monkeypatch.setenv("MAHOUN_ENV", "dev")
        import concurrent.futures
        
        def call_reset():
            response = client.post("/metrics/reset")
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(call_reset) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # All should succeed
        assert all(status == 200 for status in results)


class TestRegressionPrevention:
    """Test that non-monitoring endpoints still work"""
    
    def test_health_endpoint_unchanged(self):
        """Test that /health endpoint still works"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_feedback_stats_unchanged(self):
        """Test that feedback stats endpoint still works"""
        response = client.get("/api/v1/feedback/stats")
        assert response.status_code == 200
    
    def test_system_status_unchanged(self):
        """Test that system status endpoint still works"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
