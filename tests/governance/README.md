# Governance Test Suite

This directory contains comprehensive tests for the MAHOUN governance subsystem.

## Overview

The governance subsystem includes:
- **GovernanceLock**: Immutable governance enforcement
- **FortressValidator**: Forensic validation of reasoning responses
- **GovernanceContext**: Runtime context enforcement
- **ProvenanceAttestation**: Cryptographic integrity for provenance
- **ProvenanceChain**: Lineage tracking and verification
- **FortressProtectedReasoningService**: Automatic validation wrapper
- **API Integration**: Proof-carrying response validation

## Test Files

### Core Component Tests

#### `test_governance_lock.py`
Tests for GovernanceLock immutable governance enforcement.

**Coverage**:
- Mode immutability (cannot change after initialization)
- Forensic logging (bypass attempts logged)
- Fail-closed behavior (defaults to STRICT)
- Cryptographic authorization (DISABLED mode requires token)
- Immutability verification
- Performance tests

**Run**: `pytest tests/governance/test_governance_lock.py -v`

#### `test_governance_context.py`
Tests for GovernanceContext runtime enforcement.

**Coverage**:
- Context creation and lifecycle
- Context requirement enforcement
- Child context creation
- Attestation generation
- Scope enforcement
- Performance tests

**Run**: `pytest tests/governance/test_governance_context.py -v`

#### `test_provenance_attestation.py`
Tests for ProvenanceAttestation cryptographic integrity.

**Coverage**:
- Attestation creation with hash and signature
- Timestamp internal generation
- Integrity verification
- InferenceProvenance creation
- ProvenanceWithAttestation creation
- ProvenanceChain creation and verification
- Performance tests

**Run**: `pytest tests/governance/test_provenance_attestation.py -v`

#### `test_provenance_chain.py`
Tests for ProvenanceChain lineage tracking.

**Coverage**:
- Chain creation
- Lineage parent auto-setting
- Chain verification
- Integrity validation
- Performance tests

**Run**: `pytest tests/governance/test_provenance_chain.py -v`

### Integration Tests

#### `test_fortress_protected_service.py`
Tests for FortressProtectedReasoningService automatic validation.

**Coverage**:
- Reasoning execution with validation
- Batch reasoning
- Statistics tracking
- Health checks
- Decorator functionality
- Performance tests

**Run**: `pytest tests/governance/test_fortress_protected_service.py -v`

#### `test_api_integration.py`
Tests for API integration with proof-carrying responses.

**Coverage**:
- Verdict generation endpoint
- Verdict verification endpoint
- Ledger query endpoint
- Health check endpoint
- Error handling
- Proof-carrying response validation
- Performance tests

**Run**: `pytest tests/governance/test_api_integration.py -v`

## Running Tests

### Run All Governance Tests
```bash
pytest tests/governance/ -v
```

### Run Specific Test File
```bash
pytest tests/governance/test_governance_lock.py -v
```

### Run Specific Test Class
```bash
pytest tests/governance/test_governance_lock.py::TestModeImmutability -v
```

### Run Specific Test
```bash
pytest tests/governance/test_governance_lock.py::TestModeImmutability::test_initialization_sets_mode -v
```

### Run with Coverage
```bash
pytest tests/governance/ --cov=mahoun --cov-report=html
```

### Run with Performance Tracking
```bash
pytest tests/governance/ -v --durations=10
```

### Run Only Fast Tests
```bash
pytest tests/governance/ -v -m "not slow"
```

## Test Fixtures

### Shared Fixtures (conftest.py)

#### `reset_governance_lock`
Auto-used fixture that resets GovernanceLock before each test.

#### `valid_response`
Creates a valid ReasoningResponse that passes all FortressValidator checks.

#### `validator`
Creates a FortressValidator instance in strict mode.

#### `governance_context`
Creates a GovernanceContext instance.

#### `provenance_attestation`
Creates a ProvenanceAttestation instance.

#### `inference_provenance`
Creates an InferenceProvenance instance.

#### `provenance_chain`
Creates a ProvenanceChain instance.

## Test Results

See [TEST_RESULTS.md](./TEST_RESULTS.md) for detailed test results.

**Current Status**:
- **Total Tests**: 142
- **Passed**: 107 (75%)
- **Failed**: 35 (25%)

## Known Issues

### 1. GovernanceContext.require_provenance()
Missing required parameters `governance_scope_id` and `runtime_attestation_id`.

**Fix**: Update method signature in `mahoun/core/governance/governance_context.py`

### 2. Child Context Lineage
Lineage not properly inherited in child contexts.

**Fix**: Update `create_child_context()` to properly append to lineage

### 3. Frozen Dataclass Modification
Cannot modify frozen attestation for testing broken lineage.

**Fix**: Use `dataclasses.replace()` or create new instance

### 4. FortressProtectedService Integration
GovernanceContext not properly integrated.

**Fix**: Fix context manager usage in `mahoun/reasoning/fortress_integration.py`

### 5. API Test Client
TestClient not properly configured.

**Fix**: Setup proper test fixtures and dependencies

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_<component>_<scenario>.py`
2. **Use descriptive test names**: `test_<action>_<expected_result>`
3. **Add docstrings**: Explain what the test validates
4. **Use fixtures**: Reuse shared fixtures from conftest.py
5. **Test edge cases**: Include error handling and boundary conditions
6. **Add performance tests**: For critical paths
7. **Update documentation**: Update this README with new tests

## Test Categories

### Unit Tests
Test individual components in isolation.

### Integration Tests
Test components working together.

### Performance Tests
Test performance characteristics (marked with `@pytest.mark.slow`).

### Security Tests
Test security bypass prevention.

### Determinism Tests
Test deterministic behavior.

## CI/CD Integration

These tests are run automatically in CI/CD pipeline:

```yaml
# .github/workflows/04-quality-gates.yml
- name: Run Governance Tests
  run: |
    pytest tests/governance/ --cov=mahoun --cov-fail-under=95
```

## References

- [Governance Integration Spec](../../.kiro/specs/governance-integration/)
- [Governance Test Suite Spec](../../.kiro/specs/governance-test-suite/)
- [MAHOUN Rules](../../.kiro/steering/rules.md)
- [Kiro Rules](../../.kiro/steering/kirorules.md)
