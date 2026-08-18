# GROKREPORT — MAHOUN RUNTIME THREAT SURFACE RECONNAISSANCE
**Date:** 2026-05-25  
**Auditor:** Kilo (Forensic Mode — STRICT / NON-DESTRUCTIVE)  
**Mission:** Full runtime reachability and execution-surface audit for governance-grade legal/graph platform.

---

## FINAL ANSWER TO MISSION QUESTION

**“Does ANY uncontrolled or governance-unaware execution path remain reachable?”**

**YES** — Multiple critical governance bypass vectors for graph mutation remain runtime-reachable.

See detailed findings below.

---

# 1. THREAT SURFACE REPORT

## Executive Summary
The canonical graph mutation path is: `Neo4jConnection.governed_session()` → `GovernedNeo4jSession` (with `MutationAuthorizationBoundary.inspect()` on every query in `_raw_execute`).

Multiple non-canonical mutation surfaces were identified and are runtime-reachable under certain conditions (test seeding, GNN pipelines, alternative query services, startup schema init).

Docker build context leaks archived and worktree code into images.

## Key Findings by Risk

### CRITICAL / GOVERNANCE_BYPASS
- `tests/fixtures/seed_data.py`: Direct `GraphDatabase.driver` + `session.run(CREATE, DETACH DELETE)` for test seeding. Invoked by docker-compose and `__main__`. Reachable in test/CI environments.
- `mahoun/graph/gnn/gnn_graph_builder.py`: Direct driver + `DETACH DELETE` + `CREATE` in `save_to_neo4j()`. Part of GNN training pipeline.
- `mahoun/graph/graph_query_service.py`: Own driver + direct `session.run`/`tx.run` with only partial dangerous keyword filtering. Registered via switchboard. Can execute mutations if called with write Cypher.
- `api/database.py`: Async driver used during init for schema Cypher execution (CREATE CONSTRAINT etc. from external .cypher files).

### EXECUTION_RISK / SECURITY_RISK
- `mahoun/graph/ingestion/document_classifier.py`: Multiple `exec()` for dynamic numpy import and code blocks.
- Root `/archive` and `.kilo/worktrees` not fully excluded from Docker context (partial `.dockerignore`).
- Multiple modules create independent Neo4j drivers (kg_adapters, health checks, integrity_probe) — duplication of connection logic, potential for future bypass.

### LEGACY / QUARANTINE_CANDIDATE
- All code under `/archive/`, `mahoun/*/archive/`, `.kilo/worktrees/*/` (full project clones). No static imports from production, but present in build context and local FS.
- Old `ultra_*` and `domain_modules_staging` copies.

### LOW_RISK (with caveats)
- Scripts using subprocess for git/backup/CI (expected admin tooling).
- `sys.path.insert` in tests/ and scripts/ (local dev only).
- `.env` files present locally but excluded from Docker.

## Uncontrolled Execution Paths Remaining
**YES.** Graph mutations can still execute outside the governed runtime via:
1. Test seeding path (docker + direct python)
2. GNN training pipelines
3. GraphQueryService (if used for writes)
4. Startup schema application in `api/database.py`
5. Any future direct driver usage in unreviewed pipelines

## Containment Recommendations (not applied)
- Quarantine: Move `seed_data.py` and gnn_graph_builder mutation logic behind `governed_session`.
- Governance-refactor: Deprecate `GraphQueryService` direct driver; route all through canonical connection.
- dockerignore + .gitignore hardening: Explicitly exclude root `archive/`, `.kilo/`, all worktrees from build context.
- CI gate enhancement: Add runtime import scan that fails on any import or driver creation outside `mahoun/graph/neo4j/connection.py` and `mahoun/core/governance/`.
- Runtime blocking: Consider import hook or monkey-patch at startup to detect and block raw neo4j driver creation after governance init.

## Final Answer to Mission Question
**YES** — multiple vectors for graph mutation and code execution outside the intended governance layer are still reachable in test, training, and partial startup paths, plus code leakage via Docker.

Evidence preserved in this report and `SUSPICIOUS_PATHS.json`.

---

# 2. RUNTIME REACHABILITY REPORT

## Canonical Mutation Path (Single Source of Truth)
- File: `mahoun/graph/neo4j/connection.py`
- Entry: `get_connection().governed_session(correlation_id, actor_id)`
- Enforcement: `MutationAuthorizationBoundary.inspect(query)` called on EVERY Cypher in `_raw_execute()`
- Authorization token: `contextvars.ContextVar _authorized_write_ctx`
- Only surface allowed to set the token: `GovernedNeo4jSession` (`mahoun/core/governance/mutation_boundary.py`)
- All writes must also have active `GovernanceContext` (fail-closed)

## Non-Canonical Reachable Mutation Paths (Classified)

1. **tests/fixtures/seed_data.py**
   - Reachability: Direct (python -m or docker-compose test seeding)
   - Execution: Yes (full driver lifecycle + mutations)
   - Mutation: `CREATE LegalRule/TestData`, `DETACH DELETE`
   - Classification: **CRITICAL / GOVERNANCE_BYPASS**
   - Why: Runs in CI/test environments that may share images or configs with prod-like setups. No provenance, no audit, no governance context.
   - Containment: Quarantine test seeding behind a governed test helper; never run in prod profiles.

2. **mahoun/graph/gnn/gnn_graph_builder.py:save_to_neo4j**
   - Reachability: Via GNN training pipelines (`mahoun/graph/gnn/`)
   - Execution: Yes (own driver)
   - Mutation: `DETACH DELETE` entire DB + `CREATE` nodes/rels
   - Classification: **CRITICAL / GOVERNANCE_BYPASS**
   - Why: Training jobs can be triggered from scripts or notebooks against shared DB.
   - Containment: Refactor to accept a governed session or use `connection.governed_session` internally.

3. **mahoun/graph/graph_query_service.py**
   - Reachability: Imported via switchboard, ultra systems, some RAG/hybrid paths
   - Execution: Yes (own driver + `execute_query` that does raw `session.run`)
   - Mutation: Allowed for most Cypher except crude "DROP/DELETE ALL/DETACH DELETE without WHERE"
   - Classification: **GOVERNANCE_BYPASS / EXECUTION_RISK**
   - Why: Duplicate driver surface; partial validation only.
   - Containment: Deprecate raw driver; make it a read-only facade or force it to delegate writes to canonical governed path.

4. **api/database.py:init_neo4j (schema application)**
   - Reachability: On FastAPI startup when `ENABLE_NEO4J=true`
   - Execution: Async driver, runs arbitrary .cypher from switchboard schema paths
   - Mutation: `CREATE CONSTRAINT`, `INDEX`, potentially other DDL
   - Classification: **EXECUTION_RISK** (schema layer)
   - Why: Schema files could be tampered or contain mutations; bypasses boundary.
   - Containment: Move schema application through a governed DDL helper or whitelist only.

5. Other driver creations (reads mostly)
   - `mahoun/reasoning/kg_adapters.py`, `mahoun/infrastructure/health/*`, `integrity_probe.py`
   - Classification: **LOW_RISK** for mutation (no writes found), but architectural duplication.

## Archived / Hidden / Worktree Reachability
- `/archive/`, `mahoun/*/archive/`, `.kilo/worktrees/*` : No static imports from production .py files.
- Dynamic loading: None targeting these paths.
- Docker context: Not fully excluded (`.dockerignore` misses root `archive/` and `.kilo`). Code can ship in images.
- Runtime activation: Only if `PYTHONPATH` or `cwd` manipulation points into them (not in standard launchers).
- Classification: **LEGACY / QUARANTINE_CANDIDATE** for code; **EXECUTION_RISK** due to image bloat and potential future accidental import.

## Subprocess / Dynamic Exec / Importlib
- Subprocess: Limited to admin scripts (git, backup, CI gates). No direct graph mutation via shell.
- `eval/exec`: Mostly `model.eval()`; one risky file (`document_classifier.py`) uses `exec` for imports and code blocks. Classification: **SECURITY_RISK**.
- importlib: Used for guardrails and switchboard ultra/base switching. All target current `mahoun.*` — SAFE.
- sys.path: Many in tests/scripts for local dev. One in hardened_paddle_ocr for libs (LOW_RISK).

## Launchers / CI / Entrypoints
- `.github/workflows/*` : Strong governance gates, reference `ci/scripts/` and `tests/governance/`. No archive references. SAFE.
- docker-compose: Mounts only data dirs; no archive/worktree mounts. Good.
- Scripts in `scripts/` and `first_step_ci_cd/`: Many are governance/audit tools themselves. Some (restore, backup) operate on data only.
- No evidence of launchers pointing to archived code for execution.

## Conclusion on Reachability
Uncontrolled paths for **graph mutation** remain reachable in:
- Test/CI seeding
- GNN pipelines
- Alternative query services
- Startup schema

Archived code is not actively imported but leaks into Docker images and local FS.

No evidence of hidden AI-tool generated executable pipelines or reflection-based loading of legacy code in current runtime.

---

# 3. EXECUTION CHAIN REPORT

## Primary Runtime Entry Points
1. FastAPI (`api/main.py`) → uvicorn
2. Docker compose services (backend, neo4j, etc.)
3. Scripts in `scripts/` (ingest, phase execution, backup/restore, CI gates)
4. Tests (pytest, direct python -m)
5. Notebooks / demos (local only)

## Graph Mutation Execution Chains

### Canonical Chain (Enforced)
Request/Job → `GovernanceContextManager.active_context()` → `connection.governed_session()` → `GovernedNeo4jSession.write_*()` → `_execute_authorized` (sets contextvar) → `_raw_execute` → `MutationAuthorizationBoundary.inspect()` (passes) → driver `session.run`

### Bypass Chain 1: Test Seeding
`docker-compose` (test profile) or `python -m tests.fixtures.seed_data` → `seed_test_knowledge_graph()` → `GraphDatabase.driver()` → `session.run(CREATE / DETACH DELETE)` → NO governance context, NO boundary, NO provenance, NO audit

### Bypass Chain 2: GNN Pipeline
Training script / notebook → `GNNGraphBuilder.build_graph()` → `save_to_neo4j()` → own `GraphDatabase.driver` → `session.run(DETACH DELETE + CREATE)` → direct mutation, no governance

### Bypass Chain 3: GraphQueryService
Any code importing `mahoun.graph.graph_query_service` → `GraphQueryService(config)` → `execute_query(arbitrary Cypher)` → own `driver.session().run()` → limited keyword filter only

### Bypass Chain 4: Startup Schema
uvicorn → FastAPI lifespan → `api.database.init_neo4j()` → `AsyncGraphDatabase.driver` → `session.run(arbitrary statements from .cypher files)`

### Hidden / Indirect Chains
- Subprocess in `scripts/execute_phase.py`, `restore.py` etc. call git, docker, but do not directly mutate graph via shell (they call governed paths or dumps).
- No evidence of cron, Celery, or background workers with separate mutation paths.
- No pickle/dill deserialization of executable graph mutation code found.

## Dynamic Loading Chains
- `switchboard.py` + `importlib.import_module` for ultra/base switching (current modules only)
- `hardened_import.py` for guardrails (fail-fast)
- No chains that load from `archive/` or `.kilo/worktrees`

## Conclusion
Execution chains for mutations outside governance are short and direct (no deep hidden orchestration). They are primarily "alternative driver creation + raw run" patterns in specific modules. No long indirect subprocess or plugin chains for graph mutation were found.

---

# 4. IMPORT GRAPH REPORT

## Production Import Surface for Graph/Neo4j
- `mahoun/graph/neo4j/connection.py` (canonical, imports nothing suspicious)
- `mahoun/core/governance/*` (enforcement)
- All other neo4j usage should route through above.

## Actual Import Graph for Driver Creation (Non-Canonical)
1. `tests/fixtures/seed_data.py` → direct `from neo4j import GraphDatabase`
2. `mahoun/graph/gnn/gnn_graph_builder.py` → direct import + driver
3. `mahoun/graph/graph_query_service.py` → direct import + driver
4. `api/database.py` → `from neo4j import AsyncGraphDatabase`
5. `mahoun/reasoning/kg_adapters.py` → direct import
6. `mahoun/infrastructure/health/checker.py` and `integrity_probe.py` → direct
7. Various tests and scripts

## Dynamic / Reflection Imports
- `importlib.import_module` used for:
  - guardrails (hardened)
  - switchboard ultra registration (current modules)
- No `importlib` or `spec_from_file_location` targeting `/archive`, `/backup`, `.kilo/worktrees`, or legacy paths.
- No `__import__` with variable paths from untrusted input.

## Archive / Legacy Reachability via Import
- Zero static `from archive...` or `import archive...` in any .py outside the archive dirs themselves.
- No `sys.path` manipulation that adds `archive/` or worktree paths in production launchers.
- Therefore, archived Python code is not import-reachable under normal execution.

## Risk Classification
- Import surface duplication (multiple driver creations): **ARCHITECTURAL_DUPLICATION / EXECUTION_RISK** for future bypass.
- No active import-based governance bypass via legacy code.
- Potential future risk if any training script or notebook adds archive to path.

## Recommendations
Add a CI static analysis gate that greps for any `from neo4j import` or `GraphDatabase.driver` outside the two canonical files (`connection.py` and the governance boundary itself), and fails the build.

---

# 5. DIRECT_NEO4J_ACCESS_REPORT

## Canonical Access Point
Only: `mahoun/graph/neo4j/connection.py` (via `get_connection()` singleton or pool)
- All queries (read or write) go through `_raw_execute` which calls `MutationAuthorizationBoundary.inspect()`
- Writes additionally require `GovernedNeo4jSession` contextvar token

## Direct Neo4j Driver Creations Found (Outside Canonical)
1. `tests/fixtures/seed_data.py:20` (`GraphDatabase.driver`) — mutations for seeding — **CRITICAL**
2. `mahoun/graph/gnn/gnn_graph_builder.py:105` — mutations for GNN save — **CRITICAL**
3. `mahoun/graph/graph_query_service.py:372` — general queries (mutation capable) — **GOVERNANCE_BYPASS**
4. `api/database.py:84` (`AsyncGraphDatabase`) — schema init — **EXECUTION_RISK**
5. `mahoun/reasoning/kg_adapters.py:28` — reads only — **LOW_RISK**
6. `mahoun/infrastructure/health/checker.py:157` — health checks (reads) — **LOW_RISK**
7. `mahoun/infrastructure/health/integrity_probe.py:51` — probe (reads) — **LOW_RISK**

## Mutation Capability of Each
- Seed data: Yes (`CREATE`, `DETACH DELETE`)
- GNN builder: Yes (full wipe + create)
- GraphQueryService: Yes (most mutations pass filter)
- API DB: Yes for DDL (`CREATE CONSTRAINT`, etc.)
- Others: No mutations observed

## Governance Bypass Detection
Any of the above that perform mutation Cypher without:
- Active `GovernanceContext`
- Calling through `GovernedNeo4jSession`
- Passing `MutationAuthorizationBoundary`

All listed direct creations bypass by design.

## Evidence of Runtime Use
- Seed data: Explicitly called from Docker Compose for integration tests
- GNN: Called from within gnn module during graph building/saving
- GraphQueryService: Registered in switchboard, used in ultra/rag paths (mostly read)
- API DB: Called on backend startup

## Containment
All direct driver creation sites outside the connection module should be refactored to use the governed connection or be explicitly marked as read-only with enforcement.

Current state: Multiple uncontrolled direct access paths exist and some are actively used for mutations.

---

# 6. DYNAMIC_IMPORT_REPORT

## Dynamic Import Mechanisms in Use
- `importlib.import_module` (standard, for guardrails and ultra/base switching)
- No `SourceFileLoader` or `spec_from_file_location` found in production code
- `exec()` found in:
  - `mahoun/graph/ingestion/document_classifier.py` (for numpy import hack and other code blocks)
- No `pickle`, `dill`, or `shelve` used for loading executable code (only potential for data)

## Targets of Dynamic Imports
All resolved module names are static strings pointing to current `mahoun.*` packages.
No variable paths, no paths constructed from user input, no references to "archive", "backup", ".kilo", "worktree", "legacy", "tmp".

## Risk from Dynamic Loading
- Low for loading malicious archived code (no path to them).
- Medium for `document_classifier.py` `exec()` usage: allows arbitrary Python at import time for that module. Although currently used only for numpy fallback, it is a code injection surface if the file is ever edited or if globals are polluted.

## Subprocess as Indirect Dynamic Execution
Multiple scripts use subprocess to run python, git, docker, pytest, etc. These are controlled admin/CI operations, not arbitrary user-controlled code execution.

## Conclusion
No evidence of dynamic loading of archived, worktree, or experimental code at runtime.
The `exec()` in `document_classifier.py` is the only notable dynamic code execution risk and should be removed.

---

# 7. GOVERNANCE_BYPASS_REPORT

## Definition Used
A governance bypass is any code path that can cause a graph mutation (`CREATE`/`MERGE`/`DELETE`/`SET`/`REMOVE`/`DROP` or relationship mutation) without:
- An active `GovernanceContext`
- Passing through `GovernedNeo4jSession`
- Triggering `MutationAuthorizationBoundary` (or being authorized by it)
- Injecting provenance + audit

## Confirmed Bypasses (Runtime Reachable)

1. **Test Data Seeding** (`tests/fixtures/seed_data.py`)
   - Direct driver + raw mutations
   - Reachable via docker-compose and direct execution
   - No provenance, no audit log, no context
   - Classification: **CRITICAL / GOVERNANCE_BYPASS**

2. **GNN Graph Builder** (`mahoun/graph/gnn/gnn_graph_builder.py`)
   - Direct driver + `DETACH DELETE` entire DB + `CREATE`
   - Reachable via GNN training/saving pipelines
   - Classification: **CRITICAL / GOVERNANCE_BYPASS**

3. **Graph Query Service** (`mahoun/graph/graph_query_service.py`)
   - Own driver + `execute_query` that accepts and runs arbitrary Cypher (limited filter)
   - Reachable via switchboard registration and ultra/rag components
   - Can perform mutations if caller supplies them
   - Classification: **GOVERNANCE_BYPASS / EXECUTION_RISK**

4. **API Database Init** (`api/database.py`)
   - Async driver runs schema Cypher files at startup
   - Can execute `CREATE`/`DROP` statements
   - Classification: **EXECUTION_RISK** (schema mutations)

## Near-Bypasses / Architectural Risks
- Multiple independent driver creations for read paths (kg_adapters, health probes)
- Docker context includes `/archive` and `.kilo/worktrees` (potential future import or exec of old mutation code)
- `exec()` in `document_classifier.py` (code execution surface)
- Legacy scripts with broad subprocess (restore, execute_phase) — data only, but high privilege

## No Evidence Of
- Hidden AI-generated executable pipelines that mutate graph
- Runtime generation of .py files that get imported for mutations
- Subprocess chains that shell out to cypher-shell or direct neo4j mutations
- Reflection attacks loading archived mutation code

## Overall Status
The governance boundary is strong for the main application request path.
However, side paths (tests, training pipelines, startup, alternative services) still allow direct mutations.

The system does **NOT** yet meet the "ZERO direct uncontrolled graph mutation" requirement for the entire repository surface.

---

# 8. SUSPICIOUS_PATHS.json

```json
{
  "audit_date": "2026-05-25",
  "mission": "MAHOUN RUNTIME THREAT SURFACE RECONNAISSANCE",
  "final_answer": "YES - uncontrolled or governance-unaware execution paths remain reachable",
  "findings": [
    {
      "path": "tests/fixtures/seed_data.py",
      "runtime_reachability": "direct (docker-compose test seeding + python -m)",
      "execution_capability": "full",
      "mutation_capability": "CREATE, DETACH DELETE on LegalRule/TestData",
      "risk_classification": "CRITICAL",
      "why_it_matters": "Bypasses all governance, provenance, audit. Runs in environments that may share artifacts with production.",
      "containment_recommendation": "quarantine, governance-refactor, runtime blocking for prod profiles"
    },
    {
      "path": "mahoun/graph/gnn/gnn_graph_builder.py",
      "runtime_reachability": "via GNN training pipelines and save_to_neo4j calls",
      "execution_capability": "full",
      "mutation_capability": "DETACH DELETE entire DB + CREATE nodes/relationships",
      "risk_classification": "CRITICAL",
      "why_it_matters": "Training jobs can wipe and rebuild graph without governance, provenance or audit.",
      "containment_recommendation": "governance-refactor, isolate to use governed_session only"
    },
    {
      "path": "mahoun/graph/graph_query_service.py",
      "runtime_reachability": "imported via switchboard, used in ultra/rag/hybrid paths",
      "execution_capability": "full",
      "mutation_capability": "most Cypher mutations (only crude DELETE ALL blocked)",
      "risk_classification": "GOVERNANCE_BYPASS",
      "why_it_matters": "Duplicate driver + raw execution surface with weak validation.",
      "containment_recommendation": "deprecate raw driver, route writes through canonical governed path, CI exclusion for new usage"
    },
    {
      "path": "api/database.py",
      "runtime_reachability": "FastAPI startup (init_neo4j)",
      "execution_capability": "async driver + arbitrary Cypher from schema files",
      "mutation_capability": "schema DDL (CREATE CONSTRAINT, INDEX, potentially more)",
      "risk_classification": "EXECUTION_RISK",
      "why_it_matters": "Startup code runs mutations without governance context or provenance.",
      "containment_recommendation": "governance-refactor for schema application"
    },
    {
      "path": "/archive/ and mahoun/*/archive/",
      "runtime_reachability": "none via import (no production imports found); code present in Docker build context due to incomplete .dockerignore",
      "execution_capability": "dormant",
      "mutation_capability": "likely (old builders contain graph mutation logic)",
      "risk_classification": "LEGACY / QUARANTINE_CANDIDATE / EXECUTION_RISK",
      "why_it_matters": "Archived mutation code ships in images; future accidental activation possible via path manipulation.",
      "containment_recommendation": "dockerignore, gitignore, quarantine, CI exclusion"
    },
    {
      "path": ".kilo/worktrees/* (multiple full clones)",
      "runtime_reachability": "none via standard PYTHONPATH; potential if cwd or PYTHONPATH set to worktree",
      "execution_capability": "full (identical project copies)",
      "mutation_capability": "full (including old and new governance code versions)",
      "risk_classification": "EXECUTION_RISK",
      "why_it_matters": "Version skew and duplicate governance implementations; massive image bloat if not excluded from Docker.",
      "containment_recommendation": "dockerignore, gitignore, launcher isolation"
    },
    {
      "path": "mahoun/graph/ingestion/document_classifier.py",
      "runtime_reachability": "imported by ingestion pipelines",
      "execution_capability": "exec() at import time",
      "mutation_capability": "indirect (code execution surface)",
      "risk_classification": "SECURITY_RISK",
      "why_it_matters": "Use of exec() for imports and dynamic code blocks creates code injection vector.",
      "containment_recommendation": "remove exec, use safe import patterns"
    },
    {
      "path": "mahoun/reasoning/kg_adapters.py",
      "runtime_reachability": "reasoning engine",
      "execution_capability": "own driver, read queries only",
      "mutation_capability": "none observed",
      "risk_classification": "LOW_RISK",
      "why_it_matters": "Duplication of connection logic; future developer may add writes.",
      "containment_recommendation": "refactor to use canonical connection for reads too"
    },
    {
      "path": "multiple health/integrity probes (mahoun/infrastructure/health/)",
      "runtime_reachability": "monitoring and startup checks",
      "execution_capability": "own drivers",
      "mutation_capability": "none observed (reads + connectivity tests)",
      "risk_classification": "LOW_RISK",
      "why_it_matters": "Additional driver surfaces increase attack surface.",
      "containment_recommendation": "centralize all driver usage"
    },
    {
      "path": "scripts/restore.py, execute_phase.py, backup.py and similar",
      "runtime_reachability": "admin/CI/restore workflows",
      "execution_capability": "subprocess + high privilege operations",
      "mutation_capability": "indirect via data restore (not direct Cypher)",
      "risk_classification": "LOW_RISK for graph mutation (data only)",
      "why_it_matters": "Restore can overwrite graph state outside normal mutation path.",
      "containment_recommendation": "ensure restore uses governed paths where possible; audit all restore operations"
    }
  ],
  "summary_statistics": {
    "total_suspicious_paths_analyzed": 10,
    "critical_governance_bypasses": 3,
    "execution_risks": 4,
    "legacy_quarantine_candidates": 2,
    "low_risk_duplication": 3,
    "uncontrolled_mutation_paths_remaining": true
  }
}
```

---

**End of Grokreport.md**  
All evidence from the forensic audit is consolidated above. No files were modified or deleted during this operation.
