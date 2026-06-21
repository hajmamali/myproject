# OUTBOX & METRICS ISOLATION - REALITY MAP

## Effective Schema Analysis
- **Primary Table:** `legal.chunks`
- **Partitioning:** Range-partitioned by `created_date`.
- **Existing Metric Columns:** `pagerank_score`, `centrality_score`, `community_id`, `authority_score`.
- **Embedding:** Currently `VECTOR(1024)` (per `master_schema.sql`) or `VECTOR(768)` (per migration 002).
- **Outbox Conflict:** A table named `outbox` exists for indexing tasks.
- **Versioning:** `legal.chunks` lacks a `version` column (unlike `laws` or `articles`).

## Implementation Plan
### Phase 1: Transactional Outbox (SoT Discipline)
- **Schema:** `governance`
- **Table:** `governance.transactional_outbox`
- **Trigger:** Attached to `legal.chunks` (parent).
- **Strategy:** Snapshot payload (JSONB).

### Phase 2: Metrics Isolation
- **New Table:** `legal.chunk_graph_metrics`
- **Decommissioned Columns:** `pagerank_score`, `centrality_score`, `community_id`, `authority_score`.
- **Constraint:** Use `DROP COLUMN IF EXISTS` to handle schema variance.

## Discovery Proofs
- `mahoun/graph/schema/sql/master_schema.sql:1805` -> `legal.chunks` definition.
- `mahoun/graph/schema/sql/master_schema.sql:660` -> `outbox` definition.
- `mahoun/graph/schema/migrations/002_optimize_vector_and_partitioning.sql:123` -> Partitioning evidence.
