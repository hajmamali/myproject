"""
MAHOUN Secrets Configuration
============================
Secure credential management - NO default passwords in production.

Rules:
1. In production/staging: credentials MUST be set via env AND not be dev placeholders
2. In development: can use safe dev defaults for convenience
3. Never commit real secrets to code

Usage:
    from mahoun.core.secrets import get_secret, require_secret
    
    # Soft get (returns None if not set)
    api_key = get_secret("OPENAI_API_KEY")
    
    # Hard require (raises if not set OR is a dev placeholder in prod/staging)
    db_password = require_secret("DB_NEO4J_PASSWORD")
"""

import os
import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Canonical required secrets (compose + backend must use these names)
REQUIRED_SECRETS = frozenset({
    "DB_NEO4J_PASSWORD",
    "DB_POSTGRES_PASSWORD", 
    "SECURITY_JWT_SECRET",
})

# Known dev-only placeholder values (FORBIDDEN in staging/prod)
DEV_PLACEHOLDERS = frozenset({
    "dev_password_change_me",
    "CHANGE_ME",
    "changeme",
    "password",
    "secret",
    "<CHANGE_ME_REQUIRED>",
    "<CHANGE_ME_OPTIONAL>",
    "",
})

# Development-only defaults (NEVER use real credentials here)
_DEV_DEFAULTS = {
    "DB_NEO4J_PASSWORD": "dev_password_change_me",
    "NEO4J_USER": "neo4j",
    "DB_POSTGRES_PASSWORD": "dev_password_change_me",
    "REDIS_PASSWORD": "",
}


def get_env() -> str:
    """Get current environment (dev/staging/prod)"""
    from mahoun.core.environment import get_current_environment
    env_context = get_current_environment()
    if env_context.is_production():
        return "prod"
    elif env_context.is_staging():
        return "staging"
    elif env_context.is_test():
        return "test"
    return "dev"


def is_dev() -> bool:
    """Check if running in development mode"""
    from mahoun.core.environment import is_development
    return is_development()


def is_production() -> bool:
    """Check if running in production or staging (strict mode)"""
    from mahoun.core.environment import is_production, is_staging
    return is_production() or is_staging()


def _is_dev_placeholder(value: str) -> bool:
    """Check if value is a known dev placeholder (unsafe for prod)"""
    if not value or not value.strip():
        return True
    value_lower = value.lower().strip()
    return value_lower in {p.lower() for p in DEV_PLACEHOLDERS}


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a secret from environment.
    
    In dev: falls back to dev defaults if not set
    In prod/staging: returns None if not set (use require_secret for mandatory)
    
    SECURITY: Does NOT validate placeholders for soft gets.
              Use require_secret() for critical credentials.
    """
    value = os.getenv(name)
    
    if value:
        return value
    
    if is_dev() and name in _DEV_DEFAULTS:
        logger.debug(f"Using dev default for {name}")
        return _DEV_DEFAULTS[name]
    
    return default


def require_secret(name: str) -> str:
    """
    Get a required secret with strict validation.
    
    SECURITY POLICY:
    - In dev: allows dev defaults for convenience
    - In staging/prod: MUST be set AND not be a dev placeholder
    
    Raises:
        RuntimeError: If secret is missing or is a dev placeholder in prod/staging
    
    Usage:
        password = require_secret("DB_NEO4J_PASSWORD")
    """
    value = os.getenv(name)
    
    # In production/staging: strict validation
    if is_production():
        if value is None or value == "":
            raise RuntimeError(
                f"🔐 SECURITY GATE: Required secret '{name}' is NOT SET in {get_env()} environment.\n"
                f"   This is MANDATORY for production/staging deployments.\n"
                f"   Set it in your environment or .env file (which must not be committed)."
            )
        
        if _is_dev_placeholder(value):
            raise RuntimeError(
                f"🔐 SECURITY GATE: Secret '{name}' contains a DEV PLACEHOLDER in {get_env()} environment.\n"
                f"   Value: '{value[:20]}...' (truncated)\n"
                f"   Dev placeholders are FORBIDDEN in staging/production.\n"
                f"   Generate a strong secret: openssl rand -base64 32"
            )
        
        return value
    
    # In test: allow placeholders and missing secrets (graceful degradation for test suite)
    if get_env() == "test":
        if not value:
            if name in _DEV_DEFAULTS:
                logger.debug(
                    f"🧪 Test env: using dev default for {name} (test-friendly fallback)"
                )
                return _DEV_DEFAULTS[name]
            else:
                # For non-Neo4j/Postgres secrets in tests, return empty string (graceful degradation)
                logger.debug(
                    f"🧪 Test env: {name} not set, returning empty string (graceful degradation)"
                )
                return ""
        
        # Test allows placeholders without warnings (test-friendly)
        if _is_dev_placeholder(value):
            logger.debug(f"🧪 Test env: {name} uses dev placeholder (acceptable in tests)")
        
        return value
    
    # In dev: allow defaults with warning
    if is_dev():
        if not value:
            if name in _DEV_DEFAULTS:
                logger.warning(
                    f"⚠️ Using dev default for {name}. "
                    f"Set in .env for production readiness!"
                )
                return _DEV_DEFAULTS[name]
            else:
                raise RuntimeError(
                    f"Required secret {name} not set. "
                    f"Add to .env or use one of: {list(_DEV_DEFAULTS.keys())}"
                )
        
        # Dev allows placeholders but warns
        if _is_dev_placeholder(value):
            logger.warning(
                f"⚠️ {name} uses a dev placeholder. "
                f"This is OK in dev but will FAIL in staging/prod."
            )
        
        return value
    
    # Fallback (unknown env)
    raise RuntimeError(
        f"Unknown MAHOUN_ENV: {get_env()}. Must be dev|staging|prod|test"
    )


def validate_all_required_secrets() -> Dict[str, str]:
    """
    Validate ALL required secrets at startup.
    
    Returns:
        Dict mapping secret name to status string
    
    Raises:
        RuntimeError: If any required secret is invalid in prod/staging
    """
    results: Dict[str, str] = {}
    errors = []
    
    for secret_name in REQUIRED_SECRETS:
        try:
            value = require_secret(secret_name)
            if is_production():
                results[secret_name] = "✅ SET (validated)"
            else:
                results[secret_name] = "⚠️ DEV (OK)"
        except RuntimeError as e:
            results[secret_name] = f"❌ FAIL: {str(e)[:50]}..."
            errors.append(str(e))
    
    if errors and is_production():
        raise RuntimeError(
            f"🔐 SECRETS VALIDATION FAILED in {get_env()}:\n" + 
            "\n".join(f"  - {err}" for err in errors)
        )
    
    return results


__all__ = [
    "get_secret",
    "require_secret", 
    "get_env",
    "is_dev",
    "is_production",
    "validate_all_required_secrets",
    "REQUIRED_SECRETS",
]




