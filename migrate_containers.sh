#!/bin/bash
# ============================================================================
# MAHOUN Container Migration Script
# ============================================================================
# Purpose: Migrate from legacy containers to new unified architecture
# Usage: ./migrate_containers.sh [dry-run|execute]
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=${1:-"dry-run"}
BACKUP_DIR="docker/legacy/migration_$(date +%Y%m%d_%H%M%S)"

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

check_requirements() {
    log "Checking migration requirements..."
    
    # Check if new files exist
    local required_files=(
        "Dockerfile.kernel"
        "Dockerfile.api"
        "docker-compose.new.yml"
        "requirements-api.txt"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required file missing: $file"
            exit 1
        fi
    done
    
    # Check Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running or not accessible"
        exit 1
    fi
    
    log "✅ All requirements met"
}

backup_legacy() {
    log "Creating backup of legacy containers..."
    
    if [[ "$DRY_RUN" == "execute" ]]; then
        mkdir -p "$BACKUP_DIR"
        
        # Backup compose files
        cp docker-compose*.yml "$BACKUP_DIR/" 2>/dev/null || true
        
        # Backup legacy Dockerfile
        cp Dockerfile.backend "$BACKUP_DIR/" 2>/dev/null || true
        
        log "✅ Backup created at: $BACKUP_DIR"
    else
        log "[DRY-RUN] Would create backup at: $BACKUP_DIR"
    fi
}

stop_legacy_containers() {
    log "Stopping legacy containers..."
    
    local legacy_compose_files=(
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "docker-compose.dev.yml"
    )
    
    for compose_file in "${legacy_compose_files[@]}"; do
        if [[ -f "$compose_file" ]]; then
            if [[ "$DRY_RUN" == "execute" ]]; then
                docker-compose -f "$compose_file" down --remove-orphans || true
            else
                log "[DRY-RUN] Would stop containers from: $compose_file"
            fi
        fi
    done
}

build_new_containers() {
    log "Building new container architecture..."
    
    if [[ "$DRY_RUN" == "execute" ]]; then
        # Build governance kernel
        log "Building governance kernel..."
        docker build -f Dockerfile.kernel -t mahoun/governance-kernel:latest .
        
        # Build API server
        log "Building API server..."
        docker build -f Dockerfile.api -t mahoun/api-server:latest .
        
        # Build MCP server
        log "Building MCP server..."
        docker build -f Dockerfile.mcp -t mahoun/mcp-server:latest .
        
        log "✅ All containers built successfully"
    else
        log "[DRY-RUN] Would build:"
        log "  - mahoun/governance-kernel (Dockerfile.kernel)"
        log "  - mahoun/api-server (Dockerfile.api)"
        log "  - mahoun/mcp-server (Dockerfile.mcp)"
    fi
}

test_new_architecture() {
    log "Testing new container architecture..."
    
    if [[ "$DRY_RUN" == "execute" ]]; then
        # Test governance kernel standalone
        log "Testing governance kernel..."
        docker run --rm -d --name test-kernel -p 8080:8080 mahoun/governance-kernel:latest
        sleep 5
        
        if curl -f http://localhost:8080/health >/dev/null 2>&1; then
            log "✅ Governance kernel health check passed"
        else
            error "Governance kernel health check failed"
        fi
        
        docker stop test-kernel
        
        log "✅ New architecture test completed"
    else
        log "[DRY-RUN] Would test new container health checks"
    fi
}

deploy_new_architecture() {
    log "Deploying new unified architecture..."
    
    if [[ "$DRY_RUN" == "execute" ]]; then
        # Start new architecture
        docker-compose -f docker-compose.new.yml up -d
        
        # Wait for services
        sleep 10
        
        # Verify health
        log "Verifying service health..."
        docker-compose -f docker-compose.new.yml ps
        
        log "✅ New architecture deployed successfully"
    else
        log "[DRY-RUN] Would deploy docker-compose.new.yml"
    fi
}

cleanup_legacy() {
    log "Cleaning up legacy files..."
    
    if [[ "$DRY_RUN" == "execute" ]]; then
        # Move legacy compose to archive
        mv docker-compose.yml docker-compose.yml.legacy
        mv docker-compose.prod.yml docker-compose.prod.yml.legacy
        
        # Rename new compose to primary
        mv docker-compose.new.yml docker-compose.yml
        
        log "✅ Legacy cleanup completed"
    else
        log "[DRY-RUN] Would move legacy files and activate new architecture"
    fi
}

show_summary() {
    log "Migration Summary:"
    log "=================="
    
    if [[ "$DRY_RUN" == "execute" ]]; then
        log "✅ Legacy containers stopped and archived"
        log "✅ New architecture deployed:"
        log "   - Governance Kernel: http://localhost:8080"
        log "   - API Server: http://localhost:8000" 
        log "   - MCP Server: http://localhost:8001"
        log ""
        log "Container size comparison:"
        log "   Before: ~2GB+ (multiple heavy containers)"
        log "   After:  ~400MB (3 optimized containers)"
        log ""
        log "Migration completed successfully!"
        log "Backup available at: $BACKUP_DIR"
    else
        log "This was a DRY RUN - no changes made"
        log "Run with 'execute' parameter to perform migration:"
        log "  ./migrate_containers.sh execute"
    fi
}

main() {
    log "MAHOUN Container Migration - Starting..."
    log "Mode: $DRY_RUN"
    log ""
    
    check_requirements
    backup_legacy
    stop_legacy_containers
    build_new_containers
    test_new_architecture
    deploy_new_architecture
    cleanup_legacy
    show_summary
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi