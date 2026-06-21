-- ============================================================================
-- Labeling & Training Data Schema
-- ============================================================================
-- Schema for storing labeled data, annotations, and training datasets
-- ============================================================================

-- Create labeling schema
CREATE SCHEMA IF NOT EXISTS labeling;

SET search_path TO labeling, public;

-- ============================================================================
-- Enums
-- ============================================================================

CREATE TYPE labeling.label_status AS ENUM (
    'pending',
    'in_progress', 
    'completed',
    'reviewed',
    'rejected'
);

CREATE TYPE labeling.entity_type AS ENUM (
    'ARTICLE',
    'LAW_NAME',
    'COURT',
    'PERSON',
    'ORGANIZATION',
    'LOCATION',
    'DATE',
    'MONEY',
    'CASE_NUMBER',
    'VERDICT',
    'OTHER'
);

CREATE TYPE labeling.annotation_source AS ENUM (
    'manual',
    'automatic',
    'semi_automatic',
    'imported'
);

-- ============================================================================
-- Documents for Labeling
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_doc_id UUID,  -- Reference to legal.laws or other source
    content TEXT NOT NULL,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    metadata JSONB DEFAULT '{}',
    status labeling.label_status DEFAULT 'pending',
    assigned_to VARCHAR(100),
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Indexes
    CONSTRAINT documents_content_not_empty CHECK (length(content) > 0)
);

CREATE INDEX idx_labeling_docs_status ON labeling.documents(status);
CREATE INDEX idx_labeling_docs_priority ON labeling.documents(priority DESC);
CREATE INDEX idx_labeling_docs_assigned ON labeling.documents(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_labeling_docs_hash ON labeling.documents(content_hash);

-- ============================================================================
-- Entity Annotations (NER Labels)
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.entity_annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES labeling.documents(id) ON DELETE CASCADE,
    entity_type labeling.entity_type NOT NULL,
    entity_text TEXT NOT NULL,
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source labeling.annotation_source DEFAULT 'manual',
    annotator VARCHAR(100),
    context_before TEXT,
    context_after TEXT,
    metadata JSONB DEFAULT '{}',
    is_validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT entity_positions_valid CHECK (start_pos >= 0 AND end_pos > start_pos),
    CONSTRAINT entity_confidence_valid CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_entity_annotations_doc ON labeling.entity_annotations(document_id);
CREATE INDEX idx_entity_annotations_type ON labeling.entity_annotations(entity_type);
CREATE INDEX idx_entity_annotations_source ON labeling.entity_annotations(source);
CREATE INDEX idx_entity_annotations_validated ON labeling.entity_annotations(is_validated);

-- ============================================================================
-- Sentence Classifications
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.sentence_classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES labeling.documents(id) ON DELETE CASCADE,
    sentence_text TEXT NOT NULL,
    start_pos INTEGER NOT NULL,
    end_pos INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source labeling.annotation_source DEFAULT 'manual',
    annotator VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    is_validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT sentence_positions_valid CHECK (start_pos >= 0 AND end_pos > start_pos)
);

CREATE INDEX idx_sentence_class_doc ON labeling.sentence_classifications(document_id);
CREATE INDEX idx_sentence_class_category ON labeling.sentence_classifications(category);

-- ============================================================================
-- Training Datasets
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.training_datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,  -- 'ner', 'classification', 'qa', etc.
    version VARCHAR(20) DEFAULT '1.0.0',
    total_samples INTEGER DEFAULT 0,
    train_samples INTEGER DEFAULT 0,
    val_samples INTEGER DEFAULT 0,
    test_samples INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Training Samples (Links documents to datasets)
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.training_samples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id UUID NOT NULL REFERENCES labeling.training_datasets(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES labeling.documents(id) ON DELETE CASCADE,
    split VARCHAR(20) NOT NULL,  -- 'train', 'val', 'test'
    sample_data JSONB NOT NULL,  -- Complete sample with labels
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT training_split_valid CHECK (split IN ('train', 'val', 'test')),
    UNIQUE(dataset_id, document_id)
);

CREATE INDEX idx_training_samples_dataset ON labeling.training_samples(dataset_id);
CREATE INDEX idx_training_samples_split ON labeling.training_samples(split);

-- ============================================================================
-- Annotation Quality Metrics
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.annotation_quality (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES labeling.documents(id) ON DELETE CASCADE,
    annotator VARCHAR(100) NOT NULL,
    total_annotations INTEGER DEFAULT 0,
    validated_annotations INTEGER DEFAULT 0,
    rejected_annotations INTEGER DEFAULT 0,
    avg_confidence FLOAT,
    inter_annotator_agreement FLOAT,  -- If multiple annotators
    quality_score FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(document_id, annotator)
);

CREATE INDEX idx_annotation_quality_annotator ON labeling.annotation_quality(annotator);

-- ============================================================================
-- Active Learning Queue
-- ============================================================================

CREATE TABLE IF NOT EXISTS labeling.active_learning_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES labeling.documents(id) ON DELETE CASCADE,
    uncertainty_score FLOAT NOT NULL,
    diversity_score FLOAT,
    priority_score FLOAT GENERATED ALWAYS AS (
        uncertainty_score * 0.7 + COALESCE(diversity_score, 0) * 0.3
    ) STORED,
    selected_for_labeling BOOLEAN DEFAULT FALSE,
    selected_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uncertainty_valid CHECK (uncertainty_score >= 0 AND uncertainty_score <= 1)
);

CREATE INDEX idx_active_learning_priority ON labeling.active_learning_queue(priority_score DESC);
CREATE INDEX idx_active_learning_selected ON labeling.active_learning_queue(selected_for_labeling);

-- ============================================================================
-- Label Statistics (Materialized View)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS labeling.label_statistics AS
SELECT 
    entity_type,
    COUNT(*) as total_count,
    AVG(confidence) as avg_confidence,
    COUNT(CASE WHEN is_validated THEN 1 END) as validated_count,
    COUNT(CASE WHEN source = 'manual' THEN 1 END) as manual_count,
    COUNT(CASE WHEN source = 'automatic' THEN 1 END) as automatic_count
FROM labeling.entity_annotations
GROUP BY entity_type;

CREATE UNIQUE INDEX idx_label_stats_type ON labeling.label_statistics(entity_type);

-- ============================================================================
-- Functions
-- ============================================================================

-- Function to update document status
CREATE OR REPLACE FUNCTION labeling.update_document_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Update document status based on annotations
    UPDATE labeling.documents
    SET 
        status = CASE 
            WHEN (SELECT COUNT(*) FROM labeling.entity_annotations 
                  WHERE document_id = NEW.document_id AND is_validated = TRUE) > 0
            THEN 'completed'::labeling.label_status
            ELSE 'in_progress'::labeling.label_status
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.document_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update document status
CREATE TRIGGER trigger_update_document_status
AFTER INSERT OR UPDATE ON labeling.entity_annotations
FOR EACH ROW
EXECUTE FUNCTION labeling.update_document_status();

-- Function to refresh label statistics
CREATE OR REPLACE FUNCTION labeling.refresh_statistics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY labeling.label_statistics;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample Data (for testing)
-- ============================================================================

-- Insert sample document
INSERT INTO labeling.documents (content, content_hash, status, priority)
VALUES (
    'ماده 10 قانون مدنی در مورد اهلیت افراد است.',
    encode(digest('ماده 10 قانون مدنی در مورد اهلیت افراد است.', 'sha256'), 'hex'),
    'pending',
    1
) ON CONFLICT (content_hash) DO NOTHING;

-- ============================================================================
-- Grants (Security)
-- ============================================================================

-- Grant permissions to application user
GRANT USAGE ON SCHEMA labeling TO mahoun;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA labeling TO mahoun;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA labeling TO mahoun;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA labeling TO mahoun;

-- ============================================================================
-- Comments (Documentation)
-- ============================================================================

COMMENT ON SCHEMA labeling IS 'Schema for labeled data and training datasets';
COMMENT ON TABLE labeling.documents IS 'Documents queued for labeling';
COMMENT ON TABLE labeling.entity_annotations IS 'NER entity annotations';
COMMENT ON TABLE labeling.sentence_classifications IS 'Sentence-level classifications';
COMMENT ON TABLE labeling.training_datasets IS 'Training dataset metadata';
COMMENT ON TABLE labeling.training_samples IS 'Individual training samples';
COMMENT ON TABLE labeling.annotation_quality IS 'Annotation quality metrics';
COMMENT ON TABLE labeling.active_learning_queue IS 'Active learning prioritization queue';

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX idx_entity_annotations_doc_type ON labeling.entity_annotations(document_id, entity_type);
CREATE INDEX idx_entity_annotations_validated_type ON labeling.entity_annotations(is_validated, entity_type);

-- Full-text search on entity text
CREATE INDEX idx_entity_text_gin ON labeling.entity_annotations USING gin(to_tsvector('persian', entity_text));

-- JSONB indexes for metadata queries
CREATE INDEX idx_entity_metadata_gin ON labeling.entity_annotations USING gin(metadata);
CREATE INDEX idx_document_metadata_gin ON labeling.documents USING gin(metadata);

COMMIT;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check tables created
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname = 'labeling'
ORDER BY tablename;

-- Check indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'labeling'
ORDER BY tablename, indexname;
