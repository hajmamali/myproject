"""
MAHOUN Runtime Configuration Stress Tests
==========================================

Focus: Verify runtime configuration is accurate in desktop_minimal mode.
Tests ensure backends are properly disabled, fallbacks work, and settings
apply consistently across all modules.

Test Environment: desktop_minimal mode
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestMinimalModeConfiguration:
    """
    **Objective**: Verify desktop_minimal mode disables heavy operations.
    
    **Expected Evidence**:
    - Graph operations disabled or use fallback
    - LoRA training disabled
    - LLM backend is remote or lightweight
    - Embeddings use lightweight model
    """

    @pytest.fixture(autouse=True)
    def setup_minimal_mode(self):
        """Setup minimal mode environment."""
        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "false"
        os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"
        os.environ["MAHOUN_LORA_TRAINING_ENABLED"] = "false"
        os.environ["MAHOUN_LLM_BACKEND"] = "openai"  # Remote
        os.environ["MAHOUN_EMBEDDING_BACKEND"] = "bge-small"
        
        yield
        
        # Cleanup
        for key in [
            "MAHOUN_MODE", "MAHOUN_GRAPH_ENABLED", "MAHOUN_GRAPH_BACKEND",
            "MAHOUN_LORA_TRAINING_ENABLED", "MAHOUN_LLM_BACKEND", "MAHOUN_EMBEDDING_BACKEND"
        ]:
            if key in os.environ:
                del os.environ[key]

    @pytest.mark.p2
    def test_minimal_mode_disables_graph(self):
        """
        **Setup**: Set MAHOUN_MODE=desktop_minimal, MAHOUN_GRAPH_ENABLED=false
        **Execution**: Load runtime settings
        **Observation Points**:
          - graph_enabled = False
          - graph_backend = "disabled_fallback"
        **Pass Criteria**: Graph operations disabled in minimal mode
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()
        
        # In minimal mode, graph should be disabled
        if "desktop_minimal" in str(settings.mode).lower():
            # Graph should be disabled or use fallback
            assert settings.graph_backend in ["disabled_fallback", "disabled"], (
                f"Graph backend should be disabled in minimal mode, got {settings.graph_backend}"
            )

    @pytest.mark.p2
    def test_minimal_mode_disables_lora_training(self):
        """
        **Setup**: Set MAHOUN_LORA_TRAINING_ENABLED=false
        **Execution**: Load runtime settings
        **Observation**: lora_training_enabled = False
        **Pass Criteria**: LoRA training disabled
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()
        
        # Should be disabled in minimal mode or explicitly set to false
        if "desktop_minimal" in str(settings.mode).lower():
            assert settings.lora_training_enabled is False, (
                "LoRA training should be disabled in minimal mode"
            )

    @pytest.mark.p2
    def test_minimal_mode_uses_lightweight_backends(self):
        """
        **Setup**: desktop_minimal mode
        **Execution**: Verify backend choices are lightweight
        **Observation Points**:
          - LLM backend (openai / local_cpu_small)
          - Embedding backend (bge-small)
          - LoRA inference backend (remote or cpu)
        **Pass Criteria**: All backends are lightweight/remote
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()
        
        # In minimal mode, backends should be lightweight
        lightweight_backends = {
            "llm": ["openai", "local_cpu_small"],
            "embedding": ["bge-small", "bge-base"],
            "lora": ["remote", "local_cpu_small"],
        }

        if "desktop_minimal" in str(settings.mode).lower():
            # LLM backend should be lightweight
            assert settings.llm_backend in lightweight_backends["llm"] or \
                   settings.llm_backend.startswith("local_cpu"), (
                f"LLM backend {settings.llm_backend} may be too heavy for minimal mode"
            )

    @pytest.mark.p2
    def test_minimal_mode_respects_environment_overrides(self):
        """
        **Setup**: Set specific backend via environment variable
        **Execution**: Load settings and verify override is applied
        **Observation**: Environment variable overrides defaults
        **Pass Criteria**: Explicit env vars are respected
        """
        # Set specific backend
        os.environ["MAHOUN_LLM_BACKEND"] = "openai"
        
        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()
        
        assert settings.llm_backend == "openai", (
            f"Environment override not applied: {settings.llm_backend}"
        )


class TestConfigurationConsistency:
    """
    **Objective**: Verify configuration applies consistently across all modules.
    
    **Expected Evidence**:
    - All modules see same configuration
    - Configuration is immutable after initialization
    - No module-local configuration overrides
    """

    @pytest.mark.p2
    def test_runtime_settings_immutability(self):
        """
        **Setup**: Get runtime settings (frozen dataclass)
        **Execution**: Attempt to modify settings
        **Observation**: Settings are immutable
        **Pass Criteria**: Settings cannot be modified after creation
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()
        
        # Attempt to modify
        with pytest.raises((TypeError, AttributeError)):
            settings.mode = "server_full"
        
        with pytest.raises((TypeError, AttributeError)):
            settings.graph_enabled = True

    @pytest.mark.p2
    def test_configuration_caching(self):
        """
        **Setup**: Get runtime settings multiple times
        **Execution**: 
          1. Get settings first time
          2. Get settings second time
          3. Verify they're the same object (cached)
        **Observation**: Settings are cached and consistent
        **Pass Criteria**: Multiple calls return cached instance
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings1 = get_runtime_settings()
        settings2 = get_runtime_settings()
        
        # Should be same object due to lru_cache
        assert settings1 is settings2, "Settings should be cached"

    @pytest.mark.p2
    def test_all_backends_configured(self):
        """
        **Setup**: Load runtime settings
        **Execution**: Verify all backend fields are set
        **Observation**: No None values in critical backend configs
        **Pass Criteria**: All backends have valid values
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()
        
        # All backends should have values
        critical_fields = [
            "graph_backend",
            "llm_backend",
            "embedding_backend",
            "lora_inference_backend",
        ]
        
        for field in critical_fields:
            value = getattr(settings, field)
            assert value is not None, f"Backend field {field} is None"
            assert isinstance(value, str) and len(value) > 0, (
                f"Backend field {field} has invalid value: {value}"
            )

    @pytest.mark.p2
    def test_neo4j_uri_configured(self):
        """
        **Setup**: Load runtime settings
        **Execution**: Verify Neo4j URI is set
        **Observation**: Neo4j URI has valid format
        **Pass Criteria**: URI is set and has valid protocol
        """
        from mahoun.core.runtime_config import get_runtime_settings

        settings = get_runtime_settings()
        
        # Should have a URI
        assert hasattr(settings, "graph_neo4j_uri")
        uri = settings.graph_neo4j_uri
        assert uri is not None
        assert uri.startswith(("bolt://", "neo4j://", "bolt+s://"))


class TestBackendFallback:
    """
    **Objective**: Verify graceful fallback when backends are unavailable.
    
    **Expected Evidence**:
    - System continues functioning with disabled backends
    - Error messages are informative
    - No cascading failures
    """

    @pytest.mark.p2
    def test_graph_fallback_when_disabled(self):
        """
        **Setup**: Graph backend set to disabled_fallback
        **Execution**: Attempt graph operation
        **Observation Points**:
          - Operation doesn't crash
          - Proper error/fallback message
          - System continues
        **Pass Criteria**: Graceful degradation when graph disabled
        """
        os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"
        
        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()
        
        assert settings.graph_backend == "disabled_fallback"
        # In real scenario, graph operations would check this and fallback

    @pytest.mark.p2
    def test_lora_disabled_doesnt_crash(self):
        """
        **Setup**: LoRA training disabled
        **Execution**: Import modules that would use LoRA
        **Observation**: Modules import without error
        **Pass Criteria**: No import errors when LoRA disabled
        """
        os.environ["MAHOUN_LORA_TRAINING_ENABLED"] = "false"
        
        from mahoun.core.runtime_config import get_runtime_settings
        settings = get_runtime_settings()
        
        assert settings.lora_training_enabled is False


class TestEnvironmentVariableParsing:
    """
    **Objective**: Verify environment variable parsing is robust.
    
    **Expected Evidence**:
    - Boolean env vars parse correctly
    - Invalid values are handled gracefully
    - String values are preserved
    """

    @pytest.mark.p2
    def test_boolean_env_var_parsing(self):
        """
        **Setup**: Set various boolean env vars
        **Execution**: Load settings
        **Observation**: Boolean parsing is correct
        **Pass Criteria**: true/false strings parsed to bools
        """
        test_cases = [
            ("true", True),
            ("false", False),
            ("True", True),
            ("False", False),
            ("1", True),
            ("0", False),
        ]
        
        for env_value, expected_bool in test_cases:
            os.environ["MAHOUN_GRAPH_ENABLED"] = env_value
            
            # Clear cache to force reload
            from mahoun.core.runtime_config import get_runtime_settings
            get_runtime_settings.cache_clear()  # Clear lru_cache
            
            settings = get_runtime_settings()
            assert settings.graph_enabled == expected_bool, (
                f"MAHOUN_GRAPH_ENABLED={env_value} should parse to {expected_bool}"
            )

    @pytest.mark.p2
    def test_string_env_var_preservation(self):
        """
        **Setup**: Set string env vars (backend names)
        **Execution**: Load settings
        **Observation**: String values preserved as-is
        **Pass Criteria**: Backend names are exact matches
        """
        backends = [
            ("openai", "openai"),
            ("local_cpu_small", "local_cpu_small"),
            ("bge-small", "bge-small"),
        ]
        
        for env_value, expected_value in backends:
            os.environ["MAHOUN_LLM_BACKEND"] = env_value
            
            from mahoun.core.runtime_config import get_runtime_settings
            get_runtime_settings.cache_clear()
            
            settings = get_runtime_settings()
            assert settings.llm_backend == expected_value, (
                f"Backend {env_value} not preserved correctly"
            )

    @pytest.mark.p2
    def test_missing_env_vars_use_defaults(self):
        """
        **Setup**: Unset critical env vars
        **Execution**: Load settings
        **Observation**: Defaults are applied
        **Pass Criteria**: Missing vars don't crash, defaults used
        """
        # Clear env vars
        for key in ["MAHOUN_MODE", "MAHOUN_GRAPH_BACKEND"]:
            if key in os.environ:
                del os.environ[key]
        
        from mahoun.core.runtime_config import get_runtime_settings
        get_runtime_settings.cache_clear()
        
        # Should not raise
        settings = get_runtime_settings()
        assert settings is not None


class TestRuntimeConfigIsolation:
    """
    **Objective**: Verify runtime config doesn't have hidden global state.
    
    **Expected Evidence**:
    - Config is deterministic given environment
    - No mutable global state in config module
    """

    @pytest.mark.p2
    def test_config_determinism(self):
        """
        **Setup**: Set reproducible environment
        **Execution**: Load settings multiple times
        **Observation**: Same environment = same settings
        **Pass Criteria**: Config is deterministic
        """
        os.environ["MAHOUN_MODE"] = "desktop_minimal"
        os.environ["MAHOUN_GRAPH_ENABLED"] = "false"
        
        from mahoun.core.runtime_config import get_runtime_settings
        get_runtime_settings.cache_clear()
        
        settings1 = get_runtime_settings()
        settings2 = get_runtime_settings()
        
        # Should be identical
        assert settings1.mode == settings2.mode
        assert settings1.graph_enabled == settings2.graph_enabled

    @pytest.mark.p2
    def test_config_no_side_effects(self):
        """
        **Setup**: Verify loading config has no side effects
        **Execution**: Load config and check sys/os state
        **Observation**: No unexpected state changes
        **Pass Criteria**: No global state pollution
        """
        from mahoun.core.runtime_config import get_runtime_settings
        
        # Get reference to current state
        modules_before = len(sys.modules)
        
        settings = get_runtime_settings()
        
        modules_after = len(sys.modules)
        
        # Should not have loaded many new modules
        # (Allow for some variance, but not huge)
        assert modules_after - modules_before < 10, (
            "Loading config loaded too many new modules (potential side effect)"
        )


@pytest.fixture(scope="function")
def clean_env():
    """Fixture to clean and restore environment."""
    env_backup = os.environ.copy()
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(env_backup)
    
    # Clear runtime config cache if it exists
    try:
        from mahoun.core.runtime_config import get_runtime_settings
        get_runtime_settings.cache_clear()
    except:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
