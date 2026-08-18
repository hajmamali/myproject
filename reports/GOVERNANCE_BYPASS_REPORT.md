# MAHOUN GOVERNANCE_BYPASS_REPORT
Date: 2026-05-25

## Definition Used
A governance bypass is any code path that can cause a graph mutation (CREATE/MERGE/DELETE/SET/REMOVE/DROP or relationship mutation) without:
- An active GovernanceContext
- Passing through GovernedNeo4jSession
- Triggering MutationAuthorizationBoundary (or being authorized by it)
- Injecting provenance + audit

## Confirmed Bypasses (Runtime Reachable)

1. **Test Data Seeding** (tests/fixtures/seed_data.py)
   - Direct driver + raw mutations
   - Reachable via docker-compose and direct execution
   - No provenance, no audit log, no context
   - Classification: CRITICAL / GOVERNANCE_BYPASS

2. **GNN Graph Builder** (mahoun/graph/gnn/gnn_graph_builder.py)
   - Direct driver + DETACH DELETE entire DB + CREATE
   - Reachable via GNN training/saving pipelines
   - Classification: CRITICAL / GOVERNANCE_BYPASS

3. **Graph Query Service** (mahoun/graph/graph_query_service.py)
   - Own driver + execute_query that accepts and runs arbitrary Cypher (limited filter)
   - Reachable via switchboard registration and ultra/rag components
   - Can perform mutations if caller supplies them
   - Classification: GOVERNANCE_BYPASS / EXECUTION_RISK

4. **API Database Init** (api/database.py)
   - Async driver runs schema Cypher files at startup
   - Can execute CREATE/DROP statements
   - Classification: EXECUTION_RISK (schema mutations)

## Near-Bypasses / Architectural Risks
- Multiple independent driver creations for read paths (kg_adapters, health probes)
- Docker context includes /archive and .kilo/worktrees (potential future import or exec of old mutation code)
- exec() in document_classifier.py (code execution surface)
- Legacy scripts with broad subprocess (restore, execute_phase) — data only, but high privilege

## No Evidence Of
- Hidden AI-generated executable pipelines that mutate graph
- Runtime generation of .py files that get imported for mutations
- Subprocess chains that shell out to cypher-shell or direct neo4j mutations
- Reflection attacks loading archived mutation code

## Overall Status
The governance boundary is strong for the main application request path.
However, side paths (tests, training pipelines, startup, alternative services) still allow direct mutations.

The system does NOT yet meet the "ZERO direct uncontrolled graph mutation" requirement for the entire repository surface.
