# MAHOUN RUNTIME REACHABILITY REPORT
Date: 2026-05-25

## Canonical Mutation Path (Single Source of Truth)
- File: mahoun/graph/neo4j/connection.py
- Entry: get_connection().governed_session(correlation_id, actor_id)
- Enforcement: MutationAuthorizationBoundary.inspect(query) called on EVERY Cypher in _raw_execute()
- Authorization token: contextvars.ContextVar _authorized_write_ctx
- Only surface allowed to set the token: GovernedNeo4jSession (mahoun/core/governance/mutation_boundary.py)
- All writes must also have active GovernanceContext (fail-closed)

## Non-Canonical Reachable Mutation Paths (Classified)

1. tests/fixtures/seed_data.py
   - Reachability: Direct (python -m or docker-compose test seeding)
   - Execution: Yes (full driver lifecycle + mutations)
   - Mutation: CREATE LegalRule/TestData, DETACH DELETE
   - Classification: CRITICAL / GOVERNANCE_BYPASS
   - Why: Runs in CI/test environments that may share images or configs with prod-like setups. No provenance, no audit, no governance context.
   - Containment: Quarantine test seeding behind a governed test helper; never run in prod profiles.

2. mahoun/graph/gnn/gnn_graph_builder.py:save_to_neo4j
   - Reachability: Via GNN training pipelines (mahoun/graph/gnn/)
   - Execution: Yes (own driver)
   - Mutation: DETACH DELETE entire DB + CREATE nodes/rels
   - Classification: CRITICAL / GOVERNANCE_BYPASS
   - Why: Training jobs can be triggered from scripts or notebooks against shared DB.
   - Containment: Refactor to accept a governed session or use connection.governed_session internally.

3. mahoun/graph/graph_query_service.py
   - Reachability: Imported via switchboard, ultra systems, some RAG/hybrid paths
   - Execution: Yes (own driver + execute_query that does raw session.run)
   - Mutation: Allowed for most Cypher except crude "DROP/DELETE ALL/DETACH DELETE without WHERE"
   - Classification: GOVERNANCE_BYPASS / EXECUTION_RISK
   - Why: Duplicate driver surface; partial validation only.
   - Containment: Deprecate raw driver; make it a read-only facade or force it to delegate writes to canonical governed path.

4. api/database.py:init_neo4j (schema application)
   - Reachability: On FastAPI startup when ENABLE_NEO4J=true
   - Execution: Async driver, runs arbitrary .cypher from switchboard schema paths
   - Mutation: CREATE CONSTRAINT, INDEX, potentially other DDL
   - Classification: EXECUTION_RISK (schema layer)
   - Why: Schema files could be tampered or contain mutations; bypasses boundary (though boundary would catch CREATE if it were regular).
   - Containment: Move schema application through a governed DDL helper or whitelist only.

5. Other driver creations (reads mostly)
   - mahoun/reasoning/kg_adapters.py, mahoun/infrastructure/health/*, integrity_probe.py
   - Classification: LOW_RISK for mutation (no writes found), but architectural duplication.

## Archived / Hidden / Worktree Reachability
- /archive/, mahoun/*/archive/, .kilo/worktrees/* : No static imports from production .py files.
- Dynamic loading: None targeting these paths.
- Docker context: Not fully excluded (.dockerignore misses root archive/ and .kilo). Code can ship in images.
- Runtime activation: Only if PYTHONPATH or cwd manipulation points into them (not in standard launchers).
- Classification: LEGACY / QUARANTINE_CANDIDATE for code; EXECUTION_RISK due to image bloat and potential future accidental import.

## Subprocess / Dynamic Exec / Importlib
- Subprocess: Limited to admin scripts (git, backup, CI gates). No direct graph mutation via shell.
- eval/exec: Mostly model.eval(); one risky file (document_classifier.py) uses exec for imports and code blocks. Classification: SECURITY_RISK.
- importlib: Used for guardrails and switchboard ultra/base switching. All target current mahoun.* — SAFE.
- sys.path: Many in tests/scripts for local dev. One in hardened_paddle_ocr for libs (LOW_RISK).

## Launchers / CI / Entrypoints
- .github/workflows/* : Strong governance gates, reference ci/scripts/ and tests/governance/. No archive references. SAFE.
- docker-compose: Mounts only data dirs; no archive/worktree mounts. Good.
- Scripts in scripts/ and first_step_ci_cd/: Many are governance/audit tools themselves. Some (restore, backup) operate on data only.
- No evidence of launchers pointing to archived code for execution.

## Conclusion on Reachability
Uncontrolled paths for **graph mutation** remain reachable in:
- Test/CI seeding
- GNN pipelines
- Alternative query services
- Startup schema

Archived code is not actively imported but leaks into Docker images and local FS.

No evidence of hidden AI-tool generated executable pipelines or reflection-based loading of legacy code in current runtime.
