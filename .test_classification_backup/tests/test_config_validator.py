"""
Test Configuration Validator
=============================

Tests for runtime configuration validation to ensure fail-fast behavior
on misconfiguration that could compromise zero-hallucination guarantees.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from mahoun.core.config_validator import (
    validate_runtime_config,
    ConfigurationError,
    ValidationError,
)
from mahoun.core.runtime_config import MahounRuntimeSettings


class TestConfigurationValidator:
    """Test suite for configuration validator"""

    def test_valid_desktop_minimal_config(self):
        """Test: Valid desktop_minimal configuration passes validation"""
        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=False,
            graph_backend="disabled_fallback",
            lora_training_enabled=False,
            lora_inference_backend="remote",
            llm_backend="openai",
            embedding_backend="bge-small",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            # Should not raise
            validate_runtime_config()

    def test_valid_server_full_config(self):
        """Test: Valid server_full configuration passes validation"""
        settings = MahounRuntimeSettings(
            mode="server_full",
            graph_enabled=True,
            graph_backend="local_full",
            lora_training_enabled=True,
            lora_inference_backend="local_gpu",
            llm_backend="local_gpu",
            embedding_backend="bge-default",
            embedding_model_path="",
            llm_model_path="",
            graph_neo4j_password="test_password",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            # Should not raise
            validate_runtime_config()

    def test_invalid_desktop_minimal_with_local_graph(self):
        """Test: desktop_minimal + local graph backend = INVALID"""
        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=True,
            graph_backend="local_full",  # ← INVALID for desktop_minimal
            lora_training_enabled=False,
            lora_inference_backend="remote",
            llm_backend="openai",
            embedding_backend="bge-small",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_runtime_config()

            error_msg = str(exc_info.value)
            assert "MODE_GRAPH_CONSISTENCY" in error_msg
            assert "desktop_minimal mode cannot use local graph backend" in error_msg
            assert "local_full" in error_msg

    def test_valid_desktop_minimal_with_remote_graph(self):
        """Test: desktop_minimal + remote graph backend = VALID"""
        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=True,
            graph_backend="remote",  # ← VALID for desktop_minimal
            lora_training_enabled=False,
            lora_inference_backend="remote",
            llm_backend="openai",
            embedding_backend="bge-small",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            # Should not raise
            validate_runtime_config()

    def test_missing_neo4j_password_for_local_graph(self):
        """Test: local graph backend requires Neo4j password"""
        settings = MahounRuntimeSettings(
            mode="server_full",
            graph_enabled=True,
            graph_backend="local_full",
            lora_training_enabled=True,
            lora_inference_backend="local_gpu",
            llm_backend="local_gpu",
            embedding_backend="bge-default",
            embedding_model_path="",
            llm_model_path="",
            graph_neo4j_password="",  # ← MISSING
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_runtime_config()

            error_msg = str(exc_info.value)
            assert "NEO4J_PASSWORD_MISSING" in error_msg
            assert "Neo4j password required" in error_msg

    def test_invalid_graph_backend(self):
        """Test: Invalid graph backend raises error"""
        settings = MahounRuntimeSettings(
            mode="server_full",
            graph_enabled=True,
            graph_backend="invalid_backend",  # ← INVALID
            lora_training_enabled=True,
            lora_inference_backend="local_gpu",
            llm_backend="local_gpu",
            embedding_backend="bge-default",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_runtime_config()

            error_msg = str(exc_info.value)
            assert "GRAPH_BACKEND_INVALID" in error_msg
            assert "invalid_backend" in error_msg

    def test_graph_disabled_warning(self, caplog):
        """Test: Graph disabled generates warning about verdict generation"""
        import logging
        caplog.set_level(logging.WARNING)

        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=False,
            graph_backend="disabled_fallback",
            lora_training_enabled=False,
            lora_inference_backend="remote",
            llm_backend="openai",
            embedding_backend="bge-small",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            validate_runtime_config()

            # Check warning was logged
            assert any(
                "verdict generation will be UNAVAILABLE" in record.message
                for record in caplog.records
            )

    def test_lora_training_in_desktop_minimal_warning(self, caplog):
        """Test: LoRA training in desktop_minimal generates warning"""
        import logging
        caplog.set_level(logging.WARNING)

        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=False,
            graph_backend="disabled_fallback",
            lora_training_enabled=True,  # ← WARNING
            lora_inference_backend="remote",
            llm_backend="openai",
            embedding_backend="bge-small",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            validate_runtime_config()

            # Check warning was logged
            assert any(
                "LoRA training enabled in desktop_minimal mode" in record.message
                for record in caplog.records
            )

    def test_local_gpu_in_desktop_minimal_warning(self, caplog):
        """Test: Local GPU in desktop_minimal generates warning"""
        import logging
        caplog.set_level(logging.WARNING)

        settings = MahounRuntimeSettings(
            mode="desktop_minimal",
            graph_enabled=False,
            graph_backend="disabled_fallback",
            lora_training_enabled=False,
            lora_inference_backend="remote",
            llm_backend="local_gpu",  # ← WARNING
            embedding_backend="bge-small",
            embedding_model_path="",
            llm_model_path="",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            validate_runtime_config()

            # Check warning was logged
            assert any(
                "Local GPU LLM backend enabled in desktop_minimal mode" in record.message
                for record in caplog.records
            )

    def test_validation_success_logged(self, caplog):
        """Test: Successful validation is logged"""
        import logging
        caplog.set_level(logging.INFO)

        settings = MahounRuntimeSettings(
            mode="server_full",
            graph_enabled=True,
            graph_backend="local_full",
            lora_training_enabled=True,
            lora_inference_backend="local_gpu",
            llm_backend="local_gpu",
            embedding_backend="bge-default",
            embedding_model_path="",
            llm_model_path="",
            graph_neo4j_password="test_password",
        )

        with patch("mahoun.core.config_validator.get_runtime_settings", return_value=settings):
            validate_runtime_config()

            # Check success was logged
            assert any(
                "Runtime configuration validated successfully" in record.message
                for record in caplog.records
            )


class TestConfigFileValidation:
    """Test suite for YAML config file validation"""

    def test_valid_yaml_config(self, tmp_path):
        """Test: Valid YAML config file passes validation"""
        from mahoun.core.config_validator import validate_config_file

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
mode: server_full
graph:
  enabled: true
  backend: local_full
"""
        )

        # Should not raise
        validate_config_file(str(config_file))

    def test_missing_config_file(self):
        """Test: Missing config file raises error"""
        from mahoun.core.config_validator import validate_config_file

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_file("/nonexistent/config.yaml")

        assert "Configuration file not found" in str(exc_info.value)

    def test_invalid_yaml_syntax(self, tmp_path):
        """Test: Invalid YAML syntax raises error"""
        from mahoun.core.config_validator import validate_config_file

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
mode: server_full
  invalid: indentation
"""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_file(str(config_file))

        assert "Invalid YAML" in str(exc_info.value)

    def test_missing_mode_field(self, tmp_path):
        """Test: Missing 'mode' field raises error"""
        from mahoun.core.config_validator import validate_config_file

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
graph:
  enabled: true
"""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_file(str(config_file))

        assert "missing required field: 'mode'" in str(exc_info.value)

    def test_invalid_mode_value(self, tmp_path):
        """Test: Invalid mode value raises error"""
        from mahoun.core.config_validator import validate_config_file

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
mode: invalid_mode
"""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_file(str(config_file))

        assert "Invalid mode 'invalid_mode'" in str(exc_info.value)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
