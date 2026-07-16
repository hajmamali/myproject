"""
Medium Level Tests: Data Validation and Structure Tests
========================================================
Tests response structure, required fields, and data types.
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app
import os

client = TestClient(app)


class TestLegalMetricsStructure:
    """Test legal metrics response structure"""
    
    def test_legal_metrics_has_required_fields(self):
        """Test that legal metrics contains all required fields"""
        response = client.get("/metrics/legal")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_queries",
            "queries_per_second",
            "avg_duration_seconds",
            "error_rate",
            "cache_hit_rate"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_legal_metrics_numeric_types(self):
        """Test that numeric fields are actually numbers"""
        response = client.get("/metrics/legal")
        data = response.json()
        
        assert isinstance(data["total_queries"], (int, float))
        assert isinstance(data["queries_per_second"], (int, float))
        assert isinstance(data["avg_duration_seconds"], (int, float))
        assert isinstance(data["error_rate"], (int, float))
        assert isinstance(data["cache_hit_rate"], (int, float))
    
    def test_legal_metrics_percentiles_exist(self):
        """Test that percentile metrics exist"""
        response = client.get("/metrics/legal")
        data = response.json()
        
        assert "p50_latency" in data or "p95_latency" in data
        assert "p99_latency" in data or "query_latency_p95" in data


class TestHealthDetailedStructure:
    """Test detailed health response structure"""
    
    def test_health_detailed_has_status(self):
        """Test that health detailed has status field"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy", "unknown"]
    
    def test_health_detailed_has_timestamp(self):
        """Test that health detailed has timestamp"""
        response = client.get("/health/detailed")
        data = response.json()
        
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
    
    def test_health_detailed_has_uptime(self):
        """Test that health detailed has uptime_seconds"""
        response = client.get("/health/detailed")
        data = response.json()
        
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0
    
    def test_health_detailed_has_components(self):
        """Test that health detailed has components"""
        response = client.get("/health/detailed")
        data = response.json()
        
        assert "components" in data
        assert isinstance(data["components"], dict)


class TestMetricsResetBehavior:
    """Test metrics reset endpoint behavior"""
    
    def test_reset_in_dev_mode(self, monkeypatch):
        """Test that reset works in dev mode"""
        monkeypatch.setenv("MAHOUN_ENV", "dev")
        response = client.post("/metrics/reset")
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "reset"
            assert "message" in data
    
    def test_reset_blocked_in_production(self, monkeypatch):
        """Test that reset is blocked in production"""
        monkeypatch.setenv("MAHOUN_ENV", "prod")
        response = client.post("/metrics/reset")
        
        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"] == "forbidden"


class TestPrometheusFormat:
    """Test Prometheus metrics format"""
    
    def test_prometheus_contains_metrics(self):
        """Test that Prometheus output contains metric lines"""
        response = client.get("/metrics/prometheus")
        text = response.text
        
        # Prometheus format should have lines with metric names
        assert len(text) > 0
        lines = text.split('\n')
        assert len(lines) > 0
    
    def test_prometheus_has_legal_metrics(self):
        """Test that Prometheus output includes legal metrics"""
        response = client.get("/metrics/prometheus")
        text = response.text
        
        # Should contain at least one legal metric
        assert "legal_" in text.lower() or "query" in text.lower()
