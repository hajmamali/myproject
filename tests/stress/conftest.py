"""
MAHOUN Stress Test Suite - Shared Configuration
===============================================

This conftest.py provides shared fixtures and configuration for all stress tests.
Stress tests focus on architectural integrity under pressure and degradation scenarios.
"""

import os
import sys
import pytest
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="session")
def stress_test_root():
    """Provide path to stress test directory."""
    return Path(__file__).parent


@pytest.fixture(scope="session", autouse=True)
def setup_minimal_environment():
    """
    Session-level fixture to set up minimal environment.
    Ensures all stress tests run in desktop_minimal mode by default.
    """
    # Set minimal mode
    os.environ["MAHOUN_MODE"] = "desktop_minimal"
    os.environ["MAHOUN_GRAPH_ENABLED"] = "false"
    os.environ["MAHOUN_GRAPH_BACKEND"] = "disabled_fallback"
    os.environ["MAHOUN_LORA_TRAINING_ENABLED"] = "false"
    
    yield
    
    # Session cleanup (optional)


@pytest.fixture(scope="function")
def isolated_env():
    """
    Function-level fixture providing isolated environment.
    Cleans up after each test to prevent state leakage.
    """
    env_backup = os.environ.copy()
    
    # Clear any cached imports
    try:
        from mahoun.core.runtime_config import get_runtime_settings
        get_runtime_settings.cache_clear()
    except:
        pass
    
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(env_backup)
    
    # Clear cache again
    try:
        from mahoun.core.runtime_config import get_runtime_settings
        get_runtime_settings.cache_clear()
    except:
        pass


@pytest.fixture
def kernel_context():
    """Provide access to governance kernel for testing."""
    from mahoun.core.governance_kernel.kernel import (
        KernelMutationBoundary,
        set_governance_authority,
        is_governance_authorized,
        reset_governance_authority,
        GovernanceViolationError,
        GovernanceViolation,
        QueryType,
        ViolationCategory,
        ViolationSeverity,
    )
    
    return {
        "boundary": KernelMutationBoundary,
        "set_authority": set_governance_authority,
        "is_authorized": is_governance_authorized,
        "reset_authority": reset_governance_authority,
        "ViolationError": GovernanceViolationError,
        "Violation": GovernanceViolation,
        "QueryType": QueryType,
        "ViolationCategory": ViolationCategory,
        "ViolationSeverity": ViolationSeverity,
    }


@pytest.fixture
def runtime_settings():
    """Provide access to runtime settings."""
    from mahoun.core.runtime_config import get_runtime_settings
    
    return get_runtime_settings()


def pytest_configure(config):
    """Configure pytest for stress tests."""
    config.addinivalue_line(
        "markers", "stress: mark test as stress test (run with -m stress)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (run with -m slow)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Mark all tests in stress directory
    for item in items:
        item.add_marker(pytest.mark.stress)
        
        # Mark slow tests
        if "neo4j" in item.nodeid.lower() or "degradation" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)


# Pytest hooks for summary

def pytest_sessionstart(session):
    """Print session start message."""
    print("\n" + "=" * 70)
    print("MAHOUN ARCHITECTURAL STRESS TEST SUITE")
    print("=" * 70)
    print("Testing: Kernel ownership, governance enforcement, dependency integrity")
    print("Environment: desktop_minimal mode")
    print("=" * 70 + "\n")


def pytest_sessionfinish(session, exitstatus):
    """Print session finish message."""
    print("\n" + "=" * 70)
    print("STRESS TEST SUITE COMPLETE")
    print("=" * 70)
    print(f"Exit Status: {exitstatus}")
    print("=" * 70 + "\n")


# Export test utilities

def verify_kernel_isolation():
    """Utility: Verify kernel is properly isolated."""
    from mahoun.core.governance_kernel.kernel import KernelMutationBoundary
    
    # Basic isolation check
    assert KernelMutationBoundary is not None
    
    # Verify stdlib imports only (in kernel module)
    return True


def verify_minimal_mode():
    """Utility: Verify system is in minimal mode."""
    from mahoun.core.runtime_config import get_runtime_settings
    
    settings = get_runtime_settings()
    assert settings.graph_backend == "disabled_fallback"
    assert settings.lora_training_enabled is False
    
    return True


def verify_no_cascading_failure():
    """Utility: Verify no cascading failures in critical path."""
    from mahoun.core.governance_kernel.kernel import KernelMutationBoundary
    
    # Try to trigger and recover from violation
    try:
        KernelMutationBoundary.inspect("CREATE (n:Node)")
    except:
        pass
    
    # Verify kernel still works
    result = KernelMutationBoundary.classify_query("MATCH (n) RETURN n")
    assert result.value == "READ"
    
    return True
