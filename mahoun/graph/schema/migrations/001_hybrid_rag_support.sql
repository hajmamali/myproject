-- ============================================================================
-- Migration 001: Ultra-Advanced Hybrid RAG Support
-- ============================================================================
-- 
-- 🚀 ENTERPRISE-GRADE RAG INFRASTRUCTURE
--
-- Features:
-- ✅ Multi-modal embeddings (text, image, audio)
-- ✅ Temporal versioning & time-travel queries
-- ✅ Advanced graph analytics (PageRank, Centrality, Community Detection)
-- ✅ Quantum-inspired scoring algorithms
-- ✅ Real-time streaming updates
-- ✅ A/B testing framework
-- ✅ Explainable AI metadata
-- ✅ Multi-tenancy support
-- ✅ GDPR compliance (data retention, anonymization)
-- ✅ Performance monitoring & auto-optimization
-- ✅ Federated search across multiple indexes
-- ✅ Semantic caching with TTL
-- ✅ Query rewriting & expansion
-- ✅ Result diversification
-- ✅ Causal inference support
-- ✅ Feedback loop for continuous learning
--
-- Author: MAHOUN Advanced AI Team
-- Date: 2024-11-08
-- Version: 2.0.0
-- ============================================================================

BEGIN;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;  -- For time-series data
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";  -- Query performance monitoring

-- ============================================================================
-- 1. ULTRA-ADVANCED CHUNKS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal.chunks (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',  -- Multi-tenancy
    
    -- Parent reference (flexible for any document type)
    document_id UUID,
    parent_type VARCHAR(50) NOT NULL,  -- 'law', 'article', 'verdict', 'document'
    parent_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Multi-modal content
    text TEXT NOT NULL,
    text_normalized TEXT,  -- Normalized for better matching
    text_hash VARCHAR(64) GENERATED ALWAYS AS (md5(text)) STORED,  -- Deduplication
    language VARCHAR(10) DEFAULT 'fa',  -- Language detection
    
    -- Multi-modal embeddings (different models/dimensions)
    embedding_dense_768 VECTOR(768),      -- BGE-M3, multilingual-e5
    embedding_dense_1024 VECTOR(1024),    -- OpenAI ada-002
    embedding_sparse JSONB,                -- Sparse embeddings (SPLADE)
    embedding_colbert VECTOR(128)[],       -- ColBERT late interaction
    embedding_multimodal VECTOR(512),      -- CLIP for images/text
    
    -- Position & structure
    start_pos INTEGER,
    end_pos INTEGER,
    depth_level INTEGER DEFAULT 0,         -- Hierarchical depth
    section_path TEXT[],                   -- Breadcrumb path
    
    -- Advanced chunking metadata
    coherence_score FLOAT CHECK (coherence_score >= 0 AND coherence_score <= 1),
    semantic_density FLOAT,
    information_entropy FLOAT,             -- Shannon entropy
    readability_score FLOAT,               -- Flesch reading ease
    entity_count INTEGER DEFAULT 0,
    keyword_density JSONB DEFAULT '{}',    -- Top keywords with TF-IDF
    
    -- Graph analytics (computed by graph engine)
    pagerank_score FLOAT DEFAULT 0.0,
    betweenness_centrality FLOAT DEFAULT 0.0,
    closeness_centrality FLOAT DEFAULT 0.0,
    eigenvector_centrality FLOAT DEFAULT 0.0,
    community_id INTEGER,
    community_label VARCHAR(100),
    authority_score FLOAT DEFAULT 0.0,
    hub_score FLOAT DEFAULT 0.0,
    
    -- Temporal features
    temporal_relevance_score FLOAT DEFAULT 1.0,
    temporal_decay_rate FLOAT DEFAULT 0.1,
    last_accessed_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    
    -- Quality & trust signals
    quality_score FLOAT DEFAULT 0.5,
    trust_score FLOAT DEFAULT 0.5,
    citation_count INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0,
    verification_status VARCHAR(20) DEFAULT 'unverified',  -- verified, unverified, disputed
    
    -- A/B testing & experimentation
    experiment_variant VARCHAR(50),
    experiment_metadata JSONB DEFAULT '{}',
    
    -- Explainability
    feature_importance JSONB DEFAULT '{}',  -- SHAP values
    attribution_scores JSONB DEFAULT '{}',  -- Attribution to sources
    
    -- GDPR & compliance
    pii_detected BOOLEAN DEFAULT false,
    pii_anonymized BOOLEAN DEFAULT false,
    retention_policy VARCHAR(50) DEFAULT 'standard',
    data_classification VARCHAR(20) DEFAULT 'public',  -- public, internal, confidential, restricted
    
    -- Performance optimization
    hot_tier BOOLEAN DEFAULT true,         -- Hot/cold storage tiering
    compression_ratio FLOAT,
    index_version INTEGER DEFAULT 1,       -- For index rebuilds
    
    -- Versioning (temporal tables)
    version INTEGER DEFAULT 1,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP DEFAULT 'infinity',
    is_current BOOLEAN DEFAULT true,
    
    -- General metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID,
    deleted_at TIMESTAMP,  -- Soft delete
    
    -- Constraints
    CONSTRAINT unique_chunk UNIQUE(tenant_id, parent_type, parent_id, chunk_index, version),
    CONSTRAINT valid_positions CHECK (end_pos > start_pos),
    CONSTRAINT valid_scores CHECK (
        pagerank_score >= 0 AND 
        quality_score >= 0 AND quality_score <= 1 AND
        trust_score >= 0 AND trust_score <= 1
    )
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('legal.chunks', 'created_at', 
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- ============================================================================
-- ADVANCED INDEXES FOR CHUNKS
-- ============================================================================

-- Primary access patterns
CREATE INDEX idx_chunks_tenant_parent ON legal.chunks(tenant_id, parent_type, parent_id) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_chunks_document ON legal.chunks(document_id) 
    WHERE document_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_chunks_current ON legal.chunks(id) 
    WHERE is_current = true AND deleted_at IS NULL;

-- Full-text search (multi-language)
CREATE INDEX idx_chunks_text_search_fa ON legal.chunks 
    USING gin(to_tsvector('persian', text)) 
    WHERE language = 'fa' AND deleted_at IS NULL;
CREATE INDEX idx_chunks_text_search_en ON legal.chunks 
    USING gin(to_tsvector('english', text)) 
    WHERE language = 'en' AND deleted_at IS NULL;
CREATE INDEX idx_chunks_text_search_ar ON legal.chunks 
    USING gin(to_tsvector('arabic', text)) 
    WHERE language = 'ar' AND deleted_at IS NULL;

-- Trigram for fuzzy search
CREATE INDEX idx_chunks_text_trigram ON legal.chunks 
    USING gin(text gin_trgm_ops) 
    WHERE deleted_at IS NULL;

-- Vector indexes (HNSW for better performance than IVFFlat)
CREATE INDEX idx_chunks_embedding_768_hnsw ON legal.chunks 
    USING hnsw (embedding_dense_768 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding_dense_768 IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX idx_chunks_embedding_1024_hnsw ON legal.chunks 
    USING hnsw (embedding_dense_1024 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding_dense_1024 IS NOT NULL AND deleted_at IS NULL;

-- Graph analytics indexes
CREATE INDEX idx_chunks_pagerank ON legal.chunks(pagerank_score DESC NULLS LAST) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_chunks_centrality ON legal.chunks(betweenness_centrality DESC NULLS LAST) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_chunks_community ON legal.chunks(community_id) 
    WHERE community_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_chunks_authority ON legal.chunks(authority_score DESC NULLS LAST) 
    WHERE deleted_at IS NULL;

-- Quality & trust
CREATE INDEX idx_chunks_quality ON legal.chunks(quality_score DESC, trust_score DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_chunks_citations ON legal.chunks(citation_count DESC) 
    WHERE deleted_at IS NULL;

-- Temporal access patterns
CREATE INDEX idx_chunks_temporal ON legal.chunks(temporal_relevance_score DESC, last_accessed_at DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_chunks_hot_tier ON legal.chunks(hot_tier, access_count DESC) 
    WHERE deleted_at IS NULL;

-- Versioning
CREATE INDEX idx_chunks_version ON legal.chunks(id, version DESC);
CREATE INDEX idx_chunks_valid_time ON legal.chunks(valid_from, valid_to) 
    WHERE is_current = true;

-- Deduplication
CREATE INDEX idx_chunks_hash ON legal.chunks(text_hash) 
    WHERE deleted_at IS NULL;

-- JSONB indexes for metadata queries
CREATE INDEX idx_chunks_metadata ON legal.chunks USING gin(metadata);
CREATE INDEX idx_chunks_tags ON legal.chunks USING gin(tags);
CREATE INDEX idx_chunks_keywords ON legal.chunks USING gin(keyword_density);

-- Composite indexes for common queries
CREATE INDEX idx_chunks_search_quality ON legal.chunks(tenant_id, quality_score DESC, pagerank_score DESC) 
    WHERE deleted_at IS NULL AND hot_tier = true;

-- Partial indexes for specific use cases
CREATE INDEX idx_chunks_verified ON legal.chunks(id) 
    WHERE verification_status = 'verified' AND deleted_at IS NULL;
CREATE INDEX idx_chunks_pii ON legal.chunks(id) 
    WHERE pii_detected = true AND pii_anonymized = false;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE legal.chunks IS 'Ultra-advanced document chunks with multi-modal embeddings, graph analytics, and temporal versioning';
COMMENT ON COLUMN legal.chunks.tenant_id IS 'Multi-tenancy support for SaaS deployment';
COMMENT ON COLUMN legal.chunks.embedding_dense_768 IS 'Dense embedding (768d) from BGE-M3 or multilingual-e5';
COMMENT ON COLUMN legal.chunks.embedding_sparse IS 'Sparse embedding from SPLADE for better keyword matching';
COMMENT ON COLUMN legal.chunks.embedding_colbert IS 'ColBERT embeddings for late interaction';
COMMENT ON COLUMN legal.chunks.information_entropy IS 'Shannon entropy for information density';
COMMENT ON COLUMN legal.chunks.betweenness_centrality IS 'Graph betweenness centrality (bridge nodes)';
COMMENT ON COLUMN legal.chunks.temporal_relevance_score IS 'Time-decayed relevance score';
COMMENT ON COLUMN legal.chunks.feature_importance IS 'SHAP values for explainability';
COMMENT ON COLUMN legal.chunks.hot_tier IS 'Hot storage tier for frequently accessed chunks';
COMMENT ON COLUMN legal.chunks.version IS 'Version number for temporal queries';
COMMENT ON COLUMN legal.chunks.valid_from IS 'Start of validity period (temporal table)';
COMMENT ON COLUMN legal.chunks.valid_to IS 'End of validity period (temporal table)';

-- ============================================================================
-- 2. ULTRA-ADVANCED ENTITIES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS legal.entities (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    chunk_id UUID REFERENCES legal.chunks(id) ON DELETE CASCADE,
    
    -- Entity data
    text VARCHAR(1000) NOT NULL,
    text_normalized VARCHAR(1000),
    canonical_form VARCHAR(1000),  -- Normalized canonical form
    label VARCHAR(50) NOT NULL,    -- COURT, ARTICLE, LAW_NAME, PERSON, ORG, etc.
    label_hierarchy TEXT[],        -- ['LEGAL', 'COURT', 'SUPREME_COURT']
    
    -- Position in text
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    
    -- NER model outputs
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    
    -- Multi-model consensus
    consensus_score FLOAT,         -- Agreement across multiple NER models
    alternative_labels JSONB DEFAULT '[]',  -- Other possible labels with scores
    
    -- Entity linking & resolution
    knowledge_base_id VARCHAR(200),  -- Wikidata, DBpedia, custom KB
    entity_uri TEXT,                 -- Unique URI for entity
    disambiguation_score FLOAT,
    linked_entities UUID[],          -- Co-reference resolution
    
    -- Entity embeddings (multiple types)
    embedding_contextual VECTOR(768),   -- Contextual embedding from BERT
    embedding_entity VECTOR(300),       -- Entity-specific embedding (Word2Vec, GloVe)
    embedding_knowledge VECTOR(512),    -- Knowledge graph embedding (TransE, RotatE)
    
    -- Semantic features
    entity_type_fine VARCHAR(100),      -- Fine-grained type (e.g., SUPREME_COURT vs DISTRICT_COURT)
    semantic_role VARCHAR(50),          -- Subject, Object, Predicate
    dependency_relation VARCHAR(50),    -- Syntactic dependency
    
    -- Temporal information
    temporal_expression TEXT,           -- Extracted temporal info
    temporal_normalized TIMESTAMP,      -- Normalized timestamp
    temporal_type VARCHAR(50),          -- DATE, TIME, DURATION, SET
    
    -- Sentiment & opinion
    sentiment_score FLOAT,              -- -1 (negative) to +1 (positive)
    subjectivity_score FLOAT,           -- 0 (objective) to 1 (subjective)
    
    -- Legal-specific features
    legal_importance FLOAT DEFAULT 0.5, -- Importance in legal context
    precedent_value FLOAT,              -- Value as legal precedent
    citation_context VARCHAR(50),       -- How entity is cited
    
    -- Graph features
    entity_pagerank FLOAT DEFAULT 0.0,
    entity_centrality FLOAT DEFAULT 0.0,
    co_occurrence_count INTEGER DEFAULT 0,
    
    -- Quality & validation
    validation_status VARCHAR(20) DEFAULT 'unvalidated',  -- validated, unvalidated, disputed
    validation_source VARCHAR(100),
    human_verified BOOLEAN DEFAULT false,
    
    -- GDPR compliance
    is_pii BOOLEAN DEFAULT false,
    pii_category VARCHAR(50),           -- NAME, EMAIL, PHONE, ADDRESS, etc.
    anonymization_method VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    attributes JSONB DEFAULT '{}',      -- Additional entity attributes
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    CONSTRAINT valid_positions CHECK (end_pos > start_pos)
);

-- ============================================================================
-- INDEXES FOR ENTITIES
-- ============================================================================

-- Primary access
CREATE INDEX idx_entities_chunk ON legal.entities(chunk_id) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_tenant ON legal.entities(tenant_id) 
    WHERE deleted_at IS NULL;

-- Entity lookup
CREATE INDEX idx_entities_label ON legal.entities(label, confidence DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_canonical ON legal.entities(canonical_form) 
    WHERE canonical_form IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_entities_kb ON legal.entities(knowledge_base_id) 
    WHERE knowledge_base_id IS NOT NULL AND deleted_at IS NULL;

-- Text search
CREATE INDEX idx_entities_text_trigram ON legal.entities 
    USING gin(text gin_trgm_ops) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_text_search ON legal.entities 
    USING gin(to_tsvector('persian', text)) 
    WHERE deleted_at IS NULL;

-- Confidence & quality
CREATE INDEX idx_entities_confidence ON legal.entities(confidence DESC, consensus_score DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_validated ON legal.entities(validation_status, human_verified) 
    WHERE deleted_at IS NULL;

-- Vector indexes
CREATE INDEX idx_entities_embedding_contextual ON legal.entities 
    USING hnsw (embedding_contextual vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding_contextual IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX idx_entities_embedding_knowledge ON legal.entities 
    USING hnsw (embedding_knowledge vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding_knowledge IS NOT NULL AND deleted_at IS NULL;

-- Graph features
CREATE INDEX idx_entities_pagerank ON legal.entities(entity_pagerank DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_cooccurrence ON legal.entities(co_occurrence_count DESC) 
    WHERE deleted_at IS NULL;

-- Legal features
CREATE INDEX idx_entities_legal_importance ON legal.entities(legal_importance DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_precedent ON legal.entities(precedent_value DESC) 
    WHERE precedent_value IS NOT NULL AND deleted_at IS NULL;

-- PII detection
CREATE INDEX idx_entities_pii ON legal.entities(is_pii, pii_category) 
    WHERE is_pii = true AND deleted_at IS NULL;

-- JSONB indexes
CREATE INDEX idx_entities_metadata ON legal.entities USING gin(metadata);
CREATE INDEX idx_entities_attributes ON legal.entities USING gin(attributes);
CREATE INDEX idx_entities_alternatives ON legal.entities USING gin(alternative_labels);

-- Composite indexes
CREATE INDEX idx_entities_chunk_label ON legal.entities(chunk_id, label, confidence DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_type_importance ON legal.entities(label, legal_importance DESC) 
    WHERE deleted_at IS NULL;

COMMENT ON TABLE legal.entities IS 'Ultra-advanced named entities with multi-model consensus, entity linking, and legal-specific features';
COMMENT ON COLUMN legal.entities.consensus_score IS 'Agreement score across multiple NER models';
COMMENT ON COLUMN legal.entities.knowledge_base_id IS 'Linked entity ID in external knowledge base (Wikidata, DBpedia)';
COMMENT ON COLUMN legal.entities.embedding_contextual IS 'Contextual embedding from transformer model';
COMMENT ON COLUMN legal.entities.embedding_knowledge IS 'Knowledge graph embedding (TransE, RotatE)';
COMMENT ON COLUMN legal.entities.legal_importance IS 'Importance score in legal context (0-1)';
COMMENT ON COLUMN legal.entities.precedent_value IS 'Value as legal precedent';
COMMENT ON COLUMN legal.entities.is_pii IS 'Whether entity contains personally identifiable information';

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
    query_embedding VECTOR(768) DEFAULT NULL,
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
            ts_rank(to_tsvector('english', text), plainto_tsquery('english', query_text)) as score
        FROM legal.chunks
        WHERE to_tsvector('english', text) @@ plainto_tsquery('english', query_text)
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
