# CI Execution Strategy for Persian Legal Knowledge Graph Adversarial Tests

## Overview

This document describes the CI/CD execution strategy for the adversarial test suite for the Persian Legal Knowledge Graph. The strategy ensures comprehensive validation while optimizing for CI resource usage.

## Test Categories and Priority

### P0 Critical Tests (Every PR)
- **test_01_structural_integrity.py**: Orphan detection, topology validation, duplicates, constraints
- **test_02_ontology_validation.py**: Relationship direction, node type correctness, property completeness
- **Markers**: `@pytest.mark.p0_critical`

**Execution**: Run on every pull request before merge. Blocking failures.

**Rationale**: These tests detect fundamental graph corruption that would make the KG unusable for legal reasoning.

### P1 Integration Tests (Nightly)
- **test_03_reference_integrity.py**: Reference existence, direction, cross-law validity
- **test_05_semantic_consistency.py**: Relation semantics, legal priority, exception handling
- **Markers**: `@pytest.mark.p1_integration`, `@pytest.mark.integration`

**Execution**: Run nightly in CI with full Neo4j instance. Non-blocking but alerts on failure.

**Rationale**: These tests require Neo4j and validate complex semantic relationships that are critical but less likely to break on small changes.

### P2 Extended Tests (Weekly)
- **test_04_temporal_version_integrity.py**: Amendment tracking, repealed laws, version management
- **test_06_data_quality.py**: Persian text normalization, Unicode issues, data quality
- **Markers**: `@pytest.mark.p2_extended`, `@pytest.mark.integration`

**Execution**: Run weekly full regression. Non-blocking but requires investigation.

**Rationale**: These tests validate temporal integrity and data quality which are important but change infrequently.

### P3 Full Tests (Monthly)
- **test_07_idempotency.py**: Ingestion idempotency, deterministic construction
- **test_08_adversarial_injection.py**: Malicious input handling, injection attacks
- **test_09_graph_fingerprint.py**: Fingerprinting, reproducibility
- **test_10_query_capability.py**: Complex query validation
- **Markers**: `@pytest.mark.p3_full`, `@pytest.mark.slow`

**Execution**: Run monthly comprehensive regression. Non-blocking but requires investigation.

**Rationale**: These tests are resource-intensive and validate edge cases and security properties.

## CI Pipeline Configuration

### GitHub Actions Workflow

```yaml
name: KG Adversarial Tests

on:
  pull_request:
    branches: [main, develop]
  schedule:
    # Nightly at 2 AM UTC
    - cron: '0 2 * * *'
    # Weekly on Sunday at 3 AM UTC
    - cron: '0 3 * * 0'
    # Monthly on 1st at 4 AM UTC
    - cron: '0 4 1 * *'

jobs:
  p0-critical:
    name: P0 Critical Tests (Every PR)
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run P0 tests
        run: |
          pytest tests/kg_adversarial/test_01_structural_integrity.py \
                 tests/kg_adversarial/test_02_ontology_validation.py \
                 -v --tb=short --cov=mahoun --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  p1-integration:
    name: P1 Integration Tests (Nightly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    services:
      neo4j:
        image: neo4j:5.18
        env:
          NEO4J_AUTH: neo4j/test_password
        ports:
          - 7687:7687
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run P1 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
        run: |
          pytest tests/kg_adversarial/test_03_reference_integrity.py \
                 tests/kg_adversarial/test_05_semantic_consistency.py \
                 -v --tb=short -m integration

  p2-extended:
    name: P2 Extended Tests (Weekly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' && github.event.schedule == '0 3 * * 0'
    services:
      neo4j:
        image: neo4j:5.18
        env:
          NEO4J_AUTH: neo4j/test_password
        ports:
          - 7687:7687
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run P2 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_adversarial/test_04_temporal_version_integrity.py \
                 tests/kg_adversarial/test_06_data_quality.py \
                 -v --tb=short -m integration -m slow

  p3-full:
    name: P3 Full Tests (Monthly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' && github.event.schedule == '0 4 1 * *'
    services:
      neo4j:
        image: neo4j:5.18
        env:
          NEO4J_AUTH: neo4j/test_password
        ports:
          - 7687:7687
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run P3 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_adversarial/test_07_idempotency.py \
                 tests/kg_adversarial/test_08_adversarial_injection.py \
                 tests/kg_adversarial/test_09_graph_fingerprint.py \
                 tests/kg_adversarial/test_10_query_capability.py \
                 -v --tb=short -m integration -m slow
```

## Local Development Execution

### Quick Test (Unit Tests Only)
```bash
# Run unit tests without Neo4j
pytest tests/kg_adversarial/test_06_data_quality.py::TestUTF8Integrity -v
```

### Integration Tests (With Neo4j)
```bash
# Start Neo4j locally
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export DB_NEO4J_PASSWORD=test_password
export MAHOUN_INTEGRATION=1

pytest tests/kg_adversarial/ -v -m integration
```

### Full Test Suite
```bash
# Run all tests (requires Neo4j)
export MAHOUN_INTEGRATION=1
export MAHOUN_SLOW=1

pytest tests/kg_adversarial/ -v
```

### Specific Test Category
```bash
# Run only structural integrity tests
pytest tests/kg_adversarial/test_01_structural_integrity.py -v

# Run only ontology validation tests
pytest tests/kg_adversarial/test_02_ontology_validation.py -v
```

## Test Isolation and Cleanup

### Fixture Isolation
- Each test uses a fresh Neo4j database via `neo4j_empty_graph` fixture
- Fixtures automatically clean up after test completion
- No test pollution between test cases

### Database Cleanup
```python
# Automatic cleanup in fixtures
yield conn
# Cleanup: clear all data
conn.execute_query("MATCH (n) DETACH DELETE n")
```

## Failure Handling

### Blocking Failures
- P0 Critical tests block PR merge
- Any failure requires immediate investigation
- Failures create GitHub issues automatically

### Non-Blocking Failures
- P1, P2, P3 tests create alerts but don't block
- Failures are logged and tracked
- Weekly review of non-blocking failures

### Alert Configuration
```yaml
# Example alert configuration
alerts:
  - name: KG Structural Integrity Failure
    condition: p0-critical == failure
    action: create_issue, notify_team
  
  - name: KG Reference Integrity Failure
    condition: p1-integration == failure
    action: slack_alert, create_ticket
```

## Performance Considerations

### Test Parallelization
- Unit tests run in parallel by default
- Integration tests run sequentially to avoid Neo4j contention
- Use `pytest-xdist` for parallel unit test execution:
  ```bash
  pytest tests/kg_adversarial/test_06_data_quality.py -n auto
  ```

### Neo4j Resource Management
- Use lightweight Neo4j Docker image for CI
- Limit memory allocation: `NEO4J_dbms_memory_heap_max__size=512m`
- Clean database between test suites

### Timeout Configuration
```ini
# pytest.ini
[pytest]
timeout = 300  # 5 minute timeout per test
timeout_method = thread
```

## Coverage Requirements

### Minimum Coverage Targets
- P0 Critical: 100% coverage of graph schema code
- P1 Integration: 90% coverage of graph query code
- P2 Extended: 80% coverage of data processing code
- P3 Full: 70% coverage of edge case handlers

### Coverage Reporting
```bash
# Generate coverage report
pytest tests/kg_adversarial/ --cov=mahoun/graph --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Security Considerations

### Credential Management
- Never commit real Neo4j passwords
- Use environment variables or secrets management
- CI uses test-only credentials

### Injection Test Safety
- Adversarial injection tests use isolated test database
- No production data used in injection tests
- Tests validate rejection of malicious input, don't execute it

## Monitoring and Reporting

### Test Metrics Tracking
- Test execution time per category
- Failure rate per test category
- Flaky test detection
- Coverage trends over time

### Dashboard Configuration
```yaml
# Example metrics dashboard
metrics:
  - name: KG Test Pass Rate
    query: pass_rate / total_tests
    target: > 95%
  
  - name: KG Test Duration
    query: avg_execution_time
    target: < 10 minutes for P0
```

## Maintenance

### Test Updates
- Review and update tests when schema changes
- Add new tests for new features
- Remove obsolete tests when features are deprecated
- Update fixtures to match current data structures

### Regular Review
- Monthly review of test failures
- Quarterly review of test coverage
- Annual review of test strategy and priorities

## Rollback Strategy

### Test Rollback
If a test suite is consistently failing:
1. Identify the root cause
2. Fix the underlying issue (preferred)
3. If issue is in test, mark test as `@pytest.mark.skip` with explanation
4. Create issue to fix the test
5. Remove skip once issue is resolved

### Graph Rollback
If graph corruption is detected:
1. Stop all ingestions
2. Identify corruption source
3. Restore from last known good fingerprint
4. Run full adversarial test suite
5. Resume ingestion only after all tests pass
