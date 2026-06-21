import pytest
pytest.importorskip("pydantic_settings")
"""
Configuration Production Validation Tests
==========================================
Property 9: Production Fails Fast on Missing Secrets

*For any* production environment (MAHOUN_ENV=prod), missing required secrets
SHALL cause immediate startup failure with clear error message.

**Validates: Requirements 5.3**
"""

import os
from typing import Dict, Generator
from unittest.mock import patch

import pytest

from mahoun.core.config import (
    MahounSettings,
    clear_settings_cache,
    get_settings,
)
from mahoun.core.exceptions import ConfigurationError


class TestProductionFailFast:
    """
    Tests for Property 9: Production Fails Fast on Missing Secrets.
    
    **Feature: platform-hardening, Property 9: Production Fails Fast**
    **Validates: Requirements 5.3**
    """
    
    @pytest.fixture(autouse=True)
    def clean_env(self) -> Generator[None, None, None]:
        """Clean environment before and after each test."""
        # Store original env
        original_env = os.environ.copy()
        
        # Clear settings cache
        clear_settings_cache()
        
        yield
        
        # Restore original env
        os.environ.clear()
        os.environ.update(original_env)
        
        # Clear cache again
        clear_settings_cache()
    
    def _set_env(self, env_vars: Dict[str, str]) -> None:
        """Set environment variables for testing."""
        # Clear MAHOUN_ prefixed vars first
        keys_to_remove = [k for k in os.environ if k.startswith('MAHOUN_')]
        for key in keys_to_remove:
            del os.environ[key]
        
        # Set new vars
        for key, value in env_vars.items():
            os.environ[key] = value
    
    # =========================================================================
    # Production Debug Mode Tests
    # =========================================================================
    
    def test_production_rejects_debug_true(self) -> None:
        """
        Test that production environment rejects debug=True.
        
        **Property 9: Production Fails Fast**
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'true',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'DEBUG must be False in production' in str(exc_info.value)
    
    def test_staging_rejects_debug_true(self) -> None:
        """
        Test that staging environment also rejects debug=True.
        """
        self._set_env({
            'MAHOUN_ENV': 'staging',
            'MAHOUN_DEBUG': 'true',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'DEBUG must be False in production' in str(exc_info.value)
    
    # =========================================================================
    # Production Guard Mode Tests
    # =========================================================================
    
    def test_production_rejects_guard_mode_off(self) -> None:
        """
        Test that production environment rejects GUARD_MODE=OFF.
        
        **Property 9: Production Fails Fast**
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'OFF',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'GUARD_MODE cannot be OFF in production' in str(exc_info.value)
    
    def test_production_accepts_guard_mode_strict(self) -> None:
        """
        Test that production accepts GUARD_MODE=STRICT.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        settings = MahounSettings()
        assert settings.guard_mode == 'STRICT'
    
    def test_production_accepts_guard_mode_audit(self) -> None:
        """
        Test that production accepts GUARD_MODE=AUDIT.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'AUDIT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        settings = MahounSettings()
        assert settings.guard_mode == 'AUDIT'
    
    # =========================================================================
    # Production Ledger Backend Tests
    # =========================================================================
    
    def test_production_rejects_ledger_noop(self) -> None:
        """
        Test that production environment rejects LEDGER_BACKEND=noop.
        
        **Property 9: Production Fails Fast**
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'noop',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'LEDGER_BACKEND cannot be noop in production' in str(exc_info.value)
    
    def test_production_accepts_ledger_jsonl(self) -> None:
        """
        Test that production accepts LEDGER_BACKEND=jsonl.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        settings = MahounSettings()
        assert settings.ledger_backend == 'jsonl'
    
    def test_production_accepts_ledger_sqlite(self) -> None:
        """
        Test that production accepts LEDGER_BACKEND=sqlite.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'sqlite',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        settings = MahounSettings()
        assert settings.ledger_backend == 'sqlite'
    
    # =========================================================================
    # Production LLM API Key Tests
    # =========================================================================
    
    def test_production_openai_requires_api_key(self) -> None:
        """
        Test that production with OpenAI provider requires API key.
        
        **Property 9: Production Fails Fast**
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'openai',
            # No MAHOUN_OPENAI_API_KEY
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'OPENAI_API_KEY required' in str(exc_info.value)
    
    def test_production_openai_with_api_key_works(self) -> None:
        """
        Test that production with OpenAI provider and API key works.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'openai',
            'MAHOUN_OPENAI_API_KEY': 'sk-test-key-12345',
        })
        
        settings = MahounSettings()
        assert settings.llm_provider == 'openai'
        assert settings.openai_api_key == 'sk-test-key-12345'
    
    def test_production_anthropic_requires_api_key(self) -> None:
        """
        Test that production with Anthropic provider requires API key.
        
        **Property 9: Production Fails Fast**
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'anthropic',
            # No MAHOUN_ANTHROPIC_API_KEY
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'ANTHROPIC_API_KEY required' in str(exc_info.value)
    
    def test_production_azure_requires_endpoint_and_key(self) -> None:
        """
        Test that production with Azure provider requires endpoint and API key.
        
        **Property 9: Production Fails Fast**
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'azure',
            # No MAHOUN_AZURE_OPENAI_ENDPOINT or MAHOUN_AZURE_OPENAI_API_KEY
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'AZURE_OPENAI_ENDPOINT required' in str(exc_info.value)
    
    def test_production_local_llm_no_api_key_required(self) -> None:
        """
        Test that production with local LLM provider doesn't require API key.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'false',
            'MAHOUN_GUARD_MODE': 'STRICT',
            'MAHOUN_LEDGER_BACKEND': 'jsonl',
            'MAHOUN_LLM_PROVIDER': 'local',
        })
        
        settings = MahounSettings()
        assert settings.llm_provider == 'local'
    
    # =========================================================================
    # Development Mode Tests (Should Not Fail)
    # =========================================================================
    
    def test_dev_mode_allows_debug(self) -> None:
        """
        Test that dev mode allows debug=True.
        """
        self._set_env({
            'MAHOUN_ENV': 'dev',
            'MAHOUN_DEBUG': 'true',
        })
        
        settings = MahounSettings()
        assert settings.debug is True
        assert settings.env == 'dev'
    
    def test_dev_mode_allows_guard_off(self) -> None:
        """
        Test that dev mode allows GUARD_MODE=OFF.
        """
        self._set_env({
            'MAHOUN_ENV': 'dev',
            'MAHOUN_GUARD_MODE': 'OFF',
        })
        
        settings = MahounSettings()
        assert settings.guard_mode == 'OFF'
    
    def test_dev_mode_allows_ledger_noop(self) -> None:
        """
        Test that dev mode allows LEDGER_BACKEND=noop.
        """
        self._set_env({
            'MAHOUN_ENV': 'dev',
            'MAHOUN_LEDGER_BACKEND': 'noop',
        })
        
        settings = MahounSettings()
        assert settings.ledger_backend == 'noop'
    
    def test_dev_mode_no_api_keys_required(self) -> None:
        """
        Test that dev mode doesn't require API keys for any provider.
        """
        self._set_env({
            'MAHOUN_ENV': 'dev',
            'MAHOUN_LLM_PROVIDER': 'openai',
            # No API key
        })
        
        settings = MahounSettings()
        assert settings.llm_provider == 'openai'
        assert settings.openai_api_key is None
    
    def test_test_mode_allows_all(self) -> None:
        """
        Test that test mode allows all configurations.
        """
        self._set_env({
            'MAHOUN_ENV': 'test',
            'MAHOUN_DEBUG': 'true',
            'MAHOUN_GUARD_MODE': 'OFF',
            'MAHOUN_LEDGER_BACKEND': 'noop',
        })
        
        settings = MahounSettings()
        assert settings.env == 'test'
        assert settings.debug is True
        assert settings.guard_mode == 'OFF'
        assert settings.ledger_backend == 'noop'
    
    # =========================================================================
    # Error Message Quality Tests
    # =========================================================================
    
    def test_error_messages_are_clear(self) -> None:
        """
        Test that error messages clearly indicate what's wrong.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'true',
        })
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        error_msg = str(exc_info.value)
        
        # Should mention the problem
        assert 'DEBUG' in error_msg
        # Should mention production
        assert 'production' in error_msg.lower()
    
    # =========================================================================
    # get_settings() Integration Tests
    # =========================================================================
    
    def test_get_settings_raises_configuration_error(self) -> None:
        """
        Test that get_settings() raises ConfigurationError on invalid config.
        """
        self._set_env({
            'MAHOUN_ENV': 'prod',
            'MAHOUN_DEBUG': 'true',
        })
        
        clear_settings_cache()
        
        with pytest.raises(ConfigurationError):
            get_settings()
    
    def test_get_settings_caches_valid_config(self) -> None:
        """
        Test that get_settings() caches valid configuration.
        """
        self._set_env({
            'MAHOUN_ENV': 'dev',
        })
        
        clear_settings_cache()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same cached instance
        assert settings1 is settings2


class TestConfigurationValidation:
    """
    Additional configuration validation tests.
    """
    
    @pytest.fixture(autouse=True)
    def clean_env(self) -> Generator[None, None, None]:
        """Clean environment before and after each test."""
        original_env = os.environ.copy()
        clear_settings_cache()
        
        yield
        
        os.environ.clear()
        os.environ.update(original_env)
        clear_settings_cache()
    
    def test_invalid_env_value_rejected(self) -> None:
        """Test that invalid environment values are rejected."""
        os.environ['MAHOUN_ENV'] = 'invalid_env'
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'env must be one of' in str(exc_info.value)
    
    def test_invalid_guard_mode_rejected(self) -> None:
        """Test that invalid guard mode values are rejected."""
        os.environ['MAHOUN_ENV'] = 'dev'
        os.environ['MAHOUN_GUARD_MODE'] = 'INVALID'
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'guard_mode must be one of' in str(exc_info.value)
    
    def test_invalid_log_level_rejected(self) -> None:
        """Test that invalid log level values are rejected."""
        os.environ['MAHOUN_ENV'] = 'dev'
        os.environ['MAHOUN_LOG_LEVEL'] = 'INVALID'
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'log_level must be one of' in str(exc_info.value)
    
    def test_invalid_llm_provider_rejected(self) -> None:
        """Test that invalid LLM provider values are rejected."""
        os.environ['MAHOUN_ENV'] = 'dev'
        os.environ['MAHOUN_LLM_PROVIDER'] = 'invalid_provider'
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'llm_provider must be one of' in str(exc_info.value)
    
    def test_invalid_ledger_backend_rejected(self) -> None:
        """Test that invalid ledger backend values are rejected."""
        os.environ['MAHOUN_ENV'] = 'dev'
        os.environ['MAHOUN_LEDGER_BACKEND'] = 'invalid_backend'
        
        with pytest.raises(ValueError) as exc_info:
            MahounSettings()
        
        assert 'ledger_backend must be one of' in str(exc_info.value)
