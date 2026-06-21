-- ============================================================================
-- Migration 004: Transactional Outbox and Metrics Isolation
-- Purpose: 
--  1. Implement Transactional Outbox pattern for Neo4j projection.
--  2. Isolate volatile graph metrics to reduce write amplification on chunks.
-- ============================================================================

BEGIN;

-- ============================================================================
-- PHASE 1: GOVERNANCE SCHEMA & TRANSACTIONAL OUTBOX
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS governance;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outbox_status') THEN
        CREATE TYPE governance.outbox_status AS ENUM ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS governance.transactional_outbox (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type  VARCHAR(64) NOT NULL,
    aggregate_id    UUID NOT NULL,
    action          VARCHAR(16) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    payload         JSONB NOT NULL,
    status          governance.outbox_status NOT NULL DEFAULT 'PENDING',
    retry_count     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id  UUID NULL,
    last_error      TEXT NULL,
    locked_at       TIMESTAMPTZ NULL
);

-- Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_outbox_status_created ON governance.transactional_outbox (status, created_at) 
    WHERE status IN ('PENDING', 'FAILED');
CREATE INDEX IF NOT EXISTS idx_outbox_aggregate ON governance.transactional_outbox (aggregate_type, aggregate_id);

-- ============================================================================
-- PHASE 2: VERSIONING & METRICS ISOLATION
-- ============================================================================

-- Ensure legal.chunks has versioning
ALTER TABLE legal.chunks ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 1;

-- Create Metrics Table
CREATE TABLE IF NOT EXISTS legal.chunk_graph_metrics (
    chunk_id       UUID PRIMARY KEY REFERENCES legal.chunks(id) ON DELETE CASCADE,
    pagerank       FLOAT8,
    centrality     FLOAT8,
    betweenness    FLOAT8,
    closeness      FLOAT8,
    eigenvector    FLOAT8,
    community_id   INT,
    last_updated   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_pagerank ON legal.chunk_graph_metrics (pagerank DESC);

-- Backfill Metrics from legal.chunks if columns exist
DO $$
BEGIN
    -- This handles migration-001/master_schema style columns
    INSERT INTO legal.chunk_graph_metrics (chunk_id, pagerank, centrality, community_id)
    SELECT id, pagerank_score, centrality_score, community_id 
    FROM legal.chunks
    ON CONFLICT (chunk_id) DO UPDATE SET
        pagerank = EXCLUDED.pagerank,
        centrality = EXCLUDED.centrality,
        community_id = EXCLUDED.community_id;
EXCEPTION WHEN undefined_column THEN
    -- Fallback for systems where some columns might be missing
    RAISE NOTICE 'Skipping backfill due to missing columns in legal.chunks';
END $$;

-- ============================================================================
-- TRIGGERS: ATOMICITY & VERSIONING
-- ============================================================================

-- 1. Version Increment Trigger
CREATE OR REPLACE FUNCTION legal.fn_increment_chunk_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_increment_chunk_version ON legal.chunks;
CREATE TRIGGER tr_increment_chunk_version
    BEFORE UPDATE ON legal.chunks
    FOR EACH ROW
    EXECUTE FUNCTION legal.fn_increment_chunk_version();

-- 2. Outbox Snapshot Trigger
CREATE OR REPLACE FUNCTION governance.fn_chunks_to_outbox()
RETURNS TRIGGER AS $$
DECLARE
    v_correlation_id UUID;
BEGIN
    -- Try to capture correlation_id from session context if available
    BEGIN
        v_correlation_id := current_setting('mahoun.current_correlation_id', true)::uuid;
    EXCEPTION WHEN OTHERS THEN
        v_correlation_id := NULL;
    END;

    IF (TG_OP = 'DELETE') THEN
        INSERT INTO governance.transactional_outbox (aggregate_type, aggregate_id, action, payload, correlation_id)
        VALUES ('legal.chunks', OLD.id, 'DELETE', jsonb_build_object('id', OLD.id), v_correlation_id);
        RETURN OLD;
    ELSE
        INSERT INTO governance.transactional_outbox (aggregate_type, aggregate_id, action, payload, correlation_id)
        VALUES (
            'legal.chunks', 
            NEW.id, 
            TG_OP, 
            to_jsonb(NEW) - 'embedding' - 'embedding_dense_1024' - 'embedding_bge_m3_768' - 'embedding_e5_large_1024', -- Strip heavy vectors from outbox
            v_correlation_id
        );
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_chunks_to_outbox ON legal.chunks;
CREATE TRIGGER tr_chunks_to_outbox
    AFTER INSERT OR UPDATE OR DELETE ON legal.chunks
    FOR EACH ROW
    EXECUTE FUNCTION governance.fn_chunks_to_outbox();

-- ============================================================================
-- CLEANUP: STOP WRITE AMPLIFICATION
-- ============================================================================

-- Safe column removal
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS pagerank_score;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS centrality_score;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS community_id;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS authority_score;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS hub_score;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS betweenness;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS closeness;
ALTER TABLE legal.chunks DROP COLUMN IF EXISTS eigenvector;

COMMIT;
