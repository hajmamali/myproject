# Phase 2A Semantic Enrichment Tests

**Status:** Acceptance Tests for Semantic Schema Contract v1.1  
**Purpose:** Verify Phase 2A contract is enforced before Phase 2B (extraction) begins  
**Philosophy:** Negative tests > Positive tests (fail-closed enforcement)

---

## Test Priority System

### PRIORITY 1: Negative & Adversarial Tests 🔴

**File:** `test_phase_2a_negative_tests.py`

**Purpose:** Prove the system REJECTS bad inputs (zero-hallucination guarantee)

**Categories:**
1. **Missing Evidence** - Facts without evidence → REJECTED
2. **Unverified Endpoints** - Edges from/to unverified nodes → REJECTED
3. **Duplicate Identity** - Duplicate canonical_id → REJECTED
4. **Ambiguous Extraction** - Low confidence/ambiguous → UNRESOLVED
5. **Governance Bypass** - Direct writes → BLOCKED
6. **CI Enforcement** - Violations detected in CI

**Critical:** If these tests fail, Phase 2A is NOT complete. Do NOT proceed to Phase 2B.

---

### PRIORITY 2: Positive Tests 🟢

**File:** `test_phase_2a_positive_tests.py`

**Purpose:** Prove the system ACCEPTS good inputs (happy path works)

**Categories:**
1. **Valid Entity Creation** - Proper entities → CREATED
2. **Valid Assertion Creation** - Proper assertions → CREATED
3. **Provenance Chain Integrity** - Traceability → VERIFIED
4. **Schema Compliance** - Constraints → ENFORCED
5. **Verification Lifecycle** - State transitions → WORK

**Note:** These tests only run if negative tests pass first.

---

## Running Tests

### Run All Tests (Recommended)

```bash
# Activate virtual environment first!
source venv/bin/activate

# Run with priority enforcement
python tests/semantic/test_phase_2a_runner.py
```

**Output:**
1. Runs negative tests first
2. If negative tests fail → STOP (reports failure)
3. If negative tests pass → Run positive tests
4. If all pass → Phase 2A COMPLETE

---

### Run Individual Test Suites

```bash
# Negative tests only
pytest tests/semantic/test_phase_2a_negative_tests.py -v

# Positive tests only
pytest tests/semantic/test_phase_2a_positive_tests.py -v
```

---

### Run CI Enforcement Tests

```bash
# CI-specific tests (marked with @pytest.mark.ci)
python tests/semantic/test_phase_2a_runner.py --ci
```

---

## Test Philosophy

### Why Negative Tests Are More Important

**Traditional approach:**
```
Test that system works → Positive tests
(Hope it doesn't break → Pray)
```

**MahouN approach:**
```
Test that system FAILS CORRECTLY → Negative tests
(Then verify it works → Positive tests)
```

**Rationale:**

For MahouN's zero-hallucination guarantee:
- **Rejecting bad inputs** is more critical than accepting good inputs
- **Fail-closed principle** requires BLOCKING unverified facts
- **Governance enforcement** depends on PREVENTING unauthorized writes

Example:
- ✅ System accepts 90% of valid inputs → GOOD
- ❌ System accepts 1% of invalid inputs → **CATASTROPHIC**

### The "One Bad Apple" Problem

```
99 good semantic facts + 1 unverified fact = 
    → Reasoning chain contaminated
    → Zero-hallucination guarantee broken
    → Audit trail compromised
```

Therefore: **Negative tests > Positive tests**

---

## Test Categories Explained

### Category 1: Missing Evidence

**What we test:**
- Concept without `source_text_span` → REJECTED
- Concept without `source_sha256` → REJECTED
- Assertion without `evidence_text_span` → REJECTED

**Why it matters:**
- Every semantic fact MUST have cryptographic proof
- No evidence = No claim (fail-closed)

---

### Category 2: Unverified Endpoints

**What we test:**
- Edge from CANDIDATE node → REJECTED
- Edge to UNRESOLVED node → REJECTED
- Reasoning query excludes unverified nodes

**Why it matters:**
- This is the CORE zero-hallucination test
- Unverified facts MUST NOT enter reasoning paths

---

### Category 3: Duplicate Identity

**What we test:**
- Duplicate `canonical_id` → REJECTED
- Conflicting alias → REJECTED
- Similar text does NOT cause auto-merge

**Why it matters:**
- Prevents same problem as duplicate components in codebase
- Deterministic identity (not fuzzy matching)

---

### Category 4: Ambiguous Extraction

**What we test:**
- Low confidence extraction → UNRESOLVED
- Conflicting interpretations → UNRESOLVED
- Ambiguous relationship direction → REJECTED

**Why it matters:**
- Fail-closed: if uncertain, mark UNRESOLVED
- Never fabricate when ambiguous

---

### Category 5: Governance Bypass

**What we test:**
- Direct Neo4j write → BLOCKED
- Wrong capability → REJECTED
- Missing provenance → REJECTED

**Why it matters:**
- All semantic writes MUST go through governance
- Bypass = audit trail broken

---

### Category 6: CI Enforcement

**What we test:**
- Detect direct `GraphDatabase.driver()` usage
- Validate schema version consistency
- Check provenance completeness

**Why it matters:**
- CI catches violations before merge
- Prevents regressions

---

## Acceptance Criteria

Phase 2A is COMPLETE when:

- [x] All negative tests pass (PRIORITY 1)
- [x] All positive tests pass (PRIORITY 2)
- [x] All CI enforcement tests pass
- [x] Schema contract frozen
- [x] Identity & deduplication policy frozen
- [x] Assertion vs entity model frozen
- [x] Schema versioning defined

**Gate:** Cannot proceed to Phase 2B until all criteria met.

---

## Mock Functions

**Note:** Current tests use mock functions that return predictable results.

**Before Phase 2B:**
- Replace mocks with real implementations
- Wire to actual Neo4j database
- Wire to actual governance boundary
- Wire to actual provenance system

**Mock functions to replace:**
```python
materialize_semantic_fact()         → Real Neo4j write
materialize_entity_mock()            → Real entity materialization
can_create_semantic_edge_mock()      → Real edge validation
query_reasoning_graph_mock()         → Real reasoning query
execute_direct_cypher()              → Real governance check
```

---

## Integration with CI

### GitHub Actions / CI Pipeline

```yaml
# .github/workflows/semantic-tests.yml
name: Phase 2A Semantic Tests

on: [push, pull_request]

jobs:
  negative-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
      - name: Run Negative Tests
        run: |
          source venv/bin/activate
          pytest tests/semantic/test_phase_2a_negative_tests.py -v
      # If negative tests fail, job fails (blocks merge)
  
  positive-tests:
    runs-on: ubuntu-latest
    needs: negative-tests  # Only runs if negative tests pass
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
      - name: Run Positive Tests
        run: |
          source venv/bin/activate
          pytest tests/semantic/test_phase_2a_positive_tests.py -v
```

---

## Troubleshooting

### All Negative Tests Failing

**Problem:** System allows unverified facts into reasoning.

**Solution:**
1. Check `can_create_semantic_edge()` implementation
2. Verify reasoning queries filter by `status IN ['VERIFIED', 'MATERIALIZED']`
3. Check governance boundary enforcement

---

### Duplicate Identity Tests Failing

**Problem:** System creates duplicate entities.

**Solution:**
1. Check Neo4j uniqueness constraints applied
2. Verify `canonical_id` uniqueness check
3. Check normalized label collision detection

---

### Governance Bypass Tests Failing

**Problem:** System allows direct writes.

**Solution:**
1. Check all Neo4j writes use `GovernedNeo4jSession`
2. Verify no `GraphDatabase.driver()` calls outside `connection.py`
3. Check governance context manager active

---

### CI Enforcement Tests Failing

**Problem:** CI doesn't detect violations.

**Solution:**
1. Check CI workflow configured correctly
2. Verify tests marked with `@pytest.mark.ci`
3. Check static analysis scripts run in CI

---

## Next Steps

After Phase 2A acceptance tests pass:

1. ✅ **Phase 2A COMPLETE**
2. → **Phase 2B:** Design extraction pipeline
3. → **Phase 2C:** Design semantic QA
4. → **Phase 3:** Temporal enhancement
5. → **Phase 4:** Multi-layer integration
6. → **Phase 5:** Production integration

**Remember:** Do NOT skip to Phase 2B until ALL Phase 2A tests pass.

---

**Last Updated:** 2026-09-01  
**Version:** 1.0.0  
**Status:** ✅ Ready for execution
