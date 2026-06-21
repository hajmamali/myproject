# MAHOUN Architectural Stress Tests - Implementation Guide

## Overview

This document provides a comprehensive guide to MAHOUN's architectural stress test suite. These tests verify kernel ownership, governance enforcement, dependency integrity, runtime stability, and resilience to agent-driven modifications in the desktop_minimal environment.

## Architecture

```
MAHOUN System Layers:
┌─────────────────────────────────────┐
│ Layer 3: Agents (modify code)       │
├─────────────────────────────────────┤
│ Layer 2: Services (use features)    │
├─────────────────────────────────────┤
│ Layer 1: Core/Governance (enforce)  │
├─────────────────────────────────────┤
│ Layer 0: Kernel (stdlib only)       │
└─────────────────────────────────────┘

Dependency Direction (↑):
- Kernel has NO dependencies
- Core can import from Kernel only
- Services can import from Kernel/Core
- Agents can import from all layers
```

## Test Suite Structure

### 1. Kernel Ownership Tests (`test_kernel_ownership.py`)

**Objective**: Verify kernel remains isolated and functional even when high-level dependencies fail.

**Key Tests**:
- `test_kernel_query_classification_without_reasoning` - Kernel works without reasoning module
- `test_kernel_context_authority_isolation` - Context isolation via contextvars
- `test_kernel_mutation_boundary_enforcement` - Unauthorized mutations blocked
- `test_kernel_forbidden_procedure_detection` - Forbidden procedures detected
- `test_kernel_standalone_import` - Kernel imports only stdlib
- `test_kernel_violation_immutability` - Violations are immutable (frozen)

**Pass Criteria**:
- Kernel classifies queries correctly
- Context authority doesn't leak between requests
- Unauthorized mutations raise `GovernanceViolationError`
- All kernel imports are from stdlib only

### 2. Dependency Direction Tests (`test_dependency_direction.py`)

**Objective**: Verify dependencies flow only downward (agents → services → core → kernel).

**Key Tests**:
- `test_kernel_no_reverse_dependencies` - Kernel doesn't import from core/governance/reasoning
- `test_core_governance_no_reasoning_imports` - Core doesn't import from high-level modules
- `test_no_circular_imports_between_core_modules` - Dependency graph is acyclic
- `test_lazy_imports_prevent_circular_deps` - Heavy modules are lazy-loaded
- `test_layer_0_kernel_pure_stdlib` - Layer 0 uses only stdlib
- `test_layer_1_core_only_kernel_imports` - Layer 1 respects boundaries

**Pass Criteria**:
- No reverse dependencies found
- No circular imports
- All layers maintain proper boundaries
- Lazy loading prevents issues

### 3. Runtime Configuration Tests (`test_runtime_configuration.py`)

**Objective**: Verify runtime configuration is accurate in desktop_minimal mode.

**Key Tests**:
- `test_minimal_mode_disables_graph` - Graph operations disabled or fallback
- `test_minimal_mode_disables_lora_training` - LoRA training disabled
- `test_minimal_mode_uses_lightweight_backends` - Backends are lightweight
- `test_minimal_mode_respects_environment_overrides` - Env vars respected
- `test_runtime_settings_immutability` - Settings are frozen (immutable)
- `test_configuration_caching` - Settings are cached and consistent
- `test_boolean_env_var_parsing` - Boolean env vars parse correctly
- `test_string_env_var_preservation` - String values preserved

**Pass Criteria**:
- In desktop_minimal: graph disabled, LoRA disabled
- Settings are immutable
- All backends configured with valid values
- Environment variables override defaults
- Settings are cached and deterministic

### 4. Agent Resilience Tests (`test_agent_resilience.py`)

**Objective**: Verify kernel and governance contracts survive agent-driven refactors.

**Key Tests**:
- `test_kernel_api_stability_after_mock_refactor` - APIs unchanged after refactors
- `test_governance_lock_cannot_be_disabled_by_agent` - Locks cannot be bypassed
- `test_fortress_validator_contract_immutable` - Fortress APIs stable
- `test_mutation_boundary_contract_enforced` - Mutation boundary cannot be violated
- `test_query_classification_contract` - Query classification always returns valid type
- `test_no_unsafe_eval_in_core` - No unsafe eval/exec patterns
- `test_monkeypatch_detection` - Monkeypatching can be detected and reverted

**Pass Criteria**:
- Kernel APIs remain stable
- Governance locks work correctly
- Runtime contracts enforced
- No unsafe code patterns
- Violations are properly caught

### 5. Failure Modes Tests (`test_failure_modes.py`)

**Objective**: Verify system gracefully degrades under resource constraints.

**Key Tests**:
- `test_graph_disabled_no_crash` - Disabled graph doesn't crash system
- `test_neo4j_unavailability_handled` - Neo4j failure handled gracefully
- `test_kernel_recovery_after_violation` - System recovers from violations
- `test_kernel_works_without_neo4j` - Kernel is Neo4j-independent
- `test_minimal_mode_configuration_lightweight` - Settings load quickly/lightly
- `test_kernel_import_minimal_overhead` - Kernel import overhead is minimal
- `test_governance_error_isolation` - Errors don't corrupt state

**Pass Criteria**:
- Disabled backends don't crash system
- Kernel works without Neo4j
- System recovers from errors
- Minimal resource overhead
- No cascading failures

## Running the Tests

### Prerequisites

```bash
# Ensure minimal mode is set
export MAHOUN_MODE=desktop_minimal

# Install test dependencies
pip install pytest pytest-cov
```

### Run All Stress Tests

```bash
# Run all tests with verbose output
pytest tests/stress/ -v

# Run with coverage
pytest tests/stress/ -v --cov=mahoun.core --cov-report=html

# Run specific test file
pytest tests/stress/test_kernel_ownership.py -v
```

### Run By Category

```bash
# All stress tests (marked with @pytest.mark.stress)
pytest tests/stress/ -m stress -v

# Slow tests only
pytest tests/stress/ -m slow -v

# Integration tests
pytest tests/stress/ -m integration -v
```

### Run Individual Tests

```bash
# Single test
pytest tests/stress/test_kernel_ownership.py::TestKernelIsolation::test_kernel_query_classification_without_reasoning -v

# All tests in a class
pytest tests/stress/test_kernel_ownership.py::TestKernelIsolation -v
```

### Run in Different Environments

```bash
# Desktop minimal mode (default)
export MAHOUN_MODE=desktop_minimal
pytest tests/stress/ -v

# Server full mode (test non-minimal)
export MAHOUN_MODE=server_full
pytest tests/stress/ -v
```

## Test Evidence & Validation

### What Tests Measure

1. **Kernel Integrity**: Query classification, violation detection, context isolation
2. **Governance Enforcement**: Boundary enforcement, lock immutability, authorization checks
3. **Dependency Cleanliness**: No reverse deps, no circular imports, layer boundaries
4. **Configuration Accuracy**: Settings match environment, backends configured correctly
5. **Error Recovery**: System continues after errors, no state corruption
6. **Resource Efficiency**: Minimal overhead, fast loading, low memory usage

### Observation Points

For each test, observe:
- **Error messages**: Are they informative?
- **Logs**: Does system log violations?
- **State changes**: Is state consistent before/after?
- **Resource usage**: Memory, module count, import time
- **Recovery**: Can system recover from errors?

### Pass/Fail Criteria

Tests use `assert` statements with clear messages:

```python
assert result == expected, f"Got {result}, expected {expected}"
assert isinstance(obj, Type), f"Got {type(obj)}, expected Type"
assert not is_governance_authorized(), "Authority should be reset"
```

All tests must pass with zero exceptions or warnings.

## Interpreting Results

### Success Output

```
tests/stress/test_kernel_ownership.py::TestKernelIsolation::test_kernel_query_classification_without_reasoning PASSED
tests/stress/test_kernel_ownership.py::TestKernelIsolation::test_kernel_context_authority_isolation PASSED
...
========================= 50 passed in 3.24s ==========================
```

### Failure Output

```
FAILED tests/stress/test_kernel_ownership.py::TestKernelIsolation::test_kernel_mutation_boundary_enforcement
AssertionError: Authorization context was not properly isolated
...
```

### Common Issues

1. **Import errors**: Verify Python path and dependencies installed
2. **Environment not set**: Check `MAHOUN_MODE=desktop_minimal`
3. **Cache issues**: Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`
4. **Module conflicts**: Verify no conflicting test configuration

## Extending the Tests

### Adding New Stress Tests

```python
# tests/stress/test_new_category.py

class TestNewStressCategory:
    """
    **Objective**: Verify some architectural property.
    
    **Expected Evidence**: 
    - Some condition holds
    - Some metric meets threshold
    """

    def test_specific_property(self):
        """
        **Setup**: Initial conditions
        **Execution**: Actions
        **Observation**: Metrics captured
        **Pass Criteria**: Conditions met
        """
        # Test implementation
        assert condition, "Condition must hold"
```

### Adding New Fixtures

```python
# In conftest.py

@pytest.fixture
def new_component():
    """Provide access to new component."""
    from some.module import Component
    return Component()
```

## Performance Baseline

For desktop_minimal mode:

- Kernel import: < 50ms
- Runtime settings load: < 100ms
- Query classification: < 1ms per query
- Context authority switch: < 1μs

If these baselines are exceeded, investigate:
- New module imports in hot path
- Configuration parsing overhead
- Unexpected initialization

## Troubleshooting

### Tests Hang

Check for:
- Deadlocks in mocked components
- Infinite loops in mocked functions
- Neo4j connection attempts (use mocks)

### Tests Fail Due to Import Errors

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Check imports work
python -c "from mahoun.core.governance_kernel.kernel import KernelMutationBoundary; print('OK')"
```

### Configuration Issues

```bash
# Verify environment
echo $MAHOUN_MODE
echo $MAHOUN_GRAPH_ENABLED

# Reset environment
unset MAHOUN_MODE
unset MAHOUN_GRAPH_ENABLED
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Stress Tests

on: [push, pull_request]

jobs:
  stress-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/stress/ -v --tb=short
        env:
          MAHOUN_MODE: desktop_minimal
```

## Related Documentation

- `GEMINI.md` - Agent system design
- `constitution/` - Governance rules
- `mahoun/core/governance_kernel/kernel.py` - Kernel implementation
- `mahoun/core/runtime_config.py` - Runtime configuration
- `tests/governance/` - Existing governance tests

## Key Takeaways

1. **Kernel must remain independent**: No external deps, works standalone
2. **Governance is non-bypassable**: Violations always caught and logged
3. **Dependencies are one-way**: Only downward through layers
4. **Degradation is controlled**: System continues with reduced functionality
5. **Agents cannot break contracts**: Refactors don't violate core guarantees

## Contact & Questions

For questions about stress tests:
- Check test docstrings for specific test purposes
- Review conftest.py for shared fixtures
- Examine kernel.py for governance enforcement details
