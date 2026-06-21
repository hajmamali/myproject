# Test Structure

## Overview

The Mahoun platform uses a comprehensive testing strategy combining unit tests, property-based tests, contract tests, and integration tests. This document explains the test organization, how to run different test categories, and how tests relate to our CI pipeline.

## Directory Structure

```
tests/
├── contracts/              # Contract validation tests
│   ├── test_*_contracts.py # Schema and interface contract tests
│   └── __init__.py
├── integration/            # Integration tests (require external services)
│   └── test_*_integration.py
├── harness/                # Test utilities and fixtures
├── artifacts/              # Test output and generated files
├── test_*.py               # Unit tests (fast, no external dependencies)
├── conftest.py             # Pytest fixtures and configuration
└── README.md               # This file
```

## Test Categories

### Unit Tests
**Location**: `tests/test_*.py` (root level)  
**Purpose**: Fast, isolated tests with no external dependencies  
**Run**: `pytest tests/ -v` (default)

Unit tests verify specific functionality in isolation:
- Core business logic
- Data transformations
- Error handling
- Edge cases

**Example**:
```python
def test_evidence_linked_verdict_basic():
    """Test basic verdict generation."""
    engine = EvidenceLinkedVerdictEngine(...)
    verdict = engine.generate_verdict("question", ["fact1", "fact2"])
    assert verdict.final_verdict is not None
```

### Property-Based Tests
**Location**: Mixed with unit tests, marked with `@given` decorator  
**Purpose**: Test universal properties across randomized inputs  
**Run**: `pytest tests/ -v` (included in default run)

Property tests use Hypothesis to verify correctness properties:
- Invariants that must hold for all inputs
- Round-trip properties (serialize/deserialize)
- Determinism (same input → same output)

**Example**:
```python
from hypothesis import given, strategies as st

@given(st.lists(st.text()))
def test_dataset_hash_determinism(file_contents):
    """Hash computation is deterministic."""
    hash1 = compute_hash(file_contents)
    hash2 = compute_hash(file_contents)
    assert hash1 == hash2
```

### Contract Tests
**Location**: `tests/contracts/`  
**Purpose**: Validate schemas and interfaces without testing behavior  
**Run**: `pytest tests/contracts/ -v`

Contract tests ensure:
- Pydantic models have required fields
- Type annotations are correct
- Interfaces are properly defined
- No behavior testing (just structure)

**Example**:
```python
def test_verdict_struct_contract():
    """Verify VerdictStruct has required fields."""
    from mahoun.schemas import VerdictStruct
    assert hasattr(VerdictStruct, 'final_verdict')
    assert hasattr(VerdictStruct, 'confidence_score')
```

### Integration Tests
**Location**: `tests/integration/` or marked with `@pytest.mark.integration`  
**Purpose**: Test interactions with external services  
**Run**: `MAHOUN_INTEGRATION=1 pytest tests/ -v -m "integration"`

Integration tests require:
- Neo4j database
- ChromaDB vector store
- External APIs
- LLM services

**These are SKIPPED by default** to keep CI fast.

## Test Markers

Tests can be marked with pytest markers to control execution:

```python
@pytest.mark.integration
def test_neo4j_connection():
    """Requires Neo4j to be running."""
    pass

@pytest.mark.slow
def test_large_dataset_processing():
    """Takes >10 seconds to run."""
    pass
```

**Available markers**:
- `integration`: Requires external services (skipped by default)
- `slow`: Takes significant time (skipped by default)
- `unit`: Fast tests with no dependencies (default)

## Running Tests

### Quick Commands

```bash
# Default: Fast unit tests only (90s timeout)
pytest tests/ -v

# With coverage report
pytest tests/ --cov=mahoun --cov-report=html

# Run specific test file
pytest tests/test_evidence_linked_verdict.py -v

# Run specific test function
pytest tests/test_agents.py::test_doc_parser_agent -v

# Run tests matching pattern
pytest tests/ -k "verdict" -v
```

### Environment-Specific Tests

```bash
# Integration tests (requires Neo4j, ChromaDB, etc.)
MAHOUN_INTEGRATION=1 pytest tests/ -v -m "integration"

# Slow tests (large data, heavy computation)
MAHOUN_SLOW=1 pytest tests/ -v -m "slow"

# All tests (unit + integration + slow)
MAHOUN_INTEGRATION=1 MAHOUN_SLOW=1 pytest tests/ -v
```

### Debugging Tests

```bash
# Show print statements and detailed output
pytest tests/ -v -s

# Stop on first failure
pytest tests/ --maxfail=1

# Show local variables on failure
pytest tests/ -v -l

# Run last failed tests only
pytest tests/ --lf

# Freeze diagnostics (shows last test + stack on timeout)
PYTHONFAULTHANDLER=1 pytest tests/ -vv -s --maxfail=1
```

## Relationship to CI Gates

Our CI pipeline has 8 mandatory gates (0-7) that run different test categories:

| Gate | Name | Tests Run | Purpose |
|------|------|-----------|---------|
| 0 | Lint | Static analysis | Code quality (ruff, mypy) |
| 1 | Unit | `tests/test_*.py` | Fast unit tests |
| 2 | Behavior | Property tests | Correctness properties |
| 3 | Contracts | `tests/contracts/` | Schema validation |
| 4 | Integration | Integration tests | External services |
| 5 | Security | Security scans | Vulnerability detection |
| 6 | Performance | Stress tests | Performance benchmarks |
| 7 | Architecture | Architecture tests | Design constraints |

**Run all CI gates locally**:
```bash
./scripts/ci_run_first_step.sh
# or
make ci-first-step
```

## Writing New Tests

### Where to Add Tests

1. **Unit test for new function**: Add to existing `test_*.py` or create new file
2. **Property test**: Add to relevant test file with `@given` decorator
3. **Contract test**: Add to `tests/contracts/test_*_contracts.py`
4. **Integration test**: Add to `tests/integration/` or mark with `@pytest.mark.integration`

### Test Naming Conventions

```python
# Unit test
def test_function_name_behavior():
    """Test that function_name does X when Y."""
    pass

# Property test
@given(st.integers())
def test_function_name_property(value):
    """Property: function_name is idempotent."""
    pass

# Contract test
def test_model_name_contract():
    """Verify ModelName has required fields."""
    pass
```

### Test Structure (AAA Pattern)

```python
def test_example():
    """Test description."""
    # Arrange: Set up test data
    engine = create_test_engine()
    facts = ["fact1", "fact2"]
    
    # Act: Execute the code under test
    result = engine.process(facts)
    
    # Assert: Verify the outcome
    assert result.success is True
    assert len(result.steps) > 0
```

## Common Pytest Commands Reference

```bash
# List all tests without running
pytest tests/ --collect-only

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Generate HTML coverage report
pytest tests/ --cov=mahoun --cov-report=html
open htmlcov/index.html

# Run with specific Python warnings
pytest tests/ -W error::DeprecationWarning

# Profile test execution time
pytest tests/ --durations=10

# Run tests modified since last commit
pytest tests/ --picked
```

## Troubleshooting

### Tests Timeout
- Default timeout is 90 seconds for safety
- Use `PYTHONFAULTHANDLER=1` to see where tests hang
- Check for infinite loops or blocking I/O

### Import Errors
- Ensure you're in the project root directory
- Check that `mahoun` package is installed: `pip install -e .`
- Verify PYTHONPATH includes project root

### Fixture Not Found
- Check `conftest.py` for fixture definitions
- Ensure fixture scope matches test requirements
- Look for typos in fixture names

### Integration Tests Fail
- Verify external services are running (Neo4j, ChromaDB)
- Check environment variables (NEO4J_URI, etc.)
- Ensure network connectivity

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [CI Gates Documentation](../ci/first_step/STAGES.md)
- [Contributing Guidelines](../CONTRIBUTING.md)

---

**Last Updated**: 2025-02-14
