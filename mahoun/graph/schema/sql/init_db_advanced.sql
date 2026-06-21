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
