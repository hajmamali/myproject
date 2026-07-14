# MahouN Core Boundary Audit Report

## Executive Summary

| Category | Value |
|----------|-------|
| Audit Date | 2026-07-10 |
| Core Modules Analyzed | 50+ |
| Boundary Violations | 10 unique files with dependencies on non-core |
| Severity Distribution | HIGH: 8, MEDIUM: 2 |
| Architectural Risk | HIGH |

**Overall Finding**: The MahouN Core layer has multiple architectural boundary violations where core modules depend on external layers (AI, Infrastructure, Graph), violating the principle that Core should be the authority layer that other layers depend on, not the other way around.

---

## Core Inventory (Partial)

| Module Path | Responsibility | Public Interfaces | Authority Level |
|-------------|----------------|-------------------|-----------------|
| mahoun/core/governance/ | Governance kernel, mutation boundaries, provenance | GovernanceContext, MutationAuthorizationBoundary | ✅ Authoritative |
| mahoun/core/protocols/ | Protocol definitions for decoupling | AI runtime protocols, query protocols | ✅ Authoritative |
| mahoun/core/fortress_validator.py | Final validation layer for reasoning | FortressValidator, validate_reasoning_response | ✅ Authoritative |
| mahoun/core/policy_resolver.py | Centralized execution policy engine | PolicyResolver, ExecutionPolicy | ✅ Authoritative |
| mahoun/core/unified_governance.py | Two-layer governance coordination | UnifiedGovernanceController | ✅ Authoritative |

---

## Violation Details (Full Evidence)

### Violation ID: CORE-BOUNDARY-001
- **Severity**: HIGH
- **Location**: mahoun/core/fortress_validator.py:51
- **Dependency**: mahoun/reasoning/unified_reasoning_service
- **Direction**: CORE → REASONING LAYER
- **Evidence**:
  ```python
  def __getattr__(name: str) -> Any:
      if name == "ReasoningResponse":
          try:
              from mahoun.reasoning.unified_reasoning_service import ReasoningResponse
              return ReasoningResponse
          except ImportError:
              return Any
  ```
- **Why this violates architecture**: Core depends on the reasoning layer for a model type, making Core dependent on an external layer.
- **Risk**: Changes to the reasoning layer's ReasoningResponse could break core validation logic.
- **Recommendation**: Define ReasoningResponse as a protocol or dataclass in Core.

---

### Violation ID: CORE-BOUNDARY-002
- **Severity**: HIGH
- **Location**: mahoun/core/fortress_validator.py:73
- **Dependency**: mahoun/infrastructure/observability/metrics_migration
- **Direction**: CORE → INFRASTRUCTURE LAYER
- **Evidence**:
  ```python
  try:
      from mahoun.infrastructure.observability.metrics_migration import get_metrics_collector
      METRICS_AVAILABLE = True
  except ImportError:
      METRICS_AVAILABLE = False
  ```
- **Why this violates architecture**: Core depends on infrastructure for metrics collection. Metrics should be an external concern.
- **Risk**: Core logic could fail if metrics infrastructure changes.
- **Recommendation**: Use a protocol in Core for metrics collection, with implementation in infrastructure.

---

### Violation ID: CORE-BOUNDARY-003
- **Severity**: HIGH
- **Location**: mahoun/core/governance/governance_context.py:441
- **Dependency**: mahoun/infrastructure/observability/metrics_migration
- **Direction**: CORE → INFRASTRUCTURE LAYER
- **Evidence**:
  ```python
  try:
      from mahoun.infrastructure.observability.metrics_migration import get_metrics_collector
      get_metrics_collector().register_counter("mahoun_governance_missing_context_total").inc()
  except ImportError:
      pass
  ```
- **Why this violates architecture**: Governance context depends on infrastructure metrics.
- **Risk**: Same as CORE-BOUNDARY-002.
- **Recommendation**: Same as CORE-BOUNDARY-002.

---

### Violation ID: CORE-BOUNDARY-004
- **Severity**: HIGH
- **Location**: mahoun/core/governance/mutation_boundary.py:592
- **Dependency**: mahoun/security/governance_behavioral_integration
- **Direction**: CORE → SECURITY LAYER
- **Evidence**:
  ```python
  try:
      from mahoun.security.governance_behavioral_integration import observe_mutation_background
      observe_mutation_background(
          actor_id=self._actor_id,
          operation_type=m_type.value,
          entity_count=1,
          correlation_id=self._correlation_id,
      )
  except Exception as e:
      logger.debug(f"[MAB] Behavioral monitoring hook failed (non-blocking): {e}")
  ```
- **Why this violates architecture**: Mutation boundary depends on external security layer for behavioral monitoring.
- **Risk**: Changes to the security layer could affect core governance logic.
- **Recommendation**: Define a protocol for mutation observers in Core.

---

### Violation ID: CORE-BOUNDARY-005
- **Severity**: HIGH
- **Location**: mahoun/core/governance/outbox_worker.py:7-8
- **Dependency**:
  - mahoun/graph/neo4j/connection
  - mahoun/graph/sync/outbox_worker
- **Direction**: CORE → GRAPH LAYER
- **Evidence**:
  ```python
  from mahoun.core.governance.governance_context import GovernanceContextManager
  from mahoun.graph.neo4j.connection import get_connection
  from mahoun.graph.sync.outbox_worker import OutboxWorker as _SyncOutboxWorker
  ```
- **Why this violates architecture**: Governance outbox worker depends on graph layer implementation details.
- **Risk**: Core governance logic is tied to Neo4j.
- **Recommendation**: Abstract graph operations behind a protocol in Core.

---

### Violation ID: CORE-BOUNDARY-006
- **Severity**: MEDIUM
- **Location**: mahoun/core/health_checker.py:10
- **Dependency**: mahoun/infrastructure/health_checker
- **Direction**: CORE → INFRASTRUCTURE LAYER
- **Evidence**:
  ```python
  from mahoun.infrastructure.health_checker import (
      HealthChecker,
      HealthStatus,
      ComponentHealth,
  )
  ```
- **Why this violates architecture**: Core health checker is just a re-export of infrastructure.
- **Risk**: Couples Core to infrastructure health implementation.
- **Recommendation**: Define health check protocols in Core.

---

### Violation ID: CORE-BOUNDARY-007
- **Severity**: HIGH
- **Location**: mahoun/core/models/__init__.py:17, 34, 48
- **Dependency**:
  - mahoun/ai/models
  - mahoun/audit/models
  - mahoun/infrastructure/models
- **Direction**: CORE → AI/AUDIT/INFRASTRUCTURE LAYERS
- **Evidence**:
  ```python
  from mahoun.ai.models import (
      AIResponse,
      TokenUsage,
      GenerationMetadata,
      ResponseStatus,
      create_success_response,
      create_error_response,
      PromptTemplate,
      EvidenceSlot,
      ContextRequirement,
      EvidenceSlotType,
      LEGAL_REASONING_TEMPLATE,
      CONTRACT_ANALYSIS_TEMPLATE,
      create_custom_template,
  )
  from mahoun.audit.models import (
      AuditEvent,
      AuditEventType,
      AuditContext,
      AuditSeverity,
      create_audit_event,
      create_model_load_event,
      create_generation_event,
      create_fortress_validation_event,
      create_governance_violation_event,
      create_security_breach_event,
  )
  from mahoun.infrastructure.models import (
      DeploymentProfile,
      ResourceLimits,
      PerformanceTargets,
      ProfileType,
      DESKTOP_MINIMAL,
      ENTERPRISE_FULL,
      load_profile_from_env,
      validate_profile_compatibility,
      create_custom_profile,
  )
  ```
- **Why this violates architecture**: Core models module is a compatibility shim re-exporting non-core models.
- **Risk**: Core becomes a dumping ground for all models, losing architectural clarity.
- **Recommendation**: Move shared model definitions to Core protocols or domain models in Core.

---

### Violation ID: CORE-BOUNDARY-008
- **Severity**: HIGH
- **Location**: mahoun/core/policy_deployment.py:51
- **Dependency**: mahoun/audit/models
- **Direction**: CORE → AUDIT LAYER
- **Evidence**:
  ```python
  from mahoun.audit.models import AuditEvent, AuditEventType
  ```
- **Why this violates architecture**: Policy deployment depends on audit layer models.
- **Risk**: Changes to audit models could break policy deployment.
- **Recommendation**: Define audit event protocols in Core.

---

### Violation ID: CORE-BOUNDARY-009
- **Severity**: HIGH
- **Location**: mahoun/core/policy_resolver.py:34, 402
- **Dependency**:
  - mahoun/ai/profile_manager
  - mahoun/infrastructure/models
- **Direction**: CORE → AI/INFRASTRUCTURE LAYERS
- **Evidence**:
  ```python
  if TYPE_CHECKING:
      from mahoun.ai.profile_manager import ProfileManager
      from mahoun.core.governance.governance_context import GovernanceContext
      from mahoun.infrastructure.models import DeploymentProfile
  ```
  ```python
  if profile_manager is None:
      from mahoun.ai.profile_manager import ProfileManager
      profile_manager = ProfileManager(auto_select=True)
  ```
- **Why this violates architecture**: Policy resolver depends on AI profile manager and infrastructure models.
- **Risk**: Core policy logic is tied to AI layer implementation.
- **Recommendation**: Define Profile and ProfileManager protocols in Core.

---

### Violation ID: CORE-BOUNDARY-010
- **Severity**: HIGH
- **Location**: mahoun/core/query_executor.py:24, 64
- **Dependency**: mahoun/graph/graph_query_service
- **Direction**: CORE → GRAPH LAYER
- **Evidence**:
  ```python
  if TYPE_CHECKING:
      from mahoun.graph.graph_query_service import GraphQueryService
  ```
  ```python
  if _executor_instance is None:
      # Fallback: lazy import for backward compatibility
      from mahoun.graph.graph_query_service import GraphQueryService
      return GraphQueryService()
  ```
- **Why this violates architecture**: Query executor depends on graph layer implementation, even with DI.
- **Risk**: Core query logic is tied to graph layer.
- **Recommendation**: Ensure protocols are strictly followed and avoid fallback imports.

---

### Violation ID: CORE-BOUNDARY-011
- **Severity**: HIGH
- **Location**: mahoun/core/unified_governance.py:39
- **Dependency**: mahoun/ai/profile_manager
- **Direction**: CORE → AI LAYER
- **Evidence**:
  ```python
  if TYPE_CHECKING:
      from mahoun.ai.profile_manager import ProfileManager
      from mahoun.core.governance.governance_context import GovernanceContext
      from mahoun.core.governance_kernel.kernel import (
          KernelMutationBoundary,
          QueryType,
      )
      from mahoun.core.policy_resolver import ExecutionPolicy, PolicyResolver, ViewMode
  ```
- **Why this violates architecture**: Unified governance controller depends on AI layer for profile management.
- **Risk**: Same as CORE-BOUNDARY-009.
- **Recommendation**: Same as CORE-BOUNDARY-009.

---

## Final Verdict

### CORE ARCHITECTURE STATUS: **FAIL**

**Reason**: The Core layer has 11 identified boundary violations where it depends on external layers (AI, Infrastructure, Graph, Security, Audit). This violates the architectural principle that Core should be the stable authority layer that other layers depend on, not the consumer of external implementation details.

**Risks**:
1. Core becomes fragile and dependent on external changes
2. Difficult to test Core in isolation
3. Violates single responsibility principle
4. Harder to evolve architecture

**Recommendations**:
1. Define clear protocols in Core for all external dependencies
2. Move shared model definitions to Core
3. Use dependency injection to invert dependencies
4. Refactor compatibility shims to follow protocol-based design
