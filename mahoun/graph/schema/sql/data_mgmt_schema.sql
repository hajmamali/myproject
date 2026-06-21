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
