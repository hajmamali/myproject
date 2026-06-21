# MAHOUN — Test Roadmap Recommendation
**Generated:** 2026-06-06  
**Classification:** PRODUCTION READINESS / ACTIONABLE PLAN  
**Status:** 🔴 Ready for Execution

---

## Executive Summary

### Purpose
This roadmap translates the Risk-Driven Test Gap Analysis into an **actionable, week-by-week execution plan** for achieving production-ready test coverage.

### Goals
1. **Eliminate P0 production risks** (Weeks 1-6)
2. **Stabilize core integrations** (Weeks 7-10)
3. **Complete feature coverage** (Weeks 11-14)
4. **Achieve 60%+ core coverage** (14-week timeline)

### Key Metrics
- **Current Coverage:** 38.19%
- **Target Coverage:** 60%+ (production release threshold)
- **Total Tests Needed:** 805-965 (realistic estimate, not hypothesis)
- **Timeline:** 14 weeks with 2 full-time developers
- **Risk Reduction:** 100% (from current P0 critical to production-ready)

### Investment
- **Effort:** 292-320 developer-hours total
- **Team:** 2 developers full-time
- **Duration:** 14 weeks (3.5 months)
- **ROI:** Production-ready platform, zero P0 risks, defensible security/audit posture

---

## Wave-by-Wave Execution Plan

### Wave 1: P0 Critical Security & Integrity (Weeks 1-3)
**Objective:** Eliminate security bypass and audit failure risks  
**Duration:** 3 weeks  
**Developers:** 2 full-time  
**Target Coverage:** 38% → 45%  
**Expected Risk Reduction:** 40%

#### Scope
| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.security** | 25.30% | 65% | 65-80 | P0 |
| **mahoun.ledger** | 51.62% | 75% | 45-55 | P0 |
| **mahoun.reasoning** | 43.73% | 60% | 50-60 | P0 (Phase 1) |

**Total Tests:** 185-205

#### Week 1: Security Module (Foundation)
**Focus:** Authentication & Authorization

**Deliverables:**
```
tests/security/test_api_key_lifecycle.py                     (20 tests)
  - Key generation, rotation, expiry
  - Key revocation and cleanup
  - Key validation edge cases
  
tests/security/test_api_key_collision_prevention.py          (8 tests)
  - Hash collision scenarios
  - Key uniqueness verification
  
tests/security/test_rbac_permission_matrix.py                (25 tests)
  - All role × permission combinations
  - Permission inheritance
```
  - Admin privilege checks
  - Role escalation prevention
  
tests/security/test_jwt_token_comprehensive.py               (15 tests)
  - Token creation and verification
  - Token expiry and refresh
  - Blacklist functionality
  
tests/security/test_jwt_blacklist_concurrency.py             (12 tests)
  - Concurrent revocation
  - Blacklist race conditions
  - Memory management
```

**Success Criteria:**
- ✅ API key rotation tested
- ✅ RBAC permission matrix complete
- ✅ JWT blacklist integrity verified
- ✅ Security module >= 50%

**Verification:**
```bash
source venv/bin/activate
pytest tests/security/ -v --cov=mahoun/security --cov-report=term
# Target: 12 files, 80 tests, 50%+ coverage
```

---

#### Week 2: Ledger Module + Security Completion
**Focus:** Data Integrity & Audit Trail

**Deliverables:**
```
tests/security/test_audit_logger_integrity.py                (18 tests)
  - Concurrent write handling
  - Buffer overflow scenarios
  - Entry ordering guarantees
  - Loss detection
  
tests/security/test_pii_scrubber_patterns.py                 (10 tests)
```
  - Known PII patterns
  - Edge case formats
  - False positive prevention
  
tests/security/test_prompt_injection_defense.py              (15 tests)
  - Known attack vectors
  - Escape sequence handling
  - LLM manipulation attempts

tests/ledger/test_hash_chain_integrity.py                    (20 tests)
  - Tampering detection
  - Chain verification
  - Block validation
  - Fork detection
  
tests/ledger/test_concurrent_writes.py                       (15 tests)
  - Race condition handling
  - Write ordering guarantees
  - Conflict resolution
  - Atomicity verification
  
tests/ledger/test_governance_gate_enforcement.py             (12 tests)
  - Governance context validation
  - Bypass attempt prevention
  - Ungoverned write blocking
  - Audit trail completeness
```

**Success Criteria:**
- ✅ Security module >= 65%
- ✅ Ledger hash chain verified
- ✅ Concurrent write safety proven
- ✅ Governance gate enforcement tested

**Verification:**
```bash
pytest tests/security/ tests/ledger/ -v --cov=mahoun/security --cov=mahoun/ledger
# Target: Security 65%+, Ledger 60%+
```

---

#### Week 3: Reasoning Module (Phase 1) + Ledger Completion
**Focus:** Zero-Hallucination Guarantees

**Deliverables:**
```
tests/ledger/test_blockchain_verification.py                 (10 tests)
  - Invalid block detection
  - Merkle tree integrity
  - Signature verification
  
tests/ledger/test_ledger_recovery.py                         (8 tests)
  - Restart scenarios
  - Replay consistency
  - State reconstruction

tests/reasoning/test_evidence_verdict_edge_cases.py          (30 tests)
  - Missing evidence handling
  - Invalid evidence links
  - Partial evidence scenarios
  - Evidence conflict resolution
  
tests/reasoning/test_agreement_score_boundaries.py           (15 tests)
  - 0.84, 0.85, 0.86 boundary tests
  - Symbolic/neural disagreement
  - FortressValidator integration
  - RedLines.yaml compliance
  
tests/reasoning/test_chain_of_thought_validation.py          (20 tests)
  - Incomplete reasoning steps
  - Contradictory steps
  - Step ordering
  - Logic gap detection
```

tests/reasoning/test_proof_tree_construction.py              (20 tests)
  - Proof depth requirements
  - Evidence linkage
  - Tree completeness
  - Traversal verification
```

**Success Criteria:**
- ✅ Ledger module >= 75%
- ✅ Reasoning module >= 60%
- ✅ FortressValidator agreement check tested
- ✅ Proof tree requirements verified
- ✅ **Zero P0 security/ledger risks remain**

**Verification:**
```bash
pytest tests/ledger/ tests/reasoning/ -v --cov=mahoun/ledger --cov=mahoun/reasoning
# Target: Ledger 75%+, Reasoning 60%+
```

**Wave 1 Exit Criteria:**
- [ ] All P0 security bypass paths tested
- [ ] Ledger hash chain integrity proven
- [ ] FortressValidator integration verified
- [ ] RedLines.yaml agreement threshold enforced
- [ ] Core coverage >= 45%
- [ ] Risk reduction >= 40%

---

### Wave 2: P0 Critical Data Integrity (Weeks 4-6)
**Objective:** Eliminate graph corruption and reasoning hallucination risks  
**Duration:** 3 weeks  
**Developers:** 2 full-time  
**Target Coverage:** 45% → 51%  
**Expected Risk Reduction:** 30%

#### Scope
| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.graph** | 14.97% | 40% | 90-110 | P0 |
| **mahoun.reasoning** | 60% | 72% | 45-55 | P0 (Phase 2) |

**Total Tests:** 135-165

#### Week 4: Graph Module (Foundation)
**Focus:** Neo4j Safety & Concurrency

**Deliverables:**
```
tests/graph/test_builder_concurrency.py                      (30 tests)
  - Concurrent graph construction
  - Race condition handling
  - Deadlock detection
  - Lock contention scenarios
  
tests/graph/test_neo4j_query_service_bounds.py               (25 tests)
  - Cypher injection prevention
  - Query parameter binding
  - Arbitrary Cypher blocking
  - Allowlist enforcement
  
tests/graph/test_neo4j_connection_governance.py              (15 tests)
  - Driver creation allowlist
  - Session wrapper enforcement
  - Unauthorized connection blocking
  - Governance context propagation
```

**Success Criteria:**
- ✅ Graph builder concurrency safe
- ✅ Cypher injection impossible
- ✅ Driver creation restricted
- ✅ Graph module >= 25%

**Verification:**
```bash
pytest tests/graph/ -v --cov=mahoun/graph --cov-report=term
# Target: 70 tests, 25%+ coverage
```

---

#### Week 5: Graph Module (Destructive Operations) + Reasoning Phase 2
**Focus:** GNN Safety & Policy Engine

**Deliverables:**
```
tests/graph/test_gnn_destructive_capability_gates.py         (20 tests)
  - DETACH DELETE control
  - DROP constraint enforcement
  - Two-key-turn requirement
  - Environment gates
  - Actor ID + correlation ID validation
  
tests/graph/test_graph_analytics_determinism.py              (25 tests)
  - PageRank reproducibility
  - Community detection consistency
  - Traversal order stability
  - Aggregation determinism
  
tests/graph/test_batch_operations_integrity.py               (20 tests)
  - Atomicity guarantees
  - Rollback on failure
  - Partial update prevention
  - Transaction boundaries

tests/reasoning/test_policy_engine_rules.py                  (15 tests)
  - Rule application logic
  - Rule conflict resolution
```
  - Policy hierarchy
  - Exception handling
  
tests/reasoning/test_knowledge_graph_reasoning.py            (20 tests)
  - Graph traversal correctness
  - Inference path validation
  - Contradiction detection
  - Provenance tracking
```

**Success Criteria:**
- ✅ GNN destructive ops gated
- ✅ Graph analytics deterministic
- ✅ Batch operations atomic
- ✅ Policy engine tested
- ✅ Graph module >= 35%
- ✅ Reasoning module >= 66%

**Verification:**
```bash
pytest tests/graph/ tests/reasoning/ -v --cov=mahoun/graph --cov=mahoun/reasoning
# Target: Graph 35%+, Reasoning 66%+
```

---

#### Week 6: Graph Completion + Reasoning Phase 2 Completion
**Focus:** Schema Safety & Causal Inference

**Deliverables:**
```
tests/graph/test_schema_migration_safety.py                  (20 tests)
  - Data preservation during migration
  - Constraint validation
  - Index consistency
  - Rollback capability
  
tests/graph/test_graph_query_provenance.py                   (15 tests)
  - Correlation ID propagation
```
  - Query audit trail
  - Actor tracking
  - Mutation attribution

tests/reasoning/test_causal_inference_validation.py          (15 tests)
  - Causal chain construction
  - Effect estimation
  - Confounding detection
  - Intervention analysis
  
tests/reasoning/test_adapter_fallback_behavior.py            (10 tests)
  - LLM adapter failure handling
  - RAG adapter degradation
  - Guardrails adapter bypass detection
  - Monitoring adapter loss
  
tests/reasoning/test_reasoning_determinism.py                (10 tests)
  - Temperature = 0 enforcement
  - Seed management
  - Result reproducibility
  - Non-determinism detection
```

**Success Criteria:**
- ✅ Graph module >= 40%
- ✅ Reasoning module >= 72%
- ✅ Schema migrations safe
- ✅ Causal inference validated
- ✅ **Zero P0 graph/reasoning risks remain**

**Verification:**
```bash
pytest tests/graph/ tests/reasoning/ -v --cov=mahoun/graph --cov=mahoun/reasoning
# Target: Graph 40%+, Reasoning 72%+
```

**Wave 2 Exit Criteria:**
- [ ] Graph destructive operations gated
- [ ] Cypher injection impossible
```
- [ ] Graph analytics deterministic
- [ ] Reasoning policy engine tested
- [ ] Causal inference validated
- [ ] Core coverage >= 51%
- [ ] Risk reduction >= 70% (cumulative)

---

### Wave 3: P1 Core Integration (Weeks 7-10)
**Objective:** Eliminate workflow and data processing failures  
**Duration:** 4 weeks  
**Developers:** 2 full-time  
**Target Coverage:** 51% → 57%  
**Expected Risk Reduction:** 20%

#### Scope
| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.orchestrator** | 11.96% | 50% | 75-95 | P1 |
| **mahoun.pipelines** | 24.06% | 50% | 95-115 | P1 |
| **mahoun.retrieval** | 28.94% | 52% | 50-60 | P1 |
| **mahoun.crypto** | 55.77% | 72% | 20-25 | P1 |
| **mahoun.core** | 65.97% | 75% | 18-25 | P1 |

**Total Tests:** 260-320

#### Week 7: Orchestrator Module
**Focus:** State Machine & Workflow Safety

**Deliverables:**
```
tests/orchestrator/test_state_machine_all_transitions.py     (35 tests)
  - Every state transition edge
  - Valid/invalid transition matrix
```
  - State persistence
  - Transition rollback
  
tests/orchestrator/test_state_machine_deadlock.py            (15 tests)
  - Cycle detection
  - Stuck state identification
  - Recovery mechanisms
  - Timeout handling
  
tests/orchestrator/test_chatbot_context_isolation.py         (20 tests)
  - Cross-session boundary enforcement
  - Context leakage prevention
  - Memory cleanup
  - User data segregation
  
tests/orchestrator/test_workflow_error_recovery.py           (15 tests)
  - Retry logic
  - Circuit breaker
  - Graceful degradation
  - Partial execution handling
```

**Success Criteria:**
- ✅ State machine fully tested
- ✅ Deadlock detection working
- ✅ Context isolation verified
- ✅ Orchestrator module >= 40%

---

#### Week 8: Pipelines Module (Part 1)
**Focus:** Ingestion & Determinism

**Deliverables:**
```
tests/pipelines/test_chunking_determinism.py                 (40 tests)
  - Reproducible chunking
  - Boundary consistency
  - Seed management
```
  - Non-determinism detection
  
tests/pipelines/test_embedding_generation_failure.py         (25 tests)
  - Model loading errors
  - Fallback behavior
  - Batch processing
  - Memory management
  
tests/pipelines/test_bm25_index_integrity.py                 (20 tests)
  - Index construction
  - Corruption detection
  - Incremental updates
  - Consistency verification
  
tests/pipelines/test_query_rewriting_loop_prevention.py      (15 tests)
  - Expansion termination
  - Infinite loop detection
  - Depth limiting
  - Cycle prevention
```

**Success Criteria:**
- ✅ Chunking deterministic
- ✅ Embedding fallback tested
- ✅ BM25 integrity verified
- ✅ Query rewriting safe
- ✅ Pipelines module >= 35%

---

#### Week 9: Pipelines Module (Part 2) + Retrieval
**Focus:** NLP Hardening & Search Accuracy

**Deliverables:**
```
tests/pipelines/test_ocr_preprocessing_edge_cases.py         (20 tests)
  - Malformed documents
  - Encoding issues
```
  - Image quality degradation
  - Language detection
  
tests/pipelines/test_nlp_hardening_adversarial.py            (15 tests)
  - Injection attempt detection
  - Special character handling
  - Unicode edge cases
  - Prompt manipulation prevention
  
tests/pipelines/test_provenance_mapping.py                   (10 tests)
  - Source tracking
  - Lineage preservation
  - Metadata integrity
  - Citation accuracy

tests/retrieval/test_graph_enhanced_retrieval_accuracy.py    (30 tests)
  - Precision metrics
  - Recall metrics
  - Relevance ranking
  - Graph influence validation
  
tests/retrieval/test_gat_reranker_determinism.py             (15 tests)
  - Score reproducibility
  - Model versioning
  - Feature consistency
  - Ranking stability
```

**Success Criteria:**
- ✅ NLP hardening validated
- ✅ Provenance tracking complete
- ✅ Retrieval accuracy verified
- ✅ Pipelines module >= 50%
- ✅ Retrieval module >= 40%

---

#### Week 10: Crypto, Core, Retrieval Completion
**Focus:** Cryptographic Integrity & Governance

**Deliverables:**
```
tests/retrieval/test_hybrid_search_weighting.py              (12 tests)
  - BM25 vs vector balance
  - Weight tuning validation
  - Hybrid fusion logic
  - Performance metrics
  
tests/retrieval/test_citation_engine_attribution.py          (18 tests)
  - Source tracking accuracy
  - Attribution completeness
  - Misattribution prevention
  - Legal citation formatting

tests/crypto/test_merkle_tree_tampering.py                   (12 tests)
  - Proof verification
  - Tampering detection
  - Tree reconstruction
  - Root consistency
  
tests/crypto/test_ed25519_signature_edge_cases.py            (10 tests)
  - Forgery attempts
  - Invalid signatures
  - Key rotation
  - Signature verification
  
tests/crypto/test_proof_system_construction.py               (8 tests)
  - Proof completeness
  - Proof validation
  - Chain of custody
  - Reconstruction capability

tests/core/test_fortress_validator_comprehensive.py          (15 tests)
```
  - All 6 checks individually
  - Check combinations
  - Bypass prevention
  - RedLines.yaml compliance
  
tests/core/test_runtime_config_validation.py                 (10 tests)
  - Malformed config handling
  - Missing required fields
  - Type validation
  - Environment-specific settings
```

**Success Criteria:**
- ✅ Orchestrator module >= 50%
- ✅ Pipelines module >= 50%
- ✅ Retrieval module >= 52%
- ✅ Crypto module >= 72%
- ✅ Core module >= 75%
- ✅ **Zero P1 workflow/pipeline risks remain**

**Wave 3 Exit Criteria:**
- [ ] State machine fully tested
- [ ] Pipelines deterministic
- [ ] Retrieval accuracy verified
- [ ] Crypto integrity proven
- [ ] FortressValidator comprehensive
- [ ] Core coverage >= 57%
- [ ] Risk reduction >= 90% (cumulative)

---

### Wave 4: P2 Feature Completeness (Weeks 11-14)
**Objective:** Eliminate partial functionality and observability gaps  
**Duration:** 4 weeks  
**Developers:** 2 full-time  
**Target Coverage:** 57% → 61%  
**Expected Risk Reduction:** 10%

#### Scope
| Module | Current | Target | Tests | Priority |
|--------|---------|--------|-------|----------|
| **mahoun.agents** | 49.69% | 65% | 60-75 | P2 |
| **mahoun.rag** | 50.46% | 62% | 50-60 | P2 |
| **mahoun.llm** | 41.74% | 55% | 35-45 | P2 |
| **mahoun.infrastructure** | 39.19% | 55% | 25-30 | P2 |
| **mahoun.monitoring** | 30.58% | 50% | 30-40 | P2 |
| **mahoun.governance** | 80.47% | 85% | 15-20 | P1 |
| **mahoun.invariants** | 77.27% | 85% | 10-12 | P1 |

**Total Tests:** 225-275

#### Week 11: Agents Module
**Focus:** Domain Agent Workflows

**Deliverables:**
```
tests/agents/test_contract_agent_comprehensive.py            (50 tests)
  - Contract analysis workflows
  - Clause extraction
  - Risk identification
  - Compliance checking
  - Edge case handling
  
tests/agents/test_dispute_agent_workflows.py                 (40 tests)
  - Dispute resolution flows
  - Evidence gathering
  - Argument construction
  - Outcome prediction
```

tests/agents/test_risk_assessment_agent.py                   (40 tests)
  - Risk scoring logic
  - Factor weighting
  - Scenario modeling
  - Mitigation recommendations
```

**Success Criteria:**
- ✅ Contract agent tested
- ✅ Dispute workflows validated
- ✅ Risk assessment working
- ✅ Agents module >= 60%

---

#### Week 12: RAG & LLM Modules
**Focus:** Model Management & Retrieval Quality

**Deliverables:**
```
tests/rag/test_citation_engine_accuracy.py                   (25 tests)
  - Source attribution
  - Citation formatting
  - Provenance tracking
  - Legal citation standards
  
tests/rag/test_query_router_selection.py                     (20 tests)
  - Route decision logic
  - Fallback routing
  - Performance-based selection
  - Load balancing
  
tests/rag/test_hybrid_rag_weighting.py                       (15 tests)
  - Vector vs keyword balance
  - Fusion algorithms
  - Quality metrics
  - Tuning validation

tests/llm/test_model_manager_fallback.py                     (20 tests)
```
  - Primary model failure
  - Backup model activation
  - Degradation handling
  - Error propagation
  
tests/llm/test_bandit_algorithm.py                           (10 tests)
  - Model selection logic
  - Exploration vs exploitation
  - Performance tracking
  - Adaptation over time
  
tests/llm/test_local_driver_errors.py                        (10 tests)
  - GPU memory exhaustion
  - Model loading failures
  - Timeout handling
  - Batch processing errors
```

**Success Criteria:**
- ✅ RAG module >= 60%
- ✅ LLM module >= 52%
- ✅ Citation engine accurate
- ✅ Model fallback working

---

#### Week 13: Infrastructure & Monitoring
**Focus:** Observability & Health Checks

**Deliverables:**
```
tests/infrastructure/test_health_checker_comprehensive.py    (20 tests)
  - All service checks
  - False positive prevention
  - Dependency health
  - Cascading failure detection
  
tests/infrastructure/test_cache_invalidation.py              (10 tests)
  - Cache coherence
  - TTL enforcement
```
  - Eviction policies
  - Memory pressure handling
  
tests/infrastructure/test_persistence_recovery.py            (10 tests)
  - State restoration
  - Crash recovery
  - Data consistency
  - Corruption detection

tests/monitoring/test_alerting_thresholds.py                 (15 tests)
  - Threshold validation
  - Alert triggering
  - Alert suppression
  - Escalation logic
  
tests/monitoring/test_anomaly_detection.py                   (12 tests)
  - Pattern recognition
  - False positive rate
  - Sensitivity tuning
  - Baseline establishment
  
tests/monitoring/test_metric_aggregation.py                  (10 tests)
  - Aggregation accuracy
  - Time window handling
  - Percentile calculation
  - Cardinality management
```

**Success Criteria:**
- ✅ Infrastructure module >= 53%
- ✅ Monitoring module >= 48%
- ✅ Health checks reliable
- ✅ Alerting validated

---

#### Week 14: Governance & Invariants Completion
**Focus:** Policy Enforcement & Contract Validation

**Deliverables:**
```
tests/governance/test_policy_enforcement_edge_cases.py       (12 tests)
  - Policy conflict resolution
  - Edge case handling
  - Override mechanisms
  - Audit logging
  
tests/governance/test_compliance_audit_completeness.py       (10 tests)
  - Audit trail completeness
  - Report generation
  - Compliance validation
  - Regulatory requirements

tests/invariants/test_ledger_invariants_EL_I1_I7.py          (10 tests)
  - All 7 ledger invariants
  - Violation detection
  - Recovery mechanisms
  - Enforcement guarantees
```

**Success Criteria:**
- ✅ All P2 modules >= 50%
- ✅ Governance module >= 85%
- ✅ Invariants module >= 85%
- ✅ **Zero P2 functionality gaps remain**
- ✅ **Core coverage >= 61%**

**Wave 4 Exit Criteria:**
- [ ] All agents tested
- [ ] RAG quality verified
- [ ] LLM fallback working
- [ ] Infrastructure stable
- [ ] Monitoring reliable
- [ ] Governance complete
- [ ] Invariants enforced
- [ ] Core coverage >= 61%
- [ ] Risk reduction = 100%

---

## Timeline Visualization

```
Week  1  2  3  4  5  6  7  8  9 10 11 12 13 14
      [===Wave 1===][===Wave 2===][======Wave 3=====][======Wave 4======]
      Security/Ledger Graph/Reason Orch/Pipe/Retr   Agents/RAG/LLM/Infra
      P0 Critical     P0 Data      P1 Integration   P2 Feature Complete
      
Coverage:
38%   ----45%-------51%----------57%--------------61%

Risk Reduction:
 0%   ----40%-------70%----------90%--------------100%
```

---

## Resource Requirements

### Team Composition
- **2 Full-Time Developers** (14 weeks)
- Skills Required:
  - Python testing (pytest, fixtures, mocking)
  - Domain knowledge (security, cryptography, graph databases)
  - CI/CD (bash scripting, coverage tools)

### Tools & Infrastructure
- **pytest** with coverage plugin
- **pytest-asyncio** for async tests
- **pytest-cov** for coverage reporting
- **hypothesis** for property-based testing (optional)
- **Neo4j test container** for graph integration tests
- **Redis test instance** for caching tests
- **CI runner capacity** (increased for parallel test execution)

### Time Investment
```
Total Tests: 805-965 (use 885 midpoint)
Time per test: 20 minutes average (write + debug + verify)
Total hours: 885 × 0.33 = 292 hours
```

Team capacity: 80 hours/week (2 devs × 40 hours)
Timeline: 292 / 80 = 3.65 weeks average per wave
4 waves × 3.65 = 14.6 weeks ≈ 14 weeks
```

**Risk Buffer:** +20% for discovery and refactoring = **17 weeks total** (conservative)

---

## Success Metrics

### Coverage Metrics
| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| **Core Coverage** | 38.19% | 60% | 🔴 |
| **P0 Min Coverage** | 14.97% (graph) | 70% all | 🔴 |
| **Security** | 25.30% | 65% | 🔴 |
| **Ledger** | 51.62% | 75% | 🔴 |
| **Reasoning** | 43.73% | 72% | 🔴 |
| **Graph** | 14.97% | 40% | 🔴 |

### Risk Metrics
| Wave | Risk Reduction | Cumulative | Status |
|------|----------------|------------|--------|
| Wave 1 | 40% | 40% | 🔴 Not Started |
| Wave 2 | 30% | 70% | 🔴 Not Started |
| Wave 3 | 20% | 90% | 🔴 Not Started |
| Wave 4 | 10% | 100% | 🔴 Not Started |

### Quality Metrics
- **P0 Critical Paths Tested:** 0 / 18 (0%)
- **Security Bypass Scenarios Tested:** 0 / 6 (0%)
- **Ledger Corruption Scenarios Tested:** 0 / 5 (0%)
- **Reasoning Hallucination Paths Tested:** 0 / 8 (0%)
```
- **Graph Destructive Operations Tested:** 0 / 4 (0%)

---

## CI Integration Strategy

### New CI Gates

#### Gate 10: P0 Coverage Enforcement
```bash
#!/bin/bash
# ci/gates/gate_10_p0_coverage.sh

source venv/bin/activate

# Run coverage on P0 modules only
pytest tests/ -v \
    --cov=mahoun/security \
    --cov=mahoun/ledger \
    --cov=mahoun/reasoning \
    --cov=mahoun/graph \
    --cov-report=json \
    --cov-fail-under=70

# Check individual module thresholds
python3 ci/scripts/check_p0_coverage.py coverage.json

# Fail if any P0 module < 70%
if [ $? -ne 0 ]; then
    echo "❌ P0 module coverage below 70% threshold"
    exit 1
fi

echo "✅ All P0 modules meet coverage requirements"
```

#### Gate 11: Critical Path Verification
```bash
#!/bin/bash
# ci/gates/gate_11_critical_paths.sh

# Verify all P0 critical paths have tests
python3 ci/scripts/verify_critical_paths.py \
    --manifest constitution/critical_paths.yaml \
    --test-dir tests/
```

if [ $? -ne 0 ]; then
    echo "❌ Untested critical paths detected"
    exit 1
fi

echo "✅ All critical paths covered"
```

### CI Pipeline Structure
```yaml
# .github/workflows/test_coverage_gates.yml

name: Test Coverage Gates

on: [push, pull_request]

jobs:
  p0-critical-tests:
    name: P0 Critical Module Tests
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -e ".[dev]"
      - name: Run P0 Tests
        run: |
          source venv/bin/activate
          pytest tests/security/ tests/ledger/ tests/reasoning/ tests/graph/ \
            -v --cov=mahoun/security --cov=mahoun/ledger \
            --cov=mahoun/reasoning --cov=mahoun/graph \
            --cov-report=json --cov-report=term
      - name: Check P0 Coverage Thresholds
        run: |
```
          source venv/bin/activate
          python ci/scripts/check_p0_coverage.py coverage.json
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.json
          flags: p0-critical

  critical-path-verification:
    name: Critical Path Coverage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Verify Critical Paths
        run: |
          python ci/scripts/verify_critical_paths.py \
            --manifest constitution/critical_paths.yaml \
            --test-dir tests/
```

### Coverage Tracking Dashboard
```bash
# Weekly coverage report script
# scripts/weekly_coverage_report.sh

#!/bin/bash
WEEK=$(date +%V)
OUTPUT="reports/coverage_week_${WEEK}.json"

source venv/bin/activate
pytest tests/ -v --cov=mahoun --cov-report=json:${OUTPUT}

echo "📊 Week ${WEEK} Coverage Report generated"

# Compare to previous week
PREV_WEEK=$((WEEK - 1))
PREV_REPORT="reports/coverage_week_${PREV_WEEK}.json"

if [ -f "${PREV_REPORT}" ]; then
    python ci/scripts/compare_coverage.py \
        --baseline ${PREV_REPORT} \
        --current ${OUTPUT}
fi
```

---

## Risk Management

### Identified Risks

#### Risk 1: Test Creation Takes Longer Than Estimated
**Probability:** Medium  
**Impact:** High (timeline slip)  
**Mitigation:**
- Start with template tests (Week 1)
- Parallelize test creation across 2 developers
- Use AI code generation for boilerplate
- 20% buffer built into timeline

#### Risk 2: Coverage Tool Reports Inaccurate Coverage
**Probability:** Low  
**Impact:** High (false confidence)  
**Mitigation:**
- Manual code review of critical paths
- Property-based tests for additional validation
- Mutation testing to verify test quality

#### Risk 3: Tests Pass But Don't Catch Real Bugs
**Probability:** Medium  
**Impact:** Critical (false security)  
**Mitigation:**
- Code review of all P0 tests
- Penetration testing after Wave 1
- Chaos engineering after Wave 2
- Real-world scenario validation

#### Risk 4: Developer Capacity Insufficient
**Probability:** Medium  
**Impact:** High (timeline slip)  
**Mitigation:**
- Freeze feature development during test creation
- Onboard additional developer if Week 3 behind schedule
- Reduce scope (defer P2 modules to post-release)

#### Risk 5: Neo4j/Redis Test Infrastructure Unstable
**Probability:** Low  
**Impact:** Medium (test flakiness)
**Mitigation:**
- Use Docker containers for test isolation
- Implement test fixtures with cleanup
- Retry flaky tests (max 3 times)
- Monitor test infrastructure health

### Contingency Plans

**If Week 3 Behind Schedule:**
1. Add 3rd developer to team
2. Reduce reasoning test count (60 → 40 tests)
3. Extend Wave 1 by 1 week

**If Wave 2 Behind Schedule:**
1. Defer Wave 4 P2 modules to post-release
2. Focus on P0/P1 only (security through pipelines)
3. Target 55% coverage instead of 61%

**If Critical Bug Found During Testing:**
1. Immediately fix bug (takes precedence)
2. Add regression test for bug
3. Document in known issues log
4. Adjust timeline by +1 week

---

## Monitoring & Reporting

### Weekly Status Report Template
```markdown
# Week X Test Coverage Status

## Summary
- Tests Created This Week: X
- Cumulative Tests: X / 885
- Coverage: X.X% (target: X%)
- Risk Reduction: X% (target: X%)

## Completed
- Module A: X tests (coverage: X%)
- Module B: X tests (coverage: X%)

## In Progress
- Module C: X/X tests

## Blockers
- Issue 1: Description + resolution plan
```

## Risks
- Risk 1: Description + mitigation

## Next Week Plan
- Module D: X tests
- Module E: X tests
```

### Dashboard Metrics (Weekly Update)
```python
# scripts/update_coverage_dashboard.py

import json
from datetime import datetime

metrics = {
    "week": datetime.now().isocalendar().week,
    "total_tests": 0,  # from pytest --collect-only
    "core_coverage": 0.0,  # from coverage.json
    "p0_coverage": {
        "security": 0.0,
        "ledger": 0.0,
        "reasoning": 0.0,
        "graph": 0.0
    },
    "risk_reduction": 0.0,  # calculated from completed P0 paths
    "on_track": True  # timeline assessment
}

# Save to dashboard
with open("reports/dashboard_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
```

### Stakeholder Communication

**Weekly Email Update:**
- Coverage progress vs target
- Tests created vs plan
- Blockers and resolutions
- Timeline assessment

**End-of-Wave Presentation:**
- Wave objectives achieved
- Coverage gains
- Risk reduction quantified
- Bugs found and fixed
- Next wave preview

---

## Post-Completion Strategy

### Production Release Checklist
- [ ] Core coverage >= 60%
- [ ] All P0 modules >= 70%
- [ ] All P0 critical paths tested
- [ ] Security penetration test passed
- [ ] Ledger chaos test passed
- [ ] Reasoning validation complete
- [ ] Graph integrity verified
- [ ] CI gates passing
- [ ] Documentation updated
- [ ] Runbook created

### Continuous Improvement

#### Month 1 Post-Release
1. **Monitor Production Incidents**
   - Any incident triggers immediate test creation
   - Regression test added within 24 hours
   - Root cause analysis within 48 hours

2. **Measure Test Quality**
   - Run mutation testing on P0 modules
   - Target: 80%+ mutation score
   - Fix weak tests identified

3. **Property-Based Testing**
   - Add Hypothesis tests for determinism
   - Add contract-based tests for governance
   - Target: 50+ property tests

#### Quarter 2
1. **Integration Test Suite**
   - End-to-end legal reasoning flows
   - Multi-user concurrent scenarios
   - Failure recovery validation
   - Target: 100 integration tests

2. **Performance Testing**
   - Load testing (1000 concurrent requests)
   - Stress testing (resource exhaustion)
```
   - Chaos engineering (service failures)
   - Target: P99 latency < 500ms

3. **Security Hardening**
   - Penetration test quarterly
   - Dependency vulnerability scanning
   - SAST/DAST integration
   - Target: Zero P0 security findings

#### Ongoing
1. **Monthly Risk Re-Assessment**
   - Re-run risk-driven gap analysis
   - Update priorities as code evolves
   - Track risk reduction trend

2. **Coverage Non-Regression**
   - CI blocks any coverage decrease
   - New features require tests upfront
   - Test-to-code ratio >= 0.8

3. **Test Health Monitoring**
   - Flaky test detection and fixing
   - Test execution time tracking
   - Test failure pattern analysis

---

## Appendix: Test Templates

### Security Test Template
```python
# tests/security/test_api_key_template.py
"""
API Key Lifecycle Tests

Coverage Target:
- api_keys.py lines 89-234 (generation, rotation, revocation)

Critical Paths:
- Key generation uniqueness
- Key rotation security
- Revocation enforcement
```
"""

import pytest
from mahoun.security.api_keys import APIKeyManager, KeyStatus

@pytest.fixture
def api_key_manager():
    """Fresh APIKeyManager for each test."""
    return APIKeyManager()

class TestAPIKeyGeneration:
    """Test key generation security."""
    
    def test_key_generation_creates_unique_keys(self, api_key_manager):
        """Verify generated keys are unique."""
        key1, meta1 = api_key_manager.generate_key("test1")
        key2, meta2 = api_key_manager.generate_key("test2")
        
        assert key1 != key2
        assert meta1.key_id != meta2.key_id
        assert meta1.key_hash != meta2.key_hash
    
    def test_key_generation_uses_secure_random(self, api_key_manager):
        """Verify keys use cryptographically secure randomness."""
        keys = [api_key_manager.generate_key(f"test{i}")[0] for i in range(100)]
        
        # Check no duplicates
        assert len(keys) == len(set(keys))
        
        # Check sufficient entropy (key length)
        assert all(len(k) >= 40 for k in keys)  # prefix + 32 bytes base64
    
    # Add 18 more tests for key generation edge cases...

class TestAPIKeyRotation:
    """Test key rotation security."""
```
    
    def test_key_rotation_revokes_old_key(self, api_key_manager):
        """Verify old key is revoked after rotation."""
        old_key, old_meta = api_key_manager.generate_key("test")
        
        # Rotate
        new_key, new_meta = api_key_manager.rotate_key(old_meta.key_id)
        
        # Old key should be revoked
        assert api_key_manager.validate_key(old_key) is None
        assert old_meta.status == KeyStatus.REVOKED
        
        # New key should work
        assert api_key_manager.validate_key(new_key) is not None
    
    # Add 10 more tests for key rotation scenarios...

# Add TestAPIKeyRevocation, TestAPIKeyExpiry, etc...
```

### Ledger Test Template
```python
# tests/ledger/test_hash_chain_template.py
"""
Ledger Hash Chain Integrity Tests

Coverage Target:
- blockchain.py lines 45-178 (hash chain construction, verification)

Critical Paths:
- Tampering detection
- Chain verification
- Block validation
"""

import pytest
from mahoun.ledger.blockchain import LedgerBlockchain
from mahoun.core.exceptions import LogicViolationException

@pytest.fixture
def blockchain():
    """Fresh blockchain for each test."""
    return LedgerBlockchain()
```

class TestHashChainIntegrity:
    """Test hash chain tampering detection."""
    
    def test_tampering_detection_invalid_hash(self, blockchain):
        """Verify tampering is detected when block hash is modified."""
        # Create valid chain
        blockchain.add_block({"action": "write", "data": "test1"})
        blockchain.add_block({"action": "write", "data": "test2"})
        
        # Tamper with middle block
        blockchain.blocks[1].hash = "tampered_hash"
        
        # Verification should fail
        with pytest.raises(LogicViolationException, match="Hash chain integrity violated"):
            blockchain.verify_chain()
    
    def test_tampering_detection_modified_data(self, blockchain):
        """Verify tampering is detected when block data is modified."""
        blockchain.add_block({"action": "write", "data": "original"})
        
        # Tamper with data
        blockchain.blocks[-1].data["data"] = "tampered"
        
        # Hash should no longer match
        with pytest.raises(LogicViolationException):
            blockchain.verify_chain()
    
    # Add 18 more tests for hash chain scenarios...

# Add TestBlockValidation, TestChainVerification, etc...
```

---

## Conclusion

This roadmap provides a **realistic, evidence-based plan** for achieving production-ready test coverage in 14 weeks. The focus is on **risk reduction, not coverage percentage**, ensuring that the most critical security, integrity, and correctness gaps are addressed first.

**Key Success Factors:**
```
1. **Discipline:** Follow the wave sequence strictly (no skipping ahead)
2. **Focus:** Freeze feature development during P0 waves
3. **Quality:** Code review all P0 tests
4. **Verification:** Run penetration/chaos tests after each wave
5. **Communication:** Weekly status updates to stakeholders

**Next Steps:**
1. Review and approve this roadmap
2. Allocate 2 developers full-time
3. Create Week 1 test templates
4. Begin execution on Monday

**Expected Outcome:**
- 60%+ core coverage
- Zero P0 production risks
- Production-ready security posture
- Defensible audit trail
- Zero-hallucination guarantee verified

---

**Document Status:** ✅ Ready for Execution  
**Owner:** Test Infrastructure Team  
**Approvers:** Engineering Lead, Security Lead, QA Lead  
**Next Review:** End of Week 3 (Wave 1 completion)

