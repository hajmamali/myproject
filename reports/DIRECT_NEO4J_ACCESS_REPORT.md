# MAHOUN DIRECT_NEO4J_ACCESS_REPORT
Date: 2026-05-25

## Canonical Access Point
Only: mahoun/graph/neo4j/connection.py (via get_connection() singleton or pool)
- All queries (read or write) go through _raw_execute which calls MutationAuthorizationBoundary.inspect()
- Writes additionally require GovernedNeo4jSession contextvar token

## Direct Neo4j Driver Creations Found (Outside Canonical)
1. tests/fixtures/seed_data.py:20 (GraphDatabase.driver) - mutations for seeding - CRITICAL
2. mahoun/graph/gnn/gnn_graph_builder.py:105 - mutations for GNN save - CRITICAL
3. mahoun/graph/graph_query_service.py:372 - general queries (mutation capable) - GOVERNANCE_BYPASS
4. api/database.py:84 (AsyncGraphDatabase) - schema init - EXECUTION_RISK
5. mahoun/reasoning/kg_adapters.py:28 - reads only - LOW_RISK
6. mahoun/infrastructure/health/checker.py:157 - health checks (reads) - LOW_RISK
7. mahoun/infrastructure/health/integrity_probe.py:51 - probe (reads) - LOW_RISK

## Mutation Capability of Each
- Seed data: Yes (CREATE, DETACH DELETE)
- GNN builder: Yes (full wipe + create)
- GraphQueryService: Yes (most mutations pass filter)
- API DB: Yes for DDL (CREATE CONSTRAINT, etc.)
- Others: No mutations observed

## Governance Bypass Detection
Any of the above that perform mutation Cypher without:
- Active GovernanceContext
- Calling through GovernedNeo4jSession
- Passing MutationAuthorizationBoundary

All listed direct creations bypass by design.

## Evidence of Runtime Use
- Seed data: Explicitly called from Docker Compose for integration tests
- GNN: Called from within gnn module during graph building/saving
- GraphQueryService: Registered in switchboard, used in ultra/rag paths (mostly read)
- API DB: Called on backend startup

## Containment
All direct driver creation sites outside the connection module should be refactored to use the governed connection or be explicitly marked as read-only with enforcement.

Current state: Multiple uncontrolled direct access paths exist and some are actively used for mutations.
