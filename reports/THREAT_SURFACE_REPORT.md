# MAHOUN RUNTIME THREAT SURFACE REPORT
Date: 2026-05-25
Auditor: Kilo (Forensic Mode)

## Executive Summary
The canonical graph mutation path is: Neo4jConnection.governed_session() -> GovernedNeo4jSession (with MutationAuthorizationBoundary.inspect() on every query in _raw_execute).

Multiple non-canonical mutation surfaces were identified and are runtime-reachable under certain conditions (test seeding, GNN pipelines, alternative query services, startup schema init).

Docker build context leaks archived and worktree code into images.

## Key Findings by Risk

### CRITICAL / GOVERNANCE_BYPASS
- tests/fixtures/seed_data.py: Direct GraphDatabase.driver + session.run(CREATE, DETACH DELETE) for test seeding. Invoked by docker-compose and __main__. Reachable in test/CI environments.
- mahoun/graph/gnn/gnn_graph_builder.py: Direct driver + DETACH DELETE + CREATE in save_to_neo4j(). Part of GNN training pipeline.
- mahoun/graph/graph_query_service.py: Own driver + direct session.run/tx.run with only partial dangerous keyword filtering. Registered via switchboard. Can execute mutations if called with write Cypher.
- api/database.py: Async driver used during init for schema Cypher execution (CREATE CONSTRAINT etc. from external .cypher files).

### EXECUTION_RISK / SECURITY_RISK
- mahoun/graph/ingestion/document_classifier.py: Multiple exec() for dynamic numpy import and code blocks.
- Root /archive and .kilo/worktrees not fully excluded from Docker context (partial .dockerignore).
- Multiple modules create independent Neo4j drivers (kg_adapters, health checks, integrity_probe) — duplication of connection logic, potential for future bypass.

### LEGACY / QUARANTINE_CANDIDATE
- All code under /archive/, mahoun/*/archive/, .kilo/worktrees/*/ (full project clones). No static imports from production, but present in build context and local FS.
- Old ultra_* and domain_modules_staging copies.

### LOW_RISK (with caveats)
- Scripts using subprocess for git/backup/CI (expected admin tooling).
- sys.path.insert in tests/ and scripts/ (local dev only).
- .env files present locally but excluded from Docker.

## Uncontrolled Execution Paths Remaining
YES. Graph mutations can still execute outside the governed runtime via:
1. Test seeding path (docker + direct python)
2. GNN training pipelines
3. GraphQueryService (if used for writes)
4. Startup schema application in api/database.py
5. Any future direct driver usage in unreviewed pipelines

## Containment Recommendations (not applied)
- Quarantine: Move seed_data.py and gnn_graph_builder mutation logic behind governed_session.
- Governance-refactor: Deprecate GraphQueryService direct driver; route all through canonical connection.
- dockerignore + .gitignore hardening: Explicitly exclude root archive/, .kilo/, all worktrees from build context.
- CI gate enhancement: Add runtime import scan that fails on any import or driver creation outside mahoun/graph/neo4j/connection.py and mahoun/core/governance/.
- Runtime blocking: Consider import hook or monkey-patch at startup to detect and block raw neo4j driver creation after governance init.

## Final Answer to Mission Question
"Does ANY uncontrolled or governance-unaware execution path remain reachable?"
**YES** — multiple vectors for graph mutation and code execution outside the intended governance layer are still reachable in test, training, and partial startup paths, plus code leakage via Docker.

Evidence preserved in this report and SUSPICIOUS_PATHS.json.
