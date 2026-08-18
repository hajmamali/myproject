# MAHOUN EXECUTION CHAIN REPORT
Date: 2026-05-25

## Primary Runtime Entry Points
1. FastAPI (api/main.py) -> uvicorn
2. Docker compose services (backend, neo4j, etc.)
3. Scripts in scripts/ (ingest, phase execution, backup/restore, CI gates)
4. Tests (pytest, direct python -m)
5. Notebooks / demos (local only)

## Graph Mutation Execution Chains

### Canonical Chain (Enforced)
Request/Job -> GovernanceContextManager.active_context() -> connection.governed_session() -> GovernedNeo4jSession.write_*() -> _execute_authorized (sets contextvar) -> _raw_execute -> MutationAuthorizationBoundary.inspect() (passes) -> driver session.run

### Bypass Chain 1: Test Seeding
docker-compose (test profile) or python -m tests.fixtures.seed_data -> seed_test_knowledge_graph() -> GraphDatabase.driver() -> session.run(CREATE / DETACH DELETE) -> NO governance context, NO boundary, NO provenance, NO audit

### Bypass Chain 2: GNN Pipeline
Training script / notebook -> GNNGraphBuilder.build_graph() -> save_to_neo4j() -> own GraphDatabase.driver -> session.run(DETACH DELETE + CREATE) -> direct mutation, no governance

### Bypass Chain 3: GraphQueryService
Any code importing mahoun.graph.graph_query_service -> GraphQueryService(config) -> execute_query( arbitrary Cypher ) -> own driver.session().run() -> limited keyword filter only

### Bypass Chain 4: Startup Schema
uvicorn -> FastAPI lifespan -> api.database.init_neo4j() -> AsyncGraphDatabase.driver -> session.run( arbitrary statements from .cypher files )

### Hidden / Indirect Chains
- Subprocess in scripts/execute_phase.py, restore.py etc. call git, docker, but do not directly mutate graph via shell (they call governed paths or dumps).
- No evidence of cron, Celery, or background workers with separate mutation paths.
- No pickle/dill deserialization of executable graph mutation code found.

## Dynamic Loading Chains
- switchboard.py + importlib.import_module for ultra/base switching (current modules only)
- hardened_import.py for guardrails (fail-fast)
- No chains that load from archive/ or .kilo/worktrees

## Conclusion
Execution chains for mutations outside governance are short and direct (no deep hidden orchestration). They are primarily "alternative driver creation + raw run" patterns in specific modules. No long indirect subprocess or plugin chains for graph mutation were found.
