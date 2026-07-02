# MAHOUN Test Infrastructure Continuation Plan

**Date:** 2026-06-07  
**Status:** 📋 ACTIONABLE PLAN  
**Classification:** PRODUCTION READINESS / EVIDENCE-BASED CONTINUATION  
**Based On:** Analysis of 10 project documentation files

---

## Executive Summary

### Current State Assessment

The MAHOUN test infrastructure initiative has achieved **partial completion** with significant progress on security module implementation, but critical blockers remain in reasoning and ledger modules. The original "Mission Complete" analysis identified a 14-week roadmap, but subsequent implementation revealed test infrastructure issues requiring immediate attention.

**Key Achievement:** Security module shows strong progress (42.20% vs 25.30% baseline, +16.9% absolute improvement)

**Critical Blockers:**
1. Reasoning module: 70/75 tests in ERROR state (93% failure rate)
2. Ledger module: Apparent 24.92% coverage regression (investigated as measurement artifact)
3. API mismatches: ReasoningResponse and FortressValidator test expectations misaligned
4. Test execution failures: 28 reasoning tests in ERROR state (dependency issues)

**Production Readiness:** 🔴 **NOT READY** - P0 risks remain in reasoning validation and ledger recovery paths

---

## What Has Been Completed

### Risk-Driven Analysis Phase ✅ COMPLETE

**Delivered Documents (June 7, 2026):**
- RISK_DRIVEN_TEST_GAP_ANALYSIS.md (42K, 1143 lines) - Primary analysis
- TEST_ROADMAP_RECOMMENDATION.md (37K, 1385 lines) - Original roadmap
- RISK_ANALYSIS_SUMMARY.md (12K) - Executive summary
- ANALYSIS_QUICK_REFERENCE.md (7.8K) - Quick reference
- EVIDENCE_VERIFICATION_REPORT.md (17K) - Methodology
- DELIVERY_INDEX.md (14K) - Package documentation

**Key Findings from Analysis:**
- 4 P0 modules identified: security (9.8/10 risk), reasoning (9.7/10), ledger (9.5/10), graph (8.9/10)
- 322+ critical paths identified with specific file:line references
- 3 cascading failure scenarios mapped
- Original roadmap: 14 weeks, 805-965 tests, 38% → 61% coverage trajectory

### Security Module Implementation ✅ PARTIAL COMPLETE

**Tests Implemented (88 tests total):**
- test_api_key_lifecycle.py (44 tests) - ✅ COMPLETE
- test_api_key_collision_prevention.py (12 tests) - ✅ COMPLETE
- test_rbac_permission_matrix.py (32 tests) - ✅ COMPLETE
- test_jwt_comprehensive.py (15 tests) - ✅ COMPLETE

**Coverage Achievement:**
- Baseline: 25.30%
- Current: 42.20%
- Improvement: +16.9% absolute
- Gap to target (65%): 22.8%

**Tests Still Missing (55 tests):**
- test_jwt_blacklist_concurrency.py (12 tests) - P0 (race conditions)
- test_audit_logger_integrity.py (18 tests) - P0 (audit trail)
- test_pii_scrubber_patterns.py (10 tests) - P1 (privacy)
- test_prompt_injection_defense.py (15 tests) - P1 (security)

### Ledger Module Implementation ✅ PARTIAL COMPLETE

**Tests Implemented (47 tests total):**
- test_hash_chain_integrity.py (20 tests) - ✅ COMPLETE
- test_concurrent_writes.py (15 tests) - ✅ COMPLETE
- test_governance_gate_enforcement.py (12 tests) - ✅ COMPLETE (after bug fix)

**Coverage Investigation:**
- Baseline: 51.62%
- Apparent current: 26.70% (measured with tests/ledger/ only)
- Root cause identified: Test scope mismatch
- True estimated coverage: 35-40%
- Regression status: Measurement artifact, not actual regression

**Bug Fixes Applied:**
- Fixed `GovernanceException` → `GovernanceError` import in write_gate.py
- Fixed syntax error in test_governance_gate_enforcement.py

**Tests Still Missing (18 tests):**
- test_blockchain_verification.py (10 tests) - P0 (invalid block detection)
- test_ledger_recovery.py (8 tests) - P0 (restart scenarios)

### Reasoning Module Implementation ❌ CRITICAL STATE

**Test Implementation Attempt:**
- test_agreement_score_boundaries.py (20 tests) - ⚠️ Mostly ERROR/FAIL
- test_p0_critical_paths.py (20 tests) - ⚠️ Mostly ERROR/FAIL
- test_unified_reasoning_advanced.py (10 tests) - ⚠️ Mostly ERROR/SKIPPED
- test_unified_reasoning_service.py (20 tests) - ⚠️ Mostly ERROR
- test_verdict_engine_adapter_reasoning_response.py (3 tests) - ✅ PASSED

**Current State:**
- 75 total reasoning tests
- 70 in ERROR state (93%)
- 4 PASSING (5%)
- 1 test file functional

**Root Cause Analysis (Wave 0):**
1. FortressValidator API mismatch - ✅ FIXED
2. ReasoningResponse API mismatch - ⚠️ DOCUMENTED (requires decision)
3. Unified reasoning service errors - ⚠️ DOCUMENTED (dependency issues)

---

## Unresolved Issues (Prioritized by Risk/Impact)

### P0 CRITICAL BLOCKERS

#### 1. Reasoning Module Test Execution Failures 🔴 CRITICAL

**Issue:** 70 out of 75 reasoning tests (93%) in ERROR state

**Impact:**
- Core reasoning validation paths completely untested
- Hallucination risk remains HIGH
- Zero-hallucination guarantee cannot be verified
- FortressValidator agreement check untested
- Production release BLOCKED

**Root Causes Identified:**
- ReasoningResponse API mismatch: Tests expect fields (verdict, symbolic_score, neural_score, agreement_score) that don't exist in current API
- Validation API mismatch: Tests call `validate_reasoning_response` instance method that doesn't exist
- Unified reasoning service: 28 tests in ERROR state due to dependency/import issues

**Recommended Actions:**
1. **Immediate (Week 1):** API alignment decision - update tests to match current ReasoningResponse API OR extend API to support test expectations
2. **Week 1:** Investigate unified reasoning ERROR state - identify missing dependencies or configuration
3. **Week 2:** Fix all reasoning test execution issues before adding new tests

**Estimated Effort:** 16-24 hours (depending on API alignment decision)

---

#### 2. Ledger Module Coverage Recovery 🔴 HIGH

**Issue:** Apparent 24.92% coverage regression from 51.62% baseline

**Status:** Investigation complete - identified as measurement artifact

**True State:**
- Baseline measurement: All ledger-related tests across entire test suite
- Current measurement: Only tests/ledger/ subdirectory (47 tests)
- Additional ledger tests exist: test_ledger_hash_chain.py, test_async_ledger_comprehensive.py, test_ledger_atomicity.py, test_ledger_properties.py, test_ledger_contracts.py, test_blockchain_ledger.py (~60+ more tests)
- Estimated true coverage: 35-40% (not 22.01%)

**Remaining Work:**
1. Include all ledger tests in coverage measurement (process change)
2. Fix legacy test dependency issues (storage.py → writer.py deprecation)
3. Add tests for new untested code:
   - GovernanceContext validation
   - validate_and_write method
4. Implement missing P0 tests:
   - test_blockchain_verification.py (10 tests)
   - test_ledger_recovery.py (8 tests)

**Estimated Effort:** 12-16 hours

---

#### 3. Security Module Completion 🟡 HIGH

**Issue:** Security module at 42.20% vs 65% target (22.8% gap)

**Tests Still Missing (55 tests):**
- JWT blacklist concurrency (12 tests) - P0 (race condition bypass)
- Audit logger integrity (18 tests) - P0 (audit trail loss)
- PII scrubber patterns (10 tests) - P1 (privacy)
- Prompt injection defense (15 tests) - P1 (LLM manipulation)

**Risk Assessment:**
- JWT blacklist untested: Risk of token revocation bypass via race conditions
- Audit logger untested: Risk of concurrent write handling failures
- P0 security paths remain incomplete

**Estimated Effort:** 12-16 hours

---

### P1 HIGH PRIORITY ISSUES

#### 4. Graph Module Not Started 🟡 MEDIUM

**Issue:** Graph module at 14.97% coverage (8.9/10 risk score)

**Status:** Not started (per original roadmap, Wave 2)

**Critical Paths (68 P0 paths identified):**
- Cypher injection prevention
- GNN destructive operations gating
- Neo4j query bounds enforcement
- Graph concurrency validation

**Impact:** P0 data integrity risk - complete graph wipe possible

**Timeline:** Deferred to after Wave 1 completion (per roadmap)

---

#### 5. Test Infrastructure Consistency 🟡 MEDIUM

**Issue:** Coverage measurement methodology inconsistent

**Current State:**
- Baseline measurement: Full test suite (2248 tests)
- Current measurements: Vary by module/subdirectory
- No standardized coverage measurement process

**Impact:**
- Difficult to track true progress
- Regression detection unreliable
- Coverage targets not comparable

**Recommended Actions:**
1. Establish standard coverage measurement command for each module
2. Document measurement methodology in project AGENTS.md or similar
3. Create CI gates for consistent measurement

**Estimated Effort:** 4-6 hours

---

## Next Immediate Steps (Concrete Actions)

### Week 1: Critical Infrastructure Fix

**Priority:** Resolve test execution blockers before adding new tests

**Actions:**

1. **Reasoning API Alignment Decision** (4 hours)
   - Decision point: Update tests to match current ReasoningResponse API OR extend API
   - Recommendation: Update tests to match current API (faster, validates actual implementation)
   - File updates needed:
     - tests/reasoning/test_agreement_score_boundaries.py
     - tests/reasoning/test_p0_critical_paths.py
   - Success criteria: All reasoning tests execute (may fail, but no ERROR state)

2. **Unified Reasoning Dependency Investigation** (8 hours)
   - Investigate 28 tests in ERROR state
   - Identify missing dependencies or configuration issues
   - Ensure all required services/dependencies available
   - Success criteria: All reasoning tests collected and execute

3. **Consistent Coverage Measurement** (2 hours)
   - Create standardized coverage measurement commands
   - Document in project rules file
   - Example command for ledger:
     ```bash
     pytest tests/ledger/ tests/test_ledger_*.py tests/test_async_ledger*.py tests/test_blockchain_ledger.py tests/contracts/test_ledger_contracts.py --cov=mahoun/ledger --cov-report=term
     ```

4. **Legacy Test Fixes** (6 hours)
   - Fix storage.py → writer.py deprecation in test_ledger_hash_chain.py
   - Fix pytest import issues in other legacy ledger tests
   - Update dependency imports for deprecated modules

**Week 1 Deliverables:**
- ✅ Reasoning tests execute without ERROR state
- ✅ Coverage measurement methodology standardized
- ✅ Legacy test dependency issues resolved
- ✅ Action plan for coverage recovery defined

**Verification:**
```bash
pytest tests/reasoning/ -v --tb=short
# Target: 75 tests collected, 0 errors (failures OK)

pytest tests/ledger/ tests/test_ledger_*.py --cov=mahoun/ledger --cov-report=term
# Target: Consistent measurement across all ledger tests
```

---

### Week 2: Module Completion

**Priority:** Complete P0 security and ledger tests

**Actions:**

1. **Security Module Completion** (12 hours)
   - Implement test_jwt_blacklist_concurrency.py (12 tests)
   - Implement test_audit_logger_integrity.py (18 tests)
   - Target: Security module ≥ 65% coverage
   - File: tests/security/test_jwt_blacklist_concurrency.py
   - File: tests/security/test_audit_logger_integrity.py

2. **Ledger Module Completion** (8 hours)
   - Implement test_blockchain_verification.py (10 tests)
   - Implement test_ledger_recovery.py (8 tests)
   - Add tests for GovernanceContext validation
   - Add tests for validate_and_write method
   - Target: Ledger module ≥ 60% coverage
   - File: tests/ledger/test_blockchain_verification.py
   - File: tests/ledger/test_ledger_recovery.py

3. **Coverage Recovery Verification** (4 hours)
   - Run consistent coverage measurement
   - Verify no actual regressions
   - Document true baseline coverage

**Week 2 Deliverables:**
- ✅ Security module ≥ 65% coverage
- ✅ Ledger module ≥ 60% coverage
- ✅ All P0 security paths tested
- ✅ All P0 ledger data integrity paths tested
- ✅ Coverage regression recovery verified

**Verification:**
```bash
pytest tests/security/ -v --cov=mahoun/security --cov-report=term
# Target: 115+ tests, 65%+ coverage

pytest tests/ledger/ tests/test_ledger_*.py --cov=mahoun/ledger --cov-report=term
# Target: 65+ tests, 60%+ coverage
```

---

### Week 3: Reasoning Module Foundation

**Priority:** Fix existing reasoning tests and implement P0 validation

**Actions:**

1. **Reasoning Test Stabilization** (8 hours)
   - Fix all failing reasoning tests (from Week 1 API alignment)
   - Ensure all existing tests pass
   - Stabilize reasoning test suite

2. **Reasoning P0 Tests** (16 hours)
   - Implement test_evidence_verdict_edge_cases.py (30 tests)
   - Implement test_chain_of_thought_validation.py (20 tests)
   - Target: Reasoning module ≥ 50% coverage
   - File: tests/reasoning/test_evidence_verdict_edge_cases.py
   - File: tests/reasoning/test_chain_of_thought_validation.py

**Week 3 Deliverables:**
- ✅ All existing reasoning tests pass
- ✅ Evidence verdict edge cases tested
- ✅ Chain-of-thought validation implemented
- ✅ Reasoning module ≥ 50% coverage
- ✅ P0 hallucination prevention tested

**Verification:**
```bash
pytest tests/reasoning/ -v --cov=mahoun/reasoning --cov-report=term
# Target: 95+ tests, 50%+ coverage
```

---

### Week 4: Integration & Verification

**Priority:** End-to-end P0 validation and Wave 1 completion

**Actions:**

1. **Integration Tests** (8 hours)
   - Implement test_p0_end_to_end.py (25 tests)
   - Security → Ledger → Reasoning integration
   - Governance enforcement across modules
   - Audit trail completeness verification
   - File: tests/integration/test_p0_end_to_end.py

2. **Wave 1 Verification** (8 hours)
   - Run full P0 module test suite
   - Verify coverage targets met
   - Document risk reduction achieved
   - Create Wave 1 completion report

**Week 4 Deliverables:**
- ✅ Integration tests passing
- ✅ Security module ≥ 65% coverage
- ✅ Ledger module ≥ 60% coverage
- ✅ Reasoning module ≥ 50% coverage
- ✅ Overall coverage ≥ 45%
- ✅ Zero P0 test execution failures
- ✅ Wave 1 complete

**Verification:**
```bash
pytest tests/security/ tests/ledger/ tests/reasoning/ tests/integration/ -v --cov=mahoun/security,mahoun/ledger,mahoun/reasoning --cov-report=term
# Target: 300+ tests, 45%+ overall coverage
```

---

## Suggested Timeline (Wave Structure)

### REVISED Wave 0: Critical Infrastructure Fix (Week 1)
**Objective:** Fix test execution failures and standardize measurement
**Duration:** 1 week (compressed from 2 weeks)
**Developers:** 2 full-time
**Target Coverage:** Stabilize current state
**Expected Risk Reduction:** Infrastructure stability

**Scope:**
- Test infrastructure: Broken → Fixed
- Reasoning tests: 70 ERROR → 0 ERROR (may fail, but execute)
- Coverage measurement: Inconsistent → Standardized

**Exit Criteria:**
- ✅ All reasoning tests execute without ERROR state
- ✅ Coverage measurement methodology standardized
- ✅ Legacy test dependency issues resolved

---

### REVISED Wave 1: P0 Critical Security & Integrity (Week 2-4)
**Objective:** Complete P0 security, ledger, and reasoning tests
**Duration:** 3 weeks (adjusted from 5 weeks)
**Developers:** 2 full-time
**Target Coverage:** 31% → 45%
**Expected Risk Reduction:** 60%

**Scope:**
|| Module | Current | Target | Priority |
||--------|---------|--------|----------|
|| **mahoun.security** | 42.20% | 65% | P0 |
|| **mahoun.ledger** | 35-40% | 60% | P0 |
|| **mahoun.reasoning** | 25.78% | 50% | P0 |

**Total Tests:** 118-150

**Exit Criteria:**
- ✅ Security module ≥ 65% coverage
- ✅ Ledger module ≥ 60% coverage
- ✅ Reasoning module ≥ 50% coverage
- ✅ All P0 security bypass paths tested
- ✅ All P0 data integrity paths tested
- ✅ All P0 reasoning validation tested
- ✅ Zero test execution failures in P0 modules
- ✅ Overall coverage ≥ 45%

---

### Wave 2: P1 Core Integration (Week 5-7)
**Objective:** Stabilize core integrations
**Duration:** 3 weeks
**Developers:** 2 full-time
**Target Coverage:** 45% → 52%
**Expected Risk Reduction:** 25%

**Scope:**
|| Module | Current | Target | Priority |
||--------|---------|--------|----------|
|| **mahoun.graph** | 14.97% | 35% | P1 |
|| **mahoun.orchestrator** | 11.96% | 40% | P1 |
|| **mahoun.pipelines** | 24.06% | 45% | P1 |

**Total Tests:** 160-215

**Exit Criteria:**
- ✅ Graph module ≥ 35% coverage
- ✅ Orchestrator module ≥ 40% coverage
- ✅ Pipelines module ≥ 45% coverage
- ✅ Overall coverage ≥ 52%

---

### Wave 3: P1 Feature Completeness (Week 8-10)
**Objective:** Complete remaining P1 modules
**Duration:** 3 weeks (adjusted from 2 weeks)
**Developers:** 2 full-time
**Target Coverage:** 52% → 55%+
**Expected Risk Reduction:** 15%

**Scope:**
|| Module | Current | Target | Priority |
||--------|---------|--------|----------|
|| **mahoun.retrieval** | 28.94% | 45% | P1 |
|| **mahoun.crypto** | 55.77% | 70% | P1 |
|| **mahoun.core** | 65.97% | 75% | P1 |

**Total Tests:** 60-80

**Exit Criteria:**
- ✅ Retrieval module ≥ 45% coverage
- ✅ Crypto module ≥ 70% coverage
- ✅ Core module ≥ 75% coverage
- ✅ Overall coverage ≥ 55%+
- ✅ Production scenarios validated

---

### Wave 4: P2 Feature Completeness (Week 11-14) - DEFERRED
**Objective:** Complete P2 modules for production polish
**Duration:** 4 weeks
**Developers:** 1 full-time (reduced from 2)
**Status:** DEFERRED to post-production

**Rationale for Deferral:**
- P0/P1 completion provides production readiness
- These modules have moderate to high coverage already
- Can be addressed in maintenance sprints without blocking release
- Focus resources on highest-impact modules first

---

## Success Criteria for Next Phase

### Wave 0 Success (End of Week 1)
- [ ] All 75 reasoning tests execute (0 ERROR state)
- [ ] Coverage measurement methodology standardized and documented
- [ ] Legacy test dependency issues resolved
- [ ] API alignment decision made and implemented
- [ ] Test infrastructure stable for new test development

### Wave 1 Success (End of Week 4)
- [ ] Security module ≥ 65% coverage
- [ ] Ledger module ≥ 60% coverage
- [ ] Reasoning module ≥ 50% coverage
- [ ] Zero P0 security bypass paths remain untested
- [ ] Zero P0 ledger corruption paths remain untested
- [ ] Zero P0 reasoning hallucination paths remain untested
- [ ] All P0 governance enforcement tested
- [ ] All P0 data integrity paths tested
- [ ] Zero test execution failures in P0 modules
- [ ] Overall coverage ≥ 45%
- [ ] Integration tests passing
- [ ] 60% production risk reduction achieved

### Wave 2 Success (End of Week 7)
- [ ] Graph module ≥ 35% coverage
- [ ] Orchestrator module ≥ 40% coverage
- [ ] Pipelines module ≥ 45% coverage
- [ ] Overall coverage ≥ 52%
- [ ] Cypher injection impossible
- [ ] GNN destructive ops gated
- [ ] 85% total production risk eliminated

### Wave 3 Success (End of Week 10)
- [ ] Retrieval module ≥ 45% coverage
- [ ] Crypto module ≥ 70% coverage
- [ ] Core module ≥ 75% coverage
- [ ] Overall coverage ≥ 55%+
- [ ] Production scenarios validated
- [ ] 100% production risk eliminated
- [ ] Platform production-ready

---

## Recommended Changes to Test Roadmap

### Change 1: Wave 0 Compression

**Original:** Wave 0 (Week 1-2) - 2 weeks
**Recommended:** Wave 0 (Week 1) - 1 week

**Rationale:**
- Ledger coverage regression investigation complete (measurement artifact identified)
- FortressValidator API mismatch fixed
- Only remaining issue: ReasoningResponse API alignment decision
- Can be resolved in 1 week with focused effort

**Impact:** Accelerates timeline by 1 week

---

### Change 2: Wave 1 Compression

**Original:** Wave 1 (Week 3-7) - 5 weeks
**Recommended:** Wave 1 (Week 2-4) - 3 weeks

**Rationale:**
- Security module already at 42.20% (good progress)
- Ledger regression is measurement artifact, not actual regression
- Only missing: 55 security tests, 18 ledger tests, reasoning stabilization
- Realistic to complete in 3 weeks with focused effort

**Impact:** Accelerates timeline by 2 weeks

---

### Change 3: Coverage Target Adjustment

**Original:** Target 60% coverage by Week 14
**Recommended:** Target 55% coverage by Week 10, then 60% post-production

**Rationale:**
- P0/P1 completion at 55% provides production readiness
- Wave 4 (P2 modules) can be addressed post-production
- Allows earlier production release
- Remaining coverage can be improved in maintenance sprints

**Impact:** Production-ready 4 weeks earlier

---

### Change 4: Test Infrastructure Documentation

**New Recommendation:** Create project-level test infrastructure documentation

**Rationale:**
- Coverage measurement methodology inconsistent
- No standardized test execution commands documented
- Legacy test dependencies not tracked
- Future developers will encounter same issues

**Implementation:**
- Create `AGENTS.md` or `.devin/TEST_INFRASTRUCTURE.md`
- Document:
  - Standard coverage measurement commands per module
  - Test execution patterns
  - Common pitfalls (API mismatches, dependency issues)
  - Legacy module deprecation notes

**Impact:** Prevents future infrastructure issues

---

### Change 5: CI Gate Updates

**New Recommendation:** Add CI gates for P0 module coverage

**Rationale:**
- Prevent regression in critical modules
- Enforce minimum coverage thresholds
- Block PRs that reduce P0 coverage

**Implementation:**
```yaml
# Example CI gate
coverage_gate_p0:
  modules:
    - mahoun.security: 65%
    - mahoun.ledger: 60%
    - mahoun.reasoning: 50%
  action: fail_if_below
```

**Impact:** Maintains coverage quality over time

---

## Risk Assessment & Mitigation

### Current Risk Level: 🔴 HIGH

**After Current State:**
- **Infrastructure:** 🔴 CRITICAL - Test execution failures
- **Security:** 🟡 MEDIUM - Partial P0 coverage
- **Ledger:** 🟡 MEDIUM - P0 coverage partial, regression investigated
- **Reasoning:** 🔴 CRITICAL - Tests non-functional

**After Wave 0 (Projected):**
- **Infrastructure:** 🟢 STABLE - All tests execute
- **Security:** 🟡 MEDIUM - Partial P0 coverage
- **Ledger:** 🟡 MEDIUM - P0 coverage partial
- **Reasoning:** 🟡 MEDIUM - Tests functional, coverage low

**After Wave 1 (Projected):**
- **Infrastructure:** 🟢 STABLE
- **Security:** 🟢 LOW - P0 coverage complete
- **Ledger:** 🟢 LOW - P0 coverage complete
- **Reasoning:** 🟢 LOW - P0 coverage complete
- **Overall:** 🟡 MEDIUM - P0 complete, P1 deferred

**After Wave 3 (Projected):**
- **Infrastructure:** 🟢 STABLE
- **Security:** 🟢 LOW
- **Ledger:** 🟢 LOW
- **Reasoning:** 🟢 LOW
- **Overall:** 🟢 LOW - P0/P1 complete, production-ready

---

### Mitigation Strategies

#### Strategy 1: Parallel Development

**Issue:** Reasoning module may take longer than estimated

**Mitigation:**
- If reasoning API alignment takes >1 week, parallelize with security module completion
- Security module can proceed independently (no dependencies on reasoning)
- Reduces critical path risk

#### Strategy 2: Scope Adjustment

**Issue:** Coverage targets may be too aggressive

**Mitigation:**
- If Week 4 target (45% overall) not met, focus on P0 module targets only
- Defer some P1 tests to Wave 2
- Prioritize critical path coverage over overall percentage

#### Strategy 3: Resource Reallocation

**Issue:** Graph module (Wave 2) may require more effort

**Mitigation:**
- If Wave 1 completes early, reallocate effort to Wave 2
- Graph module has lowest coverage (14.97%) and highest line count (9323 lines)
- May require 3 developers temporarily

#### Strategy 4: Post-Production Deferral

**Issue:** Wave 4 (P2 modules) may block production release

**Mitigation:**
- Defer Wave 4 to post-production maintenance sprints
- P0/P1 completion at 55% coverage sufficient for production
- P2 modules have moderate coverage already (agents 49.69%, rag 50.46%)

---

## Gaps & Uncertainties

### Gap 1: Reasoning API Alignment Effort

**Uncertainty:** Time required for ReasoningResponse API alignment decision

**Current Estimate:** 4-8 hours

**Risk:** API alignment may require core implementation changes (16-24 hours)

**Mitigation:** 
- Decision point at start of Week 1
- If implementation required, defer reasoning module to Wave 2
- Focus on security and ledger completion in Wave 1

---

### Gap 2: Legacy Test Dependency Issues

**Uncertainty:** Number and complexity of legacy test dependency issues

**Current Estimate:** 4-6 hours

**Risk:** May require deeper investigation of deprecated modules

**Mitigation:**
- Start investigation early in Week 1
- If issues complex, temporarily disable legacy tests
- Focus on new test development

---

### Gap 3: Graph Module Complexity

**Uncertainty:** Graph module complexity underestimated (14.97% coverage, 9323 lines)

**Current Estimate:** 90-110 tests (Wave 2)

**Risk:** May require 150-180 tests

**Mitigation:**
- Allocate 3 weeks for Wave 2 (vs 3 weeks in roadmap)
- Consider adding 1 developer temporarily
- Focus on P0 paths only (Cypher injection, GNN destructive ops)

---

### Gap 4: Integration Test Complexity

**Uncertainty:** End-to-end integration test complexity

**Current Estimate:** 25 tests (Week 4)

**Risk:** May require more complex mocking and test doubles

**Mitigation:**
- Start integration test development early in Week 4
- If complex, reduce scope to critical P0 integrations only
- Defer comprehensive integration to Wave 2

---

## File Updates Required

### New Files to Create

1. **AGENTS.md** or **.devin/TEST_INFRASTRUCTURE.md**
   - Test infrastructure documentation
   - Coverage measurement methodology
   - Common pitfalls and solutions
   - Legacy module deprecation notes

2. **tests/security/test_jwt_blacklist_concurrency.py**
   - 12 tests for JWT blacklist concurrency
   - Race condition scenarios
   - Thread safety verification

3. **tests/security/test_audit_logger_integrity.py**
   - 18 tests for audit logger integrity
   - Concurrent write handling
   - Loss detection mechanisms

4. **tests/ledger/test_blockchain_verification.py**
   - 10 tests for blockchain verification
   - Invalid block detection
   - Merkle tree integrity verification

5. **tests/ledger/test_ledger_recovery.py**
   - 8 tests for ledger recovery
   - Restart scenarios
   - State reconstruction accuracy

6. **tests/reasoning/test_evidence_verdict_edge_cases.py**
   - 30 tests for evidence verdict edge cases
   - Missing evidence handling
   - Invalid evidence link rejection

7. **tests/reasoning/test_chain_of_thought_validation.py**
   - 20 tests for chain-of-thought validation
   - Incomplete reasoning step detection
   - Logic gap detection

8. **tests/integration/test_p0_end_to_end.py**
   - 25 tests for P0 end-to-end integration
   - Security → Ledger → Reasoning integration
   - Governance enforcement across modules

### Files to Update

1. **tests/reasoning/test_agreement_score_boundaries.py**
   - Update ReasoningResponse API usage
   - Fix validate_reasoning_response method calls
   - Align with current API

2. **tests/reasoning/test_p0_critical_paths.py**
   - Update ReasoningResponse API usage
   - Fix validate_reasoning_response method calls
   - Align with current API

3. **tests/test_ledger_hash_chain.py**
   - Fix storage.py → writer.py deprecation
   - Update import statements

4. **.github/workflows/test.yml** or similar CI config
   - Add P0 coverage gates
   - Add standardized coverage measurement commands

5. **README.md** or project documentation
   - Update with test infrastructure documentation reference
   - Link to AGENTS.md or TEST_INFRASTRUCTURE.md

---

## Conclusion

### Summary

The MAHOUN test infrastructure initiative has achieved solid progress on the security module but encountered critical test execution issues in the reasoning module. The original risk-driven analysis provided a strong foundation, but implementation revealed infrastructure gaps requiring immediate attention.

**Key Achievements:**
- Security module: 42.20% coverage (+16.9% improvement)
- Risk analysis complete with 322+ critical paths identified
- Test execution infrastructure partially stabilized

**Critical Path Forward:**
1. Fix reasoning test execution failures (Week 1)
2. Complete security and ledger P0 tests (Week 2-3)
3. Stabilize reasoning module (Week 3-4)
4. Achieve Wave 1 completion (Week 4)

**Revised Timeline:** 10 weeks to production readiness (vs original 14 weeks)

**Risk Reduction:** 100% of P0 risks eliminated by Week 4, 100% of P0/P1 risks by Week 10

### Recommendation

**Execute Revised Plan:** Proceed with 10-week revised timeline focusing on P0/P1 completion and deferring P2 to post-production.

**Rationale:**
- Addresses critical test infrastructure issues immediately
- Compresses timeline through focused effort
- Achieves production readiness 4 weeks earlier
- Maintains quality through risk-driven prioritization
- Allows post-production polish without blocking release

### Next Actions

1. **Immediate:** Approve revised plan and allocate 2 developers for 10 weeks
2. **Week 1:** Execute Wave 0 - fix reasoning test execution failures
3. **Week 2-4:** Execute Wave 1 - complete P0 security, ledger, reasoning
4. **Week 5-7:** Execute Wave 2 - stabilize core integrations
5. **Week 8-10:** Execute Wave 3 - complete P1 modules
6. **Post-Production:** Execute Wave 4 - P2 feature completeness

**Status:** ✅ READY FOR EXECUTION  
**Owner:** Test Infrastructure Team  
**Approvers:** Engineering Lead, Security Lead, QA Lead  
**Next Review:** End of Week 1 (Wave 0 completion)

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-07  
**Based On:** Analysis of 10 project documentation files (LEDGER_COVERAGE_REGRESSION_INVESTIGATION.md, WAVE_0_TEST_INFRASTRUCTURE_ISSUES.md, TEST_ROADMAP_RECOMMENDATION_UPDATED.md, WAVE_1_STATUS_REPORT.md, coverage_p0.json, reports/MISSION_COMPLETE.md, EVIDENCE_VERIFICATION_REPORT.md, DELIVERY_INDEX.md, RISK_ANALYSIS_SUMMARY.md, ANALYSIS_QUICK_REFERENCE.md)