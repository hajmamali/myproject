-- MAHOUN Master Schema
-- Generated automatically
-- ============================================================

-- File: data_management/migrations/001_initial_schema.sql
-- ------------------------------------------------------------
-- ============================================================================
-- MAHOUN Data Management System - Initial Database Schema
-- ============================================================================
-- 
-- This migration creates the core database schema for MAHOUN's data management
-- and backup system, including backup catalog, restore history, quality reports,
-- audit logs, and monitoring tables.
--
-- Version: 1.0.0
-- Author: MAHOUN Team
-- ============================================================================

-- Create schema for data management
CREATE SCHEMA IF NOT EXISTS data_mgmt;

-- Set search path
SET search_path TO data_mgmt, public;

-- ============================================================================
-- Backup Catalog Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS backup_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_type VARCHAR(50) NOT NULL CHECK (database_type IN ('postgresql', 'neo4j', 'redis', 'chromadb', 'elasticsearch')),
    backup_type VARCHAR(20) NOT NULL CHECK (backup_type IN ('full', 'incremental', 'differential')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'verifying', 'uploading', 'corrupted')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    size_bytes BIGINT NOT NULL DEFAULT 0 CHECK (size_bytes >= 0),
    compressed_size_bytes BIGINT NOT NULL DEFAULT 0 CHECK (compressed_size_bytes >= 0),
    encrypted BOOLEAN NOT NULL DEFAULT FALSE,
    checksum VARCHAR(64),
    storage_path TEXT NOT NULL,
    cloud_locations JSONB DEFAULT '[]'::jsonb,
    parent_backup_id UUID REFERENCES backup_catalog(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by VARCHAR(100),
    
    -- Constraints
    CONSTRAINT valid_compression CHECK (compressed_size_bytes <= size_bytes),
    CONSTRAINT completed_has_timestamp CHECK (
        (status = 'completed' AND completed_at IS NOT NULL) OR
        (status != 'completed')
    )
);

-- Indexes for backup_catalog
CREATE INDEX idx_backup_catalog_database_type ON backup_catalog(database_type);
CREATE INDEX idx_backup_catalog_backup_type ON backup_catalog(backup_type);
CREATE INDEX idx_backup_catalog_status ON backup_catalog(status);
CREATE INDEX idx_backup_catalog_created_at ON backup_catalog(created_at DESC);
CREATE INDEX idx_backup_catalog_parent ON backup_catalog(parent_backup_id) WHERE parent_backup_id IS NOT NULL;
CREATE INDEX idx_backup_catalog_metadata ON backup_catalog USING gin(metadata);

-- Comment on table
COMMENT ON TABLE backup_catalog IS 'MAHOUN backup catalog storing metadata for all backup operations';

-- ============================================================================
-- Restore History Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS restore_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restore_point_id UUID NOT NULL,
    backup_id UUID REFERENCES backup_catalog(id) ON DELETE CASCADE,
    database_type VARCHAR(50) NOT NULL CHECK (database_type IN ('postgresql', 'neo4j', 'redis', 'chromadb', 'elasticsearch')),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'rolled_back')),
    error_message TEXT,
    restored_rows BIGINT DEFAULT 0 CHECK (restored_rows >= 0),
    duration_seconds FLOAT,
    dry_run BOOLEAN NOT NULL DEFAULT FALSE,
    restored_by VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT completed_restore_has_timestamp CHECK (
        (status IN ('completed', 'failed', 'rolled_back') AND completed_at IS NOT NULL) OR
        (status NOT IN ('completed', 'failed', 'rolled_back'))
    )
);

-- Indexes for restore_history
CREATE INDEX idx_restore_history_restore_point ON restore_history(restore_point_id);
CREATE INDEX idx_restore_history_backup ON restore_history(backup_id);
CREATE INDEX idx_restore_history_started_at ON restore_history(started_at DESC);
CREATE INDEX idx_restore_history_status ON restore_history(status);

-- Comment on table
COMMENT ON TABLE restore_history IS 'MAHOUN restore operation history and audit trail';

-- ============================================================================
-- Quality Reports Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS quality_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    overall_score FLOAT NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    completeness_score FLOAT NOT NULL CHECK (completeness_score >= 0 AND completeness_score <= 100),
    accuracy_score FLOAT NOT NULL CHECK (accuracy_score >= 0 AND accuracy_score <= 100),
    consistency_score FLOAT NOT NULL CHECK (consistency_score >= 0 AND consistency_score <= 100),
    issues JSONB DEFAULT '[]'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    databases_checked VARCHAR(50)[] NOT NULL,
    duration_seconds FLOAT,
    critical_issues_count INT DEFAULT 0 CHECK (critical_issues_count >= 0),
    high_issues_count INT DEFAULT 0 CHECK (high_issues_count >= 0),
    medium_issues_count INT DEFAULT 0 CHECK (medium_issues_count >= 0),
    low_issues_count INT DEFAULT 0 CHECK (low_issues_count >= 0),
    executed_by VARCHAR(100)
);

-- Indexes for quality_reports
CREATE INDEX idx_quality_reports_timestamp ON quality_reports(timestamp DESC);
CREATE INDEX idx_quality_reports_overall_score ON quality_reports(overall_score);
CREATE INDEX idx_quality_reports_critical ON quality_reports(critical_issues_count) WHERE critical_issues_count > 0;
CREATE INDEX idx_quality_reports_issues ON quality_reports USING gin(issues);

-- Comment on table
COMMENT ON TABLE quality_reports IS 'MAHOUN data quality assessment reports';

-- ============================================================================
-- Audit Log Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    operation VARCHAR(50) NOT NULL,
    user_id VARCHAR(100),
    database_type VARCHAR(50),
    resource_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    signature VARCHAR(256),
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    duration_ms FLOAT,
    
    -- Prevent modification
    CONSTRAINT immutable_audit_log CHECK (false) NO INHERIT
);

-- Make audit_log append-only (prevent updates and deletes)
CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;

-- Indexes for audit_log
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_database_type ON audit_log(database_type);
CREATE INDEX idx_audit_log_resource_id ON audit_log(resource_id);
CREATE INDEX idx_audit_log_success ON audit_log(success) WHERE success = FALSE;

-- Comment on table
COMMENT ON TABLE audit_log IS 'MAHOUN tamper-proof audit log for all data operations';

-- ============================================================================
-- Backup Schedules Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS backup_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    databases VARCHAR(50)[] NOT NULL,
    backup_type VARCHAR(20) NOT NULL CHECK (backup_type IN ('full', 'incremental', 'differential')),
    cron_schedule VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    options JSONB DEFAULT '{}'::jsonb,
    retention_days INT NOT NULL DEFAULT 7 CHECK (retention_days >= 1),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    
    -- Constraints
    CONSTRAINT valid_databases CHECK (array_length(databases, 1) > 0)
);

-- Indexes for backup_schedules
CREATE INDEX idx_backup_schedules_enabled ON backup_schedules(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_backup_schedules_next_run ON backup_schedules(next_run) WHERE enabled = TRUE;
CREATE INDEX idx_backup_schedules_name ON backup_schedules(name);

-- Comment on table
COMMENT ON TABLE backup_schedules IS 'MAHOUN scheduled backup job configurations';

-- ============================================================================
-- Storage Metrics Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS storage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    storage_type VARCHAR(50) NOT NULL,
    total_bytes BIGINT NOT NULL CHECK (total_bytes >= 0),
    used_bytes BIGINT NOT NULL CHECK (used_bytes >= 0),
    available_bytes BIGINT NOT NULL CHECK (available_bytes >= 0),
    iops INTEGER CHECK (iops >= 0),
    throughput_bytes_per_sec BIGINT CHECK (throughput_bytes_per_sec >= 0),
    backup_count INTEGER DEFAULT 0 CHECK (backup_count >= 0),
    
    -- Constraints
    CONSTRAINT valid_storage_usage CHECK (used_bytes <= total_bytes),
    CONSTRAINT valid_available CHECK (available_bytes <= total_bytes)
);

-- Indexes for storage_metrics
CREATE INDEX idx_storage_metrics_timestamp ON storage_metrics(timestamp DESC);
CREATE INDEX idx_storage_metrics_storage_type ON storage_metrics(storage_type);
CREATE INDEX idx_storage_metrics_used_bytes ON storage_metrics(used_bytes);

-- Comment on table
COMMENT ON TABLE storage_metrics IS 'MAHOUN storage usage and performance metrics';

-- ============================================================================
-- Restore Points Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS restore_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL,
    description TEXT NOT NULL,
    databases VARCHAR(50)[] NOT NULL,
    backup_ids UUID[] NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    tags VARCHAR(50)[] DEFAULT ARRAY[]::VARCHAR[],
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT valid_databases CHECK (array_length(databases, 1) > 0),
    CONSTRAINT valid_backups CHECK (array_length(backup_ids, 1) > 0)
);

-- Indexes for restore_points
CREATE INDEX idx_restore_points_timestamp ON restore_points(timestamp DESC);
CREATE INDEX idx_restore_points_created_at ON restore_points(created_at DESC);
CREATE INDEX idx_restore_points_tags ON restore_points USING gin(tags);

-- Comment on table
COMMENT ON TABLE restore_points IS 'MAHOUN point-in-time restore points';

-- ============================================================================
-- Functions and Triggers
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for backup_schedules
CREATE TRIGGER update_backup_schedules_updated_at
    BEFORE UPDATE ON backup_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate backup statistics
CREATE OR REPLACE FUNCTION get_backup_statistics(
    p_database_type VARCHAR DEFAULT NULL,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    database_type VARCHAR,
    total_backups BIGINT,
    successful_backups BIGINT,
    failed_backups BIGINT,
    total_size_bytes BIGINT,
    avg_duration_seconds FLOAT,
    success_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bc.database_type,
        COUNT(*)::BIGINT as total_backups,
        COUNT(*) FILTER (WHERE bc.status = 'completed')::BIGINT as successful_backups,
        COUNT(*) FILTER (WHERE bc.status = 'failed')::BIGINT as failed_backups,
        SUM(bc.size_bytes)::BIGINT as total_size_bytes,
        AVG(EXTRACT(EPOCH FROM (bc.completed_at - bc.created_at)))::FLOAT as avg_duration_seconds,
        (COUNT(*) FILTER (WHERE bc.status = 'completed')::FLOAT / NULLIF(COUNT(*), 0))::FLOAT as success_rate
    FROM backup_catalog bc
    WHERE 
        (p_database_type IS NULL OR bc.database_type = p_database_type)
        AND bc.created_at >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY bc.database_type;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views
-- ============================================================================

-- View for recent backups
CREATE OR REPLACE VIEW recent_backups AS
SELECT 
    id,
    database_type,
    backup_type,
    status,
    created_at,
    completed_at,
    size_bytes,
    compressed_size_bytes,
    ROUND((1.0 - compressed_size_bytes::FLOAT / NULLIF(size_bytes, 0)) * 100, 2) as compression_ratio_pct,
    EXTRACT(EPOCH FROM (completed_at - created_at)) as duration_seconds
FROM backup_catalog
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- View for backup health
CREATE OR REPLACE VIEW backup_health AS
SELECT 
    database_type,
    COUNT(*) as total_backups_24h,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_backups,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_backups,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))), 2) as avg_duration_seconds,
    MAX(created_at) as last_backup_time
FROM backup_catalog
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY database_type;

-- ============================================================================
-- Grants (adjust as needed for your security model)
-- ============================================================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA data_mgmt TO PUBLIC;

-- Grant select on all tables to read-only role (create role if needed)
-- GRANT SELECT ON ALL TABLES IN SCHEMA data_mgmt TO readonly_role;

-- ============================================================================
-- Initial Data
-- ============================================================================

-- Insert default backup schedule for MAHOUN
INSERT INTO backup_schedules (name, databases, backup_type, cron_schedule, retention_days, created_by)
VALUES 
    ('daily_full_backup', ARRAY['postgresql', 'neo4j', 'redis', 'chromadb', 'elasticsearch'], 'full', '0 2 * * *', 7, 'system'),
    ('hourly_incremental_backup', ARRAY['postgresql', 'neo4j'], 'incremental', '0 * * * *', 2, 'system')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- End of Migration
-- ============================================================================

COMMENT ON SCHEMA data_mgmt IS 'MAHOUN Data Management System schema - v1.0.0';


-- ============================================================

-- File: deployment/docker/init-db.sql
-- ------------------------------------------------------------
-- ============================================================================
-- MAHOUN v1.0 - PostgreSQL Initialization Script
-- ============================================================================
-- Creates tables for users, audit logs, sessions, and metadata

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Users Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('admin', 'analyst', 'viewer'))
);

-- ============================================================================
-- API Keys Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used TIMESTAMP
);

-- ============================================================================
-- Sessions Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true
);

-- ============================================================================
-- Audit Logs Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    request_id UUID NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    query_text TEXT,
    context_used TEXT,
    answer_generated TEXT,
    citations JSONB,
    nli_verification JSONB,
    hallucination_check JSONB,
    uncertainty_score FLOAT,
    latency_ms INTEGER,
    status_code INTEGER,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_request_id ON audit_logs(request_id);

-- ============================================================================
-- Documents Metadata Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT,
    law_type VARCHAR(100),
    law_id VARCHAR(100),
    case_id VARCHAR(100),
    date_published DATE,
    date_revoked DATE,
    is_active BOOLEAN DEFAULT true,
    source VARCHAR(255),
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_doc_id ON documents_metadata(doc_id);
CREATE INDEX idx_documents_law_id ON documents_metadata(law_id);
CREATE INDEX idx_documents_is_active ON documents_metadata(is_active);

-- ============================================================================
-- Feedback Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    request_id UUID,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    is_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- System Metrics Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    tags JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_name_timestamp ON system_metrics(metric_name, timestamp);

-- ============================================================================
-- Create default admin user (password: admin123 - CHANGE THIS!)
-- ============================================================================
INSERT INTO users (username, email, hashed_password, full_name, role, is_verified)
VALUES (
    'admin',
    'admin@mahoun.ai',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWU7u3oi',  -- admin123
    'System Administrator',
    'admin',
    true
) ON CONFLICT (username) DO NOTHING;

-- ============================================================================
-- Create updated_at trigger function
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to documents_metadata table
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Grant permissions
-- ============================================================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mahoun;


-- ============================================================

-- File: pipelines/data_prep_advanced/indexing_schema.sql
-- ------------------------------------------------------------
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


-- ============================================================

-- File: scripts/init_db.sql
-- ------------------------------------------------------------
-- Removed redundant baseline section to favor advanced schema below.
-- File: scripts/init_db_advanced.sql
-- ------------------------------------------------------------
-- ============================================================================
-- MAHOUN Advanced Database Schema
-- ============================================================================
-- Enterprise-grade PostgreSQL schema with:
-- - Partitioning for scalability
-- - Advanced indexing (GiST, GIN, BRIN)
-- - Full-text search with custom dictionaries
-- - Row-level security
-- - Materialized views for analytics
-- - Audit trails with temporal tables
-- - Performance optimization
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Trigram text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- Multi-column GIN indexes
CREATE EXTENSION IF NOT EXISTS "btree_gist";     -- Multi-column GiST indexes
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- Encryption functions
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- Query performance
CREATE EXTENSION IF NOT EXISTS "tablefunc";      -- Crosstab functions
CREATE EXTENSION IF NOT EXISTS "hstore";         -- Key-value store
CREATE EXTENSION IF NOT EXISTS "vector";         -- pgvector for embeddings

-- Create schemas with proper organization
CREATE SCHEMA IF NOT EXISTS legal;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS cache;
CREATE SCHEMA IF NOT EXISTS migration;

-- Set default search path
SET search_path TO legal, public;

-- ============================================================================
-- Custom Types and Domains
-- ============================================================================

-- Status enum
CREATE TYPE legal.status_type AS ENUM (
    'draft', 'active', 'amended', 'repealed', 'suspended'
);

-- Document type enum
CREATE TYPE legal.document_type AS ENUM (
    'law', 'regulation', 'decree', 'circular', 'guideline', 'other'
);

-- Court type enum
CREATE TYPE legal.court_type AS ENUM (
    'supreme', 'appeal', 'general', 'revolutionary', 'administrative', 'military'
);

-- Case result enum
CREATE TYPE legal.case_result AS ENUM (
    'accepted', 'rejected', 'partially_accepted', 'dismissed', 'pending'
);

-- User role enum
CREATE TYPE legal.user_role AS ENUM (
    'admin', 'editor', 'viewer', 'api_user', 'analyst'
);

-- Domain for Persian text (ensures proper encoding)
CREATE DOMAIN legal.persian_text AS TEXT
    CHECK (VALUE ~ '^[\u0600-\u06FF\s\d\p{P}]+$' OR VALUE IS NULL);

-- Domain for email
CREATE DOMAIN legal.email AS VARCHAR(255)
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- ============================================================================
-- Core Legal Tables with Advanced Features
-- ============================================================================

-- Laws table with partitioning by approval year
CREATE TABLE IF NOT EXISTS legal.laws (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    name_en VARCHAR(500),
    name_normalized VARCHAR(500) GENERATED ALWAYS AS (
        lower(regexp_replace(name, '\s+', ' ', 'g'))
    ) STORED,
    law_number VARCHAR(100) UNIQUE,
    approval_date DATE NOT NULL,
    publication_date DATE,
    effective_date DATE,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    status legal.status_type DEFAULT 'active',
    full_text TEXT,
    full_text_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(full_text, ''))
    ) STORED,
    summary TEXT,
    keywords TEXT[],
    related_laws UUID[],
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER,
    
    -- Constraints
    CONSTRAINT laws_dates_check CHECK (
        approval_date <= COALESCE(publication_date, approval_date) AND
        approval_date <= COALESCE(effective_date, approval_date)
    ),
    CONSTRAINT laws_version_check CHECK (version > 0)
) PARTITION BY RANGE (approval_date);

-- Create partitions for laws by decade
CREATE TABLE legal.laws_before_2000 PARTITION OF legal.laws
    FOR VALUES FROM (MINVALUE) TO ('2000-01-01');
    
CREATE TABLE legal.laws_2000_2010 PARTITION OF legal.laws
    FOR VALUES FROM ('2000-01-01') TO ('2010-01-01');
    
CREATE TABLE legal.laws_2010_2020 PARTITION OF legal.laws
    FOR VALUES FROM ('2010-01-01') TO ('2020-01-01');
    
CREATE TABLE legal.laws_2020_onwards PARTITION OF legal.laws
    FOR VALUES FROM ('2020-01-01') TO (MAXVALUE);


-- Articles table with advanced features
CREATE TABLE IF NOT EXISTS legal.articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    law_id UUID NOT NULL,
    article_number VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(content, ''))
    ) STORED,
    notes TEXT,
    chapter VARCHAR(200),
    section VARCHAR(200),
    order_index INTEGER NOT NULL,
    embedding vector(1024),  -- BGE-M3 embeddings
    embedding_model VARCHAR(100) DEFAULT 'bge-m3',
    embedding_updated_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key with cascade
    CONSTRAINT fk_articles_law FOREIGN KEY (law_id) 
        REFERENCES legal.laws(id) ON DELETE CASCADE,
    
    -- Unique constraint
    CONSTRAINT unique_article_per_law UNIQUE (law_id, article_number),
    
    -- Check constraints
    CONSTRAINT articles_order_check CHECK (order_index > 0),
    CONSTRAINT articles_version_check CHECK (version > 0)
);

-- Verdicts table with partitioning by year
CREATE TABLE IF NOT EXISTS legal.verdicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verdict_number VARCHAR(100) NOT NULL,
    case_number VARCHAR(100) NOT NULL,
    court_name VARCHAR(200) NOT NULL,
    court_type legal.court_type NOT NULL,
    branch_number INTEGER,
    verdict_date DATE NOT NULL,
    case_type VARCHAR(100),
    subject VARCHAR(500),
    summary TEXT,
    summary_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(summary, ''))
    ) STORED,
    full_text TEXT,
    full_text_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(full_text, ''))
    ) STORED,
    result legal.case_result,
    judges TEXT[],
    parties JSONB DEFAULT '{}',  -- plaintiff, defendant info
    embedding vector(1024),
    embedding_model VARCHAR(100) DEFAULT 'bge-m3',
    embedding_updated_at TIMESTAMP,
    cited_articles UUID[],
    cited_laws UUID[],
    precedent_verdicts UUID[],
    metadata JSONB DEFAULT '{}',
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    is_precedent BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT verdicts_date_check CHECK (verdict_date <= CURRENT_DATE),
    CONSTRAINT unique_verdict_number UNIQUE (verdict_number)
) PARTITION BY RANGE (verdict_date);

-- Create partitions for verdicts by year
CREATE TABLE legal.verdicts_before_2020 PARTITION OF legal.verdicts
    FOR VALUES FROM (MINVALUE) TO ('2020-01-01');
    
CREATE TABLE legal.verdicts_2020 PARTITION OF legal.verdicts
    FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
    
CREATE TABLE legal.verdicts_2021 PARTITION OF legal.verdicts
    FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
    
CREATE TABLE legal.verdicts_2022 PARTITION OF legal.verdicts
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
    
CREATE TABLE legal.verdicts_2023 PARTITION OF legal.verdicts
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
    
CREATE TABLE legal.verdicts_2024_onwards PARTITION OF legal.verdicts
    FOR VALUES FROM ('2024-01-01') TO (MAXVALUE);

-- Citations table with relationship strength
CREATE TABLE IF NOT EXISTS legal.citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verdict_id UUID NOT NULL,
    article_id UUID NOT NULL,
    context TEXT,
    context_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(context, ''))
    ) STORED,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
    citation_type VARCHAR(50) DEFAULT 'direct',  -- direct, indirect, reference
    relevance_score FLOAT CHECK (relevance_score BETWEEN 0 AND 1),
    extracted_by VARCHAR(50) DEFAULT 'manual',  -- manual, nlp, hybrid
    verified BOOLEAN DEFAULT FALSE,
    verified_by INTEGER,
    verified_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_citations_verdict FOREIGN KEY (verdict_id)
        REFERENCES legal.verdicts(id) ON DELETE CASCADE,
    CONSTRAINT fk_citations_article FOREIGN KEY (article_id)
        REFERENCES legal.articles(id) ON DELETE CASCADE,
    
    -- Unique constraint
    CONSTRAINT unique_citation UNIQUE (verdict_id, article_id)
);


-- Documents table with full-text search
CREATE TABLE IF NOT EXISTS legal.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    title_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(title, ''))
    ) STORED,
    doc_type legal.document_type NOT NULL,
    content TEXT NOT NULL,
    content_tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('persian', coalesce(content, ''))
    ) STORED,
    source VARCHAR(200),
    url TEXT,
    file_path TEXT,
    file_hash VARCHAR(64),  -- SHA256
    file_size_bytes BIGINT,
    language VARCHAR(10) DEFAULT 'fa',
    embedding vector(1024),
    embedding_model VARCHAR(100) DEFAULT 'bge-m3',
    embedding_updated_at TIMESTAMP,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    view_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT documents_file_size_check CHECK (file_size_bytes >= 0),
    CONSTRAINT documents_view_count_check CHECK (view_count >= 0)
);

-- ============================================================================
-- User Management with Row-Level Security
-- ============================================================================

-- Users table with enhanced security
CREATE TABLE IF NOT EXISTS legal.users (
    id SERIAL PRIMARY KEY,
    email legal.email UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role legal.user_role DEFAULT 'viewer',
    department VARCHAR(100),
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    failed_login_attempts INTEGER DEFAULT 0,
    last_failed_login TIMESTAMP,
    account_locked_until TIMESTAMP,
    password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    must_change_password BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    last_activity TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT users_failed_attempts_check CHECK (failed_login_attempts >= 0),
    CONSTRAINT users_username_length CHECK (length(username) >= 3)
);

-- API Keys table with rate limiting
CREATE TABLE IF NOT EXISTS legal.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES legal.users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,  -- First chars for identification
    name VARCHAR(100),
    description TEXT,
    scopes TEXT[] DEFAULT ARRAY['read'],  -- read, write, admin
    rate_limit_per_hour INTEGER DEFAULT 1000,
    rate_limit_per_day INTEGER DEFAULT 10000,
    requests_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    ip_whitelist INET[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT api_keys_rate_limit_check CHECK (
        rate_limit_per_hour > 0 AND rate_limit_per_day > 0
    )
);

-- Sessions table for tracking
CREATE TABLE IF NOT EXISTS legal.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES legal.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB DEFAULT '{}',
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Audit and Logging with Temporal Tables
-- ============================================================================

-- Comprehensive audit logs
CREATE TABLE IF NOT EXISTS audit.logs (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES legal.users(id),
    session_id UUID REFERENCES legal.sessions(id),
    action VARCHAR(50) NOT NULL,  -- SELECT, INSERT, UPDATE, DELETE, API_CALL
    table_name VARCHAR(100),
    record_id UUID,
    endpoint VARCHAR(200),
    method VARCHAR(10),
    query_text TEXT,
    query_params JSONB DEFAULT '{}',
    answer_generated TEXT,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    latency_ms INTEGER,
    status_code INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Partitioning key
    log_date DATE GENERATED ALWAYS AS (created_at::DATE) STORED
) PARTITION BY RANGE (log_date);

-- Create monthly partitions for audit logs
CREATE TABLE audit.logs_2024_01 PARTITION OF audit.logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE audit.logs_2024_02 PARTITION OF audit.logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- Add more partitions as needed

-- Query history with analytics
CREATE TABLE IF NOT EXISTS audit.query_history (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES legal.users(id),
    query TEXT NOT NULL,
    query_hash VARCHAR(64) GENERATED ALWAYS AS (
        encode(digest(query, 'sha256'), 'hex')
    ) STORED,
    query_type VARCHAR(50),  -- semantic, keyword, hybrid
    results_count INTEGER,
    top_result_id UUID,
    execution_time_ms INTEGER,
    retrieval_strategy VARCHAR(50),
    reranking_applied BOOLEAN DEFAULT FALSE,
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Partitioning
    query_date DATE GENERATED ALWAYS AS (created_at::DATE) STORED
) PARTITION BY RANGE (query_date);


-- ============================================================================
-- Advanced Indexes for Performance
-- ============================================================================

-- Laws indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_name_gin 
    ON legal.laws USING gin(name gin_trgm_ops);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_name_normalized 
    ON legal.laws(name_normalized);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_category 
    ON legal.laws(category, subcategory);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_status 
    ON legal.laws(status) WHERE NOT is_deleted;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_approval_date 
    ON legal.laws(approval_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_full_text_tsv 
    ON legal.laws USING gin(full_text_tsv);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_keywords 
    ON legal.laws USING gin(keywords);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_laws_metadata 
    ON legal.laws USING gin(metadata jsonb_path_ops);

-- Articles indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_law_id 
    ON legal.articles(law_id) WHERE NOT is_deleted;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_number 
    ON legal.articles(article_number);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_content_tsv 
    ON legal.articles USING gin(content_tsv);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_embedding 
    ON legal.articles USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- For vector similarity search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_chapter_section 
    ON legal.articles(chapter, section);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_order 
    ON legal.articles(law_id, order_index);

-- Verdicts indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_number 
    ON legal.verdicts(verdict_number);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_case_number 
    ON legal.verdicts(case_number);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_date 
    ON legal.verdicts(verdict_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_court 
    ON legal.verdicts(court_name, court_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_type 
    ON legal.verdicts(case_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_result 
    ON legal.verdicts(result);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_full_text_tsv 
    ON legal.verdicts USING gin(full_text_tsv);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_embedding 
    ON legal.verdicts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_precedent 
    ON legal.verdicts(is_precedent) WHERE is_precedent = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_verdicts_cited_articles 
    ON legal.verdicts USING gin(cited_articles);

-- Citations indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_citations_verdict 
    ON legal.citations(verdict_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_citations_article 
    ON legal.citations(article_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_citations_confidence 
    ON legal.citations(confidence DESC) WHERE verified = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_citations_type 
    ON legal.citations(citation_type);

-- Documents indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_type 
    ON legal.documents(doc_type) WHERE NOT is_deleted;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_title_tsv 
    ON legal.documents USING gin(title_tsv);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_content_tsv 
    ON legal.documents USING gin(content_tsv);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_embedding 
    ON legal.documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_tags 
    ON legal.documents USING gin(tags);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_public 
    ON legal.documents(is_public) WHERE is_public = TRUE;

-- User indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email 
    ON legal.users(email) WHERE is_active = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role 
    ON legal.users(role) WHERE is_active = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_activity 
    ON legal.users(last_activity DESC);

-- API Keys indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_user 
    ON legal.api_keys(user_id) WHERE is_active = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_prefix 
    ON legal.api_keys(key_prefix);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_expires 
    ON legal.api_keys(expires_at) WHERE is_active = TRUE;

-- Audit indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user 
    ON audit.logs(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_action 
    ON audit.logs(action, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_endpoint 
    ON audit.logs(endpoint);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_status 
    ON audit.logs(status_code);

-- Query history indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_history_user 
    ON audit.query_history(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_history_hash 
    ON audit.query_history(query_hash);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_query_history_type 
    ON audit.query_history(query_type);


-- ============================================================================
-- Materialized Views for Analytics
-- ============================================================================

-- Law statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.law_statistics AS
SELECT 
    category,
    subcategory,
    status,
    COUNT(*) as law_count,
    COUNT(*) FILTER (WHERE approval_date >= CURRENT_DATE - INTERVAL '1 year') as recent_laws,
    AVG(EXTRACT(YEAR FROM approval_date)) as avg_approval_year,
    MIN(approval_date) as oldest_law_date,
    MAX(approval_date) as newest_law_date
FROM legal.laws
WHERE NOT is_deleted
GROUP BY category, subcategory, status;

CREATE UNIQUE INDEX ON analytics.law_statistics(category, subcategory, status);

-- Citation network analysis
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.citation_network AS
SELECT 
    a.law_id,
    l.name as law_name,
    COUNT(DISTINCT c.verdict_id) as citation_count,
    COUNT(DISTINCT c.id) FILTER (WHERE c.verified = TRUE) as verified_citations,
    AVG(c.confidence) as avg_confidence,
    ARRAY_AGG(DISTINCT v.court_type) as citing_court_types,
    MAX(v.verdict_date) as latest_citation_date
FROM legal.articles a
JOIN legal.laws l ON a.law_id = l.id
LEFT JOIN legal.citations c ON a.id = c.article_id
LEFT JOIN legal.verdicts v ON c.verdict_id = v.id
WHERE NOT a.is_deleted AND NOT l.is_deleted
GROUP BY a.law_id, l.name;

CREATE UNIQUE INDEX ON analytics.citation_network(law_id);

-- Popular queries
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.popular_queries AS
SELECT 
    query_hash,
    query,
    query_type,
    COUNT(*) as query_count,
    AVG(execution_time_ms) as avg_execution_time,
    AVG(results_count) as avg_results_count,
    AVG(user_feedback) FILTER (WHERE user_feedback IS NOT NULL) as avg_feedback,
    MAX(created_at) as last_queried_at
FROM audit.query_history
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY query_hash, query, query_type
HAVING COUNT(*) >= 5
ORDER BY query_count DESC
LIMIT 1000;

CREATE UNIQUE INDEX ON analytics.popular_queries(query_hash);

-- ============================================================================
-- Advanced Functions and Triggers
-- ============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Audit trail function
CREATE OR REPLACE FUNCTION audit_trail()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit.logs (action, table_name, record_id, metadata)
        VALUES ('INSERT', TG_TABLE_NAME, NEW.id, row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.logs (action, table_name, record_id, metadata)
        VALUES ('UPDATE', TG_TABLE_NAME, NEW.id, 
                jsonb_build_object('old', row_to_json(OLD), 'new', row_to_json(NEW)));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit.logs (action, table_name, record_id, metadata)
        VALUES ('DELETE', TG_TABLE_NAME, OLD.id, row_to_json(OLD)::jsonb);
        RETURN OLD;
    END IF;
END;
$$ language 'plpgsql';

-- Increment view count
CREATE OR REPLACE FUNCTION increment_view_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE legal.documents
    SET view_count = view_count + 1
    WHERE id = NEW.record_id AND NEW.action = 'SELECT';
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Validate embedding dimension
CREATE OR REPLACE FUNCTION validate_embedding_dimension()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.embedding IS NOT NULL AND array_length(NEW.embedding, 1) != 1024 THEN
        RAISE EXCEPTION 'Embedding must be 1024-dimensional';
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_laws_updated_at 
    BEFORE UPDATE ON legal.laws
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_articles_updated_at 
    BEFORE UPDATE ON legal.articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_verdicts_updated_at 
    BEFORE UPDATE ON legal.verdicts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON legal.documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON legal.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply audit triggers (optional - can be heavy)
-- CREATE TRIGGER audit_laws AFTER INSERT OR UPDATE OR DELETE ON legal.laws
--     FOR EACH ROW EXECUTE FUNCTION audit_trail();

-- Apply embedding validation
CREATE TRIGGER validate_article_embedding 
    BEFORE INSERT OR UPDATE ON legal.articles
    FOR EACH ROW WHEN (NEW.embedding IS NOT NULL)
    EXECUTE FUNCTION validate_embedding_dimension();

CREATE TRIGGER validate_verdict_embedding 
    BEFORE INSERT OR UPDATE ON legal.verdicts
    FOR EACH ROW WHEN (NEW.embedding IS NOT NULL)
    EXECUTE FUNCTION validate_embedding_dimension();

-- ============================================================================
-- Row-Level Security (RLS)
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE legal.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal.api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY users_select_own ON legal.users
    FOR SELECT
    USING (id = current_setting('app.current_user_id')::INTEGER);

-- Admins can see all users
CREATE POLICY users_select_admin ON legal.users
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM legal.users
            WHERE id = current_setting('app.current_user_id')::INTEGER
            AND role = 'admin'
        )
    );

-- API keys policy
CREATE POLICY api_keys_select_own ON legal.api_keys
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

-- Audit logs policy
CREATE POLICY audit_logs_select_own ON audit.logs
    FOR SELECT
    USING (
        user_id = current_setting('app.current_user_id')::INTEGER
        OR EXISTS (
            SELECT 1 FROM legal.users
            WHERE id = current_setting('app.current_user_id')::INTEGER
            AND role IN ('admin', 'analyst')
        )
    );

-- ============================================================================
-- Performance Optimization
-- ============================================================================

-- Analyze tables for query planner
ANALYZE legal.laws;
ANALYZE legal.articles;
ANALYZE legal.verdicts;
ANALYZE legal.citations;
ANALYZE legal.documents;

-- Set statistics targets for better query planning
ALTER TABLE legal.laws ALTER COLUMN name SET STATISTICS 1000;
ALTER TABLE legal.articles ALTER COLUMN content SET STATISTICS 1000;
ALTER TABLE legal.verdicts ALTER COLUMN full_text SET STATISTICS 1000;

-- ============================================================================
-- Sample Data and Initial Setup
-- ============================================================================

-- Insert admin user
INSERT INTO legal.users (email, username, password_hash, full_name, role, is_verified)
VALUES (
    'admin@mahoun.ai',
    'admin',
    crypt('Admin@123456', gen_salt('bf', 12)),
    'System Administrator',
    'admin',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Grant permissions
GRANT USAGE ON SCHEMA legal TO mahoun;
GRANT USAGE ON SCHEMA audit TO mahoun;
GRANT USAGE ON SCHEMA analytics TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO mahoun;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO mahoun;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✅ MAHOUN Advanced Database Schema Initialized Successfully!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '📊 Schemas: legal, audit, analytics, cache, migration';
    RAISE NOTICE '📋 Tables: laws (partitioned), articles, verdicts (partitioned), citations';
    RAISE NOTICE '🔐 Security: Row-Level Security enabled, encrypted passwords';
    RAISE NOTICE '📈 Analytics: Materialized views for statistics and insights';
    RAISE NOTICE '⚡ Performance: Advanced indexes (GIN, GiST, IVFFlat for vectors)';
    RAISE NOTICE '🔍 Search: Full-text search with Persian support';
    RAISE NOTICE '👤 Default Admin: admin@mahoun.ai / Admin@123456';
    RAISE NOTICE '============================================================================';
END $$;


-- ============================================================

-- File: scripts/migrations/000_initial_schema.sql
-- ------------------------------------------------------------
-- Migration 000: Initial Schema Setup
-- ====================================
-- Creates base schemas and essential tables
-- 
-- Author: MAHOUN Team
-- Date: 2024-01-01

BEGIN;

-- ============================================================================
-- 1. Enable Required Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- 2. Create Schemas
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS legal;
CREATE SCHEMA IF NOT EXISTS audit;

COMMENT ON SCHEMA legal IS 'Legal documents and knowledge base';
COMMENT ON SCHEMA audit IS 'Audit logs and query history';

-- ============================================================================
-- 3. Create Update Timestamp Function
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_column IS 'Auto-update updated_at timestamp';

-- ============================================================================
-- 4. Query History Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit.query_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Query info
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    
    -- Response info
    response_text TEXT,
    response_time_ms INTEGER,
    status VARCHAR(50) DEFAULT 'success',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT valid_response_time CHECK (response_time_ms >= 0)
);

-- Indexes
CREATE INDEX idx_query_history_created ON audit.query_history(created_at DESC);
CREATE INDEX idx_query_history_user ON audit.query_history(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_query_history_session ON audit.query_history(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_query_history_status ON audit.query_history(status);
CREATE INDEX idx_query_history_hash ON audit.query_history(query_hash) WHERE query_hash IS NOT NULL;

COMMENT ON TABLE audit.query_history IS 'Query and response history for analytics';

-- ============================================================================
-- 5. Documents Table (Base)
-- ============================================================================

-- Removed redundant baseline documents table to favor advanced schema above.
    
    -- Full-text search
    search_vector tsvector
);

-- Indexes
CREATE INDEX idx_documents_type ON legal.documents(document_type);
CREATE INDEX idx_documents_created ON legal.documents(created_at DESC);
CREATE INDEX idx_documents_search ON legal.documents USING gin(search_vector);

-- Trigger for search vector
CREATE TRIGGER update_documents_search_vector
BEFORE INSERT OR UPDATE ON legal.documents
FOR EACH ROW
EXECUTE FUNCTION tsvector_update_trigger(search_vector, 'pg_catalog.english', title, content);

-- Trigger for updated_at
CREATE TRIGGER update_documents_updated_at
BEFORE UPDATE ON legal.documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE legal.documents IS 'Base table for all legal documents';

-- ============================================================================
-- 6. Grant Permissions
-- ============================================================================

GRANT ALL PRIVILEGES ON SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON SCHEMA audit TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO mahoun;

-- ============================================================================
-- Success Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 000 completed successfully!';
    RAISE NOTICE '📦 Created schemas: legal, audit';
    RAISE NOTICE '📊 Created tables: query_history, documents';
    RAISE NOTICE '🔧 Enabled extensions: uuid-ossp, pg_trgm, vector';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Ready for migration 001 (Hybrid RAG Support)';
END $$;

COMMIT;


-- ============================================================

-- File: scripts/migrations/001_hybrid_rag_support.sql
-- ------------------------------------------------------------
-- Migration 001: Hybrid RAG Support
-- ===================================
-- Adds complete support for Hybrid RAG system
-- 
-- Changes:
-- 1. Add chunks table for document chunking
-- 2. Add entities table for NER results
-- 3. Add search_scores table for caching
-- 4. Enhance query_history with RAG metrics
-- 5. Add hybrid_search function
--
-- Author: MAHOUN Team
-- Date: 2024-01-01

BEGIN;

-- ============================================================================
-- 1. Chunks Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal.chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Parent reference (flexible for any document type)
    document_id UUID,
    parent_type VARCHAR(50) NOT NULL,  -- 'law', 'article', 'verdict', 'document'
    parent_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Content
    text TEXT NOT NULL,
    embedding VECTOR(1024),
    start_pos INTEGER,
    end_pos INTEGER,
    
    -- Chunking metadata
    coherence_score FLOAT,
    entity_count INTEGER DEFAULT 0,
    semantic_density FLOAT,
    
    -- Graph features (computed by graph analytics)
    pagerank_score FLOAT DEFAULT 0.0,
    centrality_score FLOAT DEFAULT 0.0,
    community_id INTEGER,
    authority_score FLOAT DEFAULT 0.0,
    
    -- General metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_chunk UNIQUE(parent_type, parent_id, chunk_index)
);

-- Indexes for chunks
CREATE INDEX idx_chunks_parent ON legal.chunks(parent_type, parent_id);
CREATE INDEX idx_chunks_document ON legal.chunks(document_id) WHERE document_id IS NOT NULL;
CREATE INDEX idx_chunks_pagerank ON legal.chunks(pagerank_score DESC);
CREATE INDEX idx_chunks_community ON legal.chunks(community_id) WHERE community_id IS NOT NULL;
CREATE INDEX idx_chunks_text_search ON legal.chunks USING gin(to_tsvector('english', text));

-- Note: Vector index requires pgvector extension
-- CREATE INDEX idx_chunks_embedding ON legal.chunks USING ivfflat (embedding vector_cosine_ops);

COMMENT ON TABLE legal.chunks IS 'Document chunks for RAG retrieval';
COMMENT ON COLUMN legal.chunks.parent_type IS 'Type of parent document: law, article, verdict, document';
COMMENT ON COLUMN legal.chunks.coherence_score IS 'Semantic coherence score from chunker';
COMMENT ON COLUMN legal.chunks.pagerank_score IS 'PageRank score from graph analytics';

-- ============================================================================
-- 2. Entities Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES legal.chunks(id) ON DELETE CASCADE,
    
    -- Entity data
    text VARCHAR(500) NOT NULL,
    label VARCHAR(50) NOT NULL,  -- COURT, ARTICLE, LAW_NAME, PERSON, etc.
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    
    -- Optional embedding for entity
    embedding VECTOR(1024),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_positions CHECK (end_pos > start_pos),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- Indexes for entities
CREATE INDEX idx_entities_chunk ON legal.entities(chunk_id);
CREATE INDEX idx_entities_label ON legal.entities(label);
CREATE INDEX idx_entities_text ON legal.entities USING gin(text gin_trgm_ops);
CREATE INDEX idx_entities_confidence ON legal.entities(confidence DESC);

COMMENT ON TABLE legal.entities IS 'Named entities extracted from chunks';
COMMENT ON COLUMN legal.entities.label IS 'Entity type: COURT, ARTICLE, LAW_NAME, PERSON, etc.';

-- ============================================================================
-- 3. Search Scores Table (for caching)
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal.search_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES legal.chunks(id) ON DELETE CASCADE,
    query_hash VARCHAR(64) NOT NULL,  -- MD5 hash of query
    
    -- Individual scores
    bm25_score FLOAT,
    dense_score FLOAT,
    hybrid_score FLOAT,
    gat_score FLOAT,
    graph_score FLOAT,
    
    -- Final ranking
    final_rank INTEGER,
    final_score FLOAT,
    
    -- TTL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    
    UNIQUE(chunk_id, query_hash)
);

-- Indexes for search scores
CREATE INDEX idx_search_scores_query ON legal.search_scores(query_hash);
CREATE INDEX idx_search_scores_expires ON legal.search_scores(expires_at);
CREATE INDEX idx_search_scores_rank ON legal.search_scores(query_hash, final_rank);

COMMENT ON TABLE legal.search_scores IS 'Cached search scores for performance';
COMMENT ON COLUMN legal.search_scores.query_hash IS 'MD5 hash of normalized query';

-- Auto-cleanup expired scores
CREATE OR REPLACE FUNCTION legal.cleanup_expired_scores()
RETURNS void AS $$
BEGIN
    DELETE FROM legal.search_scores WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. Enhance Query History
-- ============================================================================

-- Add new columns to query_history
ALTER TABLE audit.query_history 
    ADD COLUMN IF NOT EXISTS retrieval_method VARCHAR(50),
    ADD COLUMN IF NOT EXISTS bm25_count INTEGER,
    ADD COLUMN IF NOT EXISTS dense_count INTEGER,
    ADD COLUMN IF NOT EXISTS reranked_count INTEGER,
    ADD COLUMN IF NOT EXISTS graph_enriched BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS avg_confidence FLOAT,
    ADD COLUMN IF NOT EXISTS top_chunks JSONB;

COMMENT ON COLUMN audit.query_history.retrieval_method IS 'Method used: bm25, dense, hybrid, graph';
COMMENT ON COLUMN audit.query_history.top_chunks IS 'Top 5 chunk IDs returned';

-- ============================================================================
-- 5. Views for Easy Querying
-- ============================================================================

-- View: Searchable chunks with entity info
CREATE OR REPLACE VIEW legal.searchable_chunks AS
SELECT 
    c.id,
    c.parent_type,
    c.parent_id,
    c.chunk_index,
    c.text,
    c.embedding,
    c.pagerank_score,
    c.authority_score,
    c.coherence_score,
    c.metadata,
    ARRAY_AGG(DISTINCT e.label) FILTER (WHERE e.label IS NOT NULL) as entity_labels,
    COUNT(DISTINCT e.id) as entity_count,
    ARRAY_AGG(DISTINCT e.text) FILTER (WHERE e.text IS NOT NULL) as entity_texts
FROM legal.chunks c
LEFT JOIN legal.entities e ON e.chunk_id = c.id
GROUP BY c.id;

COMMENT ON VIEW legal.searchable_chunks IS 'Chunks with aggregated entity information';

-- View: Chunk statistics
CREATE OR REPLACE VIEW legal.chunk_statistics AS
SELECT 
    parent_type,
    COUNT(*) as total_chunks,
    AVG(LENGTH(text)) as avg_chunk_length,
    AVG(entity_count) as avg_entities_per_chunk,
    AVG(coherence_score) as avg_coherence,
    AVG(pagerank_score) as avg_pagerank
FROM legal.chunks
GROUP BY parent_type;

COMMENT ON VIEW legal.chunk_statistics IS 'Statistics about chunks by parent type';

-- ============================================================================
-- 6. Hybrid Search Function
-- ============================================================================

CREATE OR REPLACE FUNCTION legal.hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1024) DEFAULT NULL,
    top_k INTEGER DEFAULT 10,
    bm25_weight FLOAT DEFAULT 0.4,
    dense_weight FLOAT DEFAULT 0.4,
    graph_weight FLOAT DEFAULT 0.2,
    min_score FLOAT DEFAULT 0.0
)
RETURNS TABLE (
    chunk_id UUID,
    text TEXT,
    parent_type VARCHAR(50),
    parent_id UUID,
    bm25_score FLOAT,
    dense_score FLOAT,
    graph_score FLOAT,
    hybrid_score FLOAT,
    entity_labels TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH bm25_results AS (
        SELECT 
            id,
            ts_rank(to_tsvector('persian', text), plainto_tsquery('persian', query_text)) as score
        FROM legal.chunks
        WHERE to_tsvector('persian', text) @@ plainto_tsquery('persian', query_text)
    ),
    dense_results AS (
        SELECT 
            id,
            CASE 
                WHEN query_embedding IS NOT NULL AND embedding IS NOT NULL 
                THEN 1 - (embedding <=> query_embedding)
                ELSE 0.0
            END as score
        FROM legal.chunks
        WHERE query_embedding IS NOT NULL AND embedding IS NOT NULL
        ORDER BY embedding <=> query_embedding
        LIMIT top_k * 3
    ),
    combined AS (
        SELECT 
            c.id,
            c.text,
            c.parent_type,
            c.parent_id,
            COALESCE(b.score, 0.0) as bm25_score,
            COALESCE(d.score, 0.0) as dense_score,
            COALESCE(c.pagerank_score, 0.0) as graph_score,
            (
                COALESCE(b.score, 0.0) * bm25_weight +
                COALESCE(d.score, 0.0) * dense_weight +
                COALESCE(c.pagerank_score, 0.0) * graph_weight
            ) as hybrid_score,
            ARRAY_AGG(DISTINCT e.label) FILTER (WHERE e.label IS NOT NULL) as entity_labels
        FROM legal.chunks c
        LEFT JOIN bm25_results b ON b.id = c.id
        LEFT JOIN dense_results d ON d.id = c.id
        LEFT JOIN legal.entities e ON e.chunk_id = c.id
        WHERE b.id IS NOT NULL OR d.id IS NOT NULL
        GROUP BY c.id, c.text, c.parent_type, c.parent_id, c.pagerank_score, b.score, d.score
    )
    SELECT 
        combined.id,
        combined.text,
        combined.parent_type,
        combined.parent_id,
        combined.bm25_score,
        combined.dense_score,
        combined.graph_score,
        combined.hybrid_score,
        combined.entity_labels
    FROM combined
    WHERE combined.hybrid_score >= min_score
    ORDER BY combined.hybrid_score DESC
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION legal.hybrid_search IS 'Hybrid search combining BM25, dense, and graph scores';

-- ============================================================================
-- 7. Triggers
-- ============================================================================

-- Update entity_count in chunks when entities change
CREATE OR REPLACE FUNCTION legal.update_chunk_entity_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE legal.chunks
    SET entity_count = (
        SELECT COUNT(*) FROM legal.entities WHERE chunk_id = NEW.chunk_id
    )
    WHERE id = NEW.chunk_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_entity_count
AFTER INSERT OR DELETE ON legal.entities
FOR EACH ROW
EXECUTE FUNCTION legal.update_chunk_entity_count();

-- Update updated_at timestamp
CREATE TRIGGER update_chunks_updated_at 
BEFORE UPDATE ON legal.chunks
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 8. Grant Permissions
-- ============================================================================

GRANT ALL PRIVILEGES ON legal.chunks TO mahoun;
GRANT ALL PRIVILEGES ON legal.entities TO mahoun;
GRANT ALL PRIVILEGES ON legal.search_scores TO mahoun;
GRANT SELECT ON legal.searchable_chunks TO mahoun;
GRANT SELECT ON legal.chunk_statistics TO mahoun;

-- ============================================================================
-- Success Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 001 completed successfully!';
    RAISE NOTICE '📊 New tables: chunks, entities, search_scores';
    RAISE NOTICE '🔍 New function: hybrid_search()';
    RAISE NOTICE '📈 Enhanced: query_history';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Next steps:';
    RAISE NOTICE '   1. Run chunking pipeline on existing documents';
    RAISE NOTICE '   2. Extract entities from chunks';
    RAISE NOTICE '   3. Compute graph features (PageRank, etc.)';
    RAISE NOTICE '   4. Test hybrid_search() function';
END $$;

COMMIT;


-- ============================================================
