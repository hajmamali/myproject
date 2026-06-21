"""
Tests for Health Checker
=========================
Integration tests for the comprehensive health check system.
These tests connect to external services (Ollama, Vector Store, Graph DB, etc.)
"""

import pytest
import asyncio
from mahoun.infrastructure.health_checker import HealthChecker, HealthStatus, ComponentHealth

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_checker_ollama():
    """Test Ollama health check"""
    checker = HealthChecker()
    status = await checker.check_ollama()
    
    assert isinstance(status, ComponentHealth)
    assert status.component == "ollama"
    assert status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
    assert isinstance(status.details, dict)
    assert status.checked_at is not None


@pytest.mark.asyncio
async def test_health_checker_vector_store():
    """Test VectorStore health check"""
    checker = HealthChecker()
    status = await checker.check_vector_store()
    
    assert isinstance(status, ComponentHealth)
    assert status.component == "vector_store"
    assert status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
    assert isinstance(status.details, dict)


@pytest.mark.asyncio
async def test_health_checker_graph():
    """Test Graph system health check"""
    checker = HealthChecker()
    status = await checker.check_graph()
    
    assert isinstance(status, ComponentHealth)
    assert status.component == "graph"
    assert status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
    assert isinstance(status.details, dict)


@pytest.mark.asyncio
async def test_health_checker_reasoning():
    """Test Reasoning service health check"""
    checker = HealthChecker()
    status = await checker.check_reasoning()
    
    assert isinstance(status, ComponentHealth)
    assert status.component == "reasoning"
    assert status.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]


@pytest.mark.asyncio
async def test_health_checker_agents():
    """Test agents health check"""
    checker = HealthChecker()
    agents_health = await checker.check_agents()
    
    assert isinstance(agents_health, dict)
    assert len(agents_health) > 0
    
    # Check that all agents have health status
    for agent_name, health in agents_health.items():
        assert isinstance(health, ComponentHealth)
        assert health.component.startswith("agent.")


@pytest.mark.asyncio
async def test_health_checker_all():
    """Test comprehensive health check"""
    checker = HealthChecker()
    results = await checker.check_all()
    
    assert isinstance(results, dict)
    assert isinstance(results, dict)
    assert "status" in results
    assert "core" in results
    assert "graph" in results
    assert "agents" in results
    assert "self_improve" in results
    
    # Check overall status
    assert results["status"] in ["HEALTHY", "DEGRADED", "FAILED"]
    
    # Check core section
    assert isinstance(results["core"], dict)
    assert "status" in results["core"]
    assert "import_safe" in results["core"]
    
    # Check graph section
    assert isinstance(results["graph"], dict)
    assert "status" in results["graph"]
    
    # Check agents section
    assert isinstance(results["agents"], dict)
    assert "status" in results["agents"]
    assert "count" in results["agents"]


def test_component_health_to_dict():
    """Test ComponentHealth to_dict method"""
    health = ComponentHealth(
        component="test",
        status=HealthStatus.HEALTHY,
        message="Test message",
        details={"key": "value"},
        checked_at="2025-12-05T00:00:00"
    )
    
    result = health.to_dict()
    
    assert isinstance(result, dict)
    assert result["component"] == "test"
    assert result["status"] == "healthy"
    assert result["message"] == "Test message"
    assert result["details"] == {"key": "value"}
    assert result["checked_at"] == "2025-12-05T00:00:00"
