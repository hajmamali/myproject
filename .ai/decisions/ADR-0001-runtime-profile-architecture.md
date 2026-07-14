# ADR-0001: Runtime Profile Architecture (Dual-Mode: Development & Production)

> **Status:** PROPOSED
> **Date:** 2026-07-10
> **Deciders:** Project Owner + AI Assistant (adversarial review)
> **Classification:** ARCHITECTURAL / MIGRATION-GOVERNING

---

## Context

MahouN must operate in two distinct execution modes:

1. **Development Mode** — on a personal laptop with limited resources
2. **Production Mode** — on a high-performance server with full audit, immutability, and policy enforcement

The seeds of profile-based execution already exist in the codebase:
- `mahoun/core/policy_deployment.py` (versioned deployments)
- `mahoun/core/models/deployment_profile.py` (Pydantic)
- `mahoun/core/contracts/ownership.yaml` (registry)
- `mahoun/audit/` (format-aware exporters)

However, the dual-mode architecture is **not yet formalized**. A naive `MAHOUN_ENV=production` switch is insufficient because it does not capture the full policy surface (audit, signatures, agent trust, storage backend).

Without a formalized profile kernel, every future component will reinvent its own mode-detection logic, leading to **Semantic Fork** — the exact pattern that `AGENTS.md` warns against.

---

## Decision

We adopt a **Deployment Profile Kernel** with the following structure:

### 0. Critical Invariant: Dependency Direction

```
deployment  ──>  runtime       (✅ ALLOWED)
runtime_models  ──>  deployment (❌ FORBIDDEN)
```

`DeploymentProfile` is a **configuration domain object**, not a runtime event model. It decides *what policies are active, which agents may run, what audit level to use, how strict validation should be*. Therefore it must NOT depend on runtime execution models, or circular imports become inevitable.

**Enforcement:** Any import of `runtime_models` from `core/deployment/` is a critical violation.

### 0.1 Responsibility Split (Single Responsibility per file)

| File | Question it answers | Contains |
|---|---|---|
| `profile.py` | "What is a profile?" | `DeploymentProfile`, `Environment`, `EnforcementLevel`, `AuditMode` (Pydantic + enums only, NO logic) |
| `resolver.py` | "Which profile to use?" | `resolve_profile()`, config loading, `MAHOUN_ENV` resolution |
| `registry.py` | "What profiles exist?" | `PROFILE_REGISTRY`, factory functions |
| `policies.py` | "What behavior does this profile enforce?" | Policy functions that read profile and act |

> **Hard rule:** `profile.py` contains Pydantic models and enums ONLY. No I/O, no logic, no imports from runtime models.

### 1. Three Profiles (not two)

```python
class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
```

> Staging is included because every production-grade system has a pre-prod gate. Omitting it would force ad-hoc additions later.

### 2. Composite Profile Model (Pydantic)

A `DeploymentProfile` is **not** a simple enum. It carries the full policy surface:

```python
class DeploymentProfile(BaseModel):
    name: str
    environment: DeploymentEnvironment
    audit_required: bool
    strict_validation: bool
    allow_experimental_agents: bool
    require_signature: bool
    storage_backend: Literal["sqlite", "ledger"]
    audit_format: Literal["jsonl", "cef", "jsonld", "sqlite"]
    enforcement_level: Literal["relaxed", "strict"]
    resource_limits: ResourceLimits
```

### 3. Registry Pattern (no two definitions)

A single `PROFILE_REGISTRY` maps environment names to profile instances:

```python
PROFILE_REGISTRY: Dict[DeploymentEnvironment, DeploymentProfile] = {
    DeploymentEnvironment.DEVELOPMENT: DevelopmentProfile(),
    DeploymentEnvironment.STAGING: StagingProfile(),
    DeploymentEnvironment.PRODUCTION: ProductionProfile(),
}
```

> No code outside this registry is permitted to construct profile instances. This is the **Single Ownership** rule applied to profiles.

### 4. Resolver (single entry point)

A `resolve_profile()` function that reads from:
- `MAHOUN_ENV` environment variable (highest priority)
- `~/.mahoun/config.yaml` (user config)
- Default: `DEVELOPMENT` (safe default)

```python
def resolve_profile(
    env_var: str = "MAHOUN_ENV",
    config_path: Path = Path.home() / ".mahoun" / "config.yaml",
) -> DeploymentProfile:
    ...
```

> All components (Execution Engine, Governance, Agent Runtime, Storage) MUST call `resolve_profile()` at startup, not duplicate the resolution logic.

### 5. File Structure

```
mahoun/core/deployment/
├── __init__.py
├── profile.py          # Pydantic models + enums
├── registry.py         # PROFILE_REGISTRY + factory functions
├── resolver.py         # resolve_profile() + config loading
└── policies.py         # Profile-driven policy functions
```

### 6. Default Profiles

| Field | Development | Staging | Production |
|---|---|---|---|
| `audit_required` | False | True | True |
| `strict_validation` | False | True | True |
| `allow_experimental_agents` | True | False | False |
| `require_signature` | False | True | True |
| `storage_backend` | sqlite | ledger | ledger |
| `audit_format` | jsonl | jsonld | cef+jsonld |
| `enforcement_level` | relaxed | strict | strict |

---

## Consequences

### Positive

1. **Single source of truth** for deployment mode — no per-component mode detection
2. **Type-safe** — Pydantic validation prevents invalid profiles
3. **Testable** — components can be tested with explicit profile injection
4. **Auditable** — profile is recorded in audit events
5. **Extensible** — new fields (e.g., `gpu_enabled`) can be added without breaking existing code

### Negative

1. **Migration cost** — components that previously read `os.environ` directly must be refactored
2. **Configuration complexity** — `~/.mahoun/config.yaml` adds another config file
3. **Risk of over-engineering** — three profiles may be more than needed initially

### Mitigations

- Migration is incremental; we start with the 4 critical components only
- Staging can be deprecated if unused after 6 months
- The Pydantic schema makes over-specification visible (fields that are always the same across profiles can be hardcoded)

---

## Affected Components (4 critical, ordered by impact)

1. **Execution Engine** — read profile at startup, fail-fast if Production requires signature but component doesn't sign
2. **Governance Layer** — `mutation_boundary.py` checks `enforcement_level` (WARN vs BLOCK)
3. **Agent Runtime** — read `allow_experimental_agents` to filter agent registry
4. **Storage** — `storage_backend` selects SQLite vs Neo4j-ledger

---

## Compliance Verification

After implementation, run:

```bash
python scripts/validate_profile_architecture.py
```

This script enforces:
1. No component reads `os.environ["MAHOUN_ENV"]` directly (must use `resolve_profile()`)
2. No duplicate `DeploymentProfile` definitions
3. `PROFILE_REGISTRY` is the only place profiles are constructed
4. All 4 critical components have profile-aware behavior

---

## Alternatives Considered

### A) `MAHOUN_ENV` string switch only
- ❌ Does not capture full policy surface
- ❌ Components would still duplicate mode logic

### B) YAML file per environment
- ❌ No type safety
- ❌ Easy to have inconsistent files

### C) Two-profile only (no staging)
- ❌ Forces ad-hoc additions later
- ❌ Breaks production deployment pipelines

### D) Feature flags (LaunchDarkly-style)
- ❌ External dependency
- ❌ Over-engineered for this use case

---

## References

- `AGENTS.md` — Single Ownership and Semantic Fork rules
- `.ai/migration/semantic_mapping.md` — Migration status register
- `mahoun/core/policy_deployment.py` — Existing versioned deployment logic
- `mahoun/core/models/deployment_profile.py` — Existing Pydantic model (in MahouNZ)

---

*This ADR governs the design of the DeploymentProfile Kernel. Any change to this architecture requires a new ADR.*
