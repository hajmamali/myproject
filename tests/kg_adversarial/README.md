# Persian Legal Knowledge Graph - Adversarial Test Suite

## Purpose

This test suite aggressively validates the structural correctness, semantic coherence, determinism, and safety of the Persian Legal Knowledge Graph before integration with the reasoning system.

## Testing Philosophy

- **Failure detection over happy path validation**: Tests are designed to detect defects, not just confirm things work
- **Legal invariants**: Every test protects a specific legal or architectural invariant
- **No superficial smoke tests**: Every test proves something meaningful about graph integrity
- **Real Neo4j where possible**: Avoid mocks unless absolutely necessary
- **Isolated and reproducible**: Each test is independent and deterministic

## Test Categories

### 1. Structural Integrity Tests (`test_01_structural_integrity.py`)
- Orphan node detection (Article without Law, Chapter without parent, etc.)
- Invalid graph topology (impossible relationship directions, circular dependencies)
- Duplicate entity problems (duplicate Laws, Articles, same entity with multiple IDs)
- Constraint violations (missing uniqueness constraints, non-deterministic identifiers)

**Invariant protected**: Graph topology must reflect legal hierarchy and prevent data corruption.

**Failure danger**: Orphan nodes cause incomplete legal reasoning; duplicates create contradictory results.

### 2. Legal Ontology Validation Tests (`test_02_ontology_validation.py`)
- Relationship direction correctness (Law → Chapter → Article → Paragraph → Clause)
- Node type correctness (no semantic misuse of labels)
- Property completeness (mandatory properties present)
- No semantic misuse (Amendment treated as original law, precedent as legislation)

**Invariant protected**: Ontology must correctly represent Persian legal hierarchy.

**Failure danger**: Incorrect hierarchy leads to wrong legal precedence and invalid conclusions.

### 3. Reference Integrity Tests (`test_03_reference_integrity.py`)
- Target article existence verification
- Target law existence verification
- Reference direction correctness
- Cross-law reference validity
- Detection of false/missing/self/impossible references

**Invariant protected**: All legal references must resolve to existing, valid entities.

**Failure danger**: Broken references cause legal reasoning to reference non-existent laws.

### 4. Temporal and Version Integrity Tests (`test_04_temporal_version_integrity.py`)
- Amendment tracking
- Repealed law handling
- Historical version management
- Effective date validation
- Detection of future laws, repealed articles treated as current, version conflicts

**Invariant protected**: Temporal state must be consistent and deterministic.

**Failure danger**: Incorrect temporal state leads to applying repealed or future laws incorrectly.

### 5. Semantic Consistency Tests (`test_05_semantic_consistency.py`)
- Relation semantics validation (OVERRIDDEN_BY, REPLACED_BY, INTERPRETED_BY)
- Legal priority correctness
- Exception handling validation
- Precedence correctness

**Invariant protected**: Relationships must represent legal meaning correctly.

**Failure danger**: Incorrect semantics cause wrong legal priority and invalid rule application.

### 6. Data Quality Tests (`test_06_data_quality.py`)
- Persian text normalization
- Unicode issues (Arabic/Persian character confusion)
- Invisible character detection
- Duplicate whitespace
- Incorrect numbering formats
- Broken UTF-8 content

**Invariant protected**: Text data must be clean, normalized, and searchable.

**Failure danger**: Text corruption causes search failures and incorrect matching.

### 7. Idempotency Tests (`test_07_idempotency.py`)
- Multiple ingestion runs
- Node count verification
- Relationship count verification
- No duplication allowed
- Deterministic graph construction

**Invariant protected**: Graph construction must be idempotent and deterministic.

**Failure danger**: Non-idempotent ingestion causes data corruption and inconsistency.

### 8. Adversarial Injection Tests (`test_08_adversarial_injection.py`)
- Fake article numbers
- Duplicate laws
- Incorrect references
- Invalid dates
- Empty mandatory fields
- Malformed legal text

**Invariant protected**: Graph builder must fail safely on malicious/corrupted input.

**Failure danger**: Malicious input can corrupt the entire graph or cause security issues.

### 9. Graph Fingerprint Tests (`test_09_graph_fingerprint.py`)
- Node count fingerprinting
- Relationship count fingerprinting
- Label fingerprinting
- Relationship type fingerprinting
- Hash of canonical properties
- Reproducibility verification

**Invariant protected**: Graph state must be verifiable and reproducible.

**Failure danger**: Undetected graph changes cause inconsistent legal reasoning across deployments.

### 10. Query Capability Tests (`test_10_query_capability.py`)
- Find all articles affected by amendments
- Find all references to an article
- Find legal chain from Law to Article to Interpretation
- Find conflicting rules
- Find missing hierarchy links

**Invariant protected**: Graph must support realistic legal queries correctly.

**Failure danger**: Query failures prevent legal reasoning from accessing necessary information.

## Running the Tests

### All tests (requires Neo4j):
```bash
pytest tests/kg_adversarial/ -v
```

### Specific test category:
```bash
pytest tests/kg_adversarial/test_01_structural_integrity.py -v
```

### With integration marker:
```bash
pytest tests/kg_adversarial/ -m integration -v
```

### Slow tests (temporal, idempotency):
```bash
pytest tests/kg_adversarial/ -m slow -v
```

## CI Integration

These tests are marked with pytest markers:
- `@pytest.mark.p0_critical`: Critical path tests (structural integrity, ontology)
- `@pytest.mark.integration`: Requires Neo4j connection
- `@pytest.mark.slow`: Long-running tests (idempotency, temporal)

Configure CI to run:
1. P0 critical tests on every PR
2. Integration tests with Neo4j in nightly builds
3. Slow tests in weekly full regression

## Fixtures

- `neo4j_empty_graph`: Empty Neo4j database for isolated tests
- `neo4j_sample_graph`: Pre-populated with sample Persian legal data
- `corrupted_orphan_graph`: Graph with intentional orphan nodes
- `corrupted_duplicate_graph`: Graph with intentional duplicates
- `corrupted_reference_graph`: Graph with broken references

## Contributing

When adding new tests:
1. Document the invariant being protected
2. Explain why failure is dangerous
3. Describe how the defect would affect legal reasoning
4. Use existing fixtures where possible
5. Mark with appropriate pytest markers
6. Ensure test is isolated and reproducible
