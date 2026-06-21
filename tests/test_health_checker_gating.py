import pytest
import asyncio
from unittest.mock import MagicMock, patch
from mahoun.infrastructure.health_checker import HealthChecker, HealthStatus, ComponentHealth
from datetime import datetime

@pytest.mark.asyncio
async def test_healthchecker_fails_when_critical_services_down():
    """
    Test that HealthChecker reports FAILED when critical core services 
    (Vector Store or Reasoning) are UNHEALTHY.
    """
    checker = HealthChecker()
    
    # Mock all checks to return HEALTHY by default
    healthy_res = ComponentHealth(
        component="test",
        status=HealthStatus.HEALTHY,
        message="OK",
        details={},
        checked_at=datetime.now().isoformat()
    )
    
    with patch.object(HealthChecker, "check_ollama", return_value=healthy_res), \
         patch.object(HealthChecker, "check_graph", return_value=healthy_res), \
         patch.object(HealthChecker, "check_agents", return_value={}), \
         patch.object(HealthChecker, "check_refactored_modules", return_value={}), \
         patch.object(HealthChecker, "check_databases", return_value=healthy_res):
            
        # Scenario 1: Vector Store is UNHEALTHY
        unhealthy_vector = ComponentHealth(
            component="vector_store",
            status=HealthStatus.UNHEALTHY,
            message="Connection failed",
            details={},
            checked_at=datetime.now().isoformat()
        )
        
        with patch.object(HealthChecker, "check_vector_store", return_value=unhealthy_vector), \
             patch.object(HealthChecker, "check_reasoning", return_value=healthy_res):
            
            result = await checker.check_all()
            assert result["status"] == "FAILED"
            assert result["core"]["status"] == "FAILED"
            
        # Scenario 2: Reasoning is UNHEALTHY
        unhealthy_reasoning = ComponentHealth(
            component="reasoning",
            status=HealthStatus.UNHEALTHY,
            message="LLM timeout",
            details={},
            checked_at=datetime.now().isoformat()
        )
        
        with patch.object(HealthChecker, "check_vector_store", return_value=healthy_res), \
             patch.object(HealthChecker, "check_reasoning", return_value=unhealthy_reasoning):
            
            result = await checker.check_all()
            assert result["status"] == "FAILED"
            assert result["core"]["status"] == "FAILED"

        # Scenario 3: Both are HEALTHY -> Overall should be HEALTHY
        with patch.object(HealthChecker, "check_vector_store", return_value=healthy_res), \
             patch.object(HealthChecker, "check_reasoning", return_value=healthy_res):
            
            result = await checker.check_all()
            assert result["status"] == "HEALTHY"
            assert result["core"]["status"] == "HEALTHY"
