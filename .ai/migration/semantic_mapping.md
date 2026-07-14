# Semantic Mapping for Migration: MahouNZ → KingMahouN

> **Classification:** MIGRATION GOVERNANCE / BREAKING RISK REGISTER
> **Created:** 2026-07-10
> **Purpose:** Prevent blind refactor. Every file move MUST be evaluated for semantic collision before transfer.

---

## Status Legend

- ✅ **DONE** — Transferred and verified
- 🟢 **SAFE** — Recommended for transfer (no semantic collision)
- 🟡 **RISKY** — Needs deeper analysis before transfer
- 🔴 **BLOCKED** — Semantic fork risk detected, do NOT transfer
- ⏸️ **HOLD** — Awaiting decision

---

## ✅ COMPLETED TRANSFERS (10 files)

### Core Governance Modules (Core Hubs)
| Old Location | New Location | Status | Risk |
|---|---|---|---|
| `mahoun/core/unified_governance.py` | `mahoun/core/unified_governance.py` | ✅ DONE | None — canonical hub |
| `mahoun/core/policy_resolver.py` | `mahoun/core/policy_resolver.py` | ✅ DONE | None — canonical hub |

### Contracts Layer (Single Ownership)
| Old Location | New Location | Status | Risk |
|---|---|---|---|
| `mahoun/schemas/contracts/__init__.py` | `mahoun/schemas/contracts/__init__.py` | ✅ DONE | None — re-exports |
| `mahoun/schemas/contracts/core_contracts.py` | `mahoun/schemas/contracts/core_contracts.py` | ✅ DONE | None — single source |
| `mahoun/schemas/contracts/ledger_contracts.py` | `mahoun/schemas/contracts/ledger_contracts.py` | ✅ DONE | None — Semantic Fork removed |
| `mahoun/schemas/contracts/reasoning_contracts.py` | `mahoun/schemas/contracts/reasoning_contracts.py` | ✅ DONE | None — frozen=True + validators |
| `mahoun/schemas/contracts/invariants_contracts.py` | `mahoun/schemas/contracts/invariants_contracts.py` | ✅ DONE | None — canonical |

### Registry & Governance Scripts
| Old Location | New Location | Status | Risk |
|---|---|---|---|
| `mahoun/contracts/ownership.yaml` | `mahoun/contracts/ownership.yaml` | ✅ DONE | None — registry file |
| `scripts/validate_contract_ownership.py` | `scripts/validate_contract_ownership.py` | ✅ DONE | None — CI gate |

### Tests
| Old Location | New Location | Status | Risk |
|---|---|---|---|
| `tests/governance/test_el_i8_integration.py` | `tests/governance/test_el_i8_integration.py` | ✅ DONE | None — import path fix |
| `tests/contracts/test_contract_ownership.py` | `tests/contracts/test_contract_ownership.py` | ✅ DONE | None — new test |

### Audit Layer (5 files)
| Old Location | New Location | Status | Risk |
|---|---|---|---|
| `mahoun/audit/__init__.py` | `mahoun/audit/__init__.py` | ✅ DONE | None |
| `mahoun/audit/airgap_exporter.py` | `mahoun/audit/airgap_exporter.py` | ✅ DONE | Fixed: `exceptions_v2` → `exceptions.MahounError` |
| `mahoun/audit/transfer.py` | `mahoun/audit/transfer.py` | ✅ DONE | None |
| `mahoun/audit/regulatory_export_templates.py` | `mahoun/audit/regulatory_export_templates.py` | ✅ DONE | None |
| `mahoun/audit/formatters.py` | `mahoun/audit/formatters.py` | ✅ DONE | None |

### Core Additions (4 files, today)
| Old Location | New Location | Status | Risk |
|---|---|---|---|
| `mahoun/core/dependency_validator.py` | `mahoun/core/dependency_validator.py` | ✅ DONE | None |
| `mahoun/core/policy_deployment.py` | `mahoun/core/policy_deployment.py` | ✅ DONE | None |
| `mahoun/core/query_executor.py` | `mahoun/core/query_executor.py` | ✅ DONE | None |
| `mahoun/core/rollback_orchestrator.py` | `mahoun/core/rollback_orchestrator.py` | ✅ DONE | None |

---

## 🔴 BLOCKED — Semantic Fork Risk

| File | Old | Reason |
|---|---|---|
| `exceptions_v2.py` | `MahouNZ/mahoun/core/` | `exceptions.py` already exists in `KingMahouN/mahoun/core/` with `MahounError`. Transfer would create duplicate definition. **Mapped to:** `MahounError as MahounException` alias (already applied in `airgap_exporter.py`) |

---

## ⏸️ HOLD — Awaiting Semantic Mapping

### `mahoun/core/models/` (CRITICAL)

**KingMahouN has these (Domain Models):**
- `entity.py` — Legal/domain entities
- `reasoning.py` — Reasoning graph models
- `project_model/` — Project management models

**MahouNZ has these (Runtime Models):**
- `ai_response.py` — AI provider responses
- `audit_event.py` — Audit event records
- `deployment_profile.py` — Deployment configuration
- `prompt_template.py` — Prompt templates

**Proposed Namespace Restructure (per your policy):**
```
mahoun/core/
├── domain_models/      # KingMahouN existing
│   ├── entity.py
│   ├── reasoning.py
│   └── project_model/
│
└── runtime_models/     # MahouNZ incoming
    ├── ai_response.py
    ├── audit_event.py
    ├── deployment_profile.py
    └── prompt_template.py
```

**Breaking Risk if Merged Blindly:** 🔴 HIGH
- `models.Entity` could mean: legal entity, DB entity, graph entity, or agent entity
- This is the **exact Semantic Fork pattern** that your `AGENTS.md` warns about

**Required Before Transfer:**
- [ ] Map every usage of `models.Entity` in both repos
- [ ] Map every usage of `models.Reasoning` in both repos
- [ ] Decide on namespace split (domain_models vs runtime_models)
- [ ] Refactor imports across codebase

---

### `mahoun/core/protocols/` (HIGH RISK)

**KingMahouN has these:**
- `mahoun/core/protocols.py` (root) — Likely the canonical one

**MahouNZ has these:**
- `mahoun/core/protocols/__init__.py`
- `mahoun/core/protocols/advanced_protocols.py`
- `mahoun/core/protocols/ai_runtime.py`
- `mahoun/core/protocols/legacy_protocols.py`

**Critical Question:** Is `core/protocols.py` (single file) the same as `core/protocols/__init__.py` (package)?

**Required Before Transfer:**
- [ ] Diff `core/protocols.py` vs `core/protocols/__init__.py`
- [ ] Check if `legacy_protocols.py` violates AGENTS.md (legacy interfaces are forbidden)
- [ ] Decide: expand `protocols.py` to package, or keep as single file

---

### `mahoun/core/archive/` (OPTIONAL)

**Content:** Graph, ingest, rag, vector_store
**Status:** Historical/deprecated
**Recommendation:** KEEP in MahouNZ only. Do not transfer.

---

## 🟢 DUAL-MODE ARCHITECTURE (DESIGN REQUIRED)

Per your spec, the following components need profile-based execution:

### Profile Structure
```python
class DeploymentMode(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class EnforcementLevel(Enum):
    RELAXED = "relaxed"
    STRICT = "strict"

@dataclass
class DeploymentProfile:
    mode: DeploymentMode
    allow_untrusted_agents: bool
    require_audit: bool
    require_signature: bool
    enforcement_level: EnforcementLevel
    storage_backend: str  # "sqlite" | "ledger"
    audit_format: str     # "jsonl" | "cef+jsonld"
```

### Components Requiring Dual-Mode

| Component | Dev Behavior | Prod Behavior | Owner File |
|---|---|---|---|
| **Execution Engine** | Verbose logs, mock providers | Validated agents, immutable audit | TBD |
| **Governance Layer** | WARN + continue | VIOLATION + BLOCK + AUDIT | `mutation_boundary.py` |
| **Agent Runtime** | Agent → Skill → Test | Agent → Auth → Policy → Ledger | TBD |
| **Storage** | SQLite, temp state | Immutable ledger, versioned | TBD |

### Existing Profile Support

- ✅ `mahoun/core/policy_deployment.py` already has versioned deployments
- ✅ `mahoun/core/models/deployment_profile.py` (Pydantic) — needs transfer
- ❌ No central `DeploymentProfile` registry yet
- ❌ No `MAHOUN_ENV` resolution logic

---

## 🚀 NEXT STEPS (in order)

1. **DO NOT** transfer any `models/` file until namespace split is decided
2. **DO NOT** transfer any `protocols/` file until contract diff is complete
3. **DECIDE** on namespace structure (domain_models vs runtime_models)
4. **BUILD** `DeploymentProfile` infrastructure:
   - Pydantic model in `core/runtime_models/deployment_profile.py`
   - Registry in `core/deployment_profile.py` (already exists as file)
   - Resolver: `MAHOUN_ENV` + CLI args + config file
5. **WIRE** the 4 dual-mode components to read profile at startup
6. **TEST** profile switching (dev vs prod) for each component

---

## 📊 MIGRATION STATS

| Status | Count |
|---|---|
| ✅ Transferred | 19 |
| 🔴 Blocked | 1 |
| ⏸️ On Hold | 8 |
| 🟢 Designed but not built | 1 (Dual-mode infra) |

**Tests Passing:** 339 (Contracts + Governance)
**Tests Failing:** 0

---

*Last Updated: 2026-07-10*
*Authority: User + AI assistant (adversarial review)*
