# Frontend Gate Requirements Matrix

**Classification:** MANDATORY PRE-READ  
**Authority Level:** Constitutional Entry Point  
**Version:** 1.0.0  
**Status:** Normative  

---

## Executive Summary

The MAHOUN Frontend CI Gate implements a **fail-closed, constitutional governance system** with **10 primary validation checks** and **multiple supporting gates**. Frontend development is **BLOCKED** until ALL requirements pass.

**Constitutional Authority Hierarchy:**
1. `mahoun/constitutional/constitution/CONSTITUTION.md` - Highest authority
2. `mahoun/constitutional/` - Governance, security, workflow rules  
3. `AGENTS.md` - Canonical component locations
4. Implementation details - Subordinate to constitutional docs

---

## Primary Frontend Gate Checks

Based on `ci/gates/frontend_readiness_gate.py` and `ci/gates/frontend_readiness.yaml`:

### CHECK 1: Bootstrap Stability
- **Requirement:** Validates existence of bootstrap behavior snapshots, contracts, and golden masters
- **Files Required:**
  - `mahoun/bootstrap/BEHAVIOR_SNAPSHOT.md`
  - `mahoun/bootstrap/bootstrap_contract.yaml`  
  - `mahoun/bootstrap/golden_master/` (with content)
- **Validation:** Ensures Tier-0 components are stable and unauthorized changes are detected
- **Severity:** FAIL (blocks frontend)
- **Gate Script:** `ci/gates/gate_bootstrap_contract.sh`

### CHECK 2: Characterization Tests
- **Requirement:** Validates existence of characterization test suite and golden snapshots
- **Paths Required:**
  - `tests/bootstrap/characterization/`
  - `mahoun/bootstrap/golden_master/`
- **Validation:** Ensures pytest can collect and run tests successfully  
- **Severity:** FAIL (blocks frontend)
- **Gate Script:** `ci/gates/gate_bootstrap_characterization.sh`

### CHECK 3: API Contract
- **Requirement:** Validates OpenAPI specification with complete schemas
- **Locations Required:**
  - `docs/api/openapi.yaml` OR `docs/api/openapi.yml` OR `openapi.yaml`
- **Schema Paths:**
  - `api/models/` OR `mahoun/api/models/`
- **Required Sections:**
  - `paths` - All API endpoints
  - `components.schemas` - Request/response models
  - `components.responses` - Error schemas
- **Severity:** FAIL (blocks frontend)

### CHECK 4: Backend Boundary Enforcement  
- **Requirement:** Detects forbidden coupling between frontend and backend internals
- **Forbidden Patterns:**
  - Direct database module imports
  - Neo4j modules (`mahoun.graph`, `neo4j`, `GraphDatabase.driver`)
  - Embedding internals  
  - Executor classes (`ThreadPoolExecutor`, `ProcessPoolExecutor`)
  - Governance imports (`mahoun.core.governance`, `mahoun.ledger`)
- **Allowed Dependencies:** Frontend → API Contract → Application Layer ONLY
- **Severity:** FAIL (blocks frontend)
- **Gate Script:** `ci/gates/gate_architecture_boundaries.sh`

### CHECK 5: Authentication Contract
- **Requirement:** Validates authentication documentation exists
- **Locations Required:**
  - `docs/security/authentication.md` OR `docs/authentication.md`
- **Required Sections:**
  - `identity_model` - User identity structure
  - `roles` - Role definitions  
  - `permissions` - Permission matrix
  - `authentication` - Auth flow documentation
- **Severity:** FAIL (blocks frontend)

### CHECK 6: Governance Boundary
- **Requirement:** Validates user-facing API responses contain governance metadata
- **Required Fields in ALL API responses:**
  - `request_id` - Request correlation ID
  - `trace_id` - Distributed tracing ID  
  - `audit_reference` - Audit trail reference
  - `provenance` - Evidence provenance (where applicable)
  - `citation` - Legal citations (where applicable)
- **Middleware Required:**
  - `api/middleware/governance_context.py`
- **Severity:** FAIL (blocks frontend)

### CHECK 7: Error Contract
- **Requirement:** Validates unified error format across ALL endpoints
- **Required Fields in ALL error responses:**
  - `error_code` - Machine-readable error code
  - `message` - Human-readable error message  
  - `trace_id` - Correlation for debugging
  - `timestamp` - When error occurred
- **Locations Required:**
  - `mahoun/api/errors.py` OR `api/errors.py`
- **Severity:** FAIL (blocks frontend)

### CHECK 8: Observability  
- **Requirement:** Validates structured logging, correlation IDs, and audit capability
- **Components Required:**
  - `structured_logging` - JSON structured logs
  - `correlation_ids` - Request correlation  
  - `audit_capability` - Audit trail access
- **Files Required:**
  - `mahoun/core/logging.py`
  - `api/middleware/governance_context.py`  
  - `mahoun/ledger/` (ledger system)
- **Severity:** FAIL (blocks frontend)

### CHECK 9: Frontend Architecture Declaration
- **Requirement:** Frontend architecture documentation and boundaries
- **Expected:** Architecture decision records, frontend-backend contract
- **Severity:** FAIL (blocks frontend)

### CHECK 10: SDK Readiness
- **Requirement:** API client SDK or well-documented API access patterns
- **Expected:** Client libraries, API documentation, example usage
- **Severity:** FAIL (blocks frontend)

---

## Supporting Governance Gates

### Neo4j Governance Gate (`ci/gates/gate_neo4j_governance.sh`)
- **Requirement:** No raw Neo4j driver/session usage outside approved governance wrappers
- **Allowed Paths:**
  - `mahoun/graph/neo4j/connection.py`
  - `mahoun/graph/neo4j/schema.py` 
  - `mahoun/graph/neo4j/runner.py`
  - `tests/` (with proper guards)
- **Forbidden Patterns:**
  - `AsyncGraphDatabase.driver()`
  - `GraphDatabase.driver()`  
  - Raw `.session()` calls
  - `tx.run()` outside governed paths
  - APOC mutation procedures
  - Direct mutation Cypher (`MERGE`, `CREATE`, `DETACH DELETE`)
- **Severity:** FAIL (governance violation)

### Fortress Governance Gate (`ci/scripts/fortress_governance_gate.py`)
- **Critical Files Required:**
  - `mahoun/core/fortress_validator.py`
  - `mahoun/core/governance_lock.py`
  - `mahoun/core/governance/governance_context.py`
  - `mahoun/core/governance/provenance_tracker.py`
  - `constitution/RedLines.yaml`
  - `monitoring/prometheus/alerts/governance_alerts.yml`
- **Integration Requirements:**
  - `FortressValidator` in `api/routers/reasoning.py`
  - `GovernanceLock` enforcement  
  - `GovernanceContextManager` usage
  - Provenance tracking implementation
- **Bypass Prevention:** Scans for governance bypass patterns
- **Severity:** FAIL (security violation)

### Architecture Boundaries Gate (`ci/gates/gate_architecture_boundaries.sh`)
- **Boundary Rules:**
  - RAG services MUST NOT create `GovernanceContext`
  - RAG services MUST NOT call `ReasoningEngine/VerdictEngine`  
  - RAG services MUST NOT make policy decisions (`PolicyResolver`)
  - Router MUST remain orchestrator-only (no business logic)
  - No duplicate RAG service implementations
  - RAG MUST NOT bypass Container dependency injection
- **Severity:** FAIL (architectural violation)

### Coverage Gate (`ci/gates/gate_coverage.sh`)  
- **Requirements:**
  - Overall coverage MUST NOT regress from baseline
  - Critical modules MUST meet thresholds:
    - `governance`: ≥80%
    - `ledger`: ≥75% 
    - `reasoning`: ≥70%
    - `fortress`: ≥80%
  - New code MUST have test coverage
- **Baseline:** `ci/coverage_baseline.json`
- **Severity:** FAIL (quality gate)

---

## Constitutional Requirements

### Fail-Closed Principle (CONSTITUTION.md Section 10)
- **Rule:** Unknown state = unsafe conditions
- **Application:** Missing evidence is BLOCKING condition
- **Enforcement:** All gates fail when validation state unknown

### Source of Truth Principle (CONSTITUTION.md Section 7)  
- **Rule:** Every system concept has ONE authoritative source
- **Application:** No duplicated definitions allowed
- **Enforcement:** Canonical component validation via `AGENTS.md`

### Evidence-Based Engineering (CONSTITUTION.md Section 12)
- **Rule:** All decisions supported by evidence  
- **Application:** Tests, analysis reports, validation required
- **Enforcement:** No assumptions allowed in gates

### Agent Authority Boundaries (CONSTITUTION.md Section 8-9)
- **Rule:** AI agents are execution units, NOT architectural authorities
- **Application:** Agents follow constitutional governance
- **Enforcement:** Constitutional bootstrap required before any action

---

## Validation Command Matrix

| Gate | Command | Exit Codes |
|------|---------|------------|
| Frontend Readiness | `python ci/gates/frontend_readiness_gate.py` | 0=READY, 1=BLOCKED |
| Neo4j Governance | `ci/gates/gate_neo4j_governance.sh` | 0=PASS, 1=VIOLATION |
| Fortress Governance | `python ci/scripts/fortress_governance_gate.py` | 0=PASS, 1=FAIL, 2=MISSING |
| Architecture Boundaries | `ci/gates/gate_architecture_boundaries.sh` | 0=PASS, 1=VIOLATION |
| Bootstrap Contract | `ci/gates/gate_bootstrap_contract.sh` | 0=PASS, 1=VIOLATION |
| Characterization Tests | `ci/gates/gate_bootstrap_characterization.sh --mode validate` | 0=PASS, 1=FAIL |
| Coverage Gate | `ci/gates/gate_coverage.sh` | 0=PASS, 1=REGRESSED |
| Schema Drift | `python ci/scripts/schema_drift_detector.py --verify-semantic` | 0=PASS, 1=DRIFT |
| Governance Compliance | `python scripts/validate_governance_compliance.py` | 0=PASS, 1=VIOLATIONS |
| Preproduction Validation | `python scripts/run_preproduction_validation.py --profile production` | 0=PASS, 1=FAIL, 2=CONFIG_ERROR |

---

## GitHub Actions Enforcement

**Workflow:** `.github/workflows/kernel-governance.yml`

**Jobs:**
1. **kernel-integrity** - Verifies kernel files unchanged without authorization
2. **architecture-enforcement** - Checks forbidden imports and layer violations  
3. **api-compatibility** - Verifies public API unchanged without authorization
4. **governance-tests** - Runs governance-specific test suite
5. **security-validation** - Additional security checks

**Branch Protection:**
- `main` branch requires ALL jobs to pass before merge
- No force-push allowed on protected branches
- Governance cannot be disabled in CI

---

## Critical Files for Frontend Readiness

### Must Exist
- `mahoun/constitutional/constitution/CONSTITUTION.md`
- `mahoun/bootstrap/BEHAVIOR_SNAPSHOT.md`  
- `mahoun/bootstrap/bootstrap_contract.yaml`
- `docs/api/openapi.yaml` (or equivalent)
- `docs/security/authentication.md`
- `api/middleware/governance_context.py`
- `mahoun/api/errors.py` or `api/errors.py`
- `mahoun/core/logging.py`
- `constitution/RedLines.yaml`

### Must Pass Validation  
- All characterization tests in `tests/bootstrap/characterization/`
- All governance compliance checks
- All architecture boundary validations
- Schema drift detection
- Coverage thresholds

---

## Exit Condition Matrix

| Condition | Frontend Status | Action Required |
|-----------|----------------|-----------------|
| All 10 checks PASS | ✅ READY | Frontend development AUTHORIZED |
| Any check FAILS | ❌ BLOCKED | Fix violations, re-validate |
| Missing constitutional docs | 🚫 CRITICAL | Constitutional bootstrap required |
| Governance bypass detected | 🛡️ SECURITY | Security review, remediation |
| Architecture violation | 🏛️ ARCHITECTURAL | Architectural review, compliance |

---

## Final Authority

This requirements matrix is subordinate to:
1. `mahoun/constitutional/constitution/CONSTITUTION.md`  
2. `mahoun/constitutional/README.md`
3. All documents in `mahoun/constitutional/`

For conflicts or clarifications, consult constitutional documents first.

**Frontend development is BLOCKED until ALL requirements are satisfied.**

---

*Generated by MAHOUN Frontend Readiness Guardian*  
*Classification: MANDATORY COMPLIANCE DOCUMENTATION*