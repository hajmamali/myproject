"""
Easy Level Tests: Basic Smoke Tests for API Monitoring Endpoints
=================================================================
Tests basic functionality and happy paths.
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestMonitoringEndpointsBasic:
    """Basic smoke tests for monitoring endpoints"""
    
    @pytest.mark.p2
    def test_prometheus_endpoint_exists(self):
        """Test that /metrics/prometheus endpoint exists and returns 200"""
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
    
    @pytest.mark.p2
    def test_legal_metrics_endpoint_exists(self):
        """Test that /metrics/legal endpoint exists and returns 200"""
        response = client.get("/metrics/legal")
        assert response.status_code == 200
    
    @pytest.mark.p2
    def test_health_detailed_endpoint_exists(self):
        """Test that /health/detailed endpoint exists and returns 200"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
    
    @pytest.mark.p2
    def test_metrics_reset_endpoint_exists(self):
        """Test that /metrics/reset endpoint exists (POST)"""
        response = client.post("/metrics/reset")
        # Should return 200 in dev or 403 in prod
        assert response.status_code in [200, 403]


class TestMonitoringResponseTypes:
    """Test that endpoints return correct data types"""
    
    @pytest.mark.p2
    def test_prometheus_returns_text(self):
        """Test that Prometheus endpoint returns text format"""
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
        assert isinstance(response.text, str)
    
    @pytest.mark.p2
    def test_legal_metrics_returns_json(self):
        """Test that legal metrics endpoint returns JSON"""
        response = client.get("/metrics/legal")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    @pytest.mark.p2
    def test_health_detailed_returns_json(self):
        """Test that detailed health endpoint returns JSON"""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestImportAndSyntax:
    """Test that the file can be imported without errors"""
    
    @pytest.mark.p2
    def test_api_main_imports_successfully(self):
        """Test that api.main can be imported"""
        try:
            import api.main
            assert True
        except SyntaxError as e:
            pytest.fail(f"Syntax error in api.main: {e}")
    
    @pytest.mark.p2
    def test_no_import_time_error(self):
        """Test that time module is imported correctly"""
        import api.main
        assert hasattr(api.main, 'time')
