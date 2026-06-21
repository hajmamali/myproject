#!/usr/bin/env bash
# ============================================================================
# MAHOUN Platform - Generate .env.example
# ============================================================================
# This script creates a .env.example file with all required variables
# ============================================================================

set -euo pipefail

TARGET_FILE="${1:-.env.example}"

cat > "$TARGET_FILE" << 'EOF'
# ============================================================================
# MAHOUN Platform - Environment Variables Template
# ============================================================================
# Copy this file to .env and fill in your actual values
# NEVER commit .env to version control!
#
# Usage:
#   cp .env.example .env
#   nano .env  # Edit with your values
# ============================================================================

# ============================================================================
# Application Settings
# ============================================================================
MAHOUN_ENV=development
# Options: development, staging, production

LOG_LEVEL=INFO
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

LOG_FORMAT=json
# Options: json, text

# ============================================================================
# Server Configuration
# ============================================================================
BACKEND_PORT=8000
FRONTEND_PORT=80

# ============================================================================
# Neo4j Graph Database
# ============================================================================
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
# ⚠️ CHANGE THIS IN PRODUCTION! Use: openssl rand -base64 32

NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687

# Neo4j Memory Settings (laptop-safe defaults)
NEO4J_HEAP_SIZE=2G
NEO4J_PAGECACHE_SIZE=1G

# ============================================================================
# PostgreSQL Database
# ============================================================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mahoun
POSTGRES_USER=mahoun
POSTGRES_PASSWORD=changeme
# ⚠️ CHANGE THIS IN PRODUCTION!

# ============================================================================
# Redis Cache
# ============================================================================
REDIS_URL=redis://redis:6379/0
REDIS_PORT=6379
REDIS_PASSWORD=
# Optional: Set password for production

REDIS_MAX_MEMORY=1gb

# ============================================================================
# ChromaDB Vector Store
# ============================================================================
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMADB_PORT=8001
# External port (mapped to avoid conflict with backend)

CHROMA_TOKEN=
# Optional: Set token for authentication

CHROMA_TELEMETRY=FALSE
CHROMA_AUTH_PROVIDER=

# ============================================================================
# Security & Authentication
# ============================================================================
JWT_SECRET_KEY=change-me-in-production-use-openssl-rand
# ⚠️ CRITICAL: Generate with: openssl rand -base64 64

API_KEY=
# Optional: Set API key for external access

# ============================================================================
# Feature Flags
# ============================================================================
ENABLE_NEO4J=false
ENABLE_POSTGRES=false
ENABLE_REDIS=false

# Set to true when running with --profile full

# ============================================================================
# Frontend Configuration
# ============================================================================
VITE_API_URL=http://localhost:8000
# Change to your backend URL in production

# ============================================================================
# Monitoring (Optional)
# ============================================================================
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

GRAFANA_USER=admin
GRAFANA_PASSWORD=changeme
# ⚠️ CHANGE THIS IN PRODUCTION!

GRAFANA_ROOT_URL=http://localhost:3000

# ============================================================================
# Production Deployment Notes
# ============================================================================
#
# For production, generate secure passwords:
#   export NEO4J_PASSWORD="$(openssl rand -base64 32)"
#   export POSTGRES_PASSWORD="$(openssl rand -base64 32)"
#   export GRAFANA_PASSWORD="$(openssl rand -base64 32)"
#   export JWT_SECRET_KEY="$(openssl rand -base64 64)"
#   export REDIS_PASSWORD="$(openssl rand -base64 32)"
#
# Save to .env:
#   cat > .env << EOF
#   MAHOUN_ENV=production
#   NEO4J_PASSWORD=${NEO4J_PASSWORD}
#   POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
#   GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
#   JWT_SECRET_KEY=${JWT_SECRET_KEY}
#   REDIS_PASSWORD=${REDIS_PASSWORD}
#   EOF
#
# ============================================================================
EOF

echo "✅ Created $TARGET_FILE"

