# 🏛️ Architecture Decision Queue (Phase 3 Baseline)

**Baseline Hash:** `2d62c4e205636e27`
**Purpose:** Evidence-backed decision queue for architectural review. ZERO files deleted or mutated.

---

## 1. 🌟 CANONICAL_REVIEW_REQUIRED (102 Items)
*Candidates for Architecture/Governance Registry confirmation.*

- **`api.database`** (Domain: `API`, Confidence: 93.0%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points
- **`api.main`** (Domain: `API`, Confidence: 94.9%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel
- **`api.middleware.governance_context`** (Domain: `API`, Confidence: 92.0%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Has integration test coverage
- **`api.middleware.validation`** (Domain: `API`, Confidence: 93.8%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Registered in DI Container / Service Registry
- **`api.routers.finetuning`** (Domain: `API`, Confidence: 95.8%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- **`api.routers.governance`** (Domain: `API`, Confidence: 95.8%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- **`api.routers.health_v2`** (Domain: `API`, Confidence: 96.1%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Official Production Entry Point
- **`api.routers.ingest`** (Domain: `API`, Confidence: 96.1%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Official Production Entry Point
- **`api.routers.mahoun`** (Domain: `API`, Confidence: 95.6%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- **`api.routers.metrics`** (Domain: `API`, Confidence: 96.1%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Official Production Entry Point
- **`api.routers.reasoning`** (Domain: `API`, Confidence: 94.9%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- **`api.routers.search`** (Domain: `API`, Confidence: 95.8%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel
- **`api.routers.system`** (Domain: `API`, Confidence: 96.1%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Official Production Entry Point
- **`api.routers.training_datasets`** (Domain: `API`, Confidence: 95.8%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points, Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel
- **`mahoun.agents`** (Domain: `AGENTS`, Confidence: 93.0%)
  - Action: Verify canonical status with Architecture/Governance Registry
  - Reasons: Reachable from production entry points

*...and 87 more items in Architecture_Decision_Queue.json*

---

## 2. ⚠️ AMBIGUOUS_ARCHITECT_REVIEW (18 Items)
*Components with conflicting topological/reachability evidence.*

- **`mahoun.agents.base_agent`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.agents.claim_agent`** (Confidence: 93.2%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: Implements protocol: UltraBaseAgent, AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.bootstrap.golden_master.behavior_recorder`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.core.exceptions_v2`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: Has integration test coverage, AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.core.governance_kernel.kernel`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.core.policy_resolver`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: Has integration test coverage, AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.graph.neo4j.operations`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: Has integration test coverage, AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.graph.neo4j.schema`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.guardrails.exceptions`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.guardrails.runtime_invariants`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.ledger.storage`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.ledger.write_gate`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: Has integration test coverage, AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.pipelines.ingestion`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.preproduction.models`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.rag.citation_engine`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.reasoning.backward_chaining`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.reasoning.forward_chaining`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: AMBIGUOUS: High import topology count but unreachable from production entry points
- **`mahoun.reasoning.reasoning_recorder`** (Confidence: 90.0%)
  - Action: Architectural Review Required - Resolve conflicting reachability/topology evidence
  - Reasons: Has integration test coverage, AMBIGUOUS: High import topology count but unreachable from production entry points

---

## 3. 📜 LEGACY_MIGRATION_REVIEW (7 Items)
*Deprecated or legacy components requiring migration planning.*

- **`mahoun.agents.archive.base_agent_simple`** (Path: `mahoun/agents/archive/base_agent_simple.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement
- **`mahoun.agents.archive.claim_agent_simple`** (Path: `mahoun/agents/archive/claim_agent_simple.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement
- **`mahoun.agents.archive.contract_agent_simple`** (Path: `mahoun/agents/archive/contract_agent_simple.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement
- **`mahoun.agents.archive.dispute_agent_ultra`** (Path: `mahoun/agents/archive/dispute_agent_ultra.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement
- **`mahoun.agents.archive.doc_parser_agent_simple`** (Path: `mahoun/agents/archive/doc_parser_agent_simple.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement
- **`mahoun.agents.archive.orchestrator_simple`** (Path: `mahoun/agents/archive/orchestrator_simple.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement
- **`mahoun.rag.archive.ultra_evaluation_system`** (Path: `mahoun/rag/archive/ultra_evaluation_system.py`)
  - Action: Migration Review - Plan deprecation path to canonical replacement

---

## 4. 🗑️ QUARANTINE_DELETE_REVIEW (149 Items)
*Multi-source confirmed candidates for quarantine review prior to staged deletion.*

- **`api.auth`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`api.dependencies`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`api.middleware`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`api.routers`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.demo_bank_scenario`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.demo_gguf_embeddings`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.demo_hybrid_traversal`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.demo_local_llm`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.demo_switching_logic`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.financial_aml`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`demos.healthcare_compliance`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`examples.advanced_features_demo`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`examples.finetuning_demo`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`examples.fortress_validator_demo`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion
- **`examples.legal_aware_usage_examples`** (Dependents: 0)
  - Action: Quarantine Review - Confirm multi-source negative evidence before staging deletion

*...and 134 more items in Architecture_Decision_Queue.json*
