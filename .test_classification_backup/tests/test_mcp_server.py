"""
MCP Server Tests
================

Comprehensive test suite for the MCP JSON-RPC server.
"""

import pytest
from fastapi.testclient import TestClient
import os

# Set test API key before importing app
os.environ["MCP_API_KEY"] = "test-api-key-12345"

from mahoun.mcp.server import app

client = TestClient(app)

# Valid headers
VALID_HEADERS = {"X-API-Key": "test-api-key-12345"}
INVALID_HEADERS = {"X-API-Key": "wrong-key"}


class TestAuthentication:
    """Test API key authentication."""
    
    def test_missing_api_key(self):
        """Request without API key should fail."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "System.health_check",
            "id": 1
        })
        assert response.status_code == 401
        assert "Missing API key" in response.json().get("detail", "")
    
    def test_invalid_api_key(self):
        """Request with wrong API key should fail."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "System.health_check",
            "id": 1
        }, headers=INVALID_HEADERS)
        assert response.status_code == 403
        assert "Invalid API key" in response.json().get("detail", "")
    
    def test_valid_api_key(self):
        """Request with valid API key should succeed."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "System.health_check",
            "id": 1
        }, headers=VALID_HEADERS)
        # Should not be auth error
        assert response.status_code == 200


class TestJSONRPCProtocol:
    """Test JSON-RPC 2.0 protocol compliance."""
    
    def test_invalid_jsonrpc_version(self):
        """Request with wrong jsonrpc version should fail."""
        response = client.post("/mcp", json={
            "jsonrpc": "1.0",
            "method": "System.health_check",
            "id": 1
        }, headers=VALID_HEADERS)
        data = response.json()
        assert "error" in data or response.status_code == 422
    
    def test_missing_method(self):
        """Request without method should fail."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1
        }, headers=VALID_HEADERS)
        assert response.status_code == 422
    
    def test_invalid_method_format(self):
        """Method without dot separator should fail."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "InvalidMethod",
            "id": 1
        }, headers=VALID_HEADERS)
        data = response.json()
        assert data["error"]["code"] == -32600  # INVALID_REQUEST


class TestErrorHandling:
    """Test comprehensive error handling."""
    
    def test_tool_not_found(self):
        """Non-existent tool should return METHOD_NOT_FOUND."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "NonExistentTool.method",
            "id": 1
        }, headers=VALID_HEADERS)
        data = response.json()
        assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND
        assert "available_tools" in data["error"].get("data", {})
    
    def test_function_not_found(self):
        """Non-existent function should return METHOD_NOT_FOUND."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "System.nonExistentMethod",
            "id": 1
        }, headers=VALID_HEADERS)
        data = response.json()
        assert data["error"]["code"] == -32601
        assert "available_methods" in data["error"].get("data", {})
    
    def test_error_response_structure(self):
        """Error responses should follow JSON-RPC 2.0 spec."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "Invalid.method",
            "id": 123
        }, headers=VALID_HEADERS)
        data = response.json()
        
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["id"] == 123


class TestToolExecution:
    """Test actual tool method execution."""
    
    def test_system_health(self):
        """System.health should return status."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "System.health_check",
            "id": 1
        }, headers=VALID_HEADERS)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert data["id"] == 1
    
    def test_method_with_params(self):
        """Methods with parameters should work."""
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "System.get_version",
            "params": {},
            "id": 2
        }, headers=VALID_HEADERS)
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data


class TestEndpoints:
    """Test HTTP endpoints."""
    
    def test_health_endpoint(self):
        """GET /health should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_list_tools_endpoint(self):
        """GET /mcp/tools should list available tools."""
        response = client.get("/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], dict)


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.skip(reason="Rate limiting test requires slowapi setup")
    def test_rate_limit_exceeded(self):
        """Exceeding rate limit should return 429."""
        # Send 101 requests (limit is 100/minute)
        for i in range(101):
            response = client.post("/mcp", json={
                "jsonrpc": "2.0",
                "method": "System.health_check",
                "id": i
            }, headers=VALID_HEADERS)
            
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
