"""
API Configuration - Advanced Edition
=====================================
Enterprise-grade configuration management with:
- Pydantic Settings V2
- Environment validation
- Secret management
- Multi-environment support
- Configuration hot-reload
- Health checks
"""

from typing import Any, Dict, List, Literal, Optional
from functools import lru_cache
from pathlib import Path
import os
import logging

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore
from pydantic import Field, field_validator, computed_field, SecretStr
logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    
    # PostgreSQL
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = Field(default="mahoun")
    postgres_user: str = Field(default="mahoun")
    postgres_password: SecretStr = Field(
        ...,
        description="PostgreSQL password (set DB_POSTGRES_PASSWORD env var)"
    )
    postgres_pool_size: int = Field(default=10, ge=1, le=100)
    postgres_max_overflow: int = Field(default=20, ge=0, le=100)
    postgres_pool_timeout: int = Field(default=30, ge=1)
    postgres_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: SecretStr = Field(
        ...,
        description="Neo4j password (set DB_NEO4J_PASSWORD env var)"
    )
    neo4j_max_connection_lifetime: int = Field(default=3600, ge=60)
    neo4j_max_connection_pool_size: int = Field(default=50, ge=1, le=1000)
    neo4j_connection_timeout: int = Field(default=30, ge=1)
    
    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: Optional[SecretStr] = Field(default=None)
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_ttl: int = Field(default=3600, ge=60, description="Default TTL in seconds")
    redis_max_connections: int = Field(default=50, ge=1, le=1000)
    
    @computed_field
    def postgres_url(self) -> str:
        """Build PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @computed_field
    def redis_url(self) -> str:
        """Build Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password.get_secret_value()}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_prefix="DB_",
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore"
        )


class SecuritySettings(BaseSettings):
    """Security configuration"""
    
    # JWT
    jwt_secret: SecretStr = Field(
        ...,
        min_length=32,
        description="JWT secret key (set SECURITY_JWT_SECRET env var, min 32 chars)"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24, ge=1, le=720)
    jwt_refresh_expiration_days: int = Field(default=7, ge=1, le=90)
    
    # API Keys
    api_key_header: str = Field(default="X-API-Key")
    api_keys: List[SecretStr] = Field(default_factory=list, description="Valid API keys")
    
    # CORS
    cors_origins: List[str] = Field(default=[
        "http://localhost",
        "http://localhost:5173",
        "https://mahoun.ai",
        "https://enterprise.mahoun.ai"
    ])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "OPTIONS"])
    cors_allow_headers: List[str] = Field(default=["Authorization", "Content-Type"])
    cors_max_age: int = Field(default=600, ge=0)
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    rate_limit_per_hour: int = Field(default=1000, ge=1)
    rate_limit_per_day: int = Field(default=10000, ge=1)
    rate_limit_strategy: Literal["fixed", "sliding"] = Field(default="sliding")
    
    # Security Headers
    enable_hsts: bool = Field(default=True)
    enable_csp: bool = Field(default=True)
    enable_xss_protection: bool = Field(default=True)
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins"""
        if "*" in v and len(v) > 1:
            raise ValueError("Cannot use '*' with other origins")
        return v
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_prefix="SECURITY_",
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore"
        )


class ModelSettings(BaseSettings):
    """ML Model configuration"""
    
    # Paths
    model_cache_dir: Path = Field(default=Path("./models"))
    model_download_timeout: int = Field(default=300, ge=60)
    
    # Embedding Models
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    embedding_dimension: int = Field(default=768, ge=128)
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    embedding_max_length: int = Field(default=512, ge=128, le=2048)
    
    # NLI Model
    nli_model: str = Field(default="microsoft/deberta-v3-base")
    nli_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Reranking
    reranker_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    reranker_top_k: int = Field(default=10, ge=1, le=100)
    
    # Generation (if using local LLM)
    llm_model: Optional[str] = Field(default=None)
    llm_max_tokens: int = Field(default=2048, ge=128, le=8192)
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Device
    device: Literal["cpu", "cuda", "mps"] = Field(default="cpu")
    use_fp16: bool = Field(default=False, description="Use half precision")
    
    @field_validator("model_cache_dir")
    @classmethod
    def validate_cache_dir(cls, v):
        """Ensure cache directory exists"""
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_prefix="MODEL_",
            case_sensitive=False,
            extra="ignore"
        )


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling features"""
    
    # RAG Features
    enable_gat_reranking: bool = Field(default=True)
    enable_hybrid_search: bool = Field(default=True)
    enable_graph_enrichment: bool = Field(default=True)
    
    # Safety Features
    enable_guardrails: bool = Field(default=True)
    enable_uncertainty: bool = Field(default=True)
    enable_hallucination_detection: bool = Field(default=True)
    
    # Monitoring
    enable_audit_logging: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)
    
    # Experimental
    enable_active_learning: bool = Field(default=False)
    enable_ab_testing: bool = Field(default=False)
    enable_rl_optimization: bool = Field(default=False)
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_prefix="FEATURE_",
            case_sensitive=False,
            extra="ignore"
        )


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration"""
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    log_format: Literal["json", "text"] = Field(default="json")
    log_file: Optional[Path] = Field(default=None)
    log_rotation: str = Field(default="1 day")
    log_retention: str = Field(default="30 days")
    
    # Metrics
    prometheus_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    metrics_path: str = Field(default="/metrics")
    
    # Tracing
    jaeger_enabled: bool = Field(default=False)
    jaeger_host: str = Field(default="localhost")
    jaeger_port: int = Field(default=6831, ge=1, le=65535)
    
    # Health Checks
    health_check_interval: int = Field(default=30, ge=5, description="Seconds")
    health_check_timeout: int = Field(default=5, ge=1)
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_prefix="MONITORING_",
            case_sensitive=False,
            extra="ignore"
        )


class Settings(BaseSettings):
    """Main application settings - Enterprise Edition"""
    
    # Application
    app_name: str = Field(default="MAHOUN Legal AI")
    version: str = Field(default="2.0.0")
    environment: Literal["development", "staging", "production"] = Field(default="production")
    debug: bool = Field(default=False)
    
    # API Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1024, le=65535)
    workers: int = Field(default=4, ge=1, le=32)
    worker_class: str = Field(default="uvicorn.workers.UvicornWorker")
    timeout: int = Field(default=60, ge=30)
    keepalive: int = Field(default=5, ge=1)
    
    # File Upload
    max_upload_size: int = Field(default=10 * 1024 * 1024, ge=1024)  # 10MB
    allowed_extensions: List[str] = Field(default=[".pdf", ".txt", ".docx", ".json"])
    upload_dir: Path = Field(default=Path("./uploads"))
    
    # Pagination
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=1000)
    
    # Timeouts
    request_timeout: int = Field(default=30, ge=1)
    database_timeout: int = Field(default=30, ge=1)
    cache_timeout: int = Field(default=5, ge=1)
    
    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    @field_validator("upload_dir")
    @classmethod
    def validate_upload_dir(cls, v):
        """Ensure upload directory exists"""
        v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @computed_field
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @computed_field
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    def get_database_url(self, masked: bool = False) -> str:
        """Get database URL with optional password masking"""
        url = self.database.postgres_url
        if masked:
            password = self.database.postgres_password.get_secret_value()
            url = url.replace(password, "***")
        return url
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate entire configuration and return status"""
        issues: List[Any] = []
        # Check critical settings
        if self.is_production:
            if self.debug:
                issues.append("DEBUG should be False in production")
            if "*" in self.security.cors_origins:
                issues.append("CORS should not allow all origins in production")
            if not self.security.rate_limit_enabled:
                issues.append("Rate limiting should be enabled in production")
        
        # Check database connectivity (would need actual connection test)
        # This is a placeholder for validation logic
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "environment": self.environment,
            "debug": self.debug
        }
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        data = self.model_dump()
        
        if not include_secrets:
            # Mask secrets
            if "database" in data:
                if "postgres_password" in data["database"]:
                    data["database"]["postgres_password"] = "***"
                if "neo4j_password" in data["database"]:
                    data["database"]["neo4j_password"] = "***"
                if "redis_password" in data["database"]:
                    data["database"]["redis_password"] = "***"
            
            if "security" in data:
                if "jwt_secret" in data["security"]:
                    data["security"]["jwt_secret"] = "***"
                if "api_keys" in data["security"]:
                    data["security"]["api_keys"] = ["***"] * len(data["security"]["api_keys"])
        
        return data
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
            validate_default=True,
        )
    # Graceful: works without pydantic-settings extra in constrained environments


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    This function is cached to avoid re-reading environment variables
    on every call. Clear the cache to reload settings:
    
        get_settings.cache_clear()
    """
    try:
        settings = Settings()
        logger.info(f"Settings loaded for environment: {settings.environment}")
        
        # Validate configuration
        validation = settings.validate_configuration()
        if not validation["valid"]:
            logger.warning(f"Configuration issues: {validation['issues']}")
        
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise


def reload_settings() -> Settings:
    """Reload settings by clearing cache"""
    get_settings.cache_clear()
    return get_settings()


# Global settings instance
settings = get_settings()


# Export commonly used settings
__all__ = [
    "Settings",
    "DatabaseSettings",
    "SecuritySettings",
    "ModelSettings",
    "FeatureFlags",
    "MonitoringSettings",
    "get_settings",
    "reload_settings",
    "settings",
]
