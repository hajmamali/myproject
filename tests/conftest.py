"""
Test Environment Bootstrap (PR-2.5)
====================================

This file sets up the test environment at COLLECTION TIME (module import),
ensuring that tests can be collected and run without encountering ValidationErrors
for required secrets.

IMPORTANT: This is TEST-ONLY bootstrap. Runtime deployments MUST supply real secrets
via environment variables or .env files. DO NOT use these test values in production.

Security Note:
- These values are set ONLY for pytest collection/execution
- Runtime code (api/config.py) still enforces required secrets with no defaults
- PR-2 security hardening remains intact - no default passwords in runtime code
"""

import os
import sys
from pathlib import Path

# =============================================================================
# Python Path Setup (CRITICAL for module imports)
# =============================================================================
# Add project root to Python path so that all modules can be imported
# regardless of where the repository is located on the filesystem.
# This fixes "ModuleNotFoundError" when repository location changes.

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# Test-Only Environment Variables (Collection-Time Setup)
# =============================================================================
# These MUST be set before any imports of api.config or api.main occur,
# because Pydantic validates settings at module-import time.

# Signal that we're in test mode (used by api/main.py for TrustedHostMiddleware)
os.environ["MAHOUN_TESTING"] = "1"

# Disable rate limiting in test environment (prevents 429 errors in test suites)
os.environ["MAHOUN_ENABLE_RATE_LIMIT"] = "false"

# PostgreSQL password (required by DatabaseSettings)
os.environ.setdefault(
    "DB_POSTGRES_PASSWORD", "test_postgres_password_NOT_FOR_PRODUCTION"
)

# Neo4j password (required by DatabaseSettings)
os.environ.setdefault("DB_NEO4J_PASSWORD", "test_neo4j_password_NOT_FOR_PRODUCTION")

# JWT secret (required by SecuritySettings, must be >= 32 chars)
os.environ.setdefault(
    "SECURITY_JWT_SECRET",
    "test_jwt_secret_exactly_32_chars_min_NOT_FOR_PRODUCTION_USE_12345678",
)

# Optional: Redis password (if required)
os.environ.setdefault("REDIS_PASSWORD", "test_redis_password")

# Optional: Set test database URLs to prevent connection attempts
os.environ.setdefault("DB_POSTGRES_HOST", "localhost")
os.environ.setdefault("DB_POSTGRES_PORT", "5432")
os.environ.setdefault("DB_POSTGRES_USER", "test_user")
os.environ.setdefault("DB_POSTGRES_DB", "test_db")

os.environ.setdefault("DB_NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("DB_NEO4J_USER", "neo4j")

os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")


# =============================================================================
# Pytest Configuration and Fixtures
# =============================================================================

import pytest


@pytest.fixture(scope="session", autouse=True)
def test_environment_info():
    """
    Display test environment information at start of session.
    This fixture runs automatically for every test session.
    """
    print("\n" + "=" * 80)
    print("🧪 TEST ENVIRONMENT BOOTSTRAP (PR-2.5)")
    print("=" * 80)
    print("✓ Test-only secrets configured for pytest")
    print("✓ Runtime security (PR-2) remains intact")
    print("✓ Collection-time ValidationErrors resolved")
    print("=" * 80 + "\n")
    yield
    print("\n" + "=" * 80)
    print("🏁 TEST SESSION COMPLETE")
    print("=" * 80 + "\n")


# =============================================================================
# Model Warmup for Semantic Search Tests
# =============================================================================
#
# Pre-load sentence-transformers model to avoid timeout in individual tests.
# This downloads the model once at session start (~420MB, can take 60+ seconds).
#


@pytest.fixture(scope="session", autouse=False)
def warmup_embedding_model():
    """
    Pre-load sentence-transformers model for semantic search tests.
    
    This fixture prevents timeout errors in individual tests by downloading
    the model once at session start. The model is cached by sentence-transformers
    in ~/.cache/torch/sentence_transformers/.
    
    Usage:
        @pytest.mark.usefixtures("warmup_embedding_model")
        class TestSemanticSearch:
            ...
    
    Note: Not autouse=True to avoid slowing down unrelated tests.
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        print(f"\n🔥 Warming up embedding model: {model_name}")
        print("   (This may take 60+ seconds on first run to download ~420MB)")
        
        # Load model (will download if not cached)
        model = SentenceTransformer(model_name)
        
        # Verify it works with a simple encoding
        _ = model.encode("test", show_progress_bar=False)
        
        print(f"✓ Model loaded successfully (dim={model.get_sentence_embedding_dimension()})")
        
        yield model
        
    except ImportError:
        print("⚠ sentence-transformers not available, skipping warmup")
        yield None


# =============================================================================
# Integration Test Guards
# =============================================================================
#
# Automatically skip integration/slow tests unless environment variables are set.
# This prevents accidental runs of tests requiring external services.
#


def pytest_collection_modifyitems(config, items):
    """Skip integration and slow tests unless environment variables allow them."""
    run_integration = os.getenv("MAHOUN_INTEGRATION") == "1"
    run_slow = os.getenv("MAHOUN_SLOW") == "1"

    skip_integration = pytest.mark.skip(
        reason="Integration tests disabled (set MAHOUN_INTEGRATION=1)."
    )
    skip_slow = pytest.mark.skip(reason="Slow tests disabled (set MAHOUN_SLOW=1).")

    for item in items:
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)


# =============================================================================
# SECURITY REMINDER
# =============================================================================
#
# This conftest.py is ONLY for testing. It does NOT weaken production security:
#
# 1. Runtime code (api/config.py) has NO default passwords
# 2. Production code has NO default passwords
# 3. Production deployments MUST set real environment variables
# 4. Docker Compose uses ${VAR:-?ERROR} to enforce secret provision
# 5. These test values are obviously not production-like
#
# If you see these test passwords in production logs, something is very wrong!
#
# =============================================================================
