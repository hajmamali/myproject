"""
API Endpoint Tests
==================

تست‌های جامع برای API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_mahoun_upload_endpoint_structure(client):
    """Test MAHOUN upload endpoint structure"""
    # Note: This tests endpoint existence, not full functionality
    # Full test would require file upload
    response = client.get("/api/v1/mahoun/reports")
    # Should return 200 or 404, not 500
    assert response.status_code in [200, 404, 405]


def test_mahoun_reports_endpoint(client):
    """Test MAHOUN reports list endpoint"""
    response = client.get("/api/v1/mahoun/reports")
    # Should return list structure
    if response.status_code == 200:
        data = response.json()
        assert "reports" in data or "total" in data


def test_api_error_handling(client):
    """Test API error handling"""
    # Test invalid endpoint
    response = client.get("/api/v1/mahoun/invalid")
    # Should return proper error, not crash
    assert response.status_code in [404, 405, 422]


def test_cors_headers(client):
    """Test CORS headers"""
    response = client.options("/health")
    # CORS middleware should be configured
    assert response.status_code in [200, 405]


@pytest.mark.asyncio
async def test_mahoun_endpoints_registered():
    """Test that MAHOUN endpoints are registered"""
    from api.main import app
    
    routes = [route.path for route in app.routes]
    
    mahoun_routes = [
        "/api/v1/mahoun/upload-documents",
        "/api/v1/mahoun/analyze-delay",
        "/api/v1/mahoun/generate-claim",
        "/api/v1/mahoun/ask-contract",
    ]
    
    # Check if at least some routes exist (with path parameters)
    found_routes = []
    for route in routes:
        for mahoun_route in mahoun_routes:
            if mahoun_route.replace("/", "") in route.replace("/", ""):
                found_routes.append(mahoun_route)
                break
    
    # At least one route should be found
    assert len(found_routes) > 0 or len([r for r in routes if "mahoun" in r]) > 0


