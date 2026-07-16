# Test Strengthening Roadmap

**Project:** MAHOUN Test Suite Recovery  
**Spec:** test-suite-recovery Phase 4  
**Date:** 2026-07-16  
**Status:** PLANNING

## Mission Objective

Systematically improve test coverage for production modules with minimal test imports, prioritized by criticality, complexity, and current coverage gaps.

## Overview

Based on AST-based import analysis (see `WEAK_MODULE_REPORT.md`), this roadmap provides a phased approach to strengthening weak and untested modules over 10 weeks.

## Success Metrics

- **Target:** Reduce untested modules from 6 to 0
- **Target:** Reduce weak modules from 12 to <5
- **Target:** Achieve >80% line coverage for critical modules (core, reasoning, security, ledger)
- **Target:** Maintain existing strong module coverage (core, graph, ledger, pipelines, reasoning)

## Phased Roadmap

### Phase 1: Critical Weak Modules (Weeks 1-3)

**Goal:** Address highest-priority weak modules with business-critical functionality

#### Week 1: orchestrator (Priority: 0.541)
**Current State:**
- 11 files, 3,759 lines
- 2 test imports (weak)
- Tests: `test_category_2_medium.py`, `test_category_3_extreme.py`

**Test Development Plan:**
1. **Core Orchestration Logic (5 tests)**
   - Orchestrator initialization and configuration
   - State machine transitions
   - Workflow execution paths
   - Error recovery and rollback
   - Resource allocation and cleanup

2. **Integration Points (3 tests)**
   - Agent coordination integration
   - Service lifecycle management
   - Event bus integration

3. **Edge Cases (2 tests)**
   - Concurrent orchestration requests
   - Partial failure scenarios

**Deliverables:**
- `tests/orchestrator/test_core_orchestration.py` (5 tests)
- `tests/orchestrator/test_orchestrator_integration.py` (3 tests)
- `tests/orchestrator/test_orchestrator_edge_cases.py` (2 tests)

**Target Coverage:** 60% line coverage

#### Week 2: self_improve (Priority: 0.539)
**Current State:**
- 12 files, 9,104 lines
- 1 test import (weak)
- Tests: `test_ultra_legal_monitoring.py`

**Test Development Plan:**
1. **Improvement Algorithms (8 tests)**
   - Model quality assessment
   - Feedback loop processing
   - Improvement strategy selection
   - Rollback mechanisms
   - Convergence detection
   - Performance metrics collection
   - Threshold validation
   - Improvement history tracking

2. **Safety Guarantees (4 tests)**
   - Non-degradation validation
   - Improvement validation gates
   - Governance integration
   - Audit trail completeness

3. **Integration Tests (3 tests)**
   - LLM improvement integration
   - Knowledge graph improvement integration
   - End-to-end improvement cycle

**Deliverables:**
- `tests/self_improve/test_improvement_algorithms.py` (8 tests)
- `tests/self_improve/test_safety_guarantees.py` (4 tests)
- `tests/self_improve/test_improvement_integration.py` (3 tests)

**Target Coverage:** 50% line coverage (large complex module)

#### Week 3: audit (Priority: 0.395)
**Current State:**
- 6 files, 4,026 lines
- 1 test import (weak)
- Tests: `test_airgap_export.py`

**Test Development Plan:**
1. **Audit Trail Core (6 tests)**
   - Audit entry creation and validation
   - Immutability guarantees
   - Chain integrity verification
   - Audit query operations
   - Retention policy enforcement
   - Audit archival and rotation

2. **Export and Compliance (4 tests)**
   - Export format validation
   - Regulatory report generation
   - Compliance checks
   - Audit trail reconstruction

3. **Integration Tests (3 tests)**
   - Ledger integration
   - Governance integration
   - Remote ledger synchronization

**Deliverables:**
- `tests/audit/test_audit_trail_core.py` (6 tests)
- `tests/audit/test_export_compliance.py` (4 tests)
- `tests/audit/test_audit_integration.py` (3 tests)

**Target Coverage:** 70% line coverage

### Phase 2: Untested Modules (Weeks 4-6)

**Goal:** Establish baseline test coverage for modules with zero test imports

#### Week 4: ultra_systems (Priority: 0.417) + nlp (Priority: 0.231)
**ultra_systems:**
- 10 files, 4,174 lines, 0 test imports
- **Plan:** Create 12 tests covering system interfaces, data flow, integration points
- **Deliverable:** `tests/ultra_systems/test_system_core.py`
- **Target:** 40% line coverage

**nlp:**
- 2 files, 1,653 lines, 0 test imports
- **Plan:** Create 8 tests covering text processing, entity extraction, language detection
- **Deliverable:** `tests/nlp/test_nlp_processing.py`
- **Target:** 60% line coverage

#### Week 5: tracing (Priority: 0.054) + profiler (Priority: 0.033)
**tracing:**
- 3 files, 544 lines, 0 test imports
- **Plan:** Create 6 tests covering trace capture, trace propagation, trace export
- **Deliverable:** `tests/tracing/test_distributed_tracing.py`
- **Target:** 70% line coverage

**profiler:**
- 2 files, 333 lines, 0 test imports
- **Plan:** Create 5 tests covering profiler initialization, metric collection, report generation
- **Deliverable:** `tests/profiler/test_performance_profiler.py`
- **Target:** 75% line coverage

#### Week 6: flows (Priority: 0.036) + dashboard (Priority: 0.018)
**flows:**
- 2 files, 357 lines, 0 test imports
- **Plan:** Create 7 tests covering flow definition, execution, state management
- **Deliverable:** `tests/flows/test_workflow_flows.py`
- **Target:** 70% line coverage

**dashboard:**
- 2 files, 180 lines, 0 test imports
- **Plan:** Create 4 tests covering dashboard data aggregation, UI integration
- **Deliverable:** `tests/dashboard/test_dashboard_core.py`
- **Target:** 80% line coverage (small module)

### Phase 3: Remaining Weak Modules (Weeks 7-10)

**Goal:** Strengthen modules with 1-3 test imports to >10 imports

#### Week 7: uncertainty (Priority: 0.296) + services (Priority: 0.153)
**uncertainty:**
- 5 files, 3,023 lines, 1 test import
- **Plan:** Add 10 tests for ensemble methods, Gaussian processes, calibration
- **Target:** 12 total imports, 65% line coverage

**services:**
- 2 files, 1,559 lines, 1 test import
- **Plan:** Add 8 tests for service layer logic, request handling
- **Target:** 10 total imports, 70% line coverage

#### Week 8: execution (Priority: 0.141) + domain (Priority: 0.131)
**execution:**
- 4 files, 1,199 lines, 1 test import
- **Plan:** Add 9 tests for execution engine, task scheduling, result handling
- **Target:** 11 total imports, 75% line coverage

**domain:**
- 9 files, 1,070 lines, 3 test imports
- **Plan:** Add 7 tests for domain logic, business rules, validation
- **Target:** 12 total imports, 80% line coverage

#### Week 9: concurrency (Priority: 0.105) + api (Priority: 0.095)
**concurrency:**
- 3 files, 892 lines, 1 test import
- **Plan:** Add 10 tests for concurrent operations, locks, race conditions
- **Target:** 12 total imports, 70% line coverage

**api:**
- 3 files, 966 lines, 1 test import
- **Plan:** Add 8 tests for API endpoints, request validation, error handling
- **Target:** 10 total imports, 75% line coverage

#### Week 10: contracts (Priority: 0.045) + invariants (Priority: 0.017) + embeddings (Priority: 0.050)
**contracts:**
- 11 files, 458 lines, 1 test import
- **Plan:** Add 8 tests for contract validation, governance contracts
- **Target:** 10 total imports, 85% line coverage

**invariants:**
- 3 files, 173 lines, 1 test import
- **Plan:** Add 6 tests for invariant checking, violation detection
- **Target:** 8 total imports, 90% line coverage

**embeddings:**
- 2 files, 510 lines, 1 test import
- **Plan:** Add 7 tests for embedding generation, vector operations
- **Target:** 9 total imports, 75% line coverage

### Phase 4: Strengthen Moderate Modules (Ongoing)

**Goal:** Incrementally improve moderate modules (4-15 imports) to strong (>15 imports)

**Priority Order:**
1. **security** (9 imports → 20 imports) - Add 11 tests for security controls
2. **rag** (10 imports → 20 imports) - Add 10 tests for RAG pipeline
3. **llm** (7 imports → 16 imports) - Add 9 tests for LLM integration
4. **monitoring** (5 imports → 16 imports) - Add 11 tests for monitoring
5. **ai** (8 imports → 16 imports) - Add 8 tests for AI runtime

**Ongoing Activities:**
- Add 2-3 tests per sprint for each moderate module
- Target: Move all moderate modules to strong within 6 months

## Resource Requirements

### Engineering Time (per week)
- **Senior Engineer:** 2 days/week (test design, critical modules)
- **Mid-Level Engineer:** 3 days/week (test implementation)
- **QA Engineer:** 1 day/week (test review, coverage validation)

### Infrastructure
- CI pipeline time: +15 minutes per build (expanded test suite)
- Coverage measurement infrastructure: Already established (Phase 2)
- Test environment: Neo4j test instance, mock LLM services

## Success Criteria

### Phase 1 (Weeks 1-3)
- [ ] orchestrator: 60% coverage, 10+ tests
- [ ] self_improve: 50% coverage, 15+ tests
- [ ] audit: 70% coverage, 13+ tests

### Phase 2 (Weeks 4-6)
- [ ] All 6 untested modules have >40% coverage
- [ ] Zero modules with 0 test imports
- [ ] 30+ new tests created

### Phase 3 (Weeks 7-10)
- [ ] All 12 weak modules promoted to moderate (>4 imports)
- [ ] Total test count: 2,244 → 2,400+
- [ ] Overall coverage: baseline + 5%

### Phase 4 (Ongoing)
- [ ] All moderate modules promoted to strong (>15 imports)
- [ ] Critical modules (core, reasoning, security, ledger) >80% coverage
- [ ] Coverage gates enforcing baseline + regression prevention

## Risk Management

### Risk 1: Test Development Delays
**Mitigation:** Prioritize critical modules first; defer lower-priority modules if needed

### Risk 2: Coverage Measurement Accuracy
**Mitigation:** Use AST-based import analysis (Phase 4) and line coverage measurement (Phase 2)

### Risk 3: Test Maintenance Burden
**Mitigation:** Focus on maintainable unit tests; avoid brittle integration tests; use property-based tests where appropriate

### Risk 4: Resource Constraints
**Mitigation:** Stagger phases; allow 2-week buffer for each phase; engage multiple engineers

## Monitoring and Tracking

### Weekly Metrics
- New tests created (target: 15-20/week)
- Modules promoted from weak to moderate
- Coverage delta from baseline
- Test execution time

### Monthly Reviews
- Phase completion assessment
- Roadmap adjustment based on progress
- Resource reallocation as needed

### Quarterly Goals
- Q1 2026: Complete Phases 1-2 (Critical + Untested)
- Q2 2026: Complete Phase 3 (Weak → Moderate)
- Q3 2026: Phase 4 ongoing (Moderate → Strong)
- Q4 2026: Maintain coverage >80% for all critical modules

## Integration with CI/CD

### Coverage Gates (Phase 6)
- Gate enforces baseline coverage thresholds
- No coverage drops >2% allowed without justification
- New modules require >50% coverage before merge

### Test Classification (Phase 5)
- New tests classified as P1-P2 (regression protection)
- Critical module tests classified as P0 (fail-fast)
- Weak module tests run in CI to prevent future regression

## Dependencies

**Prerequisites:**
- ✅ Phase 1-3 complete (P0 fixes, coverage baseline, debt removal)
- ✅ Phase 4 complete (Weak module analysis)
- 🔄 Phase 5 in progress (CI classification)
- 🔄 Phase 6 in progress (Coverage gates)

**Blockers:**
- None identified

## Conclusion

This roadmap provides a systematic 10-week plan to strengthen MAHOUN's test infrastructure, moving from:
- **6 untested modules → 0 untested**
- **12 weak modules → <5 weak**
- **Overall coverage: baseline → baseline +5%**

Upon completion, MAHOUN will have comprehensive test coverage across all production modules, with automated regression prevention via coverage gates (Phase 6).

---

**Approved By:** [Engineering Lead]  
**Start Date:** [TBD]  
**Review Schedule:** Weekly (Mondays 10am)  
**Generated By:** `scripts/analyze_weak_modules.py` (Phase 4 deliverable)
