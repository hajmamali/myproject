# MAHOUN Frontend Readiness Gate

## Overview

The **Frontend Readiness Gate** is a CI architecture gate that **blocks frontend development** until backend/platform contracts are stable. This gate ensures that the MAHOUN platform has all necessary architectural contracts, boundaries, and validations in place before any frontend work can proceed.

### Purpose

This gate answers the critical question:

> **"Is MAHOUN ready for frontend development without architectural coupling risk?"**

The gate enforces the **Fail-Closed Principle** from the MAHOUN Constitution: if any required contract or boundary is missing or unstable, frontend development is **BLOCKED** until remediation is complete.

### Architecture Principle

The gate implements a **strict layer separation**:

```
┌─────────────────────────────────────┐
│           FRONTEND                    │
│  (React/Vite/TypeScript)               │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│         API CONTRACT                  │
│  (OpenAPI, Request/Response Schemas)  │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│       APPLICATION LAYER               │
│  (Routers, Services, Business Logic) │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│         BACKEND INTERNALS             │
│  (Database, Graph, Embeddings, etc.)  │
└─────────────────────────────────────┘
```

**Frontend MUST NOT depend on anything below the API Contract layer.**

---

## Required Conditions

All 10 checks must **PASS** for the gate to return `READY` status. Any single `FAIL` results in `NOT_READY` status.

### Check Catalog

| # | Check ID | Name | Description | Status |
|---|---------|------|-------------|--------|
| 1 | `bootstrap_stability` | Bootstrap Stability | Validates Tier-0 component stability, behavior snapshots, and contracts | **REQUIRED** |
| 2 | `characterization_tests` | Characterization Tests | Validates test suite and golden masters for regression detection | **REQUIRED** |
| 3 | `api_contract` | API Contract | Validates OpenAPI spec with request/response/error schemas | **REQUIRED** |
| 4 | `boundary_enforcement` | Backend Boundary | Detects forbidden coupling between frontend and backend internals | **REQUIRED** |
| 5 | `auth_contract` | Authentication Contract | Validates auth documentation defining identity, roles, permissions | **REQUIRED** |
| 6 | `governance_boundary` | Governance Boundary | Validates API responses contain governance metadata (request_id, trace_id, audit) | **REQUIRED** |
| 7 | `error_contract` | Error Contract | Validates unified error format with error_code, message, trace_id, timestamp | **REQUIRED** |
| 8 | `observability` | Observability | Validates structured logging, correlation IDs, audit capability | **REQUIRED** |
| 9 | `frontend_architecture` | Frontend Architecture | Requires architecture document defining framework, client strategy, state management | **REQUIRED** |
| 10 | `sdk_readiness` | API Client Readiness | Validates API client abstraction layer | **REQUIRED** |

---

## How to Run

### Basic Usage

```bash
# Run the gate from repository root
python ci/gates/frontend_readiness_gate.py

# Run with quiet output (status only)
python ci/gates/frontend_readiness_gate.py --quiet

# Run with JSON output
python ci/gates/frontend_readiness_gate.py --output json

# Run with YAML output
python ci/gates/frontend_readiness_gate.py --output yaml

# Run with custom repository root
python ci/gates/frontend_readiness_gate.py --repo-root /path/to/repo
```

### Exit Codes

| Exit Code | Status | Meaning |
|-----------|--------|---------|
| 0 | READY | All checks passed. Frontend development can proceed. |
| 1 | NOT_READY | One or more checks failed. Frontend development is BLOCKED. |

### Example Output

```
================================================================================
MAHOUN Frontend Readiness Gate Report
================================================================================
Timestamp: 2026-08-05T12:00:00.000000
Status: NOT_READY

Summary: 8 passed, 2 failed
--------------------------------------------------------------------------------

[PASS] Bootstrap Stability
  Check ID: bootstrap_stability
  Evidence:
    - BEHAVIOR_SNAPSHOT.md exists at mahoun/bootstrap/BEHAVIOR_SNAPSHOT.md
    - bootstrap_contract.yaml exists at mahoun/bootstrap/bootstrap_contract.yaml
    - golden_master directory exists with 3 entries

[FAIL] API Contract
  Check ID: api_contract
  Evidence:
    - OpenAPI specification found at docs/api/reasoning-api.yaml
  Problem: No request/response schema definitions found
  Fix: Create OpenAPI specification at docs/api/openapi.yaml with request schemas, response schemas, and error schemas

[FAIL] Authentication Contract
  Check ID: auth_contract
  Problem: Authentication documentation not found in expected locations
  Fix: Create authentication documentation at docs/security/authentication.md defining identity model, roles, and permissions

================================================================================
RESULT: Frontend development is BLOCKED.
Remediate all FAILED checks before proceeding.
================================================================================
```

---

## Check Details

### Check 1: Bootstrap Stability

**Purpose:** Validate that Tier-0 components (bootstrap layer) are stable and documented.

**Validates:**
- `mahoun/bootstrap/BEHAVIOR_SNAPSHOT.md` exists
- `mahoun/bootstrap/bootstrap_contract.yaml` exists
- `mahoun/bootstrap/golden_master/` directory exists and has snapshots
- Tier-0 components (`manager.py`, `runtime.py`, `contract_validator.py`) are present

**Evidence:** File existence and content validation.

**Fix:** Create missing files and ensure golden master snapshots are in place.

---

### Check 2: Characterization Tests

**Purpose:** Validate that characterization tests exist and can be executed.

**Validates:**
- `tests/bootstrap/characterization/` directory exists
- Test files exist in the directory
- `mahoun/bootstrap/golden_master/` has snapshot files
- `pytest` can collect tests successfully

**Evidence:** Test file count, snapshot file count, pytest collection results.

**Fix:** Create characterization tests and golden snapshots. Ensure pytest is configured correctly.

---

### Check 3: API Contract

**Purpose:** Validate that API contracts are defined and complete.

**Validates:**
- OpenAPI specification exists (`docs/api/openapi.yaml` or equivalent)
- OpenAPI spec contains `paths` section
- OpenAPI spec contains `components.schemas` for request/response types
- OpenAPI spec contains `components.responses` for error types
- Alternative: Pydantic models exist in `api/models/` or `mahoun/api/models/`

**Evidence:** OpenAPI file location, number of paths, number of schemas.

**Fix:** Create `docs/api/openapi.yaml` with complete API specification including all request schemas, response schemas, and error schemas.

---

### Check 4: Backend Boundary Enforcement

**Purpose:** Detect forbidden coupling between frontend and backend internals.

**Validates:**
- Frontend code does NOT import from `mahoun.graph` (Neo4j layer)
- Frontend code does NOT import from `mahoun.core.governance` (direct governance)
- Frontend code does NOT import from `mahoun.ledger` (ledger internals)
- Frontend code does NOT use `GraphDatabase.driver()` (Neo4j driver)
- Frontend code does NOT use `ThreadPoolExecutor` or `ProcessPoolExecutor`
- Frontend code does NOT import neo4j modules directly
- Frontend DOES use API client abstraction in `frontend/src/api/`

**Evidence:** List of violations found (if any), confirmation of clean separation.

**Fix:** Refactor frontend to use only API contract through client abstraction. Remove all direct imports of backend internals.

---

### Check 5: Authentication Contract

**Purpose:** Validate that authentication is properly documented.

**Validates:**
- `docs/security/authentication.md` exists
- Documentation contains: identity model, roles, permissions, authentication

**Evidence:** Document location, sections found.

**Fix:** Create `docs/security/authentication.md` with complete authentication contract definition.

---

### Check 6: Governance Boundary

**Purpose:** Validate that API responses contain governance metadata.

**Validates:**
- Governance middleware exists (`api/middleware/governance_context.py`)
- Middleware handles `request_id`
- Middleware handles `trace_id` / `correlation_id`
- Middleware has audit capability
- Error responses include governance fields
- Provenance/citation handling in reasoning modules

**Evidence:** Middleware file location, fields handled, provenance mechanisms.

**Fix:** Ensure governance middleware injects request_id, trace_id, and audit references. Add provenance/citation to API responses.

---

### Check 7: Error Contract

**Purpose:** Validate unified error format across all endpoints.

**Validates:**
- Error contract defined with fields: `error_code`, `message`, `trace_id`, `timestamp`
- Structured error classes exist
- Error handling in API routers

**Evidence:** Error contract file location, fields defined.

**Fix:** Define unified error format in `mahoun/api/errors.py` with all required fields.

---

### Check 8: Observability

**Purpose:** Validate observability infrastructure.

**Validates:**
- Structured logging configuration exists (`mahoun/core/logging.py`)
- Correlation ID handling exists
- Audit capability exists (`mahoun/ledger/`)

**Evidence:** Logging file location, correlation mechanisms, audit files.

**Fix:** Implement structured logging, correlation ID handling, and audit capability.

---

### Check 9: Frontend Architecture Declaration

**Purpose:** Validate frontend architecture is documented.

**Validates:**
- `docs/frontend/architecture.md` exists
- Document defines: frontend framework, API client strategy, state management, authentication integration, component strategy

**Evidence:** Document location, sections defined.

**Fix:** Create `docs/frontend/architecture.md` with all required sections.

---

### Check 10: API Client Readiness

**Purpose:** Validate API client abstraction exists and is used.

**Validates:**
- API client directory exists (`clients/` or `frontend/src/api/`)
- Client files exist with proper abstraction
- Client uses `fetch` with `API_BASE_URL`
- Client defines TypeScript types matching API contract
- Frontend components consume API through client layer

**Evidence:** Client file locations, usage patterns.

**Fix:** Create API client abstraction in `frontend/src/api/` directory. Ensure all frontend code uses this client layer.

---

## Meaning of PASS/FAIL

### PASS Status

- All 10 checks passed
- All required contracts are in place
- All boundaries are enforced
- Frontend development can **SAFELY PROCEED**
- Exit code: **0**

### FAIL Status

- One or more checks failed
- Missing or incomplete contracts
- Boundary violations detected
- Frontend development is **BLOCKED**
- Exit code: **1**

### Fail-Closed Principle

This gate implements **Fail-Closed** as defined in the MAHOUN Constitution:

> "When evidence is missing, incomplete, or contradictory, the system MUST fail closed — deny access, block the operation, stop the process."

This means:
- If a file is missing → FAIL
- If a test cannot run → FAIL
- If a contract is incomplete → FAIL
- If a boundary is violated → FAIL

There is **NO** "warn and continue" mode. Any failure blocks frontend development.

---

## Remediation Workflow

### Step 1: Identify Failed Checks

```bash
python ci/gates/frontend_readiness_gate.py
```

Note which checks have `[FAIL]` status.

### Step 2: Review Failure Details

For each failed check:
1. Read the **Problem** description
2. Read the **Fix** recommendation
3. Review the **Evidence** to understand what was found

### Step 3: Remediate

Follow the Fix recommendations for each failed check. Do **NOT** weaken checks to make them pass.

#### Common Remediation Tasks:

| Failed Check | Typical Fix |
|--------------|-------------|
| `bootstrap_stability` | Create missing snapshot/contract files |
| `characterization_tests` | Create test files and golden masters |
| `api_contract` | Create/Update OpenAPI specification |
| `boundary_enforcement` | Remove backend imports from frontend, use API client |
| `auth_contract` | Create authentication documentation |
| `governance_boundary` | Add governance metadata to middleware |
| `error_contract` | Define unified error format |
| `observability` | Implement structured logging and correlation IDs |
| `frontend_architecture` | Create architecture document |
| `sdk_readiness` | Create API client abstraction |

### Step 4: Verify Fixes

```bash
# Run the gate again
python ci/gates/frontend_readiness_gate.py

# Continue until all checks PASS
```

### Step 5: Commit Gate Files Only

```bash
# DO NOT commit changes to production code yet
git add ci/gates/frontend_readiness_gate.py
git add ci/gates/frontend_readiness.yaml
git add docs/governance/FRONTEND_READINESS_GATE.md
git commit -m "Add Frontend Readiness Gate validation tooling

Generated by Mistral Vibe.
Co-Authored-By: Mistral Vibe <vibe@mistral.ai>"
```

### Step 6: Integrate with CI/CD

Add the gate to your CI pipeline to **automatically block** frontend development:

#### GitHub Actions Example

```yaml
name: Frontend Readiness Gate

on:
  push:
    paths:
      - 'mahoun/bootstrap/**'
      - 'api/**'
      - 'frontend/**'
      - 'docs/api/**'
      - 'docs/frontend/**'
  pull_request:
    paths:
      - 'mahoun/bootstrap/**'
      - 'api/**'
      - 'frontend/**'
      - 'docs/api/**'
      - 'docs/frontend/**'

jobs:
  frontend-readiness:
    name: Frontend Readiness Gate
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install pyyaml pytest
      
      - name: Run Frontend Readiness Gate
        run: python ci/gates/frontend_readiness_gate.py
```

#### Makefile Integration

```makefile
frontend-readiness:
	python ci/gates/frontend_readiness_gate.py

ci-gate:
	@echo "Running CI Gates..."
	python ci/gates/frontend_readiness_gate.py --quiet
	@echo "Gate passed!"
```

---

## CI/CD Integration

### Pre-commit Hook (Optional)

Prevent commits to frontend code when gate is not ready:

```bash
#!/bin/sh
# .git/hooks/pre-commit

# Check if frontend files are being modified
if git diff --cached --name-only | grep -q '^frontend/' ; then
    echo "Frontend files modified - checking readiness..."
    python ci/gates/frontend_readiness_gate.py --quiet
    if [ $$? -ne 0 ]; then
        echo "ERROR: Frontend Readiness Gate failed!"
        echo "Frontend development is BLOCKED until contracts are stable."
        exit 1
    fi
fi

exit 0
```

### Protected Branch Policy

Configure your Git hosting service to require gate passage before merging:

```yaml
# GitHub Branch Protection
name: main
protection:
  required_status_checks:
    contexts:
      - "Frontend Readiness Gate"
  enforce_admins: true
```

---

## Implementation Details

### Gate Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FrontendReadinessGate                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  _check_bootstrap_stability()                            │ │
│  │  _check_characterization_tests()                         │ │
│  │  _check_api_contract()                                   │ │
│  │  _check_boundary_enforcement()                           │ │
│  │  _check_auth_contract()                                  │ │
│  │  _check_governance_boundary()                           │ │
│  │  _check_error_contract()                                 │ │
│  │  _check_observability()                                  │ │
│  │  _check_frontend_architecture()                           │ │
│  │  _check_sdk_readiness()                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Input: Repository root path                                   │
│  Output: GateReport with CheckResult[]                         │
│  Exit Code: 0 (READY) or 1 (NOT_READY)                        │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
ci/
└── gates/
    ├── frontend_readiness_gate.py    # Executable validation script
    ├── frontend_readiness.yaml       # Machine-readable configuration
    └── frontend_readiness_history.log # Historical tracking (optional)

docs/
└── governance/
    └── FRONTEND_READINESS_GATE.md     # This documentation
```

### Data Classes

```python
@dataclass
class CheckResult:
    check_id: str
    name: str
    status: str  # PASS or FAIL
    evidence: List[str]
    problem: Optional[str]
    fix: Optional[str]

@dataclass
class GateReport:
    timestamp: str
    status: str  # READY or NOT_READY
    checks: List[CheckResult]
    summary: Dict[str, int]  # {