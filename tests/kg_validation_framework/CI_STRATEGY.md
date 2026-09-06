# CI Integration Strategy for KG Validation Framework
====================================================

## Overview

This document describes the CI/CD integration strategy for the comprehensive 10-phase validation framework for the Persian Legal Knowledge Graph construction system.

## Test Phase Execution Strategy

### Phase 1-2: Input Data & Extraction Validation (Every PR)
- **Files**: `phase_01_input_validation/`, `phase_02_extraction/`
- **Markers**: `@pytest.mark.p0_critical`, `@pytest.mark.unit`
- **Execution**: Run on every pull request before merge
- **Blocking**: Yes - failures block PR merge
- **Duration**: Fast (< 5 minutes)
- **Dependencies**: No external dependencies (unit tests only)

**Rationale**: These tests validate the foundation of the pipeline. Corrupted input or extraction errors will corrupt the entire knowledge graph.

### Phase 3-4: Identity & Ontology Validation (Nightly)
- **Files**: `phase_03_identity/`, `phase_04_ontology/`
- **Markers**: `@pytest.mark.p1_high`, `@pytest.mark.unit`
- **Execution**: Run nightly at 2 AM UTC
- **Blocking**: No - creates alerts but doesn't block
- **Duration**: Medium (< 15 minutes)
- **Dependencies**: No external dependencies

**Rationale**: These tests validate identity management and ontology correctness. Critical but less likely to break on small changes.

### Phase 5: Neo4j Graph Integrity (Nightly with Neo4j)
- **Files**: `phase_05_graph_integrity/`
- **Markers**: `@pytest.mark.p1_high`, `@pytest.mark.integration`
- **Execution**: Run nightly with Neo4j service
- **Blocking**: No - creates alerts
- **Duration**: Medium (< 20 minutes)
- **Dependencies**: Neo4j database

**Rationale**: Graph integrity tests require a real Neo4j instance. These validate the actual graph state.

### Phase 6-7: Semantic & Temporal Validation (Weekly)
- **Files**: `phase_06_semantic/`, `phase_07_temporal/`
- **Markers**: `@pytest.mark.p2_medium`, `@pytest.mark.integration`
- **Execution**: Run weekly on Sunday at 3 AM UTC
- **Blocking**: No - creates alerts
- **Duration**: Long (< 30 minutes)
- **Dependencies**: Neo4j database

**Rationale**: Semantic and temporal validation is comprehensive but changes infrequently. Weekly execution is sufficient.

### Phase 8-10: Idempotency, Query, Adversarial (Monthly)
- **Files**: `phase_08_idempotency/`, `phase_09_query/`, `phase_10_adversarial/`
- **Markers**: `@pytest.mark.p3_low`, `@pytest.mark.slow`, `@pytest.mark.integration`
- **Execution**: Run monthly on 1st at 4 AM UTC
- **Blocking**: No - creates alerts
- **Duration**: Long (< 60 minutes)
- **Dependencies**: Neo4j database

**Rationale**: These are comprehensive regression tests that validate edge cases, security properties, and long-term stability.

## GitHub Actions Workflow

```yaml
name: KG Validation Framework

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
  # Phase 1-2: Every PR
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
      - name: Run Phase 1 tests
        run: |
          pytest tests/kg_validation_framework/phase_01_input_validation/ -v --tb=short
      - name: Run Phase 2 tests
        run: |
          pytest tests/kg_validation_framework/phase_02_extraction/ -v --tb=short
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  # Phase 3-4: Nightly
  p1-high:
    name: P1 High Priority Tests (Nightly)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' && github.event.schedule == '0 2 * * *'
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
      - name: Run Phase 3 tests
        run: |
          pytest tests/kg_validation_framework/phase_03_identity/ -v --tb=short
      - name: Run Phase 4 tests
        run: |
          pytest tests/kg_validation_framework/phase_04_ontology/ -v --tb=short

  # Phase 5: Nightly with Neo4j
  p1-integration:
    name: P1 Integration Tests (Nightly with Neo4j)
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule' && github.event.schedule == '0 2 * * *'
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
      - name: Run Phase 5 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
        run: |
          pytest tests/kg_validation_framework/phase_05_graph_integrity/ -v --tb=short -m integration

  # Phase 6-7: Weekly
  p2-medium:
    name: P2 Medium Priority Tests (Weekly)
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
      - name: Run Phase 6 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_validation_framework/phase_06_semantic/ -v --tb=short -m integration -m slow
      - name: Run Phase 7 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_validation_framework/phase_07_temporal/ -v --tb=short -m integration -m slow

  # Phase 8-10: Monthly
  p3-full:
    name: P3 Full Regression Tests (Monthly)
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
      - name: Run Phase 8 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_validation_framework/phase_08_idempotency/ -v --tb=short -m integration -m slow
      - name: Run Phase 9 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_validation_framework/phase_09_query/ -v --tb=short -m integration -m slow
      - name: Run Phase 10 tests
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          DB_NEO4J_PASSWORD: test_password
          MAHOUN_INTEGRATION: 1
          MAHOUN_SLOW: 1
        run: |
          pytest tests/kg_validation_framework/phase_10_adversarial/ -v --tb=short -m integration -m slow
```

## Local Development Execution

### Quick Test (Unit Tests Only)
```bash
# Run Phase 1-2 (fast, no Neo4j)
pytest tests/kg_validation_framework/phase_01_input_validation/ -v
pytest tests/kg_validation_framework/phase_02_extraction/ -v

# Run specific phase
pytest tests/kg_validation_framework/phase_03_identity/ -v
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

pytest tests/kg_validation_framework/phase_05_graph_integrity/ -v -m integration
```

### Full Test Suite
```bash
# Run all tests (requires Neo4j)
export MAHOUN_INTEGRATION=1
export MAHOUN_SLOW=1

pytest tests/kg_validation_framework/ -v
```

### Run by Priority
```bash
# Run only P0 critical tests
pytest tests/kg_validation_framework/ -v -m p0_critical

# Run only P1 high priority tests
pytest tests/kg_validation_framework/ -v -m p1_high

# Run only P2 medium priority tests
pytest tests/kg_validation_framework/ -v -m p2_medium

# Run only P3 low priority tests
pytest tests/kg_validation_framework/ -v -m p3_low
```

## Test Isolation and Cleanup

### Fixture Isolation
- Each test uses fresh fixtures from `fixtures/neo4j_fixtures.py`
- Unit tests use mock objects
- Integration tests use isolated Neo4j database
- Fixtures automatically clean up after test completion

### Database Cleanup
```python
# Automatic cleanup in fixtures
yield conn
# Cleanup: clear all data
conn.execute_query("MATCH (n) DETACH DELETE n")
```

## Failure Handling

### Blocking Failures
- P0 Critical tests (Phase 1-2) block PR merge
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
  - name: KG Input Data Validation Failure
    condition: p0-critical == failure
    action: create_issue, notify_team, block_pr
  
  - name: KG Graph Integrity Failure
    condition: p1-integration == failure
    action: slack_alert, create_ticket
  
  - name: KG Semantic Consistency Failure
    condition: p2-medium == failure
    action: slack_alert, log_incident
```

## Performance Considerations

### Test Parallelization
- Unit tests run in parallel by default
- Integration tests run sequentially to avoid Neo4j contention
- Use `pytest-xdist` for parallel unit test execution:
  ```bash
  pytest tests/kg_validation_framework/phase_01_input_validation/ -n auto
  ```

### Neo4j Resource Management
- Use lightweight Neo4j Docker image for CI
- Limit memory allocation: `NEO4J_dbms_memory_heap_max__size=512m`
- Clean database between test suites
- Use test-specific databases when possible

### Timeout Configuration
```ini
# pytest.ini
[pytest]
timeout = 300  # 5 minute timeout per test
timeout_method = thread
```

## Coverage Requirements

### Minimum Coverage Targets
- Phase 1-2: 100% coverage of input validation and extraction code
- Phase 3-4: 90% coverage of identity and ontology code
- Phase 5: 80% coverage of graph schema code
- Phase 6-7: 70% coverage of semantic and temporal code
- Phase 8-10: 60% coverage of edge case handlers

### Coverage Reporting
```bash
# Generate coverage report
pytest tests/kg_validation_framework/ --cov=mahoun --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Security Considerations

### Credential Management
- Never commit real Neo4j passwords
- Use environment variables or secrets management
- CI uses test-only credentials
- Production credentials in GitHub Secrets

### Adversarial Test Safety
- Adversarial injection tests use isolated test database
- No production data used in injection tests
- Tests validate rejection of malicious input, don't execute it
- SQL/script injection patterns are detected but not executed

## Monitoring and Reporting

### Test Metrics Tracking
- Test execution time per phase
- Failure rate per test category
- Flaky test detection
- Coverage trends over time
- Graph fingerprint stability

### Dashboard Configuration
```yaml
# Example metrics dashboard
metrics:
  - name: KG Validation Pass Rate
    query: pass_rate / total_tests
    target: > 95%
  
  - name: KG Test Duration
    query: avg_execution_time
    target: < 10 minutes for P0
  
  - name: KG Graph Fingerprint Stability
    query: fingerprint_changes / total_runs
    target: = 0 (no unexpected changes)
```

## Success Criteria

The Knowledge Graph construction system is considered ready for reasoning engine integration when:

1. All Phase 1-2 tests pass on every PR
2. All Phase 3-5 tests pass in nightly builds for 7 consecutive days
3. All Phase 6-7 tests pass in weekly builds for 4 consecutive weeks
4. All Phase 8-10 tests pass in monthly regression
5. Graph fingerprint is reproducible across 10 consecutive builds
6. No silent failures detected in any phase
7. All legal invariants are protected by tests
8. Coverage targets are met for all phases

## Failure Response Protocol

When a test fails:

1. **Block Integration**: Do not proceed with reasoning engine integration
2. **Root Cause Analysis**: Identify the source of the failure
3. **Fix the Defect**: Fix the underlying issue in the construction system
4. **Validate Fix**: Re-run the full test suite
5. **Update Documentation**: Document the fix and lessons learned
6. **Add Regression Test**: If applicable, add test to prevent recurrence

## Maintenance

### Test Updates
- Review and update tests when schema changes
- Add new tests for new features
- Remove obsolete tests when features are deprecated
- Update fixtures to match current data structures
- Update sample invalid datasets as needed

### Regular Review
- Monthly review of all test failures
- Quarterly review of test coverage
- Annual review of test strategy and priorities
- Update CI strategy as needed based on learnings

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
1. Stop all ingestions immediately
2. Identify corruption source
3. Restore from last known good fingerprint
4. Run full adversarial test suite
5. Resume ingestion only after all tests pass
