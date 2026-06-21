-- MAHOUN Database Initialization
-- ================================
-- PostgreSQL schema for legal documents and metadata

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For indexing

-- Create schemas
CREATE SCHEMA IF NOT EXISTS legal;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path TO legal, public;

-- ============================================================================
-- Legal Documents Tables
-- ============================================================================

-- Laws table
CREATE TABLE IF NOT EXISTS legal.laws (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    name_en VARCHAR(500),
    law_number VARCHAR(100),
    approval_date DATE,
    publication_date DATE,
    category VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    full_text TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Articles table
CREATE TABLE IF NOT EXISTS legal.articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    law_id UUID REFERENCES legal.laws(id) ON DELETE CASCADE,
    article_number VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    notes TEXT,
    order_index INTEGER,
    embedding VECTOR(768),  -- For semantic search
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verdicts table
CREATE TABLE IF NOT EXISTS legal.verdicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verdict_number VARCHAR(100) NOT NULL UNIQUE,
    case_number VARCHAR(100),
    court_name VARCHAR(200),
    court_type VARCHAR(100),
    verdict_date DATE,
    case_type VARCHAR(100),
    subject VARCHAR(500),
    summary TEXT,
    full_text TEXT,
    result VARCHAR(100),
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Citations table (verdicts citing articles)
CREATE TABLE IF NOT EXISTS legal.citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verdict_id UUID REFERENCES legal.verdicts(id) ON DELETE CASCADE,
    article_id UUID REFERENCES legal.articles(id) ON DELETE CASCADE,
    context TEXT,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(verdict_id, article_id)
);

-- Documents table (general legal documents)
CREATE TABLE IF NOT EXISTS legal.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    doc_type VARCHAR(100),
    content TEXT NOT NULL,
    source VARCHAR(200),
    url TEXT,
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- User and Authentication Tables
-- ============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS legal.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- API Keys table
CREATE TABLE IF NOT EXISTS legal.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES legal.users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Audit and Logging Tables
-- ============================================================================

-- Audit logs
CREATE TABLE IF NOT EXISTS audit.logs (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID,
    user_id INTEGER REFERENCES legal.users(id),
    endpoint VARCHAR(200),
    method VARCHAR(10),
    query_text TEXT,
    answer_generated TEXT,
    metadata JSONB DEFAULT '{}',
    latency_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query history
CREATE TABLE IF NOT EXISTS audit.query_history (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES legal.users(id),
    query TEXT NOT NULL,
    results_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Laws indexes
CREATE INDEX IF NOT EXISTS idx_laws_name ON legal.laws USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_laws_category ON legal.laws(category);
CREATE INDEX IF NOT EXISTS idx_laws_status ON legal.laws(status);

-- Articles indexes
CREATE INDEX IF NOT EXISTS idx_articles_law_id ON legal.articles(law_id);
CREATE INDEX IF NOT EXISTS idx_articles_number ON legal.articles(article_number);
CREATE INDEX IF NOT EXISTS idx_articles_content ON legal.articles USING gin(content gin_trgm_ops);

-- Verdicts indexes
CREATE INDEX IF NOT EXISTS idx_verdicts_number ON legal.verdicts(verdict_number);
CREATE INDEX IF NOT EXISTS idx_verdicts_date ON legal.verdicts(verdict_date);
CREATE INDEX IF NOT EXISTS idx_verdicts_court ON legal.verdicts(court_name);
CREATE INDEX IF NOT EXISTS idx_verdicts_type ON legal.verdicts(case_type);

-- Citations indexes
CREATE INDEX IF NOT EXISTS idx_citations_verdict ON legal.citations(verdict_id);
CREATE INDEX IF NOT EXISTS idx_citations_article ON legal.citations(article_id);

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_type ON legal.documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_content ON legal.documents USING gin(content gin_trgm_ops);

-- Audit indexes
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit.logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit.logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_endpoint ON audit.logs(endpoint);

-- ============================================================================
-- Functions and Triggers
-- ============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_laws_updated_at BEFORE UPDATE ON legal.laws
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON legal.articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_verdicts_updated_at BEFORE UPDATE ON legal.verdicts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON legal.documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON legal.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Sample Data (for testing)
-- ============================================================================

-- Insert sample user
INSERT INTO legal.users (email, username, password_hash, full_name, role)
VALUES (
    'admin@mahoun.local',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7qXqKqKqKq',  -- password: admin123
    'System Administrator',
    'admin'
) ON CONFLICT (email) DO NOTHING;

-- Insert sample law
INSERT INTO legal.laws (name, name_en, law_number, category, status)
VALUES (
    'قانون مدنی',
    'Civil Law',
    '1307',
    'civil',
    'active'
) ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO mahoun;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ MAHOUN database initialized successfully!';
    RAISE NOTICE '📊 Schemas: legal, audit';
    RAISE NOTICE '📋 Tables: laws, articles, verdicts, citations, documents, users';
    RAISE NOTICE '🔐 Default user: admin@mahoun.local / admin123';
END $$;
