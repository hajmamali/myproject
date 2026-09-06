# Persian Legal Knowledge Graph - Validation Framework
========================================================

## Quick Start

### Run All Tests
```bash
# Phase 1-2 (Fast, no Neo4j)
pytest tests/kg_validation_framework/phase_01_input_validation/ -v
pytest tests/kg_validation_framework/phase_02_extraction/ -v

# Phase 3-5 (Requires Neo4j)
export MAHOUN_INTEGRATION=1
pytest tests/kg_validation_framework/phase_03_identity/ -v
pytest tests/kg_validation_framework/phase_04_ontology/ -v
pytest tests/kg_validation_framework/phase_05_graph_integrity/ -v

# Phase 6-8 (Comprehensive)
pytest tests/kg_validation_framework/phase_06_semantic/ -v
pytest tests/kg_validation_framework/phase_07_temporal/ -v
pytest tests/kg_validation_framework/phase_08_idempotency/ -v

# Phase 9-10 (Full Regression)
pytest tests/kg_validation_framework/phase_09_query/ -v
pytest tests/kg_validation_framework/phase_10_adversarial/ -v
```

### Run Specific Phase
```bash
pytest tests/kg_validation_framework/phase_01_input_validation/ -v
```

### Run with Coverage
```bash
pytest tests/kg_validation_framework/ --cov=mahoun --cov-report=html
```

## Test Structure

Each phase is a separate directory with focused tests:

- **phase_01_input_validation**: Raw document validation
- **phase_02_extraction**: Pipeline transformation validation
- **phase_03_identity**: Entity deduplication validation
- **phase_04_ontology**: Schema and ontology validation
- **phase_05_graph_integrity**: Neo4j graph state validation
- **phase_06_semantic**: Relationship semantics validation
- **phase_07_temporal**: Temporal consistency validation
- **phase_08_idempotency**: Determinism and reproducibility
- **phase_09_query**: Query capability validation
- **phase_10_adversarial**: Failure mode validation

## Fixtures

Located in `fixtures/`:
- `neo4j_fixtures.py`: Neo4j connection and graph fixtures
- `sample_valid_data.py`: Valid legal document samples
- `sample_invalid_data.py`: Invalid/corrupted document samples
- `corrupted_graphs.py`: Pre-corrupted graph states for testing

## Cypher Queries

Reusable Cypher validation queries in `cypher_queries/`:
- `structural_queries.py`: Graph structure validation
- `semantic_queries.py`: Semantic relationship validation
- `temporal_queries.py`: Temporal consistency validation

## CI Integration

See `CI_STRATEGY.md` for detailed CI/CD integration strategy.

## Test Markers

- `@pytest.mark.p0_critical`: Critical path tests (every PR)
- `@pytest.mark.p1_high`: High priority tests (nightly)
- `@pytest.mark.p2_medium`: Medium priority tests (weekly)
- `@pytest.mark.p3_low`: Low priority tests (monthly)
- `@pytest.mark.integration`: Requires Neo4j
- `@pytest.mark.slow`: Long-running tests

## Failure Response

If a test fails:
1. Do not proceed with reasoning engine integration
2. Investigate root cause
3. Fix the underlying issue
4. Re-run full test suite
5. Document the fix
