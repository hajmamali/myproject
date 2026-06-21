-- ============================================================================
-- PostgreSQL Schema for IndexingService Catalog
-- ============================================================================
-- This schema implements the Catalog + Outbox pattern for tracking
-- indexing jobs and ensuring distributed consistency across multiple
-- datastores (ChromaDB, Neo4j, BM25).
--
-- Tables:
-- 1. index_jobs: Track indexing jobs (metadata, status, timing)
-- 2. index_items: Track individual items being indexed
-- 3. outbox: Outbox pattern for tracking which adapters have processed items
--
-- Usage:
--   psql -U mahoun -d mahoun -f indexing_schema.sql
-- ============================================================================

-- Drop existing tables (for clean setup)
DROP TABLE IF EXISTS outbox CASCADE;
DROP TABLE IF EXISTS index_items CASCADE;
DROP TABLE IF EXISTS index_jobs CASCADE;

-- ============================================================================
-- Table: index_jobs
-- ============================================================================
-- Tracks indexing jobs with metadata and status
--
-- Columns:
-- - job_id: Unique job identifier (UUID)
-- - job_type: Type of job (incremental, full, etc.)
-- - index_version: Version of the index schema
-- - status: Job status (running, completed, failed)
-- - meta: JSON metadata (source, batch info, etc.)
-- - error: Error message if failed
-- - started_at: Job start timestamp
-- - finished_at: Job completion timestamp
-- - created_at: Record creation timestamp
-- ============================================================================

CREATE TABLE index_jobs (
    job_id VARCHAR(36) PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    index_version VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    meta JSONB DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_index_jobs_status ON index_jobs(status);
CREATE INDEX idx_index_jobs_started_at ON index_jobs(started_at DESC);
CREATE INDEX idx_index_jobs_index_version ON index_jobs(index_version);

-- ============================================================================
-- Table: index_items
-- ============================================================================
-- Tracks individual items being indexed
--
-- Columns:
-- - id: Auto-increment primary key
-- - job_id: Reference to index_jobs
-- - chunk_id: Unique chunk identifier
-- - doc_id: Document identifier
-- - content_hash: SHA256 hash of content (for idempotency)
-- - schema_hash: SHA256 hash of schema version
-- - index_version: Version of the index schema
-- - status: Item status (pending, completed, failed)
-- - created_at: Record creation timestamp
-- - updated_at: Record update timestamp
--
-- Unique constraint on (chunk_id, index_version) ensures idempotency
-- ============================================================================

CREATE TABLE index_items (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES index_jobs(job_id) ON DELETE CASCADE,
    chunk_id VARCHAR(255) NOT NULL,
    doc_id VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    schema_hash VARCHAR(64) NOT NULL,
    index_version VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint for idempotency
    UNIQUE (chunk_id, index_version)
);

-- Indexes for efficient querying
CREATE INDEX idx_index_items_job_id ON index_items(job_id);
CREATE INDEX idx_index_items_chunk_id ON index_items(chunk_id);
CREATE INDEX idx_index_items_doc_id ON index_items(doc_id);
CREATE INDEX idx_index_items_status ON index_items(status);
CREATE INDEX idx_index_items_content_hash ON index_items(content_hash);

-- ============================================================================
-- Table: outbox
-- ============================================================================
-- Outbox pattern for tracking which adapters have processed items
--
-- Columns:
-- - id: Auto-increment primary key
-- - job_id: Reference to index_jobs
-- - chunk_id: Chunk identifier
-- - adapter: Adapter name (chroma, bm25, neo4j)
-- - applied_at: Timestamp when adapter processed the item
--
-- Unique constraint on (chunk_id, adapter) ensures each adapter processes
-- each item exactly once
-- ============================================================================

CREATE TABLE outbox (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES index_jobs(job_id) ON DELETE CASCADE,
    chunk_id VARCHAR(255) NOT NULL,
    adapter VARCHAR(50) NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate processing
    UNIQUE (chunk_id, adapter)
);

-- Indexes for efficient querying
CREATE INDEX idx_outbox_job_id ON outbox(job_id);
CREATE INDEX idx_outbox_chunk_id ON outbox(chunk_id);
CREATE INDEX idx_outbox_adapter ON outbox(adapter);
CREATE INDEX idx_outbox_applied_at ON outbox(applied_at DESC);

-- ============================================================================
-- Views for Monitoring
-- ============================================================================

-- View: Job statistics
CREATE OR REPLACE VIEW v_job_stats AS
SELECT
    j.job_id,
    j.job_type,
    j.index_version,
    j.status,
    j.started_at,
    j.finished_at,
    EXTRACT(EPOCH FROM (COALESCE(j.finished_at, NOW()) - j.started_at)) AS duration_seconds,
    COUNT(DISTINCT i.chunk_id) AS total_items,
    COUNT(DISTINCT CASE WHEN i.status = 'completed' THEN i.chunk_id END) AS completed_items,
    COUNT(DISTINCT CASE WHEN i.status = 'failed' THEN i.chunk_id END) AS failed_items,
    COUNT(DISTINCT o.id) AS outbox_entries,
    j.meta
FROM index_jobs j
LEFT JOIN index_items i ON j.job_id = i.job_id
LEFT JOIN outbox o ON j.job_id = o.job_id
GROUP BY j.job_id, j.job_type, j.index_version, j.status, j.started_at, j.finished_at, j.meta;

-- View: Adapter statistics
CREATE OR REPLACE VIEW v_adapter_stats AS
SELECT
    adapter,
    COUNT(*) AS total_processed,
    COUNT(DISTINCT chunk_id) AS unique_chunks,
    COUNT(DISTINCT job_id) AS jobs_involved,
    MIN(applied_at) AS first_processed,
    MAX(applied_at) AS last_processed
FROM outbox
GROUP BY adapter;

-- View: Recent jobs
CREATE OR REPLACE VIEW v_recent_jobs AS
SELECT
    job_id,
    job_type,
    index_version,
    status,
    started_at,
    finished_at,
    EXTRACT(EPOCH FROM (COALESCE(finished_at, NOW()) - started_at)) AS duration_seconds,
    meta
FROM index_jobs
ORDER BY started_at DESC
LIMIT 100;

-- ============================================================================
-- Functions
-- ============================================================================

-- Function: Get job progress
CREATE OR REPLACE FUNCTION get_job_progress(p_job_id VARCHAR)
RETURNS TABLE (
    job_id VARCHAR,
    status VARCHAR,
    total_items BIGINT,
    completed_items BIGINT,
    failed_items BIGINT,
    progress_percent NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        j.job_id,
        j.status,
        COUNT(i.chunk_id) AS total_items,
        COUNT(CASE WHEN i.status = 'completed' THEN 1 END) AS completed_items,
        COUNT(CASE WHEN i.status = 'failed' THEN 1 END) AS failed_items,
        CASE
            WHEN COUNT(i.chunk_id) > 0 THEN
                ROUND(100.0 * COUNT(CASE WHEN i.status = 'completed' THEN 1 END) / COUNT(i.chunk_id), 2)
            ELSE 0
        END AS progress_percent
    FROM index_jobs j
    LEFT JOIN index_items i ON j.job_id = i.job_id
    WHERE j.job_id = p_job_id
    GROUP BY j.job_id, j.status;
END;
$$ LANGUAGE plpgsql;

-- Function: Check if item is already indexed
CREATE OR REPLACE FUNCTION is_item_indexed(
    p_chunk_id VARCHAR,
    p_index_version VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM index_items
        WHERE chunk_id = p_chunk_id
          AND index_version = p_index_version
          AND status = 'completed'
    ) INTO v_exists;
    
    RETURN v_exists;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Get all jobs
-- SELECT * FROM v_job_stats ORDER BY started_at DESC;

-- Get adapter statistics
-- SELECT * FROM v_adapter_stats;

-- Get job progress
-- SELECT * FROM get_job_progress('your-job-id-here');

-- Check if item is indexed
-- SELECT is_item_indexed('chunk_123', 'v1');

-- Get failed items
-- SELECT * FROM index_items WHERE status = 'failed' ORDER BY created_at DESC;

-- Get items not yet processed by all adapters
-- SELECT
--     i.chunk_id,
--     i.doc_id,
--     COUNT(DISTINCT o.adapter) AS adapters_processed
-- FROM index_items i
-- LEFT JOIN outbox o ON i.chunk_id = o.chunk_id
-- WHERE i.status = 'completed'
-- GROUP BY i.chunk_id, i.doc_id
-- HAVING COUNT(DISTINCT o.adapter) < 3;  -- Assuming 3 adapters

-- ============================================================================
-- Grants (adjust as needed)
-- ============================================================================

-- Grant permissions to mahoun user
GRANT ALL PRIVILEGES ON TABLE index_jobs TO mahoun;
GRANT ALL PRIVILEGES ON TABLE index_items TO mahoun;
GRANT ALL PRIVILEGES ON TABLE outbox TO mahoun;
GRANT ALL PRIVILEGES ON SEQUENCE index_items_id_seq TO mahoun;
GRANT ALL PRIVILEGES ON SEQUENCE outbox_id_seq TO mahoun;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE index_jobs IS 'Tracks indexing jobs with metadata and status';
COMMENT ON TABLE index_items IS 'Tracks individual items being indexed';
COMMENT ON TABLE outbox IS 'Outbox pattern for tracking adapter writes';

COMMENT ON VIEW v_job_stats IS 'Job statistics with item counts and duration';
COMMENT ON VIEW v_adapter_stats IS 'Adapter processing statistics';
COMMENT ON VIEW v_recent_jobs IS 'Most recent 100 jobs';

-- ============================================================================
-- Done
-- ============================================================================

\echo 'Schema created successfully!'
\echo 'Tables: index_jobs, index_items, outbox'
\echo 'Views: v_job_stats, v_adapter_stats, v_recent_jobs'
\echo 'Functions: get_job_progress, is_item_indexed'
