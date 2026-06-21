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

CREATE TABLE IF NOT EXISTS legal.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Document info
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- 'law', 'verdict', 'article', 'regulation'
    content TEXT,
    
    -- Metadata
    source VARCHAR(255),
    language VARCHAR(10) DEFAULT 'fa',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
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
