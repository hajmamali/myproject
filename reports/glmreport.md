# Governance Consolidation — Pre-Migration Report

Status: READ-ONLY AUDIT / PRE-MIGRATION PROOF (no code modified)
Date: 2026-08-13
Classifier: CASE C — governed architectural migration (in-flight, abandoned mid-way)

This report is the deliverable of the pre-migration proof phase. No Tier-0
protected files, kernel lock, manifest, CI gates, or governance code were
modified to produce it. All claims cite `file:line` evidence verifiable in
the working tree.

---

## 0. SUMMARY (Decision Record)

```text
CURRENT CANONICAL AUTHORITY (runtime):
  mahoun/core/governance/mutation_boundary.py
    MutationAuthorizationBoundary.inspect()
    Gate site: mahoun/graph/neo4j/connection.py:221 (called on EVERY query)

CURRENT TIER-0 (manifest protected_files):
  mahoun/core/governance_kernel/__init__.py
  mahoun/core/governance_kernel/kernel.py

PROPOSED TARGET AUTHORITY (task + manifest §6):
  Tier-0: mahoun/core/governance_kernel/   (zero-dependency kernel)
  Tier-1: mahoun/core/governance/           (runtime services/context)
  Tooling: mahoun/governance/               (separate domain)
  App:    services/api/graph consumers

CONSTITUTIONAL BASIS:
  GOVERNANCE.md §6      → constitution/kernel.manifest.yaml = single SoT for tiers
  GOVERNANCE.md §13     → kernel change needs version bump + change record + approver
  manifest §kernel_change_policy → approver in {security-team, architecture-team, maintainer}
  ARCHITECTURE.md §5/§6 → Tier-0 = minimal, zero-dependency
  CONSTITUTION.md §7    → one authoritative source (no divergent duplicates)
  CONSTITUTION.md §8    → agents MUST NOT invent architecture (governed change only)

REPOSITORY BASIS:
  AGENTS.md 1-B declares governance/ canonical (lower authority; self-declared stale)
  kernel.manifest.yaml declares governance_kernel Tier-0 (constitutional SoT)
  kernel_guard.py seals constitution/kernel.lock against protected_files edits

ACTUAL IMPLEMENTATION OWNER (runtime gate):
  mahoun/core/governance/mutation_boundary.MutationAuthorizationBoundary
  backed by singleton _authorized_write_ctx defined ONCE at
  mahoun/core/governance/authorization_state.py:14

DUPLICATE IMPLEMENTATIONS:
  [weak, divergent, PROD-imported]
    mahoun/core/governance_kernel/__init__.py
      classify_query / enforce_governance / GovernanceError
      QueryType{READ,WRITE,DESTRUCTIVE,UNKNOWN}
  [proxy, test-only — delegates to the canonical CypherLexer]
    mahoun/core/governance_kernel/kernel.py
      KernelMutationBoundary.inspect

MUTATION AUTHORIZATION OWNER:
  mahoun/core/governance/mutation_boundary.MutationAuthorizationBoundary
  + singleton _authorized_write_ctx (governance/authorization_state.py:14)

DIRECT BYPASS PATHS (functional gate): 0
  All writes flow through connection.governed_session() → GovernedNeo4jSession
  → _raw_execute() → MutationAuthorizationBoundary.inspect().

DIVERGENT PARALLEL PATHS (reachable, non-gating): 1
  mahoun/graph/graph_query_service.py:61-66 imports the weak __init__ path
  and labels it "canonical" — contradicts AGENTS.md 1-B and the runtime gate.

DOCUMENTATION/REALITY CONTRADICTIONS: 2
  tests/test_authorization_context_canonical.py:29 imports
    governance_kernel.authorization_state — module DOES NOT EXIST → file ERRORS at collection.
  mahoun/core/governance/mutation_boundary.py comment (line 329) says
    ContextVar owned by governance_kernel.authorization_state, but line 338
    imports it from governance.authorization_state.

MANIFEST BOUNDARY VIOLATION (already committed): 1
  manifest §tier_0 forbids governance_kernel importing mahoun.core.governance,
  but governance_kernel/kernel.py:71 imports from governance.authorization_state.

CONFLICT CLASS: C — task intentionally declares a new target architecture
  (governance_kernel Tier-0); an in-flight migration was abandoned mid-way
  (test scaffolded against target state, module never created).

MIGRATION REQUIRED: YES
CONSTITUTIONAL APPROVAL REQUIRED: YES (manifest kernel_change_policy)
RECOMMENDED NEXT ACTION: see Section L / Section 12.
```

---

## A. CONSTITUTIONAL TARGET

Established from constitutional documents (highest authority, per
CONSTITUTION.md §4 and AGENTS.md header):

- **GOVERNANCE.md §6** — `constitution/kernel.manifest.yaml` is the single
  authoritative source of truth for tier classification. "If multiple
  definitions exist: The canonical manifest has authority."
- **kernel.manifest.yaml §tiers.tier_0** — protected_files:
  `mahoun/core/governance_kernel/__init__.py`,
  `mahoun/core/governance_kernel/kernel.py`. Tier-0 allowed_imports: stdlib
  only (contextvars, dataclasses, datetime, enum, hashlib, json, logging, re,
  typing, unicodedata).
- **kernel.manifest.yaml §tiers.tier_0.forbidden_imports** — Tier-0 MUST NOT
  import `mahoun.governance`, `mahoun.core.governance`, `mahoun.infrastructure`,
  `mahoun.api`, etc., nor any external lib (neo4j, pydantic, fastapi, …).
- **ARCHITECTURE.md §5/§6** — Constitutional Kernel = smallest trusted base;
  MUST remain minimal, deterministic, dependency-controlled; MUST NOT depend
  on databases/API/AI providers/enforcement tooling.
- **GOVERNANCE.md §5 (Kernel Protection Principle)** — "The kernel cannot
  depend on the police that protects it." Tier-0 MUST NOT import enforcement
  tools/validators/CI/audit tools.
- **GOVERNANCE.md §10** — Dependency direction: Tier-0 → (read-only) Tier-1
  → Tier-2 → Tier-3. Forbidden: Tier-0 → Tier-1 for execution dependency.
- **CONSTITUTION.md §7** — one authoritative source per concept; duplicate
  definitions forbidden when they can diverge.
- **CONSTITUTION.md §8** — agents are "execution units, not architectural
  authorities"; MUST NOT invent architecture.
- **GOVERNANCE.md §13 + manifest §kernel_change_policy** — changes to the
  kernel require: version bump, change record (id/version/reason/affected
  components/impact analysis), authorization (responsible authority, approval
  identity, approval timestamp), integrity update (fingerprints, attestation,
  validation evidence). Authorized approvers: `security-team`,
  `architecture-team`, `maintainer`. Required approval labels:
  `kernel-change`, `governance-override`.

**Intended target model (per task paragraphs 3 & 6, reconciled with the
manifest dependency rules):**

```
TIER-0  governance_kernel
            authorization primitives
            deterministic classification
            constitutional mutation gate
            (stdlib ONLY; may self-import within governance_kernel)
        ↓ one-way dependency
TIER-1  core/governance
            context (GovernanceContextManager)
            provenance (ProvenanceTracker, ProvenanceMetadata)
            validators (ValidatorPipeline)
            ontology (OntologyEnforcer)
            deterministic resolver
            governed sessions (GovernedNeo4jSession, GovernedWriteTransaction)
            runtime adapters
        ↓
APPLICATION
            services / API / graph consumers
            (consume governance services; MUST NOT bypass the gate)

SEPARATE TOOLING DOMAIN
TIER-1(tooling)  mahoun/governance
            kernel_guard (integrity seal)
            architecture_guard (boundary enforcement)
            api_guard (API drift)
            drift/lineage/quality/dataset governance
            (inspect only; never become architecture — ARCHITECTURE.md §7)
```

The entire `core/governance` package is NOT to be moved into Tier-0. Only the
zero-dependency primitives whose transitive closure is stdlib-only qualify.

---

## B. CURRENT RUNTIME AUTHORITY

The single, actually-running mutation-authorization gate:

- **`mahoun/graph/neo4j/connection.py:204-224`** — `_raw_execute()`:
  ```python
  from mahoun.core.governance.mutation_boundary import MutationAuthorizationBoundary
  MutationAuthorizationBoundary.inspect(query)
  ```
  Called on **every** Cypher query (reads via `execute_query` at line 250;
  writes via `governed_session()` → `GovernedNeo4jSession._execute_authorized`
  at mutation_boundary.py:806-817, which sets the auth token then calls
  `_raw_execute`).
- **`mahoun/core/governance/mutation_boundary.py:350-392`** —
  `MutationAuthorizationBoundary.inspect()`:
  1. `classify_cypher(query)` (line 372) — returns True if mutation intent or
     forbidden procedures.
  2. `_is_authorized()` (line 375) — reads the canonical ContextVar.
  3. Raises `GovernanceViolationError` fail-closed if mutation outside an
     authorized `GovernedNeo4jSession` (lines 379-392).
- **`mahoun/core/governance/mutation_boundary.py:165-247`** — `CypherLexer`
  + `classify_cypher`: NFKC unicode normalization, comment stripping,
  regex tokenization, mutation-keyword detection, forbidden-procedure
  detection (apoc/dbms/plugin/custom). Stdlib-only (`re`, `unicodedata`).
- **`mahoun/core/governance/authorization_state.py:14`** — the singleton
  `_authorized_write_ctx` ContextVar. Defined exactly **once** in the repo
  (grep for `_authorized_write_ctx[:=]ContextVar` returns 1 definition).
  `kernel.py:71` and `mutation_boundary.py:338` both **import** it (no
  duplicate redefinition — the historical 4-impl problem is already resolved).
- **`mahoun/core/governance/mutation_boundary.py:399-498`** —
  `GovernedNeo4jSession`: the ONLY authorized write surface. Its
  `_execute_authorized` sets the token via `_set_authorized(True)`, runs the
  raw executor, resets the token in `finally`.

**Bypass verification** — the `execute_write()` method is explicitly
removed (connection.py:295-319): it raises `GovernanceViolationError`
unconditionally with message "execute_write() is constitutionally
forbidden. Use connection.governed_session()."

**Contract-exemption surface** (AGENTRULES.md §6, coded allowlist, all
documented inline with `GOVERNED EXEMPTION` markers and rationale):
- `api/database.py:92` — startup schema-apply (pre-context DDL).
- `mahoun/graph/neo4j/init_schema.py:54` — operator bootstrap DDL.
- `mahoun/graph/neo4j/connection.py:220` — the chokepoint itself (allowlisted
  by `scripts/validate_governance_compliance.py`).
- `mahoun/graph/neo4j/schema.py` — DDL helpers (only from the bootstrap path).

Result: **0 functional bypasses** of the gate. The runtime authority is
unambiguous and currently lives in `mahoun/core/governance/`.

---

## C. TIER-0 DEPENDENCY CLOSURE

Candidate primitives, with direct/transitive/internal/external import analysis:

### C.1 authorization_state (`governance/authorization_state.py`)
- DIRECT IMPORTS: `contextvars` (ContextVar, Token), `sys`.
- TRANSITIVE IMPORTS: none beyond stdlib.
- EXTERNAL DEPENDENCIES: none.
- INTERNAL DEPENDENCIES: none (not even intra-`governance`).
- TIER-0 COMPATIBILITY: ✅ **YES — pure stdlib.** Strongest migration candidate.

### C.2 QueryType enum variant analysis
Two divergent `QueryType` enums exist:
- `governance_kernel/__init__.py:26` — `READ/WRITE/DESTRUCTIVE/UNKNOWN`.
- `governance_kernel/kernel.py:29` — `READ/WRITE/DDL/FORBIDDEN`.
- Neither imports non-stdlib (`enum`, `str` base only).
- TIER-0 COMPATIBILITY: ✅ both are stdlib-only by themselves — BUT they are
  semantically divergent (contract drift — see Section G). Promoting either
  requires a behavioral decision, not merely a file move.

### C.3 GovernanceViolation / GovernanceViolationError
Definitions exist in TWO places:
- `governance_kernel/kernel.py:50-63` — dataclass `GovernanceViolation` +
  `GovernanceViolationError`, stdlib-only (`dataclasses`, `enum`, `datetime`).
- `governance/violations.py` — the other canonical definition (imported by
  `mutation_boundary.py:49`, `governance_context.py:39`, etc.).
- TIER-0 COMPATIBILITY: ⚠️ depends on whether `governance/violations.py`
  pulls non-stdlib deps. **Must read `violations.py` before promoting.**
  (Not yet read in this proof phase — flagged UNSAFE/UNPROVEN, Section E.)

### C.4 CypherLexer + classify_cypher (`governance/mutation_boundary.py:165-247`)
- DIRECT IMPORTS (of just the lexer): `re`, `unicodedata`.
- TRANSITIVE IMPORTS: none (self-contained static class with `@staticmethod`/`@classmethod`).
- EXTERNAL DEPENDENCIES: none.
- INTERNAL DEPENDENCIES: none at the lexer level.
- TIER-0 COMPATIBILITY: ✅ **YES — the lexer itself is stdlib-only.** Promotable
  IF extracted from `mutation_boundary.py` (which as a whole file is Tier-1,
  see C.5) into a standalone stdlib module.

### C.5 MutationAuthorizationBoundary (full `mutation_boundary.py`)
- DIRECT IMPORTS: `hashlib`, `json`, `logging`, `re`, `contextvars`,
  `unicodedata`, `contextlib`, `dataclasses`, `datetime`, `enum`, `typing`
  (all stdlib), PLUS:
  - `governance.validator_pipeline` (ValidatorPipeline, PipelineResult) — line 46
  - `governance.provenance_tracker` (ProvenanceMetadata) — line 47
  - `governance.governance_context` (GovernanceContextManager) — line 48
  - `governance.violations` — line 49
- TRANSITIVE: ValidatorPipeline → ontology_enforcer, provenance_tracker,
  deterministic_resolver, protocols, fortress_validator (heavy, non-stdlib).
  GovernanceContextManager → fortress_validator, protocols,
  deterministic_resolver, ontology_enforcer, provenance_tracker (heavy).
- TIER-0 COMPATIBILITY: ❌ **NO as a whole file.** The *class*
  `MutationAuthorizationBoundary` (inspect only) is stdlib-compatible, but
  the *file* it lives in transitively depends on Tier-1 governance services.
  **Must be decomposed** (extract the gate into a stdlib-only kernel module;
  leave `GovernedNeo4jSession` + receipts + transactions in Tier-1).

### C.6 KernelMutationBoundary (`governance_kernel/kernel.py:78-117`)
- DIRECT IMPORTS: imports `_authorized_write_ctx`/`is_authorized`/etc. from
  `governance.authorization_state` (line 71) — currently a **Tier-0→Tier-1
  violation** of the manifest (forbidden_imports: `mahoun.core.governance`).
  Lazily imports `CypherLexer` from `governance.mutation_boundary` (line 85).
- TIER-0 COMPATIBILITY: ❌ **NO in current form** — its imports cross the
  manifest boundary. After authorization_state moves into governance_kernel
  (C.1) and the lexer is extracted into a stdlib kernel module (C.4), this
  class could become a true Tier-0 stdlib proxy. **Requires decomposition.**

---

## D. SAFE TIER-0 PRIMITIVES

Proven stdlib-only (no transitive non-stdlib, no manifest-forbidden imports):

1. **`authorization_state`** — the singleton ContextVar + set/reset/is +
   `authorize_write` cm + `_assert_no_duplicate_contextvar` guard.
   Stdlib: `contextvars`, `sys`. ✅
2. **`CypherLexer` + `classify_cypher`** (the classification primitive only,
   NOT the surrounding `MutationAuthorizationBoundary` machinery).
   Stdlib: `re`, `unicodedata`. ✅ (after extraction from the Tier-1 file)

These two are the minimal, provably Tier-0-compatible primitives. Moving them
establishes a constitutional kernel authority with a valid dependency boundary.

---

## E. UNSAFE / UNPROVEN TIER-0 PRIMITIVES

Cannot be promoted to Tier-0 without further proof or decomposition:

1. **`MutationAuthorizationBoundary` (whole)** — file transitively depends on
   Tier-1 governance (ValidatorPipeline, GovernanceContextManager, etc.).
   Must be decomposed: extract `inspect()` + `classify_cypher` to a stdlib
   kernel module; keep `GovernedNeo4jSession`/receipts/transactions in Tier-1.
2. **`KernelMutationBoundary` (current form)** — imports across the manifest
   boundary today (kernel.py:71 → governance.authorization_state; kernel.py:85
   → governance.mutation_boundary.CypherLexer). Becomes Tier-0-safe only AFTER
   the decomposition in #1 and the authorization_state move in Section F.
3. **`GovernanceViolation` / `GovernanceViolationError`** — two definitions
   exist (governance_kernel/kernel.py:50 and governance/violations.py);
   `governance/violations.py` not yet read in this phase → must verify it is
   stdlib-only before promoting, and must reconcile the duplication.

---

## F. authorization_state MIGRATION SAFETY

The strongest, lowest-risk migration candidate. Evidence:

- The singleton ContextVar is defined exactly **once** (grep confirmed only
  `governance/authorization_state.py:14` contains
  `_authorized_write_ctx: ContextVar[bool] = ContextVar(...)`).
- `governance_kernel/kernel.py:71` already imports the canonical symbols
  (`_authorized_write_ctx`, `is_authorized`, `set_authorized`,
  `reset_authorized`) — it has *no local redefinition*.
- `governance/mutation_boundary.py:338` imports the same set — also no
  redefinition.
- An in-flight migration *already asserts* the intended end-state:
  `tests/test_authorization_context_canonical.py:29` imports
  `mahoun.core.governance_kernel.authorization_state` — a module that
  **does not yet exist**, so the file ERRORS at collection today. Its
  docstring (lines 13-16) frames the move as finishing "Issue 3 of the
  remediation pass (consolidating the four authorization-boundary
  implementations down to ONE canonical ContextVar)."

Migration invariant to preserve (guidance §5):
```python
governance.authorization_state._authorized_write_ctx
    is
governance_kernel.authorization_state._authorized_write_ctx
```
i.e. **one object, one identity**, after the move.

Post-move identity proof target (the canonical state must satisfy these
identities simultaneously):
```python
governance_kernel.authorization_state._authorized_write_ctx      # DEFINITION (Tier-0)
governance.authorization_state._authorized_write_ctx             # RE-EXPORT → same object
governance_kernel.kernel._authorized_write_ctx                    # import → same object
governance.mutation_boundary._authorized_write_ctx                # import → same object
# all `is`-identical; id() equal; contextvars pass-through identical
```

A re-export (`from mahoun.core.governance_kernel.authorization_state import *`
in `governance/authorization_state.py`) is acceptable ONLY as a compatibility
mechanism preserving "one definition, one object, one authority." It MUST NOT
redefine `ContextVar`.

Existing guard that locks this invariant:
`governance/authorization_state.py:27-35` `_assert_no_duplicate_contextvar()`
scans `sys.modules` and raises `RuntimeError("DUPLICATE _authorized_write_ctx
...")` if any other module exposes a different `_authorized_write_ctx` object.
Tests `tests/test_authorization_context_canonical.py:39-72` and
`tests/test_authorization_state_singleton.py` exercise the guard. **After
migration, this guard must move too** (or remain in governance_kernel) and
still fire.

**Risk rating: LOW.** Symbol surface is small (1 ContextVar + 4 functions +
1 cm + 1 guard). Importers are enumerable (see Section G/H consumer maps).
The migration is essentially finishing a scaffolded-and-abandoned move.

---

## G. governance_kernel API CONTRACT MATRIX

Every symbol exported from `governance_kernel/__init__.py` and `kernel.py`,
with consumers and semantics. **No API removal until this matrix is complete.**

| API | Definition | Divergence | Runtime callers | Test-only callers | Semantics | Replacement target |
|---|---|---|---|---|---|---|
| `QueryType` (init) READ/WRITE/DESTRUCTIVE/UNKNOWN | `governance_kernel/__init__.py:26` | vs kernel.py `READ/WRITE/DDL/FORBIDDEN` — **contract drift** | `graph_query_service.py:62,428,507` (DESTRUCTIVE/UNKNOWN used) | many tests (test_governance_kernel, test_unified_governance_*, stress/*) | naive substr classifier; UNKNOWN→treated as WRITE | kernel.py `QueryType{READ,WRITE,DDL,FORBIDDEN}` (behavioral change!) |
| `classify_query` (init) | `__init__.py:34` | substr approach, no unicode norm, no comment strip, diverges from `CypherLexer` | `graph_query_service.py:64,75,421,500` | test_governance_kernel, test_kernel_ownership, stress | returns init QueryType | kernel.py `KernelMutationBoundary.classify_query` (delegates to CypherLexer) |
| `enforce_governance` (init) | `__init__.py:81` | requires correlation_id/actor_id; distinct from `inspect()` | `graph_query_service.py:65,92,425,504` | test_governance_kernel, test_unified_governance_controller | raises `GovernanceError` (NOT `GovernanceViolationError`) | no direct equivalence — **behavioral migration** |
| `GovernanceError` (init) | `__init__.py:72` | distinct exception type from `GovernanceViolationError` | `graph_query_service.py:63,426,505` (caught) | tests | user-facing exception | `GovernanceViolationError` (different hierarchy) |
| `QueryType` (kernel) READ/WRITE/DDL/FORBIDDEN | `kernel.py:29` | matches runtime gate intent | (not runtime-gating; TYPE_CHECKING in unified_governance.py:42) | tests/stress, test_kernel_ownership, test_failure_modes, governance_server | strong enum | canonical Tier-0 enum |
| `KernelMutationBoundary.inspect` | `kernel.py:99` | proxies `CypherLexer.analyze_intent` (governance) | NOT called as runtime gate | tests/stress, test_kernel_ownership, test_failure_modes, test_unified_governance_p0_critical | raises `GovernanceViolationError` | keep as Tier-0 proxy once lexer extracted |
| `KernelMutationBoundary.classify_query` | `kernel.py:82` | delegates to CypherLexer (governance) | not runtime | tests | returns kernel QueryType | canonical |
| `GovernanceKernel` (service) | `kernel.py:139` | HTTP validation service | `tests/governance_kernel_main.py:67` | governance_server, governance_kernel_main | containerized validator | keep (Tier-0 service) |
| `is_governance_authorized`/`set_governance_authority`/`reset_governance_authority` | `kernel.py:123-131` | delegate to authorization_state | `unified_governance.py:334` | tests | auth token accessors | canonical (re-route to governance_kernel.authorization_state after F) |
| `_authorized_write_ctx` (imported) | `kernel.py:71` | re-import of singleton | identity tests | test_authorization_context_canonical, test_authorization_state_singleton | canonical ContextVar | move ownership to governance_kernel (Section F) |
| `GovernanceViolation`/`GovernanceViolationError`/`ViolationCategory`/`ViolationSeverity` (kernel) | `kernel.py:35-63` | duplicate of `governance/violations.py` | (used in tests/stress for kernel) | stress tests | violation records | reconcile with governance/violations (Section E) |

**Consumer count (from grep over project minus `.test_classification_backup/`):**
- `governance_kernel/__init__` runtime consumers: **1** (`graph_query_service.py:61`).
- `governance_kernel/kernel` runtime consumers: **2** (`unified_governance.py:41,268,334`,
  `infrastructure/interfaces/governance_server.py:30`; plus tooling
  `scripts/runtime_trace.py:63`, `scripts/validate_governance_compliance.py:178`).
- Test consumers: ~30+ files across `tests/stress/`, `tests/governance/`,
  `tests/test_governance_kernel.py`, `tests/test_authorization_state_*.py`,
  `tests/test_authorization_context_canonical.py`.

---

## H. graph_query_service RUNTIME IMPACT

`mahoun/graph/graph_query_service.py` is the **only production runtime**
consumer of the weak parallel path. Analysis:

- Imports (`graph_query_service.py:61-66`):
  ```python
  from mahoun.core.governance_kernel import (
      QueryType, GovernanceError,
      classify_query as _kernel_classify_query,
      enforce_governance as _kernel_enforce_governance,
  )
  ```
  Local wrappers `classify_query`/`enforce_governance` (lines 69-92) re-export
  them "required by P0.2 static proof tests."
- Use sites:
  - `:421` `query_type = classify_query(query)` (in a query path)
  - `:425` `enforce_governance(query_type, correlation_id, actor_id, allow_destructive)`
  - `:426` `except GovernanceError` → `:428` checks
    `query_type in (WRITE, DESTRUCTIVE, UNKNOWN)`
  - Same pattern at `:500-507`.
- Behavioral semantics:
  - `DESTRUCTIVE` = `DETACH DELETE` / `DELETE ALL` / `DROP` / `DELETE` w/o WHERE.
  - `UNKNOWN` → treated as WRITE (fail-safe).
  - `enforce_governance` REQUIRES `correlation_id` + `actor_id` for
    WRITE/DESTRUCTIVE and `allow_destructive=True` for DESTRUCTIVE; raises
    `GovernanceError` (a generic `Exception`, NOT `GovernanceViolationError`).
- Divergence from the runtime gate:
  - The kernel.py `QueryType` has NO `DESTRUCTIVE`/`UNKNOWN` — it has
    `DDL`/`FORBIDDEN`. Replacing `DESTRUCTIVE`→`DDL` and `UNKNOWN`→`FORBIDDEN`
    is a **behavioral rename** that changes the handling branches in
    `graph_query_service.py:428,507`.
  - `enforce_governance` is NOT equivalent to `MutationAuthorizationBoundary.inspect`:
    different exception type, different required arguments, different return.
- Bypass status: `graph_query_service.py` uses this for its OWN classification
  layer (e.g., `:print(query)` paths) — it does NOT call
  `connection.execute_query` in the gated path shown; whether its
  mutations reach the DB through `connection` (and thus already pass the
  real gate) or through a separate path is **not yet proven** from the read
  so far. **Must trace whether `graph_query_service` mutating methods reach
  `_raw_execute`** before any behavioral normalization.

**Risk:** Replacing `classify_query`/`enforce_governance`/`GovernanceError`/
`QueryType{DESTRUCTIVE,UNKNOWN}` with the kernel.py/canonical variants is a
**behavioral migration**, not a pure rename. It MUST be tested explicitly:
same input queries must produce equivalent allow/deny decisions, and the
changed branches in `graph_query_service.py:428,507` must be exercised.

Per guidance §10: do NOT silently normalize divergent semantics to obtain
namespace purity.

---

## I. KERNEL CHANGE AUTHORIZATION STATUS

Manifest `§kernel_change_policy` requires, for ANY edit to protected files
(`governance_kernel/__init__.py`, `governance_kernel/kernel.py`):
- `require_version_bump: true`
- `require_approval_label`: `kernel-change` / `governance-override`
- `require_audit_record: true`
- `require_authorization: true`
- `authorized_approvers`: `security-team`, `architecture-team`, `maintainer`
- change record path: `constitution/kernel_changes.yaml`

Current `kernel_changes.yaml` records only the initial v1.0.0 entry
(approved_by: `architecture-team`, authorization_hash: `initial_hash_placeholder`).

**Authorization prerequisite for this migration:** a new change record
(version bump, e.g. 1.1.0) authored by an approver in the authorized set,
with rationale, affected components, and impact analysis. A conversational
task instruction does NOT satisfy this — the approver identity is a
repository-defined role, not the user issuing the task.

**Status: NOT YET SATISFIED.** No formal approver identity has been
recorded for a kernel version bump. Re-sealing the kernel lock without a
valid change record would fail `kernel_guard --verify`.

---

## J. PROTECTED FILE / SEAL IMPACT

CI wiring verified (grep across `ci/`, `*.sh`, `*.yml`, `*.yaml`, `Makefile`):
- `Makefile` references kernel integrity.
- `.github/workflows/kernel-governance.yml` is the CI workflow touching
  governance/constitutional/CI/enforcement files.
- `kernel_guard --verify` (via `mahoun/governance/kernel_guard.py`) reads
  `constitution/kernel.lock` and compares SHA256 of each protected file
  against the locked hashes. A mismatch → `sys.exit(1)`.
- `gate_10_constitutional_integrity.sh` (lines 41-54) verified: it hashes
  **only `mahoun/constitutional/*.md`** files into the manifest and compares
  against `ci/first_step/.constitutional_manifest.sha256` + `.seal`. It does
  **NOT** verify `kernel.lock`. So gate_10 does not block Tier-0 code edits,
  but `kernel_guard` does (separately).
- Re-seal command: `python -m mahoun.governance.kernel_guard --update`
  (requires explicit authorization / an existing change record per
  `update_lock()` docstring at kernel_guard.py:149-159).
- Authorization command: `python -m mahoun.governance.kernel_guard
  --authorize-change --version 1.1.0 --reason "..." --approved-by
  "security-team"`.

Protected-file edits this migration would require (NOT yet performed):
1. `governance_kernel/kernel.py` — change line-71 import source (governance →
   governance_kernel) to fix the manifest boundary violation. PROTECTED.
2. `governance_kernel/__init__.py` — remove/replace the weak parallel path
   (classify_query/enforce_governance/GovernanceError/divergent QueryType)
   with re-exports of the canonical kernel primitives. PROTECTED.
Non-protected (but in-kernel) new files:
3. `governance_kernel/authorization_state.py` — NEW module (the ContextVar
   definition moves here). Not in protected_files, but is kernel-internal.

Because the CURRENT committed state already violates the manifest
(kernel.py:71 imports `mahoun.core.governance`), the migration is partly a
*correction of an existing violation* — but the re-seal still requires a
change record per policy.

---

## K. MINIMUM SAFE MIGRATION SCOPE

The smallest migration that achieves "exactly one constitutional
mutation-authorization authority, with a provably valid Tier-0 dependency
boundary," WITHOUT broad refactoring or behavioral change:

**Phase 1 — Establish Tier-0 authority + fix the active boundary violation
(HIGH confidence, LOW risk):**
1. Create `mahoun/core/governance_kernel/authorization_state.py` moving the
   singleton ContextVar + `is_authorized/set_authorized/reset_authorized/
   authorize_write/_assert_no_duplicate_contextvar` (verbatim, stdlib-only).
2. Convert `governance/authorization_state.py` into a re-export shim
   (`from mahoun.core.governance_kernel.authorization_state import *`) —
   ONE object identity preserved (Section F invariant).
3. In `governance_kernel/kernel.py:71`, change the import to
   `from mahoun.core.governance_kernel.authorization_state import ...`
   → FIXES the manifest boundary violation (intra-kernel import allowed).
4. In `governance/mutation_boundary.py:338`, change the import to
   `from mahoun.core.governance_kernel.authorization_state import ...`
   → resolves the comment/code contradiction (lines 329 vs 338).
5. Fix the ERRORS-at-collection test
   `tests/test_authorization_context_canonical.py` (it already expects the
   post-migration target state).
6. Add a governance-consistency test: `id()`/`is` identity of the ContextVar
   across all four access paths + the duplicate-guard roundtrip (extending
   the existing `test_authorization_context_canonical.py` assertions).

**Phase 2 — Extract the classification primitive into Tier-0 (MEDIUM
confidence, requires decomposition, Section C.4/C.5/C.6):**
7. Move `CypherLexer` + `classify_cypher` into a stdlib-only
   `governance_kernel/` module (e.g. `kernel.py` or a new `classification.py`).
8. Make `KernelMutationBoundary.inspect` import the lexer from Tier-0
   (currently kernel.py:85 lazily imports from governance.mutation_boundary).
9. Make `governance/mutation_boundary.py` import `CypherLexer`/`classify_cypher`
   from the kernel → Tier-0 becomes the authority for classification too.

**Phase 3 — Remove the divergent parallel path (BEHAVIORAL, HIGH risk,
requires Section H proof FIRST):**
10. Once `graph_query_service.py` runtime impact is fully traced and
    behavioral tests exist, replace the weak `classify_query`/
    `enforce_governance`/`GovernanceError`/`QueryType{DESTRUCTIVE,UNKNOWN}`
    surface in `governance_kernel/__init__.py` with re-exports of the
    canonical kernel primitives, OR migrate `graph_query_service.py` to use
    the canonical primitives directly.
11. Reconcile the duplicate `GovernanceViolation` definitions
    (`governance_kernel/kernel.py:50` vs `governance/violations.py`).

**Phase 4 — Re-seal + change record (authorization-gated):**
12. Author change record in `constitution/kernel_changes.yaml` (version bump
    to 1.1.0), authorized by `security-team`/`architecture-team`/`maintainer`.
13. Re-seal: `python -m mahoun.governance.kernel_guard --update`.
14. Run `kernel_guard --verify` and the full governance gate suite.

Phases 2–4 are deferred until Phase 1 is green and the relevant proofs
(Sections E, H, I) are closed. Phase 1 touches protected files (#3, #4 in
Section J), so it STILL requires the kernel change authorization (Section I)
before execution.

---

## L. BLOCKERS

1. **FORMAL KERNEL AUTHORIZATION (BLOCKING — Section I).** Phase 1 steps 3 & 4
   edit protected files (`governance_kernel/kernel.py`, and the new
   `governance_kernel/authorization_state.py` is kernel-internal). The
   manifest's `kernel_change_policy` requires a version bump + change record
   authored by an approver in {security-team, architecture-team, maintainer}.
   A conversational task does not constitute this authorization. No
   `approved_by` may be fabricated.

2. **ARCHITECTURAL PROOF (BLOCKING for Phase 2/3 — Section E).** `governance/
   violations.py` has not been read; the `GovernanceViolation` duplication
   between `governance_kernel/kernel.py:50` and `governance/violations.py` is
   unresolved. Promoting violation types to Tier-0 requires confirming they
   are stdlib-only and reconciling the two definitions.

3. **BEHAVIORAL PROOF (BLOCKING for Phase 3 — Section H).** Replacing
   `graph_query_service.py`'s `DESTRUCTIVE`/`UNKNOWN`/`enforce_governance`/
   `GovernanceError` surface with kernel.py's `DDL`/`FORBIDDEN`/`inspect`/
   `GovernanceViolationError` is a behavioral migration. Must first prove:
   (a) whether `graph_query_service` mutating methods reach `_raw_execute`
   (and thus already pass the real gate), and
   (b) that equivalent queries produce equivalent allow/deny decisions under
   the new symbols, with the changed branches at
   `graph_query_service.py:428,507` explicitly tested.

4. **DUPLICATE CONTEXTVAR GUARD LOCATION (BLOCKING for Phase 1 finalization).**
   `_assert_no_duplicate_contextvar()` lives in `governance/authorization_state.py:27`.
   After moving the definition to `governance_kernel/authorization_state.py`,
   the guard must move too and remain invoked by a test that runs in default
   CI (a guard that is never called is not a guard — AGENTS.md 1-B).

---

## 12. DECISION

Per the decision rule, the next action is exactly one of:
`READY_FOR_MINIMAL_MIGRATION` / `BLOCKED_ON_FORMAL_AUTHORIZATION` /
`BLOCKED_ON_ARCHITECTURAL_PROOF`.

**DECISION: BLOCKED_ON_FORMAL_AUTHORIZATION**

Phase 1 is architecturally proven safe (Sections D, F) and would establish
the single constitutional mutation-authorization authority at a valid Tier-0
dependency boundary. However, Phase 1 step 3 (`governance_kernel/kernel.py`)
and the new kernel-internal module are protected/protected-surface edits
governed by `kernel.manifest.yaml §kernel_change_policy`, which requires a
change record authored by an approver in the authorized set
({security-team, architecture-team, maintainer}).

That formal authorization is NOT present. It cannot be inferred from the
task, and no approver identity may be fabricated.

**Required to unblock (exact authorization prerequisite):**

```
1. An authorized approver (security-team | architecture-team | maintainer)
   approves a kernel version bump to 1.1.0 for the consolidation migration.

2. A change record is created in constitution/kernel_changes.yaml:
     version: "1.1.0"
     reason: "Consolidate governance authorization primitives into the
              constitutional Tier-0 kernel; fix manifest boundary violation
              (governance_kernel/kernel.py -> governance import); remove the
              divergent parallel classification path."
     files_changed: governance_kernel/__init__.py,
                    governance_kernel/kernel.py,
                    governance_kernel/authorization_state.py (new),
                    governance/authorization_state.py (re-export),
                    governance/mutation_boundary.py (import source)
     approved_by: <security-team | architecture-team | maintainer>
     impact_analysis: see Sections C, F, G, H of glmreport.md

   Via: python -m mahoun.governance.kernel_guard --authorize-change \
            --version 1.1.0 --reason "..." --approved-by "<approver>"

3. After Phase 1 code changes, re-seal:
     python -m mahoun.governance.kernel_guard --update
   then verify:
     python -m mahoun.governance.kernel_guard --verify
```

Until an authorized approver is recorded, no Tier-0 protected file is
modified and the kernel lock is not re-sealed. All subsequent phases (2–4)
are additionally blocked on Sections E (architectural proof) and H
(behavioral proof) regardless.

---

## Appendix — Evidence Index (file:line)

- Runtime gate: `mahoun/graph/neo4j/connection.py:204-224, 252-293, 295-319`
- Canonical boundary: `mahoun/core/governance/mutation_boundary.py:165-247, 236-321, 350-392, 399-498, 806-817`
- Singleton ContextVar (1 def): `mahoun/core/governance/authorization_state.py:14`
- Duplicate-guard: `mahoun/core/governance/authorization_state.py:27-35`
- Kernel Tier-0 (protected): `mahoun/core/governance_kernel/kernel.py:71, 78-117`
- Weak parallel path: `mahoun/core/governance_kernel/__init__.py:26, 34, 72, 81`
- Production importer of weak path: `mahoun/graph/graph_query_service.py:61-66, 421-428, 500-507`
- Singular-ContextVar-regression tests: `tests/test_authorization_context_canonical.py:24-95`
- In-flight/abandoned migration marker: `tests/test_authorization_context_canonical.py:29, 77, 41-42`
- Manifest: `constitution/kernel.manifest.yaml` (§tier_0, §kernel_change_policy, §critical_modules)
- Change record: `constitution/kernel_changes.yaml:20-37`
- Integrity seal tooling: `mahoun/governance/kernel_guard.py:182-253, 311-346`
- CI wiring: `.github/workflows/kernel-governance.yml`, `Makefile`
- Constitutional authority: `mahoun/constitutional/constitution/CONSTITUTION.md §4, §7, §8, §10`; `GOVERNANCE.md §6, §5, §10, §13`; `ARCHITECTURE.md §5-§7, §18`

No files were modified to produce this report. All citations are
reproducible from the working tree at audit time.
