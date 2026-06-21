# MAHOUN Determinism Crisis Suite
## Zero-Tolerance Determinism Validation

**Classification:** CRITICAL GOVERNANCE ENFORCEMENT  
**Purpose:** Verify deterministic execution guarantees  
**Tolerance:** ZERO (any drift = CRITICAL FAILURE)  

---

## Overview

The Determinism Crisis Suite is the most rigorous determinism validation framework in MAHOUN's governance system. It implements **8 mandatory test categories** that verify the platform's deterministic execution guarantees under all conditions.

**Core Principle:** Same input → Same output (ALWAYS)

---

## Test Categories

### 1. Same Input 100x (`test_same_input_100x.py`)
**Purpose:** Verify identical results for identical inputs  
**Tests:** 6 tests  
**Iterations:** 100 per test  
**Total Executions:** 600  

**Validates:**
- Result determinism
- Confidence score stability
- Proof tree hash consistency
- Derived facts ordering
- Audit hash stability
- Fortress validation determinism

**Pass Criteria:** 100/100 identical results

---

### 2. Concurrent Async (`test_concurrent_async.py`)
**Purpose:** Verify determinism under concurrent execution  
**Tests:** 6 tests  
**Concurrency:** 100 parallel requests  
**Total Executions:** 600  

**Validates:**
- Concurrent execution consistency
- No race conditions
- No async state corruption
- Thread-safe validator operations
- Stats integrity
- Audit trail integrity

**Pass Criteria:** All concurrent results identical to sequential baseline

---

### 3. Retry Storm (`test_retry_storm.py`)
**Purpose:** Verify determinism under rapid repeated execution  
**Tests:** 3 tests  
**Iterations:** 1000 rapid retries  
**Total Executions:** 3000  

**Validates:**
- Rapid retry consistency
- No state accumulation
- No memory leaks
- No performance degradation

**Pass Criteria:** 1000/1000 identical results, <50MB memory growth

---

### 4. Parallel Validation (`test_parallel_validation.py`)
**Purpose:** Verify multi-validator consistency  
**Tests:** 4 tests  
**Validators:** 10 parallel instances  
**Total Executions:** 400  

**Validates:**
- Multi-validator consistency
- Independent validator determinism
- No cross-validator contamination
- Validator isolation

**Pass Criteria:** All validators produce identical results

---

### 5. Desktop/Enterprise Consistency (`test_dual_mode_consistency.py`)
**Purpose:** Verify dual-mode semantic equivalence  
**Tests:** 5 tests  
**Modes:** DESKTOP_MINIMAL vs ENTERPRISE_FULL  
**Total Executions:** 500  

**Validates:**
- Semantic equivalence across modes
- No mode-specific drift
- Resource scaling only (not semantic changes)
- Dual-mode invariance

**Pass Criteria:** Identical reasoning results across modes

---

### 6. Proof Hash Consistency (`test_hash_consistency.py`)
**Purpose:** Verify cryptographic hash stability  
**Tests:** 8 tests  
**Iterations:** 100 per test  
**Total Executions:** 800  

**Validates:**
- Proof tree hash determinism
- Audit hash determinism
- Derived facts hash stability
- Conclusion hash stability
- Canonical serialization
- Hash collision resistance
- Tampering detection
- Ordering independence

**Pass Criteria:** 100/100 identical hashes

---

### 7. Derived Fact Ordering (`test_derived_fact_ordering.py`)
**Purpose:** Verify semantic ordering stability  
**Tests:** 4 tests  
**Iterations:** 100 per test  
**Total Executions:** 400  

**Validates:**
- Deterministic fact ordering
- Topological sort stability
- Dependency ordering consistency
- No random ordering

**Pass Criteria:** 100/100 identical orderings

---

### 8. Contradiction Stability (`test_contradiction_stability.py`)
**Purpose:** Verify conflict resolution determinism  
**Tests:** 4 tests  
**Iterations:** 100 per test  
**Total Executions:** 400  

**Validates:**
- Deterministic contradiction detection
- Stable conflict resolution
- Consistent priority ordering
- No random tie-breaking

**Pass Criteria:** 100/100 identical contradiction resolutions

---

## Total Test Coverage

**Total Tests:** 40  
**Total Executions:** 6,100  
**Total Runtime:** ~10-15 minutes (DESKTOP_MINIMAL)  
**Pass Criteria:** 100% determinism (zero tolerance)  

---

## Running Tests

### Run All Determinism Tests
```bash
pytest tests/determinism/ -v
```

### Run Specific Category
```bash
pytest tests/determinism/test_same_input_100x.py -v
pytest tests/determinism/test_concurrent_async.py -v
pytest tests/determinism/test_retry_storm.py -v
```

### Run with Coverage
```bash
pytest tests/determinism/ --cov=mahoun --cov-report=html
```

### Run with Detailed Output
```bash
pytest tests/determinism/ -v -s
```

### Run Performance Benchmarks
```bash
pytest tests/determinism/ -v -m benchmark
```

---

## Failure Interpretation

### CRITICAL FAILURES (Immediate Action Required)

**Result Drift:**
```
DETERMINISM VIOLATION: Symbolic reasoning produced 2 unique results (expected 1)
```
**Cause:** Non-deterministic reasoning logic  
**Impact:** Zero-hallucination guarantee void  
**Action:** Investigate reasoning engine, check for randomness sources  

**Hash Drift:**
```
HASH DRIFT: 5 unique hashes detected
```
**Cause:** Non-canonical serialization or hash computation  
**Impact:** Audit trail integrity compromised  
**Action:** Fix canonical serialization, verify hash function  

**Race Condition:**
```
CONCURRENT DETERMINISM VIOLATION: 10 mismatches
```
**Cause:** Shared mutable state without locks  
**Impact:** Concurrent execution unsafe  
**Action:** Add async locks, make state immutable  

**Memory Leak:**
```
MEMORY LEAK DETECTED: 150MB growth
```
**Cause:** Resource not released after execution  
**Impact:** System instability under load  
**Action:** Profile memory, fix leaks  

---

## Determinism Score

Each test category produces a **determinism score** (0.0 to 1.0):

- **1.0:** Perfect determinism (100% identical results)
- **0.99:** Near-perfect (1% drift) - INVESTIGATE
- **0.95:** Significant drift (5%) - CRITICAL
- **<0.95:** Severe drift - DEPLOYMENT BLOCKER

**Minimum Acceptable Score:** 1.0 (zero tolerance)

---

## CI Integration

### GitHub Actions Workflow

```yaml
name: Determinism Crisis Suite

on: [push, pull_request]

jobs:
  determinism:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run Determinism Tests
        run: pytest tests/determinism/ -v --cov=mahoun
      - name: Check Determinism Score
        run: |
          # Fail if any test fails (zero tolerance)
          pytest tests/determinism/ --tb=short
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running Determinism Crisis Suite..."
pytest tests/determinism/ -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ DETERMINISM TESTS FAILED - Commit blocked"
    exit 1
fi

echo "✅ Determinism verified"
exit 0
```

---

## Troubleshooting

### Tests Timeout
**Symptom:** Tests hang or timeout  
**Cause:** Infinite loop or deadlock  
**Solution:** Add timeout to pytest: `pytest --timeout=300`  

### Flaky Tests
**Symptom:** Tests pass sometimes, fail sometimes  
**Cause:** Non-determinism (the thing we're testing for!)  
**Solution:** This IS a failure - investigate root cause  

### High Memory Usage
**Symptom:** Tests consume excessive memory  
**Cause:** Memory leak or large data structures  
**Solution:** Run memory profiler: `pytest --memray`  

### Slow Execution
**Symptom:** Tests take >30 minutes  
**Cause:** DESKTOP_MINIMAL resource constraints  
**Solution:** Reduce iterations or run on ENTERPRISE_FULL  

---

## Maintenance

### Adding New Tests

1. Create new test file in `tests/determinism/`
2. Inherit from `DeterminismTestBase`
3. Follow naming convention: `test_<category>_<description>.py`
4. Add to this README
5. Update CI configuration

### Modifying Iterations

**Current:** 100 iterations per test  
**Minimum:** 50 (for quick checks)  
**Recommended:** 100 (for CI)  
**Stress Test:** 1000 (for release validation)  

Edit iteration count in test files:
```python
for i in range(100):  # Change this number
    # ...
```

---

## References

- **Audit Report:** `docs/GOVERNANCE_SECURITY_AUDIT_REPORT.md`
- **Remediation Plan:** `docs/GOVERNANCE_REMEDIATION_PLAN.md`
- **RedLines Config:** `constitution/RedLines.yaml`
- **Fortress Validator:** `mahoun/core/fortress_validator.py`

---

## Contact

**Owner:** MahouN AEO Governance Council  
**Maintainer:** Engineering Security Team  
**Escalation:** If any test fails, escalate immediately to security team  

---

**END OF README**

**Last Updated:** 2026-05-14  
**Version:** 1.0.0  
**Status:** ACTIVE

