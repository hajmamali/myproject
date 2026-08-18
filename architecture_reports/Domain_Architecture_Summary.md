# 🏛️ Domain Architecture Intelligence Report (Phase 2 Baseline)

**Repository:** /home/haji/Desktop/KingMahouN
**Total Clean Modules Analyzed:** 1071

---

## 🎯 Executive Category Summary

| Category | Count | % |
|----------|-------|---|
| **AMBIGUOUS** | 18 | 1.7% |
| **CANONICAL_CANDIDATE** | 102 | 9.5% |
| **DELETE_CANDIDATE** | 149 | 13.9% |
| **INFRASTRUCTURE** | 194 | 18.1% |
| **LEGACY** | 7 | 0.7% |
| **POSSIBLE_ORPHAN** | 23 | 2.1% |
| **SUPPORTING_PRODUCTION** | 76 | 7.1% |
| **TEST_ONLY** | 428 | 40.0% |
| **TOOLING** | 74 | 6.9% |

---

## 🏛️ Domain Taxonomy & Auditable Evidence Chains

### 📦 Domain: `AGENTS`
- **Interface:** `UltraBaseAgent`
- **Total Competing Implementations:** 11

#### 🌟 Canonical Candidate(s)
- `mahoun.agents` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.agents.contract_agent` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Implements protocol: UltraBaseAgent
- `mahoun.agents.delay_agent` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Implements protocol: BaseAgent
- `mahoun.agents.orchestrator` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.agents.ultra_factory` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Implements protocol: UltraBaseAgent

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.agents.base_agent` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.agents.claim_agent` (Confidence: 93.2%)
  - Implements protocol: UltraBaseAgent
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.agents.evidence_protocol`
- `mahoun.agents.legacy_adapter`

---

### 📦 Domain: `API`
- **Interface:** `BaseModel, BaseModel, BaseModel, BaseModel`
- **Total Competing Implementations:** 16

#### 🌟 Canonical Candidate(s)
- `api.database` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `api.main` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 94.9%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel
- `api.middleware.governance_context` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `api.middleware.validation` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `api.routers.finetuning` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 95.8%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `api.routers.governance` (Layer: `KERNEL_CORE`, Confidence: 95.8%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `api.routers.health_v2` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 96.1%)
  - Reachable from production entry points
  - Official Production Entry Point
- `api.routers.ingest` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 96.1%)
  - Reachable from production entry points
  - Official Production Entry Point
- `api.routers.mahoun` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 95.6%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `api.routers.metrics` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 96.1%)
  - Reachable from production entry points
  - Official Production Entry Point
- `api.routers.reasoning` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 94.9%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `api.routers.search` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 95.8%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel
- `api.routers.system` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 96.1%)
  - Reachable from production entry points
  - Official Production Entry Point
- `api.routers.training_datasets` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 95.8%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel

#### ⚙️ Supporting Production Implementations
- `api.auth.dependencies` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `api.config` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `api.auth`
- `api.dependencies`
- `api.middleware`
- `api.routers`

---

### 📦 Domain: `AUDIT`
- **Interface:** `RegulatoryExportTemplate, RegulatoryExportTemplate, RegulatoryExportTemplate`
- **Total Competing Implementations:** 1


#### ⚙️ Supporting Production Implementations
- `mahoun.audit.models` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)

---

### 📦 Domain: `CONFIG`
- **Interface:** `N/A`
- **Total Competing Implementations:** 0


---

### 📦 Domain: `CRYPTO`
- **Interface:** `N/A`
- **Total Competing Implementations:** 4

#### 🌟 Canonical Candidate(s)
- `mahoun.crypto.proof_system` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.crypto.signatures` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points

#### ⚙️ Supporting Production Implementations
- `mahoun.crypto.key_manager` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.crypto.merkle_tree` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.crypto`

---

### 📦 Domain: `DOMAIN`
- **Interface:** `BaseDomainEngine`
- **Total Competing Implementations:** 1

#### 🌟 Canonical Candidate(s)
- `mahoun.domain.delay_analyzer` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Implements protocol: BaseDomainEngine

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.domain`
- `mahoun.domain.aml`

---

### 📦 Domain: `FINETUNING`
- **Interface:** `BaseModel, BaseModel, BaseModel, BaseModel, BaseModel`
- **Total Competing Implementations:** 2

#### 🌟 Canonical Candidate(s)
- `mahoun.finetuning.feedback_pipeline` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage

#### ⚙️ Supporting Production Implementations
- `mahoun.finetuning.document_to_training` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.finetuning.qa_templates`
- `mahoun.finetuning.unsloth_runner`

---

### 📦 Domain: `GOVERNANCE`
- **Interface:** `BaseModel`
- **Total Competing Implementations:** 0


#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.governance`

---

### 📦 Domain: `GRAPH`
- **Interface:** `BaseModel`
- **Total Competing Implementations:** 8

#### 🌟 Canonical Candidate(s)
- `mahoun.graph.concurrent_graph_builder` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.graph.graph_query_service` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.graph.legal_cypher_queries` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.graph.neo4j.connection` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.graph.ultra_graph_builder` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage

#### ⚙️ Supporting Production Implementations
- `mahoun.graph` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.graph.gnn.gnn_graph_builder` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
- `mahoun.graph.semantic_search` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.graph.neo4j.operations` (Confidence: 90.0%)
  - Has integration test coverage
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.graph.neo4j.schema` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.graph.batch`
- `mahoun.graph.batch.models`
- `mahoun.graph.batch.queue`
- `mahoun.graph.batch.worker`
- `mahoun.graph.builders.entity_linker`

---

### 📦 Domain: `GUARDRAILS`
- **Interface:** `N/A`
- **Total Competing Implementations:** 1

#### 🌟 Canonical Candidate(s)
- `mahoun.guardrails.ultra_nli_verifier` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.guardrails.exceptions` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.guardrails.runtime_invariants` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.guardrails`
- `mahoun.guardrails.hardened_import`
- `mahoun.guardrails.ultra_citation_auditor`

---

### 📦 Domain: `LEDGER`
- **Interface:** `LedgerBackend, LedgerBackend, LedgerBackend`
- **Total Competing Implementations:** 7

#### 🌟 Canonical Candidate(s)
- `mahoun.ledger.blockchain` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.ledger.guards` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.ledger.models` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.ledger.writer` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
  - Implements protocol: LedgerBackend, LedgerBackend, LedgerBackend

#### ⚙️ Supporting Production Implementations
- `mahoun.ledger.block` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
- `mahoun.ledger.privacy` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
- `mahoun.ledger.validators` (Layer: `KERNEL_CORE`, Confidence: 93.0%)

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.ledger.storage` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.ledger.write_gate` (Confidence: 90.0%)
  - Has integration test coverage
  - AMBIGUOUS: High import topology count but unreachable from production entry points

---

### 📦 Domain: `PIPELINES`
- **Interface:** `N/A`
- **Total Competing Implementations:** 14

#### 🌟 Canonical Candidate(s)
- `mahoun.pipelines._logging` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.pipelines.embed_index` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.pipelines.ingestion.document_handlers` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.pipelines.ingestion.enhanced_embedding` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.pipelines.ingestion.pipeline` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.pipelines.sync.graph_vector_sync` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.pipelines.vector_store.manager` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points

#### ⚙️ Supporting Production Implementations
- `mahoun.pipelines.ingestion.enhanced_pipeline` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.pipelines.ingestion.gguf_embedding` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
- `mahoun.pipelines.ingestion.hardened_paddle_ocr` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.pipelines.ingestion.minimal_verdict_parser` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.pipelines.query_rewriter` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  *...and 2 more*

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.pipelines.ingestion` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.pipelines.advanced_query_enhancement`
- `mahoun.pipelines.build_bm25`
- `mahoun.pipelines.chunker`
- `mahoun.pipelines.eval_retrieval`
- `mahoun.pipelines.graph`

---

### 📦 Domain: `RAG`
- **Interface:** `BaseModel, BaseModel, BaseModel`
- **Total Competing Implementations:** 5

#### 🌟 Canonical Candidate(s)
- `mahoun.rag.hybrid_rag_service` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.rag.legal_aware_retrieval` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.rag.query_router` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points

#### ⚙️ Supporting Production Implementations
- `mahoun.rag.policy_aware_rag_service` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.rag.citation_engine` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.rag`
- `mahoun.rag.training`
- `mahoun.rag.ultra_training_system`

---

### 📦 Domain: `REASONING`
- **Interface:** `LLMServiceProtocol`
- **Total Competing Implementations:** 21

#### 🌟 Canonical Candidate(s)
- `mahoun.reasoning` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.reasoning.adapters` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.reasoning.chain_of_thought` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.reasoning.evidence_linked_verdict` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.reasoning.first_order_logic` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.reasoning.fortress_integration` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.reasoning.knowledge_graph` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.reasoning.ledger_commit_service` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.reasoning.rag_evidence` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.reasoning.reasoning_engine` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.reasoning.ultra_reasoning_service` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Implements protocol: LLMServiceProtocol
- `mahoun.reasoning.unified_reasoning_service` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.reasoning.verdict_engine_adapter` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage

#### ⚙️ Supporting Production Implementations
- `mahoun.reasoning.causal_inference` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.reasoning.graph_symbolic_bridge` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.reasoning.guardrails_adapter` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.reasoning.monitoring_adapter` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.reasoning.neural_validation` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  *...and 3 more*

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.reasoning.backward_chaining` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.reasoning.forward_chaining` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.reasoning.reasoning_recorder` (Confidence: 90.0%)
  - Has integration test coverage
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `mahoun.reasoning.causal_effects`
- `mahoun.reasoning.causal_structure`
- `mahoun.reasoning.kg_adapters`
- `mahoun.reasoning.verdict_validation`

---

### 📦 Domain: `UNKNOWN`
- **Interface:** `UltraBaseAgent, UltraBaseAgent`
- **Total Competing Implementations:** 94

#### 🌟 Canonical Candidate(s)
- `mahoun.api.errors` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Implements protocol: BaseModel
- `mahoun.bootstrap.coordinators.agent_registry` (Layer: `KERNEL_CORE`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.bootstrap.coordinators.embedding_models` (Layer: `KERNEL_CORE`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.bootstrap.coordinators.llm_loader` (Layer: `KERNEL_CORE`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.bootstrap.manager` (Layer: `KERNEL_CORE`, Confidence: 95.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.bootstrap.runtime` (Layer: `KERNEL_CORE`, Confidence: 94.8%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.bootstrap.services` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.bootstrap.services.service_container` (Layer: `KERNEL_CORE`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.contracts.verdict_execution` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.core` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.config` (Layer: `KERNEL_CORE`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.core.config_validator` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.environment` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.exceptions` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.fortress_validator` (Layer: `KERNEL_CORE`, Confidence: 93.5%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `mahoun.core.governance` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.governance.authorization_state` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.governance.deterministic_resolver` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.governance.governance_context` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.core.governance.mutation_boundary` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.governance.ontology_enforcer` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.governance.provenance_tracker` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.governance.validator_pipeline` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.governance.violations` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.governance_lock` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.logging` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.models` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `mahoun.core.protocols` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.runtime_config` (Layer: `KERNEL_CORE`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.core.singleton` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.core.validation` (Layer: `KERNEL_CORE`, Confidence: 94.2%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `mahoun.llm.orchestrator` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.llm.router` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.mcp.registry` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.mcp.server` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 95.8%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel
- `mahoun.metrics` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.metrics.collector` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.metrics.metrics` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `mahoun.retrieval.hybrid_search_v2` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 92.0%)
  - Reachable from production entry points
  - Has integration test coverage
- `mahoun.retrieval.ultra_hybrid_search` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `mahoun.schemas.legal_aware_schema` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
  - Implements protocol: BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel, BaseModel
- `mahoun.switchboard` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.8%)
  - Reachable from production entry points
  - Registered in DI Container / Service Registry
- `reasoning_logic` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `reasoning_logic.core` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  - Reachable from production entry points
- `reasoning_logic.ontology` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points
- `reasoning_logic.parser` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
  - Reachable from production entry points

#### ⚙️ Supporting Production Implementations
- `mahoun` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.api_router` (Layer: `DOMAIN_SUBSYSTEM`, Confidence: 93.0%)
- `mahoun.bootstrap.coordinators` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
- `mahoun.bootstrap.executors` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
- `mahoun.bootstrap.services.benchmark_service` (Layer: `KERNEL_CORE`, Confidence: 93.0%)
  *...and 43 more*

#### ⚠️ Ambiguous / Conflicting Evidence Candidates
- `mahoun.bootstrap.golden_master.behavior_recorder` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.core.exceptions_v2` (Confidence: 90.0%)
  - Has integration test coverage
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.core.governance_kernel.kernel` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.core.policy_resolver` (Confidence: 90.0%)
  - Has integration test coverage
  - AMBIGUOUS: High import topology count but unreachable from production entry points
- `mahoun.preproduction.models` (Confidence: 90.0%)
  - AMBIGUOUS: High import topology count but unreachable from production entry points

#### 🗑️ Delete Candidates (Multi-Source Confirmed)
- `demos.demo_bank_scenario`
- `demos.demo_gguf_embeddings`
- `demos.demo_hybrid_traversal`
- `demos.demo_local_llm`
- `demos.demo_switching_logic`

---

