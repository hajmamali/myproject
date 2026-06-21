#!/bin/bash
# ============================================================================
# MAHOUN Platform - Automated Database Backup Script
# ============================================================================
# Backs up Neo4j, PostgreSQL, Redis, and ChromaDB data
# Retention: 30 days
# Schedule: Daily at 2 AM (via cron)
# ============================================================================

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"/{neo4j,postgres,redis,chromadb,volumes}

log_info "Starting backup at $(date)"

# ============================================================================
# 1. Backup Neo4j
# ============================================================================
log_info "Backing up Neo4j..."
if docker ps | grep -q mahoun-neo4j; then
    docker exec mahoun-neo4j neo4j-admin database dump neo4j \
        --to-path=/tmp/backup-${TIMESTAMP}.dump || log_error "Neo4j backup failed"
    
    docker cp mahoun-neo4j:/tmp/backup-${TIMESTAMP}.dump \
        "$BACKUP_DIR/neo4j/neo4j-${TIMESTAMP}.dump"
    
    gzip "$BACKUP_DIR/neo4j/neo4j-${TIMESTAMP}.dump"
    log_success "Neo4j backup completed"
else
    log_info "Neo4j container not running, skipping"
fi

# ============================================================================
# 2. Backup PostgreSQL
# ============================================================================
log_info "Backing up PostgreSQL..."
if docker ps | grep -q mahoun-postgres; then
    docker exec mahoun-postgres pg_dump -U mahoun mahoun \
        > "$BACKUP_DIR/postgres/postgres-${TIMESTAMP}.sql"
    
    gzip "$BACKUP_DIR/postgres/postgres-${TIMESTAMP}.sql"
    log_success "PostgreSQL backup completed"
else
    log_info "PostgreSQL container not running, skipping"
fi

# ============================================================================
# 3. Backup Redis
# ============================================================================
log_info "Backing up Redis..."
if docker ps | grep -q mahoun-redis; then
    docker exec mahoun-redis redis-cli SAVE
    docker cp mahoun-redis:/data/dump.rdb \
        "$BACKUP_DIR/redis/redis-${TIMESTAMP}.rdb"
    
    gzip "$BACKUP_DIR/redis/redis-${TIMESTAMP}.rdb"
    log_success "Redis backup completed"
else
    log_info "Redis container not running, skipping"
fi

# ============================================================================
# 4. Backup ChromaDB
# ============================================================================
log_info "Backing up ChromaDB..."
if docker ps | grep -q mahoun-chromadb; then
    docker exec mahoun-chromadb tar czf /tmp/chroma-${TIMESTAMP}.tar.gz \
        /chroma/chroma
    
    docker cp mahoun-chromadb:/tmp/chroma-${TIMESTAMP}.tar.gz \
        "$BACKUP_DIR/chromadb/"
    
    log_success "ChromaDB backup completed"
else
    log_info "ChromaDB container not running, skipping"
fi

# ============================================================================
# 5. Backup Docker Volumes (fallback)
# ============================================================================
log_info "Backing up Docker volumes..."
for volume in mahoun_neo4j_data mahoun_postgres_data mahoun_redis_data mahoun_chromadb_data; do
    if docker volume ls | grep -q "$volume"; then
        docker run --rm \
            -v "$volume":/source:ro \
            -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
            alpine tar czf "/backup/${volume}-${TIMESTAMP}.tar.gz" -C /source .
        
        log_success "Volume $volume backed up"
    fi
done

# ============================================================================
# 6. Backup Application Data
# ============================================================================
log_info "Backing up application data..."
tar czf "$BACKUP_DIR/app-data-${TIMESTAMP}.tar.gz" \
    data/ uploads/ output/ runtime/ 2>/dev/null || true

log_success "Application data backed up"

# ============================================================================
# 7. Create Backup Manifest
# ============================================================================
cat > "$BACKUP_DIR/manifest-${TIMESTAMP}.json" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "date": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
  "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
  "docker_images": {
    "backend": "$(docker images mahoun/backend:latest --format '{{.ID}}' 2>/dev/null || echo 'unknown')",
    "frontend": "$(docker images mahoun/frontend:latest --format '{{.ID}}' 2>/dev/null || echo 'unknown')"
  },
  "files": [
    $(find "$BACKUP_DIR" -name "*${TIMESTAMP}*" -type f -printf '"%p",\n' | sed '$ s/,$//')
  ]
}
EOF

log_success "Backup manifest created"

# ============================================================================
# 8. Cleanup Old Backups
# ============================================================================
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete
log_success "Old backups cleaned up"

# ============================================================================
# 9. Calculate Backup Size
# ============================================================================
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log_success "Backup completed successfully!"
log_info "Total backup size: $BACKUP_SIZE"
log_info "Backup location: $BACKUP_DIR"

# ============================================================================
# 10. Optional: Upload to S3/Cloud Storage
# ============================================================================
if [ -n "$AWS_S3_BUCKET" ]; then
    log_info "Uploading to S3..."
    aws s3 sync "$BACKUP_DIR" "s3://$AWS_S3_BUCKET/mahoun-backups/" \
        --exclude "*" --include "*${TIMESTAMP}*"
    log_success "Uploaded to S3"
fi

log_info "Backup completed at $(date)"
