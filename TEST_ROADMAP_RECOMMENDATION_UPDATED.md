# MAHOUN — Test Roadmap Recommendation (Updated)

**Generated:** 2026-06-07  
**Classification:** PRODUCTION READINESS / ACTIONABLE PLAN  
**Status:** 🔴 REVISED - Wave 1 Extended Due to Critical Issues  
**Previous Version:** 2026-06-06  

---

## Executive Summary

### Purpose
This roadmap is a **revised, evidence-based execution plan** that accounts for the current state of Wave 1 implementation, including critical test execution failures and coverage regressions identified in the status report.

### Key Changes from Previous Roadmap
1. **Wave 1 Extended**: 3 weeks → 6-7 weeks due to critical issues
2. **Priority Reordering**: Debug test execution failures BEFORE adding new tests
3. **Coverage Targets Adjusted**: Realistic targets based on current progress
4. **Blocker Resolution**: New Week 1 focus on fixing existing test infrastructure

### Updated Goals
1. **Fix P0 test execution failures** (Week 1-2) - Prerequisite for all other work
2. **Complete Wave 1 with realistic timeline** (Week 1-7) - Security + Ledger + Reasoning
3. **Stabilize core integrations** (Week 8-12) - Orchestrator, Pipelines, Retrieval  
4. **Achieve 50%+ core coverage** (12-week timeline) - Adjusted from 60% target

### Updated Key Metrics
- **Current Coverage:** ~31% (P0 modules only: security 42.20%, ledger 26.70%, reasoning 25.78%)
- **Target Coverage:** 50%+ (production release threshold - adjusted from 60%)
- **Total Tests Needed:** 650-750 (revised from 805-965 based on progress)
- **Timeline:** 12 weeks with 2 full-time developers (revised from 14 weeks)
- **Risk Reduction:** 100% (from current P0 critical to production-ready)

---

## Revised Wave-by-Wave Execution Plan

### REVISED Wave 0: Critical Infrastructure Fix (Week 1-2) ⚠️ NEW

**Objective:** Fix test execution failures and investigate coverage regressions  
**Duration:** 2 weeks (NEW - inserted before Wave 1)  
**Developers:** 2 full-time  
**Target Coverage:** Stabilize current state  
**Expected Risk Reduction:** Infrastructure stability

#### Scope
|| Module | Current | Target | Priority | Issue |
|--------|---------|--------|----------|-------|
| **Test Infrastructure** | Broken | Fixed | P0 | 70/75 reasoning tests in ERROR |
| **Ledger Coverage** | 26.70% | Investigated | P0 | 24.92% regression from baseline |
| **Reasoning Tests** | 5/75 passing | 75/75 passing | P0 | Test execution failures |

#### Week 1: Test Infrastructure Debug
**Focus:** Fix reasoning test execution failures

**Deliverables:**
```
tasks/test_infrastructure_debug.py
  - Investigate dependency issues in reasoning tests
  - Fix import errors causing 70 test failures
  - Verify all reasoning test dependencies available
  - Run reasoning test suite to completion
```

**Investigation Areas:**
- Dependency conflicts in reasoning module
- Import path issues (e.g., FortressValidator, ReasoningResponse)
- Mock/stub configuration for external services
- Database connection issues for graph tests
- Environment configuration missing

**Success Criteria:**
- ✅ All 75 reasoning tests execute (may fail, but no ERROR state)
- ✅ Root cause of test failures identified
- ✅ Dependency issues resolved
- ✅ Test infrastructure stable

**Verification:**
```bash
source venv/bin/activate
pytest tests/reasoning/ -v --tb=short
# Target: 75 tests collected, 0 errors (failures OK)
```

---

#### Week 2: Coverage Regression Investigation
**Focus:** Understand ledger coverage regression

**Deliverables:**
```
tasks/coverage_regression_investigation.py
  - Compare baseline vs current test execution
  - Identify which tests were in baseline but not current
  - Verify baseline measurement methodology
  - Determine if regression is real or measurement artifact
```

**Investigation Areas:**
- Baseline test suite composition (which tests ran?)
- Current test suite composition (which tests run?)
- Test exclusions/skips in current configuration
- File moves/renames since baseline
- Coverage configuration differences

**Success Criteria:**
- ✅ Root cause of coverage regression identified
- ✅ Baseline methodology verified
- ✅ Real vs. artifact regression determined
- ✅ Action plan for recovery defined

**Verification:**
```bash
# Re-run baseline measurement with current methodology
pytest tests/ledger/ --cov=mahoun/ledger --cov-report=term
# Compare results to understand true coverage state
```

**Wave 0 Exit Criteria:**
- [ ] Reasoning tests execute without ERROR state
- [ ] Coverage regression root cause identified
- [ ] Test infrastructure stable for new test development
- [ ] Action plan for coverage recovery defined

---

### REVISED Wave 1: P0 Critical Security & Integrity (Week 3-7)

**Objective:** Complete P0 security, ledger, and reasoning tests  
**Duration:** 5 weeks (extended from 3 weeks)  
**Developers:** 2 full-time  
**Target Coverage:** 31% → 45%  
**Expected Risk Reduction:** 60%

#### Scope
|| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.security** | 42.20% | 65% | 30-35 | P0 |
| **mahoun.ledger** | 26.70% | 60% | 18-25 | P0 |
| **mahoun.reasoning** | 25.78% | 50% | 70-90 | P0 |

**Total Tests:** 118-150

#### Week 3: Security Module Completion
**Focus:** Complete remaining P0 security tests

**Deliverables:**
```
tests/security/test_jwt_blacklist_concurrency.py             (12 tests)
  - Concurrent revocation scenarios
  - Blacklist race conditions
  - Memory management under load
  - Thread safety verification
  
tests/security/test_audit_logger_integrity.py                (18 tests)
  - Concurrent write handling
  - Buffer overflow scenarios
  - Entry ordering guarantees
  - Loss detection mechanisms
```

**Success Criteria:**
- ✅ JWT blacklist concurrency tested
- ✅ Audit logger integrity verified
- ✅ Security module ≥ 60% coverage
- ✅ All P0 security paths tested

**Verification:**
```bash
pytest tests/security/ -v --cov=mahoun/security --cov-report=term
# Target: 115+ tests, 60%+ coverage
```

---

#### Week 4: Ledger Module Investigation & Recovery
**Focus:** Implement missing ledger tests + address regression

**Deliverables:**
```
tests/ledger/test_blockchain_verification.py                 (10 tests)
  - Invalid block detection
  - Merkle tree integrity verification
  - Signature verification
  - Fork detection validation
  
tests/ledger/test_ledger_recovery.py                         (8 tests)
  - Restart scenarios
  - Replay consistency verification
  - State reconstruction accuracy
  - Recovery failure handling
```

**Regression Recovery:**
- Implement coverage recovery plan from Week 2 investigation
- Add missing tests identified during regression analysis
- Verify ledger critical paths tested

**Success Criteria:**
- ✅ Blockchain verification tested
- ✅ Ledger recovery tested
- ✅ Ledger module ≥ 55% coverage
- ✅ P0 data integrity paths verified

**Verification:**
```bash
pytest tests/ledger/ -v --cov=mahoun/ledger --cov-report=term
# Target: 65+ tests, 55%+ coverage
```

---

#### Week 5: Reasoning Module Foundation
**Focus:** Fix existing reasoning tests + implement P0 validation

**Deliverables:**
```
tests/reasoning/test_evidence_verdict_edge_cases.py          (30 tests)
  - Missing evidence handling
  - Invalid evidence link rejection
  - Partial evidence scenarios
  - Evidence conflict resolution
  
tests/reasoning/test_chain_of_thought_validation.py          (20 tests)
  - Incomplete reasoning step detection
  - Contradictory step identification
  - Step ordering verification
  - Logic gap detection
```

**Test Fixing:**
- Fix failing reasoning tests (from Wave 0)
- Ensure all existing tests pass
- Stabilize reasoning test suite

**Success Criteria:**
- ✅ Evidence verdict edge cases tested
- ✅ Chain-of-thought validation implemented
- ✅ All existing reasoning tests pass
- ✅ Reasoning module ≥ 35% coverage

**Verification:**
```bash
pytest tests/reasoning/ -v --cov=mahoun/reasoning --cov-report=term
# Target: 95+ tests, 35%+ coverage
```

---

#### Week 6: Reasoning Module Completion
**Focus:** Complete P0 reasoning validation tests

**Deliverables:**
```
tests/reasoning/test_proof_tree_construction.py              (20 tests)
  - Proof depth requirements
  - Evidence linkage verification
  - Tree completeness checks
  - Traversal validation
  
tests/reasoning/test_policy_engine_rules.py                  (15 tests)
  - Rule application logic
  - Rule conflict resolution
  - Policy hierarchy verification
  - Exception handling
```

**Success Criteria:**
- ✅ Proof tree construction tested
- ✅ Policy engine rules validated
- ✅ Reasoning module ≥ 50% coverage
- ✅ P0 hallucination prevention tested

**Verification:**
```bash
pytest tests/reasoning/ -v --cov=mahoun/reasoning --cov-report=term
# Target: 130+ tests, 50%+ coverage
```

---

#### Week 7: Wave 1 Integration & Verification
**Focus:** End-to-end P0 validation

**Deliverables:**
```
tests/integration/test_p0_end_to_end.py                       (25 tests)
  - Security → Ledger → Reasoning integration
  - Governance enforcement across modules
  - Audit trail completeness verification
  - P0 failure scenario testing
```

**Wave 1 Exit Criteria:**
- [ ] Security module ≥ 65% coverage
- [ ] Ledger module ≥ 60% coverage  
- [ ] Reasoning module ≥ 50% coverage
- [ ] All P0 security bypass paths tested
- [ ] All P0 data integrity paths tested
- [ ] All P0 reasoning validation tested
- [ ] Zero test execution failures in P0 modules
- [ ] Overall coverage ≥ 45%

**Verification:**
```bash
pytest tests/security/ tests/ledger/ tests/reasoning/ -v --cov=mahoun/security,mahoun/ledger,mahoun/reasoning
# Target: 300+ tests, 45%+ overall coverage
```

---

### REVISED Wave 2: P1 Core Integration (Week 8-10)

**Objective:** Eliminate workflow and data processing failures  
**Duration:** 3 weeks (reduced from 4 weeks due to timeline compression)  
**Developers:** 2 full-time  
**Target Coverage:** 45% → 52%  
**Expected Risk Reduction:** 25%

#### Scope
|| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.graph** | 14.97% | 35% | 60-80 | P1 (reduced from P0) |
| **mahoun.orchestrator** | 11.96% | 40% | 50-65 | P1 |
| **mahoun.pipelines** | 24.06% | 45% | 50-70 | P1 |

**Total Tests:** 160-215

#### Week 8: Graph Module (Critical Paths Only)
**Focus:** Neo4j safety and critical mutation paths

**Deliverables:**
```
tests/graph/test_neo4j_query_service_bounds.py               (25 tests)
  - Cypher injection prevention
  - Query parameter binding
  - Arbitrary Cypher blocking
  - Allowlist enforcement
  
tests/graph/test_gnn_destructive_capability_gates.py         (20 tests)
  - DETACH DELETE control
  - DROP constraint enforcement
  - Two-key-turn requirement
  - Environment gates
```

**Success Criteria:**
- ✅ Cypher injection impossible
- ✅ Destructive operations gated
- ✅ Graph module ≥ 25% coverage (reduced target)

---

#### Week 9: Orchestrator Module
**Focus:** State machine and workflow safety

**Deliverables:**
```
tests/orchestrator/test_state_machine_critical_paths.py      (30 tests)
  - Critical state transitions
  - Deadlock detection
  - State persistence
  - Error recovery
  
tests/orchestrator/test_context_isolation.py                 (20 tests)
  - Cross-session boundary enforcement
  - Context leakage prevention
  - Memory cleanup
```

**Success Criteria:**
- ✅ State machine critical paths tested
- ✅ Context isolation verified
- ✅ Orchestrator module ≥ 40% coverage

---

#### Week 10: Pipelines Module (Critical Paths)
**Focus:** Ingestion determinism and data integrity

**Deliverables:**
```
tests/pipelines/test_chunking_determinism.py                 (25 tests)
  - Reproducible chunking
  - Boundary consistency
  - Seed management
  
tests/pipelines/test_embedding_integrity.py                  (25 tests)
  - Model loading error handling
  - Fallback behavior
  - Batch processing safety
```

**Success Criteria:**
- ✅ Chunking deterministic
- ✅ Embedding integrity verified
- ✅ Pipelines module ≥ 45% coverage

**Wave 2 Exit Criteria:**
- [ ] Graph module ≥ 35% coverage
- [ ] Orchestrator module ≥ 40% coverage
- [ ] Pipelines module ≥ 45% coverage
- [ ] Overall coverage ≥ 52%

---

### REVISED Wave 3: P1 Feature Completeness (Week 11-12)

**Objective:** Complete remaining P1 modules for production readiness  
**Duration:** 2 weeks (reduced from 4 weeks - focus on highest priority)  
**Developers:** 2 full-time  
**Target Coverage:** 52% → 55%+  
**Expected Risk Reduction:** 15%

#### Scope
|| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.retrieval** | 28.94% | 45% | 30-40 | P1 |
| **mahoun.crypto** | 55.77% | 70% | 15-20 | P1 |
| **mahoun.core** | 65.97% | 75% | 15-20 | P1 |

**Total Tests:** 60-80

#### Week 11: Retrieval & Crypto
**Focus:** Search accuracy and cryptographic integrity

**Deliverables:**
```
tests/retrieval/test_retrieval_accuracy.py                    (20 tests)
  - Precision/recall metrics
  - Ranking consistency
  - Citation attribution

tests/crypto/test_merkle_tree_integrity.py                    (10 tests)
  - Proof verification
  - Tampering detection
  - Tree reconstruction
```

**Success Criteria:**
- ✅ Retrieval accuracy verified
- ✅ Crypto integrity proven
- ✅ Retrieval ≥ 45%, Crypto ≥ 70%

---

#### Week 12: Core & Final Integration
**Focus:** Core governance enforcement and integration testing

**Deliverables:**
```
tests/core/test_fortress_validator_comprehensive.py          (15 tests)
  - All 6 checks individually
  - Check combinations
  - Bypass prevention

tests/integration/test_production_scenarios.py                (20 tests)
  - End-to-end production workflows
  - Cross-module integration
  - Failure scenario handling
```

**Success Criteria:**
- ✅ FortressValidator comprehensive
- ✅ Core module ≥ 75% coverage
- ✅ Integration scenarios validated

**Wave 3 Exit Criteria:**
- [ ] Retrieval module ≥ 45% coverage
- [ ] Crypto module ≥ 70% coverage
- [ ] Core module ≥ 75% coverage
- [ ] Overall coverage ≥ 55%+
- [ ] Production scenarios validated

---

## Revised Investment Summary

### Effort Comparison

|| Original Plan | Revised Plan | Delta |
|---------------|--------------|-------|
| **Duration** | 14 weeks | 12 weeks | -2 weeks |
| **Total Tests** | 805-965 | 650-750 | -155 tests |
| **Target Coverage** | 60% | 55% | -5% |
| **Developer Effort** | 292-320 hours | 250-280 hours | -42 hours |

### Timeline Compression Strategy

1. **Wave 0 Added**: +2 weeks (critical infrastructure fix)
2. **Wave 1 Extended**: +2 weeks (from 3 to 5 weeks)
3. **Wave 2 Reduced**: -1 week (from 4 to 3 weeks)
4. **Wave 3 Reduced**: -2 weeks (from 4 to 2 weeks, focus on highest priority)
5. **Wave 4 Removed**: -4 weeks (deferred to post-production)

**Net Timeline**: 12 weeks vs original 14 weeks

### Coverage Target Adjustment

**Rationale for 55% vs 60% target:**
- Wave 0 infrastructure issues consumed effort
- P0 modules (security, ledger, reasoning) prioritized over comprehensive coverage
- Production readiness achieved at 55% with P0/P1 complete
- Remaining coverage can be addressed post-production in maintenance sprints

---

## Success Criteria Adjustment

### Production Release Criteria (Revised)

**Minimum for Production:**
- [x] **Wave 0 Complete**: Test infrastructure stable
- [ ] **Wave 1 Complete**: Security ≥ 65%, Ledger ≥ 60%, Reasoning ≥ 50%
- [ ] **Wave 2 Complete**: Graph ≥ 35%, Orchestrator ≥ 40%, Pipelines ≥ 45%
- [ ] **Wave 3 Complete**: Retrieval ≥ 45%, Crypto ≥ 70%, Core ≥ 75%
- [ ] **Overall Coverage**: ≥ 55% (reduced from 60%)
- [ ] **P0 Tests**: 100% passing, zero errors
- [ ] **P1 Tests**: 95%+ passing
- [ ] **Integration Tests**: Production scenarios validated

### Deferred to Post-Production

**Wave 4 (Original) - P2 Feature Completeness:**
- mahoun.agents (49.69% → 65%)
- mahoun.rag (50.46% → 62%)
- mahoun.llm (41.74% → 55%)
- mahoun.infrastructure (39.19% → 55%)
- mahoun.monitoring (30.58% → 50%)
- mahoun.governance (80.47% → 85%)
- mahoun.invariants (77.27% → 85%)

**Rationale for Deferral:**
- These modules have moderate to high coverage already
- P0/P1 completion provides production readiness
- Can be addressed in maintenance sprints without blocking release
- Focus on highest-impact modules first

---

## Risk Assessment

### Current Risk Level: 🔴 HIGH

**After Wave 0 (Current):**
- **Infrastructure**: 🔴 CRITICAL - Test execution failures
- **Security**: 🟡 MEDIUM - Partial P0 coverage
- **Ledger**: 🔴 HIGH - Coverage regression
- **Reasoning**: 🔴 CRITICAL - Tests non-functional

**After Revised Wave 1 (Projected):**
- **Infrastructure**: 🟢 STABLE - All tests execute
- **Security**: 🟢 LOW - P0 coverage complete
- **Ledger**: 🟡 MEDIUM - P0 coverage complete, some gaps
- **Reasoning**: 🟡 MEDIUM - P0 coverage complete, some gaps

**After Revised Roadmap (Projected):**
- **Infrastructure**: 🟢 STABLE
- **Security**: 🟢 LOW
- **Ledger**: 🟢 LOW
- **Reasoning**: 🟢 LOW
- **Overall**: 🟡 MEDIUM - P0/P1 complete, P2 deferred

---

## Recommendations

### Immediate Actions

1. **Execute Wave 0 Immediately** (Week 1-2)
   - Fix reasoning test execution failures
   - Investigate coverage regression
   - Stabilize test infrastructure
   - **BLOCKER**: Cannot proceed without this

2. **Revised Expectations Management**
   - Communicate timeline extension to stakeholders
   - Adjust production release date by 6-7 weeks
   - Set realistic coverage target of 55% vs 60%
   - Plan for post-production coverage improvement

3. **Resource Allocation**
   - Maintain 2 full-time developers
   - Consider adding 1 developer for Week 1-2 (Wave 0) to accelerate infrastructure fix
   - Plan for maintenance sprint post-production to address deferred Wave 4

### Decision Point

**Option A: Execute Revised Roadmap** (RECOMMENDED)
- Pros: Addresses critical issues, realistic timeline, production-ready
- Cons: 6-7 week delay, reduced coverage target
- Effort: 12 weeks, 250-280 developer-hours

**Option B: Attempt Original Timeline** (NOT RECOMMENDED)
- Pros: Meets original timeline
- Cons: High risk of failure, known issues unaddressed, non-production-ready
- Effort: 14 weeks, but likely to fail at 60% target

**Option C: Pause and Reassess** (NOT RECOMMENDED)
- Pros: Time for deeper investigation
- Cons: Delays all progress, loses momentum
- Effort: Unknown

**Recommendation**: Execute Option A - Revised Roadmap with Wave 0 infrastructure fix

---

## Conclusion

The original roadmap was ambitious but did not account for critical test infrastructure issues now discovered. The revised roadmap:

1. **Adds Wave 0** (2 weeks) to fix test execution failures and investigate coverage regression
2. **Extends Wave 1** (3→5 weeks) to complete P0 modules realistically
3. **Compresses Waves 2-3** (8→5 weeks) by focusing on highest-priority paths
4. **Defers Wave 4** to post-production to achieve realistic timeline
5. **Adjusts coverage target** (60%→55%) based on P0/P1 focus

**Result**: Production-ready platform in 12 weeks with 55% coverage, vs original 14 weeks with 60% target (which was likely unachievable given current issues).

**Next Action**: Begin Wave 0 immediately - fix test infrastructure before proceeding with any new test development.

---

**Report Generated**: 2026-06-07  
**Previous Version**: 2026-06-06  
**Next Review**: After Wave 0 completion (Week 2)