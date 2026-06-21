"""
MAHOUN Determinism Tests Configuration
=======================================

Classification: CRITICAL TEST INFRASTRUCTURE
Purpose: Configure test environment for determinism tests

This module ensures that determinism tests run in a controlled
environment with proper configuration.

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment for determinism tests.
    
    CRITICAL: This fixture runs ONCE per test session and configures
    the environment to allow flexible predicate usage for testing.
    
    Uses canonical environment authority for proper test isolation.
    
    In production, ontology strict mode is ENABLED.
    In tests, we disable it to allow test predicates like "human", "mortal", etc.
    """
    from mahoun.core.environment import bootstrap_environment, reset_environment
    from reasoning_logic.ontology import reset_default_ontology
    
    # Bootstrap test environment using canonical authority
    bootstrap_environment(override="test")
    
    # Reset ontology to ensure clean state
    reset_default_ontology()
    
    # Disable proof-carrying contract enforcement for determinism tests
    # (we test the contract separately in test_proof_carrying_contracts.py)
    os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"] = "false"
    
    yield
    
    # Cleanup (restore environment)
    reset_environment()
    if "MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT" in os.environ:
        del os.environ["MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT"]


@pytest.fixture(scope="function", autouse=True)
def reset_ontology_between_tests():
    """
    Reset ontology between tests to ensure isolation.
    
    This prevents shared state contamination between tests.
    """
    from reasoning_logic.ontology import reset_default_ontology
    reset_default_ontology()
    yield
    # Reset again after test
    reset_default_ontology()


@pytest.fixture(scope="function")
def determinism_test_config():
    """
    Configuration for determinism tests.
    
    Returns:
        Dict with test configuration
    """
    return {
        "iterations": 100,
        "tolerance": 0.0,  # Zero tolerance for determinism
        "timeout_seconds": 300,  # 5 minutes for 100 iterations
        "concurrency": 100,
        "max_delay_ms": 10,
    }

