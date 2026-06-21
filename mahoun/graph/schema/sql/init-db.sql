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
