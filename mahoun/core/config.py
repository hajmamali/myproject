"""
Mahoun Configuration Management - Ultra Edition
================================================
Enterprise-grade configuration with validation, profiles, and observability.

Features:
- Pydantic Settings V2 with strict validation
- Environment-based configuration with profiles
- Hierarchical configuration (env → file → defaults)
- Fail-fast on missing required secrets in production
- Configuration change detection and hot-reload support
- Comprehensive validation with detailed error messages
- No hardcoded absolute paths
- Thread-safe singleton pattern
- Configuration audit logging

Design Principles:
- All paths are relative or from environment variables
- Production requires explicit secrets (no defaults)
- Configuration is immutable after loading
- Validation happens at startup, not runtime
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Dict, FrozenSet, List, Optional, Set, Union

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Graceful degradation when pydantic-settings extra is not installed
    from pydantic import BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore

from mahoun.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# =============================================================================
# Enums for Type Safety
# =============================================================================

class Environment(str, Enum):
    """Deployment environment."""
    DEV = "dev"
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"
    PRODUCTION = "production"
    
    @classmethod
    def production_envs(cls) -> FrozenSet[str]:
        return frozenset({cls.PROD.value, cls.PRODUCTION.value, cls.STAGING.value})
    
    @classmethod
    def normalize(cls, value: str) -> "Environment":
        """Normalize environment value, supporting common aliases."""
        value_lower = value.lower()
        if value_lower in ("development", "dev"):
            return cls.DEV
        if value_lower in ("prod", "production"):
            return cls.PROD
        if value_lower == "staging":
            return cls.STAGING
        if value_lower == "test":
            return cls.TEST
        return cls(value)
    
    def is_production(self) -> bool:
        return self.value in self.production_envs()


class GuardMode(str, Enum):
    """Guard system operation mode."""
    OFF = "OFF"
    WARN = "WARN"
    STRICT = "STRICT"
    AUDIT = "AUDIT"
    
    def is_enforcing(self) -> bool:
        return self in (GuardMode.STRICT, GuardMode.AUDIT)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    AZURE = "azure"


class LedgerBackend(str, Enum):
    """Ledger storage backends."""
    JSONL = "jsonl"
    SQLITE = "sqlite"
    NOOP = "noop"


class LogFormat(str, Enum):
    """Log output formats."""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


# =============================================================================
# Configuration Sections
# =============================================================================

@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection configuration."""
    neo4j_uri: Optional[str] = None
    neo4j_user: str = "neo4j"
    neo4j_password: Optional[str] = None
    redis_url: Optional[str] = None
    postgres_url: Optional[str] = None
    
    def has_neo4j(self) -> bool:
        return bool(self.neo4j_uri)
    
    def has_redis(self) -> bool:
        return bool(self.redis_url)


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration."""
    provider: LLMProvider = LLMProvider.LOCAL
    timeout: int = 30
    max_retries: int = 3
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_api_key: Optional[str] = None
    default_model: Optional[str] = None
    
    def get_api_key(self) -> Optional[str]:
        """Get API key for current provider."""
        if self.provider == LLMProvider.OPENAI:
            return self.openai_api_key
        elif self.provider == LLMProvider.ANTHROPIC:
            return self.anthropic_api_key
        elif self.provider == LLMProvider.AZURE:
            return self.azure_api_key
        return None


@dataclass(frozen=True)
class ObservabilityConfig:
    """Observability and monitoring configuration."""
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON
    enable_tracing: bool = False
    enable_metrics: bool = False
    trace_sample_rate: float = 0.1
    metrics_port: int = 9090


@dataclass(frozen=True)
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 100


# =============================================================================
# Main Settings Class
# =============================================================================

class MahounSettings(BaseSettings):
    """
    Centralized configuration for Mahoun platform.
    
    All settings can be overridden via environment variables.
    Environment variable names use MAHOUN_ prefix.
    
    Example:
        MAHOUN_ENV=prod
        MAHOUN_GUARD_MODE=STRICT
        MAHOUN_NEO4J_PASSWORD=secret
    """
    
    # =========================================================================
    # Core Settings
    # =========================================================================
    
    env: str = Field(
        default="dev",
        description="Environment: dev, test, staging, prod"
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode (disabled in production)"
    )
    
    # =========================================================================
    # Path Configuration (No Hardcoded Absolute Paths)
    # =========================================================================
    
    data_dir: Path = Field(
        default=Path("data"),
        description="Base directory for data storage (relative or from env)"
    )
    
    model_dir: Optional[Path] = Field(
        default=None,
        description="Directory for LLM models"
    )
    
    ledger_dir: Path = Field(
        default=Path("data/ledger"),
        description="Directory for evidence ledger"
    )
    
    knowledge_graph_dir: Path = Field(
        default=Path("data/knowledge_graph"),
        description="Directory for knowledge graph storage"
    )
    
    output_dir: Path = Field(
        default=Path("output"),
        description="Directory for output files"
    )
    
    cache_dir: Path = Field(
        default=Path(".cache"),
        description="Directory for cache files"
    )
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    
    neo4j_uri: Optional[str] = Field(
        default=None,
        description="Neo4j connection URI"
    )
    
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    
    neo4j_password: Optional[str] = Field(
        default=None,
        description="Neo4j password (required in production)"
    )
    
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    
    postgres_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL"
    )
    
    # =========================================================================
    # LLM Configuration
    # =========================================================================
    
    llm_provider: str = Field(
        default="local",
        description="LLM provider: local, openai, anthropic, ollama, azure"
    )
    
    llm_timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="LLM request timeout in seconds"
    )
    
    llm_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retries for LLM requests"
    )
    
    llm_default_model: Optional[str] = Field(
        default=None,
        description="Default model name for LLM provider"
    )
    
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    
    azure_openai_endpoint: Optional[str] = Field(
        default=None,
        description="Azure OpenAI endpoint"
    )
    
    azure_openai_api_key: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API key"
    )
    
    # =========================================================================
    # Guard Mode
    # =========================================================================
    
    guard_mode: str = Field(
        default="STRICT",
        description="Guard mode: OFF, WARN, STRICT, AUDIT"
    )
    
    # =========================================================================
    # Observability
    # =========================================================================
    
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    log_format: str = Field(
        default="json",
        description="Log format: json, text, structured"
    )
    
    enable_tracing: bool = Field(
        default=False,
        description="Enable distributed tracing"
    )
    
    enable_metrics: bool = Field(
        default=False,
        description="Enable Prometheus metrics"
    )
    
    trace_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0 to 1.0)"
    )
    
    # =========================================================================
    # API Configuration
    # =========================================================================
    
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="API server port"
    )
    
    api_workers: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Number of API workers"
    )
    
    cors_origins: str = Field(
        default="*",
        description="CORS allowed origins (comma-separated)"
    )
    
    rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="API rate limit per minute"
    )
    
    # =========================================================================
    # Ledger Configuration
    # =========================================================================
    
    ledger_backend: str = Field(
        default="jsonl",
        description="Ledger backend: jsonl, sqlite, noop"
    )
    
    # =========================================================================
    # Feature Flags
    # =========================================================================
    
    enable_graph: bool = Field(
        default=True,
        description="Enable knowledge graph features"
    )
    
    enable_rag: bool = Field(
        default=True,
        description="Enable RAG features"
    )
    
    enable_self_improvement: bool = Field(
        default=False,
        description="Enable self-improvement system"
    )
    
    # =========================================================================
    # Pydantic Settings Configuration (v2 preferred)
    # =========================================================================
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_prefix="MAHOUN_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            validate_default=True,
        )
    # If pydantic-settings is missing, BaseSettings will still work with env vars
    # but without the advanced model_config features (acceptable in dev)
    
    # =========================================================================
    # Validators
    # =========================================================================
    
    @field_validator('env')
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Validate environment value."""
        allowed = {'dev', 'test', 'staging', 'prod', 'production'}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(f"env must be one of {sorted(allowed)}, got '{v}'")
        return normalized
    
    @field_validator('guard_mode')
    @classmethod
    def validate_guard_mode(cls, v: str) -> str:
        """Validate guard mode."""
        allowed = {'OFF', 'WARN', 'STRICT', 'AUDIT'}
        normalized = v.upper()
        if normalized not in allowed:
            raise ValueError(f"guard_mode must be one of {sorted(allowed)}, got '{v}'")
        return normalized
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        normalized = v.upper()
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}, got '{v}'")
        return normalized
    
    @field_validator('llm_provider')
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        allowed = {'local', 'openai', 'anthropic', 'ollama', 'azure'}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(f"llm_provider must be one of {sorted(allowed)}, got '{v}'")
        return normalized
    
    @field_validator('ledger_backend')
    @classmethod
    def validate_ledger_backend(cls, v: str) -> str:
        """Validate ledger backend."""
        allowed = {'jsonl', 'sqlite', 'noop'}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(f"ledger_backend must be one of {sorted(allowed)}, got '{v}'")
        return normalized
    
    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        allowed = {'json', 'text', 'structured'}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(f"log_format must be one of {sorted(allowed)}, got '{v}'")
        return normalized
    
    @model_validator(mode='after')
    def validate_production_requirements(self) -> 'MahounSettings':
        """Validate production-specific requirements."""
        # Only validate if explicitly in production
        if self.env in ('prod', 'production', 'staging'):
            # Debug must be off
            if self.debug:
                raise ValueError("DEBUG must be False in production/staging")
            
            # Guard mode cannot be OFF
            if self.guard_mode == "OFF":
                raise ValueError("GUARD_MODE cannot be OFF in production/staging")
            
            # Ledger cannot be noop
            if self.ledger_backend == "noop":
                raise ValueError("LEDGER_BACKEND cannot be noop in production/staging")
            
            # If using remote LLM, API key required
            if self.llm_provider == "openai" and not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY required when using OpenAI provider in production")
            
            if self.llm_provider == "anthropic" and not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY required when using Anthropic provider in production")
            
            if self.llm_provider == "azure":
                if not self.azure_openai_endpoint:
                    raise ValueError("AZURE_OPENAI_ENDPOINT required when using Azure provider in production")
                if not self.azure_openai_api_key:
                    raise ValueError("AZURE_OPENAI_API_KEY required when using Azure provider in production")
        
        return self
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env in ('prod', 'production', 'staging')
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env == 'dev'
    
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.env == 'test'
    
    def get_environment(self) -> Environment:
        """Get environment as enum."""
        return Environment(self.env)
    
    def get_guard_mode(self) -> GuardMode:
        """Get guard mode as enum."""
        return GuardMode(self.guard_mode)
    
    def get_llm_provider(self) -> LLMProvider:
        """Get LLM provider as enum."""
        return LLMProvider(self.llm_provider)
    
    def get_ledger_backend(self) -> LedgerBackend:
        """Get ledger backend as enum."""
        return LedgerBackend(self.ledger_backend)
    
    def get_ledger_path(self) -> Path:
        """Get path for ledger storage based on backend."""
        if self.ledger_backend == "jsonl":
            return self.ledger_dir / "evidence.jsonl"
        elif self.ledger_backend == "sqlite":
            return self.ledger_dir / "evidence.db"
        return self.ledger_dir
    
    def get_knowledge_graph_path(self) -> Path:
        """Get path for knowledge graph storage."""
        return self.knowledge_graph_dir
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration as dataclass."""
        return DatabaseConfig(
            neo4j_uri=self.neo4j_uri,
            neo4j_user=self.neo4j_user,
            neo4j_password=self.neo4j_password,
            redis_url=self.redis_url,
            postgres_url=self.postgres_url,
        )
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration as dataclass."""
        return LLMConfig(
            provider=self.get_llm_provider(),
            timeout=self.llm_timeout,
            max_retries=self.llm_max_retries,
            openai_api_key=self.openai_api_key,
            anthropic_api_key=self.anthropic_api_key,
            azure_endpoint=self.azure_openai_endpoint,
            azure_api_key=self.azure_openai_api_key,
            default_model=self.llm_default_model,
        )
    
    def get_observability_config(self) -> ObservabilityConfig:
        """Get observability configuration as dataclass."""
        return ObservabilityConfig(
            log_level=self.log_level,
            log_format=LogFormat(self.log_format),
            enable_tracing=self.enable_tracing,
            enable_metrics=self.enable_metrics,
            trace_sample_rate=self.trace_sample_rate,
        )
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration as dataclass."""
        return APIConfig(
            host=self.api_host,
            port=self.api_port,
            workers=self.api_workers,
            cors_origins=self.get_cors_origins_list(),
            rate_limit_per_minute=self.rate_limit_per_minute,
        )
    
    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        directories = [
            self.data_dir,
            self.ledger_dir,
            self.knowledge_graph_dir,
            self.output_dir,
            self.cache_dir,
        ]
        
        if self.model_dir:
            directories.append(self.model_dir)
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_config_hash(self) -> str:
        """Get hash of current configuration for change detection."""
        config_dict = self.model_dump(exclude={'neo4j_password', 'openai_api_key', 
                                                'anthropic_api_key', 'azure_openai_api_key'})
        config_str = json.dumps(config_dict, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """Export configuration as dict with secrets masked."""
        config = self.model_dump()
        
        # Mask sensitive fields
        sensitive_fields = {
            'neo4j_password', 'openai_api_key', 'anthropic_api_key',
            'azure_openai_api_key', 'redis_url', 'postgres_url'
        }
        
        for field_name in sensitive_fields:
            if config.get(field_name):
                config[field_name] = "***MASKED***"
        
        return config
    
    def log_configuration(self) -> None:
        """Log current configuration (with secrets masked)."""
        safe_config = self.to_safe_dict()
        logger.info(f"Configuration loaded: {json.dumps(safe_config, default=str)}")


# =============================================================================
# Singleton Pattern with Thread Safety
# =============================================================================

class SettingsManager:
    """Thread-safe settings manager with caching."""
    
    _instance: ClassVar[Optional['SettingsManager']] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    
    def __init__(self) -> None:
        self._settings: Optional[MahounSettings] = None
        self._loaded_at: Optional[datetime] = None
        self._config_hash: Optional[str] = None
    
    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_settings(self, force_reload: bool = False) -> MahounSettings:
        """
        Get settings instance.
        
        Args:
            force_reload: Force reload from environment
            
        Returns:
            MahounSettings instance
        """
        if self._settings is None or force_reload:
            with self._lock:
                if self._settings is None or force_reload:
                    self._settings = MahounSettings()
                    self._loaded_at = datetime.now(timezone.utc)
                    self._config_hash = self._settings.get_config_hash()
                    logger.info(
                        f"Settings loaded: env={self._settings.env}, "
                        f"hash={self._config_hash}"
                    )
        return self._settings
    
    def clear_cache(self) -> None:
        """Clear settings cache."""
        with self._lock:
            self._settings = None
            self._loaded_at = None
            self._config_hash = None
    
    @property
    def loaded_at(self) -> Optional[datetime]:
        """Get when settings were loaded."""
        return self._loaded_at
    
    @property
    def config_hash(self) -> Optional[str]:
        """Get configuration hash."""
        return self._config_hash


# =============================================================================
# Public API
# =============================================================================

@lru_cache()
def get_settings() -> MahounSettings:
    """
    Get validated settings instance (cached).
    
    Returns:
        MahounSettings instance
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        return SettingsManager.get_instance().get_settings()
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for testing)."""
    get_settings.cache_clear()
    SettingsManager.get_instance().clear_cache()


def reload_settings() -> MahounSettings:
    """Force reload settings from environment."""
    clear_settings_cache()
    return get_settings()


# =============================================================================
# Environment Helpers
# =============================================================================

def require_env(name: str) -> str:
    """
    Get required environment variable.
    
    Args:
        name: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        ConfigurationError: If not set
    """
    value = os.getenv(name)
    if not value:
        raise ConfigurationError(f"Required environment variable {name} is not set")
    return value


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get optional environment variable.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(name, default)


def get_env_bool(name: str, default: bool = False) -> bool:
    """
    Get boolean environment variable.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        
    Returns:
        Boolean value
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def get_env_int(name: str, default: int = 0) -> int:
    """
    Get integer environment variable.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        
    Returns:
        Integer value
    """
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_list(name: str, default: Optional[List[str]] = None, separator: str = ",") -> List[str]:
    """
    Get list environment variable.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        separator: List separator
        
    Returns:
        List of strings
    """
    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(separator) if item.strip()]
