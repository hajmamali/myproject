# Architectural Kernel and Governance Analysis Report

**Date**: August 3, 2026  
**Analysis Type**: Governed Cognitive Runtime Architectural Audit  
**Scope**: 10-Phase Comprehensive Runtime Reconstruction and Governance Verification

---

## Executive Summary

All 10 phases of the Governed Cognitive Runtime architectural audit have been completed. The analysis identified 8 authoritative kernels, 6 mutation bypass vectors (2 CRITICAL, 3 HIGH, 1 MEDIUM), and comprehensive mapping of governance, lifecycle, authority, auditability, and evolution readiness.

### Key Findings
- **8 Authoritative Kernels** identified across governance, execution, and orchestration layers
- **6 Mutation Bypass Vectors** found requiring immediate remediation
- **Protocol-Based Architecture** enables evolution readiness with loose coupling
- **Dependency Injection Container** provides testability and graceful degradation
- **Comprehensive Audit Trail** via MutationReceipt and ImmutableLedger

---

## Phase 1: Runtime Reconstruction - COMPLETED

### Execution Flow
```
Application (api/main.py)
    ↓
Middleware (GovernanceContext, Security, Rate Limiting)
    ↓
Routers (reasoning, ingest, search, system)
    ↓
Services (ReasoningEngine, RAGService, QueryRouter)
    ↓
Kernel (GovernanceKernel, MutationAuthorizationBoundary)
    ↓
Persistence (Neo4j, Postgres, Redis, ImmutableLedger)
    ↓
Infrastructure (HealthChecker, Monitoring, Observability)
```

### Key Components
- **FastAPI Application**: `api/main.py` with lifespan management
- **Switchboard**: BASE/ULTRA mode switching capability
- **Runtime Configuration Validation**: Fail-fast on misconfiguration
- **Conditional Database Initialization**: Postgres/Neo4j/Redis based on env vars
- **Governance Context Middleware**: API boundary context creation

### Startup Sequence
1. Switchboard initialization
2. Runtime config validation
3. Database initialization (conditional)
4. Middleware registration
5. Router registration
6. Application ready

---

## Phase 2: Kernel Discovery - COMPLETED

### 8 Authoritative Kernels Identified

#### 1. Governance Kernel (Tier 0)
- **Location**: `mahoun/core/governance_kernel/kernel.py`
- **Components**:
  - `KernelMutationBoundary` - Zero-dependency Cypher inspector
  - `GovernanceKernel` - HTTP-facing governance validation service
- **Classification**: KERNEL / ZERO-DEPENDENCY / NON-BYPASSABLE
- **Authority**: Query classification, mutation authorization enforcement

#### 2. Mutation Authorization Boundary
- **Location**: `mahoun/core/governance/mutation_boundary.py`
- **Components**:
  - `MutationAuthorizationBoundary` - Hard governance boundary at Neo4j write layer
  - `GovernedNeo4jSession` - Authorized entry point for all Neo4j mutations
- **Classification**: KERNEL / CONSTITUTIONAL / NON-BYPASSABLE
- **Authority**: All graph mutations must pass through this boundary

#### 3. Authorization State (Single Source of Truth)
- **Location**: `mahoun/core/governance/authorization_state.py`
- **Components**:
  - `_authorized_write_ctx` ContextVar - Canonical authorization state
  - `is_authorized()`, `set_authorized()`, `reset_authorized()` functions
- **Classification**: KERNEL / CONSTITUTIONAL / SINGLE SOURCE OF TRUTH
- **Authority**: Mutation authorization state management

#### 4. Governance Context Manager
- **Location**: `mahoun/core/governance/governance_context.py`
- **Components**:
  - `GovernanceContext` - Execution context for reasoning operations
  - `GovernanceContextManager` - Context lifecycle management
- **Classification**: CRITICAL / RUNTIME GOVERNANCE / NON-BYPASSABLE
- **Authority**: Execution scope enforcement, correlation lineage tracking

#### 5. Ingestion Runtime
- **Location**: `mahoun/core/governance/ingestion_runtime.py`
- **Components**:
  - `GovernedIngestionRuntime` - Capability-scoped document ingestion
- **Classification**: KERNEL / INGESTION AUTHORITY
- **Authority**: Document ingestion with governance enforcement

#### 6. Policy Resolver
- **Location**: `mahoun/core/policy_resolver.py`
- **Components**:
  - `PolicyResolver` - Centralized execution policy engine
  - `ExecutionPolicy` - Immutable policy specification
  - `ViewMode` enum - ACTIVE_VIEW, HISTORICAL_VIEW, MIXED_VIEW
- **Classification**: CRITICAL / CONTROL PLANE / POLICY LIFECYCLE
- **Authority**: Policy decision engine (single source of truth)

#### 7. Ledger Write Gate
- **Location**: `mahoun/ledger/write_gate.py` (gitignored - operational)
- **Components**:
  - `LedgerWriteGate` - Ledger integrity boundary
  - `LedgerWriteContext` - Separate from GovernanceContext (intentionally renamed)
- **Classification**: KERNEL / LEDGER INTEGRITY
- **Authority**: Evidence package validation before ledger writes

#### 8. Health Checker
- **Location**: `mahoun/infrastructure/health_checker.py`
- **Components**:
  - `HealthChecker` - Central health checking for all components
- **Classification**: INFRASTRUCTURE / HEALTH MONITORING
- **Authority**: Component health inspection (no instantiation)

---

## Phase 3: Capability Graph - COMPLETED

### Capabilities Mapped

| Capability | Owner | Activation | Authorization |
|------------|-------|------------|----------------|
| Graph Mutations | GovernedNeo4jSession | GovernedNeo4jSession.write_node() | MutationAuthorizationBoundary |
| Verdict Generation | EvidenceLinkedVerdictEngine | /api/v1/reasoning/generate-verdict | GovernanceContext + Fortress |
| Ledger Writes | LedgerWriteGate | LedgerCommitService.commit() | EvidencePackage validation |
| Policy Deployment | PolicyDeploymentOrchestrator | /api/v1/policy/deploy | Multi-party sign-off |
| Document Ingestion | GovernedIngestionRuntime | IngestionPipelineV2 | GovernedNeo4jSession |
| Query Routing | QueryRouterProtocol | ReasoningDependencyContainer | Protocol implementation |
| RAG Retrieval | RAGServiceProtocol | HybridRAGService | Policy filtering |

---

## Phase 4: Governance Verification - COMPLETED

### 6 Mutation Bypass Vectors Found

#### CRITICAL (2)

##### 1. Direct Neo4j Driver Usage in api/database.py
- **File**: `api/database.py:208-209`
- **Violation**: 
  ```python
  async with driver.session() as session:
      await session.run("RETURN 1")
  ```
- **Bypass Type**: Direct session usage without GovernedNeo4jSession
- **Risk**: Schema initialization bypasses MutationAuthorizationBoundary
- **Evidence**: Test file `tests/test_governance_truth_audit.py:45-50` explicitly documents this bypass

##### 2. Direct session.run() in mahoun/graph/neo4j/schema.py
- **File**: `mahoun/graph/neo4j/schema.py:66, 106, 118, 139, 148, 157, 166`
- **Violation**: Multiple `self.session.run()` calls for DDL operations
- **Bypass Type**: Direct session usage for constraint/index operations
- **Risk**: Schema modifications bypass governance boundary
- **Note**: File has comment "GOVERNED EXEMPTION: startup schema bootstrap" but this is still a bypass vector

#### HIGH (3)

##### 3. Direct session.run() in mahoun/infrastructure/workers/outbox_worker.py
- **File**: `mahoun/infrastructure/workers/outbox_worker.py:170`
- **Violation**: 
  ```python
  session.run("MATCH (n:Chunk {id: $id}) DETACH DELETE n", ...)
  ```
- **Bypass Type**: Direct mutation Cypher execution
- **Risk**: Unaudited chunk deletion bypasses governance boundary

##### 4. Direct session.run() in mahoun/graph/legal_cypher_queries.py
- **File**: `mahoun/graph/legal_cypher_queries.py:734`
- **Violation**: 
  ```python
  result = session.run(query.cypher, parameters)
  ```
- **Bypass Type**: Direct query execution
- **Risk**: Potential mutation bypass if query contains write operations

##### 5. Direct session.run() in mahoun/graph/graph_query_service.py
- **File**: `mahoun/graph/graph_query_service.py:447, 526, 1224`
- **Violation**: Multiple `gsession.run()` calls
- **Bypass Type**: Direct query execution through GovernedNeo4jSession
- **Risk**: May bypass additional validation layers

#### MEDIUM (1)

##### 6. execute_write() in mahoun/graph/neo4j/connection.py
- **File**: `mahoun/graph/neo4j/connection.py:371`
- **Violation**: 
  ```python
  batch_results = session.execute_write(batch_transaction)
  ```
- **Bypass Type**: Direct execute_write usage
- **Risk**: Batch operations may bypass individual mutation validation

---

## Phase 5: Context Integrity - COMPLETED

### Context Lifecycle

#### Creation
- **Canonical Factory**: `GovernanceContextManager.create_context()` in `mahoun/core/governance/governance_context.py`
- **API Boundary Creation**: `GovernanceContextMiddleware` in `api/middleware/governance_context.py` creates context at HTTP entry point
- **Manual Creation**: Used in scripts and workers (e.g., `scripts/backfill_vectors.py`, `mahoun/infrastructure/workers/outbox_worker.py`)
- **Test Creation**: Extensive test usage with `GovernanceContextManager.create_context()`

#### Propagation
- **API Path**: Middleware → `request.state.governance_context` → Router → Services
- **Manual Path**: Direct context passing in scripts/workers
- **Stack Propagation**: `GovernanceContextManager._get_stack().append(ctx)` used in `api/routers/reasoning.py:383`
- **ContextVar Isolation**: `_governance_stack: ContextVar[list[GovernanceContext]]` for async-safe isolation

#### Isolation
- **Mechanism**: ContextVar-based stack ensures per-async-task isolation
- **Test Reset**: `_reset_for_test()` method for test cleanup
- **Signature Verification**: HMAC signature check prevents context spoofing (test evidence in `test_adversarial_bypass_attempts.py`)

#### Destruction
- **API Path**: Automatic cleanup after request processing
- **Manual Path**: Context manager cleanup in `async with` blocks
- **Stack Cleanup**: Explicit stack pop in `api/routers/reasoning.py:428-430`

### Context Violations Found
- **Stack Manipulation**: Direct stack append in `api/routers/reasoning.py:383` - manual stack management instead of using `active_context()` context manager
- **Risk**: Potential context leakage if exception occurs before pop

---

## Phase 6: Lifecycle Integrity - COMPLETED

### Startup Sequence
1. **Switchboard Initialization** - Mode switching capability (BASE/ULTRA)
2. **Runtime Config Validation** - `validate_runtime_config()` fail-fast on misconfiguration
3. **Database Initialization** - Conditional Postgres/Neo4j/Redis init based on env vars
4. **Middleware Registration** - Security, rate limiting, governance context
5. **Router Registration** - API endpoints registered
6. **Application Ready** - `app.state.start_time` set

### Shutdown Sequence
1. **Database Cleanup** - Close database connections
2. **Error Handling** - Logged but doesn't prevent shutdown

### Lifecycle Violations Found
- **Startup Bypass**: `api/database.py:208-209` executes raw Cypher during Neo4j init without governance context (documented as "GOVERNED EXEMPTION" but still a bypass vector)
- **No Recovery Mechanism**: No explicit recovery/restart logic in lifespan

---

## Phase 7: Authority Graph - COMPLETED

### Authority Relationships

#### Policy Creation/Change Authority
- **Owner**: `PolicyDeploymentOrchestrator` in `mahoun/core/policy_deployment.py`
- **API Endpoint**: `/api/v1/policy/deploy` in `api/main.py:690`
- **Stages**: VALIDATION → STAGING → CANARY → PRODUCTION → ROLLBACK
- **Approval Workflow**: Multi-party sign-off required
- **Audit Trail**: Event-sourced deployment history
- **Locking**: Distributed lock prevents concurrent deployments

#### Ledger Ownership
- **Owner**: `LedgerWriteGate` (gitignored - operational)
- **Writer**: `EvidenceLedgerWriter` in `mahoun/ledger/writer.py`
- **Backend**: `ImmutableLedger` in `mahoun/ledger/blockchain.py`
- **Validation**: Evidence package validation before writes (B3-I1, B3-I2, B3-I3)
- **Commit Service**: `LedgerCommitService` in `mahoun/reasoning/ledger_commit_service.py`

#### Verdict Ownership
- **Owner**: `EvidenceLinkedVerdictEngine` in `mahoun/reasoning/evidence_linked_verdict.py`
- **Generation**: API endpoint `/api/v1/reasoning/generate-verdict` in `api/routers/reasoning.py`
- **Validation**: Fortress validation via `FortressProtectedReasoningService`
- **Storage**: Ledger write through `LedgerCommitService`

#### Graph Mutation Ownership
- **Owner**: `GovernedNeo4jSession` in `mahoun/core/governance/mutation_boundary.py`
- **Boundary**: `MutationAuthorizationBoundary` enforces all mutations
- **Authorization**: `_authorized_write_ctx` ContextVar tracks authorization state
- **Connection**: `Neo4jConnection.get_connection()` in `mahoun/graph/neo4j/connection.py`

---

## Phase 8: Auditability - COMPLETED

### Verdict Reconstruction
- **Ledger Query API**: `/api/v1/reasoning/query-ledger` in `api/routers/reasoning.py:822`
- **Query Options**: By verdict_id, case_id, node_id, time range
- **Use Cases**: Audit trail review, impact analysis, case history, compliance reporting
- **Proof-Carrying**: All responses include `fortress_validated`, `audit_hash`, `validation_timestamp`, `correlation_id`

### Mutation Audit
- **MutationReceipt**: Immutable forensic record for every governed graph mutation
- **Fields**: receipt_id, mutation_type, label, entity_id, correlation_id, actor_id, timestamp, content_hash, pipeline_hash
- **Ledger**: Session-level ledger of all receipts in `GovernedNeo4jSession`
- **Audit Sink**: `_append_governance_audit()` function for immutable audit logging

### Decision Explainability
- **InferenceProvenance**: Tracks symbolic execution path, rule chains, evidence nodes, contradiction branches
- **ProvenanceMetadata**: Required fields (source, timestamp, correlation_id, author) for all graph writes
- **ProvenanceTracker**: Enforces mandatory provenance metadata on all graph writes
- **Attestation**: `get_attestation()` method provides correlation lineage

---

## Phase 9: Architectural Drift - COMPLETED

### Deprecated Components Found

#### Deprecated Module Locations
- `mahoun/core/health_cache.py` → Moved to `mahoun.infrastructure.monitoring.health_cache`
- `mahoun/core/metrics/` → Moved to `mahoun.infrastructure.observability.metrics`
- `mahoun/core/monitoring/` → Moved to `mahoun.infrastructure.observability.monitoring`

#### Deprecated API Endpoints
- `/metrics` endpoint in `mahoun/monitoring/metrics_endpoint.py` marked as deprecated

#### Deprecated Functions
- `seed_test_embeddings()` in `tests/fixtures/seed_data.py` - use `seed_all_test_data()` instead
- `update_system_metrics()` in `tests/test_collector_refactored_comprehensive.py` - deprecated with warning
- `CypherQueryBuilder.where()` in `mahoun/graph/neo4j/query_builder.py` - use `where_exact` or `where_contains`
- `enrich_with_graph` parameter in `services/search/legal_search_service.py` - deprecated

#### Legacy Components
- `UnifiedLoader` in `mahoun/orchestrator/unified_loader.py` - Replaced by `GovernedIngestionRuntime`
- `GraphEnhancedReasoning` in `mahoun/reasoning/graph_enhanced.py` - Orphaned reasoning engine (not in production path)
- `LegacyBaseAgent` in `mahoun/agents/legacy_adapter.py` - Backward compatibility layer
- `LegacyAgentAdapter` in `mahoun/agents/ultra_factory.py` - Wraps legacy agents as Ultra agents

#### TODO/FIXME Comments (Acceptable)
- Multiple TODO comments in `reasoning_logic/`, `mahoun/finetuning/`, `mahoun/graph/optimizer/` for future enhancements

---

## Phase 10: Evolution Readiness - COMPLETED

### Protocol-Based Architecture
- **Core Protocols**: `mahoun/core/protocols.py` defines 6+ protocols for loose coupling
  - `QueryRouterProtocol` - Query routing and classification
  - `RAGServiceProtocol` - Retrieval-augmented generation
  - `ModelOrchestratorProtocol` - Model orchestration
  - `ModelDriverProtocol` - Model driver interface
  - `ReasoningEngineProtocol` - Reasoning engine interface
  - `QueryClassifierProtocol` - Query classification
- **Runtime Checkable**: All protocols use `@runtime_checkable` for `isinstance()` support
- **Verification Script**: `scripts/verify_protocol_architecture.py` validates protocol implementation

### Adapter Pattern Integration
- **GGUFAdapter**: Air-gap compliant local model runtime
- **VerdictEngineAdapter**: High-performance adapter for EvidenceLinkedVerdictEngine
- **Neo4jKGAdapter**: Lightweight adapter over GovernedNeo4jSession
- **UltraRAGAdapter**: Adapter wrapping UltraGraphRAG
- **OntologyGateAdapter**: Adapter for OntologyEnforcer
- **LegacyAgentAdapter**: Backward compatibility for legacy agents

### Dependency Injection
- **ReasoningDependencyContainer**: Thread-safe DI container for reasoning layer
  - Lazy initialization of expensive resources
  - Graceful fallbacks on missing dependencies
  - Singleton pattern with thread-safe initialization
  - MockDependencyContainer for testing
- **Global Container**: `get_reasoning_dependencies()` provides singleton access

### Factory Pattern
- **UltraAgentFactory**: Agent creation and registration
  - `create_agent()` - Instantiate agents by type
  - `register()` - Register custom agents
  - `list_available()` - List available agents
- **PolicyDeploymentOrchestrator**: Policy deployment lifecycle management
- **get_deployment_orchestrator()**: Singleton factory for policy orchestrator

### Evolution Impact Assessment
- **New Engines**: Can be added via protocol implementation + adapter registration
- **New Backends**: Can be integrated through protocol-based adapters (e.g., GGUFAdapter for local models)
- **New Policies**: Can be deployed through PolicyDeploymentOrchestrator with validation stages
- **New APIs**: Can be added by implementing protocols and registering with factories

---

## Critical Recommendations

### P0 (Immediate Action Required)
1. **Eliminate CRITICAL bypass vectors in `api/database.py` and `mahoun/graph/neo4j/schema.py`**
   - Replace direct `session.run()` calls with GovernedNeo4jSession
   - Ensure all schema initialization goes through mutation boundary
   - Add explicit governance context for startup operations

### P1 (High Priority)
2. **Fix context stack manipulation in `api/routers/reasoning.py`**
   - Replace manual stack append/pop with `active_context()` context manager
   - Prevent potential context leakage on exceptions

3. **Add recovery mechanism for failed startup**
   - Implement retry logic with exponential backoff
   - Add circuit breaker for database connections
   - Ensure graceful degradation on partial failures

### P2 (Medium Priority)
4. **Remove or document HIGH bypass vectors**
   - Either eliminate bypasses in `outbox_worker.py`, `legal_cypher_queries.py`, `graph_query_service.py`
   - Or add explicit governance exemptions with audit trail

5. **Clean up legacy components**
   - Remove `UnifiedLoader` if fully replaced by `GovernedIngestionRuntime`
   - Document orphan status of `GraphEnhancedReasoning` or remove if unused
   - Remove deprecated module locations after migration complete

---

## Appendix A: File References

### Key Files Analyzed
- `api/main.py` - FastAPI application entry point
- `api/database.py` - Database initialization (bypass vectors found)
- `api/middleware/governance_context.py` - Governance context middleware
- `api/routers/reasoning.py` - Reasoning endpoints
- `mahoun/core/governance_kernel/kernel.py` - Governance kernel (Tier 0)
- `mahoun/core/governance/mutation_boundary.py` - Mutation authorization boundary
- `mahoun/core/governance/authorization_state.py` - Authorization state (single source of truth)
- `mahoun/core/governance/governance_context.py` - Governance context manager
- `mahoun/core/governance/ingestion_runtime.py` - Ingestion runtime
- `mahoun/core/policy_resolver.py` - Policy resolver
- `mahoun/core/policy_deployment.py` - Policy deployment orchestrator
- `mahoun/core/protocols.py` - Core protocol definitions
- `mahoun/graph/neo4j/connection.py` - Neo4j connection management
- `mahoun/graph/neo4j/schema.py` - Schema management (bypass vectors found)
- `mahoun/reasoning/adapters.py` - Dependency injection container
- `mahoun/reasoning/evidence_linked_verdict.py` - Verdict engine
- `mahoun/infrastructure/health_checker.py` - Health checking
- `mahoun/ledger/write_gate.py` - Ledger write gate (gitignored)

---

## Appendix B: Verification Commands

### Check for Direct Neo4j Driver Usage
```bash
grep -rn "GraphDatabase.driver(" --include="*.py" . | grep -v test | grep -v connection.py
```

### Check for ContextVar Duplicates
```bash
grep -rn "ContextVar" --include="*.py" mahoun/core/
```

### Check for Mutation Boundary Duplicates
```bash
grep -rn "class.*MutationBoundary\|def classify_.*query\|def classify_cypher" --include="*.py" .
```

---

## Conclusion

The Governed Cognitive Runtime demonstrates strong architectural foundations with:
- Clear kernel boundaries and governance enforcement
- Protocol-based architecture enabling evolution
- Comprehensive audit trail via MutationReceipt and ImmutableLedger
- Dependency injection for testability and graceful degradation

However, critical bypass vectors exist in startup and schema initialization paths that must be addressed to ensure fail-closed governance. The architecture is well-positioned for evolution with proper protocol and adapter patterns.

---

**Report Generated**: August 3, 2026  
**Analysis Duration**: 10-Phase Comprehensive Audit  
**Status**: COMPLETED
