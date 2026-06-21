-- MAHOUN Legal Schema Patch
-- Applies missing legal.* tables that failed due to 'persian' FTS config
-- Uses 'simple' text search config as a compatible substitute

-- Ensure extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Ensure schemas
CREATE SCHEMA IF NOT EXISTS legal;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Enums (idempotent)
DO $$ BEGIN
  CREATE TYPE legal.status_type AS ENUM ('draft','active','amended','repealed','suspended');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE legal.document_type AS ENUM ('law','regulation','decree','circular','guideline','other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE legal.court_type AS ENUM ('supreme','appeal','general','revolutionary','administrative','military');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE legal.case_result AS ENUM ('accepted','rejected','partially_accepted','dismissed','pending');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE legal.user_role AS ENUM ('admin','editor','viewer','api_user','analyst');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- legal.laws (no partitioning, no persian FTS generated column)
CREATE TABLE IF NOT EXISTS legal.laws (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    name_en VARCHAR(500),
    law_number VARCHAR(100) UNIQUE,
    approval_date DATE NOT NULL,
    publication_date DATE,
    effective_date DATE,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    status legal.status_type DEFAULT 'active',
    full_text TEXT,
    summary TEXT,
    keywords TEXT[],
    related_laws UUID[],
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    updated_by INTEGER
);

-- legal.articles
CREATE TABLE IF NOT EXISTS legal.articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    law_id UUID NOT NULL,
    article_number VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    notes TEXT,
    chapter VARCHAR(200),
    section VARCHAR(200),
    order_index INTEGER NOT NULL,
    embedding vector(1024),
    embedding_model VARCHAR(100) DEFAULT 'bge-m3',
    embedding_updated_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_articles_law FOREIGN KEY (law_id) REFERENCES legal.laws(id) ON DELETE CASCADE,
    CONSTRAINT unique_article_per_law UNIQUE (law_id, article_number)
);

-- legal.verdicts (no partitioning, no persian FTS generated column)
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
    full_text TEXT,
    result legal.case_result,
    judges TEXT[],
    parties JSONB DEFAULT '{}',
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
    CONSTRAINT unique_verdict_number UNIQUE (verdict_number)
);

-- legal.citations
CREATE TABLE IF NOT EXISTS legal.citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verdict_id UUID NOT NULL,
    article_id UUID NOT NULL,
    context TEXT,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
    citation_type VARCHAR(50) DEFAULT 'direct',
    relevance_score FLOAT CHECK (relevance_score BETWEEN 0 AND 1),
    extracted_by VARCHAR(50) DEFAULT 'manual',
    verified BOOLEAN DEFAULT FALSE,
    verified_by INTEGER,
    verified_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_citations_verdict FOREIGN KEY (verdict_id) REFERENCES legal.verdicts(id) ON DELETE CASCADE,
    CONSTRAINT fk_citations_article FOREIGN KEY (article_id) REFERENCES legal.articles(id) ON DELETE CASCADE,
    CONSTRAINT unique_citation UNIQUE (verdict_id, article_id)
);

-- legal.documents
CREATE TABLE IF NOT EXISTS legal.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    doc_type legal.document_type NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(200),
    url TEXT,
    file_path TEXT,
    file_hash VARCHAR(64),
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- legal.chunks (from migration 001)
CREATE TABLE IF NOT EXISTS legal.chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID,
    parent_type VARCHAR(50) NOT NULL,
    parent_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding VECTOR(1024),
    start_pos INTEGER,
    end_pos INTEGER,
    coherence_score FLOAT,
    entity_count INTEGER DEFAULT 0,
    semantic_density FLOAT,
    pagerank_score FLOAT DEFAULT 0.0,
    centrality_score FLOAT DEFAULT 0.0,
    community_id INTEGER,
    authority_score FLOAT DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_chunk UNIQUE(parent_type, parent_id, chunk_index)
);

-- legal.entities (from migration 001)
CREATE TABLE IF NOT EXISTS legal.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES legal.chunks(id) ON DELETE CASCADE,
    text VARCHAR(500) NOT NULL,
    label VARCHAR(50) NOT NULL,
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    embedding VECTOR(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_positions CHECK (end_pos > start_pos),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- audit.logs (simple version without partitioning)
CREATE TABLE IF NOT EXISTS audit.logs (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID DEFAULT uuid_generate_v4(),
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(100),
    record_id UUID,
    endpoint VARCHAR(200),
    method VARCHAR(10),
    query_text TEXT,
    ip_address INET,
    metadata JSONB DEFAULT '{}',
    latency_ms INTEGER,
    status_code INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- audit.query_history (simple version)
CREATE TABLE IF NOT EXISTS audit.query_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    response_text TEXT,
    response_time_ms INTEGER,
    status VARCHAR(50) DEFAULT 'success',
    retrieval_method VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_verdicts_number ON legal.verdicts(verdict_number);
CREATE INDEX IF NOT EXISTS idx_verdicts_date ON legal.verdicts(verdict_date DESC);
CREATE INDEX IF NOT EXISTS idx_verdicts_court ON legal.verdicts(court_name, court_type);
CREATE INDEX IF NOT EXISTS idx_verdicts_deleted ON legal.verdicts(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_chunks_parent ON legal.chunks(parent_type, parent_id);
CREATE INDEX IF NOT EXISTS idx_entities_chunk ON legal.entities(chunk_id);
CREATE INDEX IF NOT EXISTS idx_laws_category ON legal.laws(category);
CREATE INDEX IF NOT EXISTS idx_articles_law ON legal.articles(law_id);

-- Grants
GRANT USAGE ON SCHEMA legal TO mahoun;
GRANT USAGE ON SCHEMA audit TO mahoun;
GRANT USAGE ON SCHEMA analytics TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA legal TO mahoun;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO mahoun;

DO $$ BEGIN
  RAISE NOTICE '✅ Legal schema patch applied successfully';
  RAISE NOTICE '   Tables: legal.laws, legal.articles, legal.verdicts, legal.citations, legal.documents, legal.chunks, legal.entities';
  RAISE NOTICE '   Tables: audit.logs, audit.query_history';
END $$;
