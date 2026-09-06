"""
Global Configuration and Fixtures for KG Validation Framework
==============================================================

Provides shared fixtures, configuration, and test utilities for all phases.
"""

import os
import sys
import pytest
from pathlib import Path
from typing import Dict, Any, Generator, Optional
from unittest.mock import Mock
import tempfile

# =============================================================================
# Python Path Setup
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# Test Environment Configuration
# =============================================================================
os.environ.setdefault("MAHOUN_TESTING", "1")
os.environ.setdefault("MAHOUN_ENABLE_RATE_LIMIT", "false")
os.environ.setdefault("DB_POSTGRES_PASSWORD", "test_postgres_password")
os.environ.setdefault("DB_NEO4J_PASSWORD", "dev_neo4j_password_2026")
os.environ.setdefault("SECURITY_JWT_SECRET", "test_jwt_secret_exactly_32_chars_min_NOT_FOR_PRODUCTION_USE_12345678")
os.environ.setdefault("DB_NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("DB_NEO4J_USER", "neo4j")

# =============================================================================
# Pytest Configuration
# =============================================================================
def pytest_configure(config):
    """Register custom pytest markers."""
    markers = [
        "p0_critical: P0 critical path tests (every PR)",
        "p1_high: P1 high priority tests (nightly)",
        "p2_medium: P2 medium priority tests (weekly)",
        "p3_low: P3 low priority tests (monthly)",
        "integration: Requires Neo4j connection",
        "slow: Long-running tests",
        "unit: Fast unit tests with no external dependencies",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)

def pytest_collection_modifyitems(config, items):
    """Skip integration and slow tests unless environment variables allow."""
    run_integration = os.getenv("MAHOUN_INTEGRATION") == "1"
    run_slow = os.getenv("MAHOUN_SLOW") == "1"

    skip_integration = pytest.mark.skip(reason="Integration tests disabled (set MAHOUN_INTEGRATION=1).")
    skip_slow = pytest.mark.skip(reason="Slow tests disabled (set MAHOUN_SLOW=1).")

    for item in items:
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "slow" in item.keywords and not run_slow:
            item.add_marker(skip_slow)

# =============================================================================
# Neo4j Configuration Fixture
# =============================================================================
@pytest.fixture(scope="session")
def neo4j_config() -> Dict[str, str]:
    """Neo4j configuration from environment variables."""
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("DB_NEO4J_PASSWORD", "dev_neo4j_password_2026"),
        "database": os.getenv("NEO4J_DATABASE", "neo4j"),
    }

# =============================================================================
# Temporary Directory Fixture
# =============================================================================
@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

# =============================================================================
# Mock Fixtures for Unit Tests
# =============================================================================
@pytest.fixture(scope="function")
def mock_parser():
    """Mock legal document parser."""
    parser = Mock()
    parser.parse.return_value = {
        "laws": [],
        "chapters": [],
        "articles": [],
        "references": []
    }
    return parser

@pytest.fixture(scope="function")
def mock_extractor():
    """Mock entity extractor."""
    extractor = Mock()
    extractor.extract_laws.return_value = []
    extractor.extract_articles.return_value = []
    extractor.extract_references.return_value = []
    return extractor

@pytest.fixture(scope="function")
def mock_graph_builder():
    """Mock graph builder."""
    builder = Mock()
    builder.build.return_value = {"nodes": 0, "relationships": 0}
    return builder

# =============================================================================
# Session Information Fixture
# =============================================================================
@pytest.fixture(scope="session", autouse=True)
def test_session_info():
    """Display test session information."""
    print("\n" + "=" * 80)
    print("🧪 KG VALIDATION FRAMEWORK TEST SESSION")
    print("=" * 80)
    print("✓ Validating Persian Legal Knowledge Graph Construction System")
    print("✓ 10-Phase Comprehensive Validation")
    print("=" * 80 + "\n")
    yield
    print("\n" + "=" * 80)
    print("🏁 TEST SESSION COMPLETE")
    print("=" * 80 + "\n")
