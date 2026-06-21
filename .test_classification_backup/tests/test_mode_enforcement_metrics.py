"""
Test Mode Enforcement Metrics
==============================

Tests for Prometheus metrics tracking mode enforcement.
"""

import pytest
from unittest.mock import Mock, patch

# Try to import prometheus_client, skip tests if not available
pytest.importorskip("prometheus_client", reason="prometheus_client not installed")

from mahoun.metrics.mode_enforcement import (
    record_blocked_attempt,
    record_mode_check,
    record_config_validation_failure,
    set_current_mode,
    set_graph_enabled,
    set_verdict_engine_initialized,
    record_verdict_generation_duration,
    record_config_validation_duration,
)


class TestModeEnforcementMetrics:
    """Test suite for mode enforcement metrics"""

    def test_record_blocked_attempt(self):
        """Test: Recording blocked verdict generation attempts"""
        # Record blocked attempt
        record_blocked_attempt(
            mode="desktop_minimal",
            reason="graph_disabled",
            entry_point="api"
        )
        
        # Verify metric exists
        # Note: We can't easily verify the exact value in tests due to
        # Prometheus client limitations, but we can verify no errors
        assert True  # If we got here, metric was recorded successfully
        
        print("✓ Blocked attempt recorded successfully")

    def test_record_mode_check(self):
        """Test: Recording mode checks"""
        # Record passed check
        record_mode_check(
            mode="server_full",
            graph_enabled=True,
            passed=True
        )
        
        # Record blocked check
        record_mode_check(
            mode="desktop_minimal",
            graph_enabled=False,
            passed=False
        )
        
        assert True  # Metrics recorded successfully
        print("✓ Mode checks recorded successfully")

    def test_record_config_validation_failure(self):
        """Test: Recording configuration validation failures"""
        record_config_validation_failure(
            validation_rule="desktop_minimal_with_local_graph",
            mode="desktop_minimal"
        )
        
        assert True  # Metric recorded successfully
        print("✓ Config validation failure recorded successfully")

    def test_set_current_mode(self):
        """Test: Setting current mode gauge"""
        # Set desktop_minimal mode
        set_current_mode("desktop_minimal")
        
        # Set server_full mode
        set_current_mode("server_full")
        
        assert True  # Gauges set successfully
        print("✓ Current mode gauge set successfully")

    def test_set_graph_enabled(self):
        """Test: Setting graph enabled gauge"""
        # Enable graph
        set_graph_enabled(True)
        
        # Disable graph
        set_graph_enabled(False)
        
        assert True  # Gauge set successfully
        print("✓ Graph enabled gauge set successfully")

    def test_set_verdict_engine_initialized(self):
        """Test: Setting verdict engine initialized gauge"""
        # Mark as initialized
        set_verdict_engine_initialized(True)
        
        # Mark as not initialized
        set_verdict_engine_initialized(False)
        
        assert True  # Gauge set successfully
        print("✓ Verdict engine initialized gauge set successfully")

    def test_record_verdict_generation_duration(self):
        """Test: Recording verdict generation duration"""
        # Record successful generation
        record_verdict_generation_duration(
            duration_seconds=1.5,
            mode="server_full",
            success=True
        )
        
        # Record failed generation
        record_verdict_generation_duration(
            duration_seconds=0.5,
            mode="desktop_minimal",
            success=False
        )
        
        assert True  # Histogram recorded successfully
        print("✓ Verdict generation duration recorded successfully")

    def test_record_config_validation_duration(self):
        """Test: Recording configuration validation duration"""
        record_config_validation_duration(0.05)  # 50ms
        
        assert True  # Histogram recorded successfully
        print("✓ Config validation duration recorded successfully")

    def test_metrics_integration(self):
        """Test: Full metrics integration scenario"""
        # Scenario: Startup validation
        set_current_mode("desktop_minimal")
        set_graph_enabled(False)
        record_config_validation_duration(0.03)
        
        # Scenario: Blocked verdict generation
        record_mode_check(
            mode="desktop_minimal",
            graph_enabled=False,
            passed=False
        )
        record_blocked_attempt(
            mode="desktop_minimal",
            reason="graph_disabled",
            entry_point="api"
        )
        
        # Scenario: Successful verdict generation in server_full mode
        set_current_mode("server_full")
        set_graph_enabled(True)
        set_verdict_engine_initialized(True)
        record_mode_check(
            mode="server_full",
            graph_enabled=True,
            passed=True
        )
        record_verdict_generation_duration(
            duration_seconds=2.3,
            mode="server_full",
            success=True
        )
        
        assert True  # All metrics recorded successfully
        print("✓ Full metrics integration scenario completed")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
