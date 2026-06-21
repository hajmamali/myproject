"""
MAHOUN Architectural Stress Test Suite
=======================================

This test suite contains hard architectural stress tests for MAHOUN that verify
kernel ownership, governance enforcement, dependency integrity, and resilience
to agent-driven modifications.

Test Categories:
1. Kernel Ownership (test_kernel_ownership.py)
   - Verify kernel remains isolated and functional
   - Verify governance boundaries are enforced
   - Verify zero external dependencies

2. Dependency Direction (test_dependency_direction.py)
   - Verify correct dependency flow direction
   - Prevent reverse dependencies
   - Detect circular imports

3. Runtime Configuration (test_runtime_configuration.py)
   - Verify desktop_minimal mode disables heavy operations
   - Verify configuration consistency
   - Verify backend fallbacks

4. Agent Resilience (test_agent_resilience.py)
   - Verify kernel survives agent refactors
   - Verify governance locks cannot be bypassed
   - Verify provenance chain immutability

5. Failure Modes (test_failure_modes.py)
   - Verify graceful degradation under resource constraints
   - Verify error recovery mechanisms
   - Verify no cascading failures

Running the Tests
=================

Run all stress tests:
  pytest tests/stress/ -v

Run specific test category:
  pytest tests/stress/test_kernel_ownership.py -v

Run with markers:
  pytest tests/stress/ -m stress -v          # All stress tests
  pytest tests/stress/ -m slow -v            # Slow tests only
  pytest tests/stress/ -m integration -v     # Integration tests

Run in minimal environment:
  export MAHOUN_MODE=desktop_minimal
  pytest tests/stress/ -v

Test Results
============

Each test includes:
- Clear test name describing what is verified
- Objective: what architectural property is verified
- Setup: initial conditions
- Execution: sequence of actions
- Observation points: metrics/logs to capture
- Pass/Fail criteria: explicit requirements

Expected Outcome
================

All tests should pass in both desktop_minimal and server_full modes.
Tests verify that:
1. Kernel remains functional independently
2. Governance enforcement is non-bypassable
3. Dependency direction is strict
4. System degrades gracefully under constraints
5. Agent modifications don't break core contracts

Stress Test Coverage
====================

Kernel Isolation:
- ✓ Query classification without reasoning
- ✓ Context authority isolation
- ✓ Mutation boundary enforcement
- ✓ Forbidden procedure detection
- ✓ Standalone kernel import

Dependency Direction:
- ✓ No reverse dependencies in kernel
- ✓ Core/governance only import from kernel
- ✓ No circular imports
- ✓ Lazy imports prevent circular deps

Runtime Configuration:
- ✓ desktop_minimal disables heavy ops
- ✓ Configuration immutability
- ✓ All backends configured
- ✓ Environment variable parsing

Agent Resilience:
- ✓ Kernel APIs stable after refactors
- ✓ Governance locks cannot be disabled
- ✓ Fortress validator contract immutable
- ✓ Runtime contracts enforced

Failure Modes:
- ✓ Graceful degradation with disabled backends
- ✓ Error recovery without state corruption
- ✓ Neo4j unavailability handled
- ✓ Cascading failures prevented

See STRESS_TEST_IMPLEMENTATION_GUIDE.md for detailed documentation.
"""

__all__ = [
    "test_kernel_ownership",
    "test_dependency_direction",
    "test_runtime_configuration",
    "test_agent_resilience",
    "test_failure_modes",
]
