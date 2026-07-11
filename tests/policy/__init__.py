"""
Policy Tests Module
===================

Tests for centralized policy enforcement system.

This module contains comprehensive tests for:
- PolicyResolver: Centralized policy decision engine
- ExecutionPolicy: Immutable policy specifications
- ViewMode: Active vs Historical vs Mixed view enforcement
- Profile integration: DESKTOP_MINIMAL vs ENTERPRISE_FULL
- Security controls: Authorization and audit requirements
- Audit trail: Policy decision logging

Test Coverage:
--------------
- test_policy_resolver.py: Core PolicyResolver functionality (78+ tests)
  * Policy resolution
  * View mode enforcement
  * Profile integration
  * Security controls
  * Audit trail
  * Edge cases and error handling

Running Tests:
--------------
```bash
# Run all policy tests
pytest tests/policy/ -v

# Run specific test class
pytest tests/policy/test_policy_resolver.py::TestPolicyResolutionCore -v

# Run with coverage
pytest tests/policy/ --cov=mahoun.core.policy_resolver --cov-report=html

# Run only view mode tests
pytest tests/policy/ -k "view_mode" -v
```

Test Fixtures:
--------------
The module provides reusable test fixtures:
- desktop_minimal_profile: Mock DESKTOP_MINIMAL profile
- enterprise_full_profile: Mock ENTERPRISE_FULL profile
- governance_context: Mock GovernanceContext
- policy_resolver_desktop: PolicyResolver with desktop profile
- policy_resolver_enterprise: PolicyResolver with enterprise profile
"""

# Re-export test utilities for convenience
from tests.policy.test_policy_resolver import (
    MockDeploymentProfile,
    MockGovernanceContext,
    MockProfileManager,
    MockResourceLimits,
    MockPerformanceTargets,
)

__all__ = [
    # Test utilities
    "MockDeploymentProfile",
    "MockGovernanceContext",
    "MockProfileManager",
    "MockResourceLimits",
    "MockPerformanceTargets",
]
