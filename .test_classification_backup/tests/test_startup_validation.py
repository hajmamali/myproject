"""
Test Startup Validation
========================

Integration tests for startup configuration validation to ensure
the application fails fast on invalid configuration.
"""

import pytest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestStartupValidation:
    """Test suite for startup validation"""

    def test_valid_config_starts_successfully(self):
        """Test: Valid configuration allows application to start"""
        # Set valid environment
        os.environ["MAHOUN_MODE"] = "server_full"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "true"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "local_full"
        os.environ["NEO4J_PASSWORD"] = "test_password"
        
        try:
            # Import after setting environment
            from api.main import app
            
            # Create test client (triggers startup)
            client = TestClient(app)
            
            # Verify app started
            response = client.get("/health")
            assert response.status_code == 200
            
        finally:
            # Cleanup
            os.environ.pop("MAHOUN_MODE", None)
            os.environ.pop("MAHOUN_GRAPH_ENABLED", None)
            os.environ.pop("MAHOUN_GRAPH_BACKEND", None)
            os.environ.pop("NEO4J_PASSWORD", None)

    def test_invalid_config_prevents_startup(self):
        """Test: Invalid configuration prevents application startup"""
        # Set INVALID environment (desktop_minimal + local graph)
        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "true"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "local_full"  # ← INVALID
        
        try:
            # Import after setting environment
            # Clear module cache to force re-import
            import sys
            if "api.main" in sys.modules:
                del sys.modules["api.main"]
            if "mahoun.core.runtime_config" in sys.modules:
                del sys.modules["mahoun.core.runtime_config"]
            
            from mahoun.core.config_validator import ConfigurationError
            
            # Attempt to create test client (should fail at startup)
            with pytest.raises(ConfigurationError) as exc_info:
                from api.main import app
                client = TestClient(app)
            
            # Verify error message
            error_msg = str(exc_info.value)
            assert "MODE_GRAPH_CONSISTENCY" in error_msg
            assert "desktop_minimal mode cannot use local graph backend" in error_msg
            
        finally:
            # Cleanup
            os.environ.pop("MAHOUN_MODE", None)
            os.environ.pop("MAHOUN_GRAPH_ENABLED", None)
            os.environ.pop("MAHOUN_GRAPH_BACKEND", None)

    def test_missing_neo4j_password_prevents_startup(self):
        """Test: Missing Neo4j password prevents startup with local graph"""
        # Set environment with missing password
        os.environ["MAHOUN_MODE"] = "server_full"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "true"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "local_full"
        os.environ.pop("NEO4J_PASSWORD", None)  # ← MISSING
        
        try:
            # Clear module cache
            import sys
            if "api.main" in sys.modules:
                del sys.modules["api.main"]
            if "mahoun.core.runtime_config" in sys.modules:
                del sys.modules["mahoun.core.runtime_config"]
            
            from mahoun.core.config_validator import ConfigurationError
            
            # Attempt to create test client (should fail at startup)
            with pytest.raises(ConfigurationError) as exc_info:
                from api.main import app
                client = TestClient(app)
            
            # Verify error message
            error_msg = str(exc_info.value)
            assert "NEO4J_PASSWORD_MISSING" in error_msg
            assert "Neo4j password required" in error_msg
            
        finally:
            # Cleanup
            os.environ.pop("MAHOUN_MODE", None)
            os.environ.pop("MAHOUN_GRAPH_ENABLED", None)
            os.environ.pop("MAHOUN_GRAPH_BACKEND", None)

    def test_desktop_minimal_with_graph_disabled_starts_with_warning(self, caplog):
        """Test: desktop_minimal with graph disabled starts but logs warning"""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Set valid desktop_minimal config
        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "false"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"
        
        try:
            # Clear module cache
            import sys
            if "api.main" in sys.modules:
                del sys.modules["api.main"]
            if "mahoun.core.runtime_config" in sys.modules:
                del sys.modules["mahoun.core.runtime_config"]
            
            # Import and create client
            from api.main import app
            client = TestClient(app)
            
            # Verify app started
            response = client.get("/health")
            assert response.status_code == 200
            
            # Verify warning was logged
            assert any(
                "verdict generation will be UNAVAILABLE" in record.message
                for record in caplog.records
            )
            
        finally:
            # Cleanup
            os.environ.pop("MAHOUN_MODE", None)
            os.environ.pop("MAHOUN_GRAPH_ENABLED", None)
            os.environ.pop("MAHOUN_GRAPH_BACKEND", None)


class TestRuntimeModeEnforcement:
    """Test runtime mode enforcement after startup"""

    def test_verdict_generation_blocked_in_desktop_minimal(self):
        """Test: Verdict generation returns 503 in desktop_minimal mode"""
        # Set desktop_minimal mode
        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "false"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"
        
        try:
            # Clear module cache
            import sys
            if "api.main" in sys.modules:
                del sys.modules["api.main"]
            if "api.routers.reasoning" in sys.modules:
                del sys.modules["api.routers.reasoning"]
            if "mahoun.core.runtime_config" in sys.modules:
                del sys.modules["mahoun.core.runtime_config"]
            
            from api.main import app
            client = TestClient(app)
            
            # Attempt to generate verdict
            response = client.post(
                "/api/v1/reasoning/generate-verdict",
                json={
                    "question": "Test question",
                    "facts": [{"value": "Test fact"}],
                }
            )
            
            # Verify 503 Service Unavailable
            assert response.status_code == 503
            
            # Verify error message
            data = response.json()
            assert "service_unavailable" in str(data)
            assert "DESKTOP_MINIMAL" in str(data)
            
        finally:
            # Cleanup
            os.environ.pop("MAHOUN_MODE", None)
            os.environ.pop("MAHOUN_GRAPH_ENABLED", None)
            os.environ.pop("MAHOUN_GRAPH_BACKEND", None)

    def test_verdict_generation_works_in_server_full(self):
        """Test: Verdict generation works in server_full mode (with mocked engine)"""
        # Set server_full mode
        os.environ["MAHOUN_MODE"] = "server_full"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "true"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "local_full"
        os.environ["NEO4J_PASSWORD"] = "test_password"
        
        try:
            # Clear module cache
            import sys
            if "api.main" in sys.modules:
                del sys.modules["api.main"]
            if "api.routers.reasoning" in sys.modules:
                del sys.modules["api.routers.reasoning"]
            if "mahoun.core.runtime_config" in sys.modules:
                del sys.modules["mahoun.core.runtime_config"]
            
            from api.main import app
            from unittest.mock import AsyncMock, MagicMock
            
            # Mock verdict engine to avoid actual graph operations
            with patch("api.routers.reasoning.get_verdict_engine") as mock_get_engine:
                mock_engine = MagicMock()
                mock_verdict = MagicMock()
                mock_verdict.final_verdict = "Test verdict"
                mock_verdict.steps = []
                mock_verdict.unresolved_conflicts = []
                mock_verdict.confidence_score = 0.9
                mock_engine.generate_verdict = AsyncMock(return_value=mock_verdict)
                mock_get_engine.return_value = mock_engine
                
                client = TestClient(app)
                
                # Attempt to generate verdict
                response = client.post(
                    "/api/v1/reasoning/generate-verdict",
                    json={
                        "question": "Test question",
                        "facts": [{"value": "Test fact"}],
                    }
                )
                
                # Verify success (200 OK)
                assert response.status_code == 200
                
                # Verify verdict returned
                data = response.json()
                assert data["success"] is True
                assert "verdict_id" in data
                
        finally:
            # Cleanup
            os.environ.pop("MAHOUN_MODE", None)
            os.environ.pop("MAHOUN_GRAPH_ENABLED", None)
            os.environ.pop("MAHOUN_GRAPH_BACKEND", None)
            os.environ.pop("NEO4J_PASSWORD", None)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
