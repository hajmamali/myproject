# Weak Module Analysis Report

**Analysis Date:** 2026-07-16T11:33:25.067685+00:00  
**Modules Analyzed:** 40  
**Spec:** test-suite-recovery Phase 4  
**Requirements:** R4 (Test Strengthening Roadmap)

## Executive Summary

This report identifies production modules with minimal test coverage using AST-based import analysis. The analyzer scanned all test files, extracted production module imports, and classified modules based on test import counts.

**Key Findings:**
- **6 Untested Modules** (0 test imports): dashboard, flows, nlp, profiler, tracing, ultra_systems
- **12 Weak Modules** (1-3 test imports): orchestrator, self_improve, audit, etc.
- **17 Moderate Modules** (4-15 test imports): security, agents, rag, etc.
- **5 Strong Modules** (>15 test imports): core, graph, ledger, pipelines, reasoning

## Classification Summary

### Untested Modules (0 imports)
- dashboard
- flows
- nlp
- profiler
- tracing
- ultra_systems

### Weak Modules (1-3 imports)
- api
- audit
- concurrency
- contracts
- domain
- embeddings
- execution
- invariants
- orchestrator
- self_improve
- services
- uncertainty

### Moderate Modules (4-15 imports)
- agents
- ai
- bootstrap
- crypto
- finetuning
- governance
- guardrails
- infrastructure
- llm
- mcp
- metrics
- monitoring
- preproduction
- rag
- retrieval
- schemas
- security

### Strong Modules (>15 imports)
- core (97 imports)
- graph (60 imports)
- ledger (34 imports)
- pipelines (17 imports)
- reasoning (81 imports)

## Priority Recommendations

Priority scores calculated as: `criticality × complexity × (1 - coverage_proxy)`

### Top 15 High-Priority Modules

| Rank | Module | Lines | Imports | Priority | Classification |
|------|--------|-------|---------|----------|----------------|
| 1 | security | 4,328 | 9 | 0.639 | moderate |
| 2 | orchestrator | 3,759 | 2 | 0.541 | weak |
| 3 | self_improve | 9,104 | 1 | 0.539 | weak |
| 4 | agents | 10,411 | 9 | 0.533 | moderate |
| 5 | ultra_systems | 4,174 | 0 | 0.417 | untested |
| 6 | rag | 7,633 | 10 | 0.400 | moderate |
| 7 | audit | 4,026 | 1 | 0.395 | weak |
| 8 | finetuning | 4,448 | 7 | 0.383 | moderate |
| 9 | llm | 4,239 | 7 | 0.365 | moderate |
| 10 | monitoring | 4,033 | 5 | 0.363 | moderate |
| 11 | ai | 4,164 | 8 | 0.350 | moderate |
| 12 | preproduction | 3,958 | 6 | 0.348 | moderate |
| 13 | schemas | 4,015 | 8 | 0.337 | moderate |
| 14 | pipelines | 25,922 | 17 | 0.330 | strong |
| 15 | retrieval | 3,771 | 7 | 0.324 | moderate |

## Detailed Analysis

### Critical Weak Modules (Priority > 0.3)

#### 1. orchestrator (Priority: 0.541, Weak)
- **Source:** 11 files, 3,759 lines
- **Test Imports:** 2 (weak coverage)
- **Test Files:**
  - `tests/verification/test_category_2_medium.py`
  - `tests/verification/test_category_3_extreme.py`
- **Rationale:** High complexity, moderate criticality, minimal test coverage
- **Recommendation:** Add 8-10 unit tests covering core orchestration logic, state management, and error handling

#### 2. self_improve (Priority: 0.539, Weak)
- **Source:** 12 files, 9,104 lines
- **Test Imports:** 1 (weak coverage)
- **Test Files:**
  - `tests/test_ultra_legal_monitoring.py`
- **Rationale:** Very high complexity (9K+ lines), moderate criticality, single test import
- **Recommendation:** Add comprehensive test suite covering improvement algorithms, feedback loops, and validation logic

#### 3. ultra_systems (Priority: 0.417, Untested)
- **Source:** 10 files, 4,174 lines
- **Test Imports:** 0 (untested)
- **Test Files:** None
- **Rationale:** Moderate complexity, moderate criticality, zero test coverage
- **Recommendation:** Create initial test suite with 10-15 tests covering core system interfaces and integration points

#### 4. audit (Priority: 0.395, Weak)
- **Source:** 6 files, 4,026 lines
- **Test Imports:** 1 (weak coverage)
- **Test Files:**
  - `tests/audit/test_airgap_export.py`
- **Rationale:** High criticality for governance, substantial complexity, minimal test coverage
- **Recommendation:** Add tests for audit trail integrity, export validation, and compliance reporting

## Corrections to Audit Misclassifications

Based on actual import counts from AST analysis:

- **mahoun.agents:** Classified as **moderate** (9 imports), NOT weak as suggested by initial audit
- **mahoun.domain:** Classified as **weak** (3 imports), NOT strong but also not as weak as initial estimate

## Actionable Test Development Roadmap

### Phase 1: Critical Weak Modules (Weeks 1-3)
1. **orchestrator** - Add orchestration logic tests
2. **self_improve** - Create comprehensive improvement algorithm test suite
3. **ultra_systems** - Establish initial test coverage
4. **audit** - Expand audit trail and compliance tests

### Phase 2: Untested Modules (Weeks 4-6)
5. **nlp** - Create NLP processing test suite
6. **tracing** - Add distributed tracing tests
7. **profiler** - Implement profiler validation tests
8. **flows** - Add workflow execution tests
9. **dashboard** - Create dashboard component tests

### Phase 3: Weak Modules with Lower Priority (Weeks 7-10)
10. **uncertainty** - Expand uncertainty quantification tests
11. **services** - Add service layer integration tests
12. **execution** - Create execution engine tests
13. **domain** - Expand domain logic tests
14. **concurrency** - Add concurrency safety tests

### Phase 4: Strengthen Moderate Modules (Ongoing)
- **security** (Priority 0.639) - Add security control tests
- **rag** (Priority 0.400) - Expand RAG pipeline tests
- **llm** (Priority 0.365) - Add LLM integration tests

## Methodology

**AST-Based Import Analysis:**
1. Scanned all `tests/test_*.py` files
2. Parsed Python AST to extract `from mahoun.X import ...` statements
3. Counted unique test files importing each module
4. Classified modules based on import counts:
   - Untested: 0 imports
   - Weak: 1-3 imports
   - Moderate: 4-15 imports
   - Strong: >15 imports

**Priority Scoring Formula:**
```
Priority = criticality_weight × complexity_weight × (1 - coverage_proxy)

Where:
- criticality_weight = Module importance (0.5-1.0)
- complexity_weight = min(1.0, line_count / 5000)
- coverage_proxy = min(1.0, import_count / 50)
```

**Criticality Weights:**
- core: 1.0 (governance kernel)
- reasoning: 0.95 (reasoning engines)
- security: 0.9 (security controls)
- ledger: 0.85 (audit ledger)
- graph: 0.8 (knowledge graph)
- orchestrator: 0.75 (orchestration)
- nlp: 0.7 (NLP processing)
- agents: 0.65 (agent system)
- domain: 0.65 (domain logic)

## Verification Evidence

**AST Scan Results:**
- Test files scanned: 242
- Production modules detected: 40
- Total import statements analyzed: 500+

**Accuracy Validation:**
- Manual spot-check of top 10 modules confirmed import counts
- Cross-referenced with `grep -r "from mahoun.X" tests/` for verification
- AST-based approach more accurate than regex-based grep (handles multi-line imports, conditional imports)

## Next Steps

1. **Review Priority Recommendations** with team leads
2. **Create GitHub Issues** for each high-priority module
3. **Assign Test Development** to appropriate engineers
4. **Track Progress** using coverage metrics
5. **Integrate** with CI coverage gates (Phase 6)

## Appendix: Full Module Analysis

See `WEAK_MODULE_REPORT.json` for complete machine-readable data including:
- All 40 module analyses
- Test file lists for each module
- Source file counts
- Line counts
- Priority scores

---

**Generated by:** `scripts/analyze_weak_modules.py`  
**Evidence:** `.kiro/specs/test-suite-recovery/WEAK_MODULE_REPORT.json`  
**Task:** Phase 4 - Weak Module Analysis (Task 5)
