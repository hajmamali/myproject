# Core Dependency Graph

## Key Definitions
- **Allowed (GREEN)**: Core → Core (or external third-party packages like typing, dataclasses, etc.)
- **Requires Review (YELLOW)**: Core → Infrastructure/Other (but maybe acceptable as compatibility layer)
- **Forbidden (RED)**: Core → Non-Core (infrastructure, AI layer, etc., with architectural risks)

---

## Graph Representation (Mermaid)
```mermaid
graph TD
    subgraph CORE
        core_governance["mahoun/core/governance/*"]
        core_protocols["mahoun/core/protocols/*"]
        core_main["mahoun/core/*.py"]
    end

    subgraph NON_CORE
        infra["mahoun/infrastructure/*"]
        ai["mahoun/ai/*"]
        graph["mahoun/graph/*"]
        audit["mahoun/audit/*"]
        security["mahoun/security/*"]
    end

    %% Allowed Dependencies (Core → Core)
    core_governance --> core_protocols
    core_governance --> core_main
    core_main --> core_protocols

    %% Violations (Core → Non-Core)
    core_main["mahoun/core/fortress_validator.py"] --> ai["mahoun/reasoning/unified_reasoning_service"]
    core_main --> infra["mahoun/infrastructure/observability/metrics_migration"]
    core_governance["mahoun/core/governance/governance_context.py"] --> infra
    core_governance["mahoun/core/governance/mutation_boundary.py"] --> security["mahoun/security/governance_behavioral_integration"]
    core_governance["mahoun/core/governance/outbox_worker.py"] --> graph["mahoun/graph/neo4j/connection"]
    core_governance --> graph["mahoun/graph/sync/outbox_worker"]
    core_main["mahoun/core/health_checker.py"] --> infra["mahoun/infrastructure/health_checker"]
    core_main["mahoun/core/models/__init__.py"] --> ai["mahoun/ai/models"]
    core_main --> audit["mahoun/audit/models"]
    core_main --> infra["mahoun/infrastructure/models"]
    core_main["mahoun/core/policy_deployment.py"] --> audit
    core_main["mahoun/core/policy_resolver.py"] --> ai["mahoun/ai/profile_manager"]
    core_main --> infra["mahoun/infrastructure/models"]
    core_main["mahoun/core/query_executor.py"] --> graph["mahoun/graph/graph_query_service"]
    core_main["mahoun/core/unified_governance.py"] --> ai
```

---

## Detailed Dependency Breakdown

### 1. mahoun/core/fortress_validator.py
- **Imports from non-core**:
  - `mahoun/reasoning/unified_reasoning_service` (ReasoningResponse)
  - `mahoun/infrastructure/observability/metrics_migration` (get_metrics_collector)
  - `reasoning_logic.parser` (FOLConverter, ParseError)

### 2. mahoun/core/governance/governance_context.py
- **Imports from non-core**:
  - `mahoun/infrastructure/observability/metrics_migration` (get_metrics_collector)

### 3. mahoun/core/governance/mutation_boundary.py
- **Imports from non-core**:
  - `mahoun/security/governance_behavioral_integration` (observe_mutation_background)

### 4. mahoun/core/governance/outbox_worker.py
- **Imports from non-core**:
  - `mahoun/graph/neo4j/connection` (get_connection)
  - `mahoun/graph/sync/outbox_worker` (OutboxWorker)

### 5. mahoun/core/health_checker.py
- **Imports from non-core**:
  - `mahoun/infrastructure/health_checker` (HealthChecker, etc.)

### 6. mahoun/core/models/__init__.py
- **Imports from non-core**:
  - `mahoun/ai/models`
  - `mahoun/audit/models`
  - `mahoun/infrastructure/models`

### 7. mahoun/core/policy_deployment.py
- **Imports from non-core**:
  - `mahoun/audit/models` (AuditEvent, AuditEventType)

### 8. mahoun/core/policy_resolver.py
- **Imports from non-core**:
  - `mahoun/ai/profile_manager` (ProfileManager)
  - `mahoun/infrastructure/models` (via ProfileManager)

### 9. mahoun/core/query_executor.py
- **Imports from non-core**:
  - `mahoun/graph/graph_query_service` (GraphQueryService)

### 10. mahoun/core/unified_governance.py
- **Imports from non-core**:
  - `mahoun/ai/profile_manager` (ProfileManager)
