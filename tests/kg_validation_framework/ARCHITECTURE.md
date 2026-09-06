# Persian Legal Knowledge Graph - Comprehensive Validation Framework
====================================================================

## Mission

Prove that the entire Legal Knowledge Graph construction system produces a trustworthy legal knowledge representation capable of supporting future legal reasoning.

**Assumption**: The system has hidden defects. We must find them before integration.

## System Components Under Validation

1. **Input Data Layer**: Raw legal documents (PDF, TXT, DOCX)
2. **Extraction Pipeline**: Parsing, entity identification, relationship extraction
3. **Entity Management**: Identity resolution, deduplication, canonical ID generation
4. **Ontology Layer**: Legal hierarchy modeling, schema definition
5. **Storage Layer**: Neo4j graph database
6. **Semantic Layer**: Relationship semantics, legal priority
7. **Temporal Layer**: Version management, amendment tracking
8. **Query Layer**: Graph traversal, legal reasoning queries

## Validation Philosophy

- **Failure Detection Over Happy Path**: Tests are designed to break the system
- **Legal Invariants**: Every test protects a specific legal or architectural invariant
- **No Superficial Tests**: No "node exists" checks - prove correctness
- **Adversarial Mindset**: Assume malicious/corrupted input
- **Real Over Mocks**: Use real Neo4j where possible
- **Deterministic**: Same input must produce same output
- **Isolated**: Each test is independent
- **Actionable**: Failures must explain what's wrong and why it matters

## Test Architecture

```
tests/kg_validation_framework/
├── ARCHITECTURE.md              # This document
├── README.md                    # Quick start guide
├── conftest.py                  # Global fixtures and configuration
├── phase_01_input_validation/   # Phase 1: Input Data Validation
├── phase_02_extraction/         # Phase 2: Extraction Pipeline Validation
├── phase_03_identity/           # Phase 3: Entity Identity and Deduplication
├── phase_04_ontology/           # Phase 4: Ontology and Schema Validation
├── phase_05_graph_integrity/     # Phase 5: Neo4j Graph Integrity Tests
├── phase_06_semantic/           # Phase 6: Semantic Relationship Testing
├── phase_07_temporal/           # Phase 7: Temporal Legal Consistency
├── phase_08_idempotency/        # Phase 8: Idempotency and Reproducibility
├── phase_09_query/              # Phase 9: Query Capability Tests
├── phase_10_adversarial/        # Phase 10: Adversarial Failure Testing
├── fixtures/                    # Test fixtures and sample data
│   ├── neo4j_fixtures.py
│   ├── sample_valid_data.py
│   ├── sample_invalid_data.py
│   └── corrupted_graphs.py
├── cypher_queries/              # Reusable Cypher validation queries
│   ├── structural_queries.py
│   ├── semantic_queries.py
│   └── temporal_queries.py
└── CI_STRATEGY.md               # CI/CD integration strategy
```

## Phase Overview

### Phase 1: Input Data Validation
**Goal**: Validate raw legal documents before processing

**Tests**:
- Duplicate document detection
- Missing document detection
- Text corruption detection
- Encoding validation
- Persian/Arabic character consistency
- Invisible Unicode character detection
- Article numbering format validation
- Reference extraction from source text
- Format change detection

**Failure Risk**: Corrupted input produces corrupted knowledge graph

### Phase 2: Extraction Pipeline Validation
**Goal**: Validate Legal Text → Entities + Relationships transformation

**Tests**:
- Law extraction correctness
- Chapter extraction correctness
- Article extraction correctness
- Paragraph extraction correctness
- Reference extraction correctness
- Amendment extraction correctness
- Entity boundary validation
- Article number accuracy
- Entity loss detection
- False entity detection
- Relationship creation validation
- Missing relationship detection

**Failure Risk**: Extraction errors create wrong legal knowledge

### Phase 3: Entity Identity and Deduplication
**Goal**: Validate identity management and prevent false merges

**Tests**:
- Same law with different names detection
- Same article appearing multiple times detection
- Similar text but different entities detection
- Different version handling
- Accidental merge detection
- Canonical ID uniqueness
- Similarity vs identity validation

**Failure Risk**: False merges create contradictory legal knowledge

### Phase 4: Ontology and Schema Validation
**Goal**: Audit the legal ontology and schema

**Tests**:
- Node label validation
- Relationship type validation
- Relationship direction validation
- Required property validation
- Allowed relationship combinations
- Article parent validation
- Judicial decision vs legislation validation
- Advisory opinion validation
- Amendment vs original law validation
- Legal hierarchy validation

**Failure Risk**: Ontology errors cause incorrect legal reasoning

### Phase 5: Neo4j Graph Integrity Tests
**Goal**: Validate the actual graph database state

**Tests**:
- Required label existence
- Required property existence
- Orphan node detection
- Empty identifier detection
- Duplicate canonical identifier detection
- Valid source node type validation
- Valid target node type validation
- Valid relationship type validation
- Impossible connection detection
- Broken reference detection

**Failure Risk**: Graph corruption causes query failures and wrong results

### Phase 6: Semantic Relationship Testing
**Goal**: Validate relationship semantics, not just existence

**Tests**:
- Semantic direction validation
- Legal priority validation
- Interpretation chain validation
- Exception handling validation
- Precedence relationship validation
- Wrong semantic direction detection
- Incorrect legal priority detection
- Invalid interpretation chain detection
- Missing exception handling detection

**Failure Risk**: Semantic errors cause wrong legal conclusions

### Phase 7: Temporal Legal Consistency
**Goal**: Validate time-related logic

**Tests**:
- Effective date validation
- Repealed law handling
- Amendment tracking
- Historical version management
- Multiple active conflicting version detection
- Future law detection
- Repealed article usage detection
- Missing version relationship detection

**Failure Risk**: Temporal errors cause applying wrong law version

### Phase 8: Idempotency and Reproducibility
**Goal**: Ensure deterministic graph construction

**Tests**:
- Multiple build consistency
- Node count consistency
- Relationship count consistency
- Graph fingerprint generation
- Node count fingerprinting
- Relationship count fingerprinting
- Label fingerprinting
- Relationship type fingerprinting
- Canonical property hashing
- Uncontrolled change detection

**Failure Risk**: Non-deterministic construction causes unpredictable behavior

### Phase 9: Query Capability Tests
**Goal**: Validate realistic legal graph queries

**Tests**:
- Legal concept query validation
- Amendment history query validation
- Reference query validation
- Legal hierarchy path query validation
- Conflicting rule query validation
- Interpretation chain query validation
- Result correctness validation
- Complete traversal validation
- Evidence path validation

**Failure Risk**: Query failures prevent legal reasoning

### Phase 10: Adversarial Failure Testing
**Goal**: Ensure system fails safely on malicious/corrupted input

**Tests**:
- Fake article handling
- Duplicate law handling
- Invalid reference handling
- Missing identifier handling
- Broken relationship handling
- Contradictory metadata handling
- Safe failure validation
- Silent corruption prevention

**Failure Risk**: Unsafe failures create undetected corruption

## Test Implementation Template

Every test must include:

```python
class TestClassName:
    """
    TEST NAME: Descriptive test name
    PURPOSE: What this test validates
    INVARIANT: The legal or architectural invariant being protected
    FAILURE RISK: How failure would corrupt the KG or affect legal reasoning
    IMPLEMENTATION: How the test works
    """
    
    def test_specific_scenario(self):
        """
        Detailed description of what this specific test case validates.
        """
        # Test implementation
        pass
```

## CI Integration Strategy

- **Phase 1-2**: Run on every PR (fast, no Neo4j required)
- **Phase 3-5**: Run nightly (requires Neo4j)
- **Phase 6-8**: Run weekly (comprehensive)
- **Phase 9-10**: Run monthly (full regression)

## Success Criteria

The Knowledge Graph is considered ready for integration when:

1. All Phase 1-2 tests pass on every PR
2. All Phase 3-5 tests pass in nightly builds
3. All Phase 6-8 tests pass in weekly builds
4. All Phase 9-10 tests pass in monthly regression
5. Graph fingerprint is reproducible across builds
6. No silent failures detected
7. All legal invariants are protected

## Failure Response Protocol

When a test fails:

1. **Block Integration**: Do not proceed with reasoning engine integration
2. **Root Cause Analysis**: Identify the source of the failure
3. **Fix the Defect**: Fix the underlying issue, not the test
4. **Validate Fix**: Re-run the full test suite
5. **Update Documentation**: Document the fix and lessons learned

## Metrics and Monitoring

Track:
- Test execution time per phase
- Failure rate per phase
- Flaky test detection
- Coverage of extraction pipeline
- Graph fingerprint stability
- Query performance metrics

## Maintenance

- Review test suite quarterly
- Update tests when schema changes
- Add new tests for new features
- Remove obsolete tests
- Update fixtures to match current data
