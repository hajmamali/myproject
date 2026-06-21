#!/usr/bin/env bash
# ============================================================================
# MAHOUN Platform - Docker Validation Script
# ============================================================================
# Validates Docker setup meets production requirements
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILURES=0

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
    ((FAILURES++))
}

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         MAHOUN Platform - Docker Validation                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 1. Prerequisites Check
# ============================================================================
log_info "1. Checking prerequisites..."

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+' | head -1)
    log_success "Docker installed: $DOCKER_VERSION"
else
    log_error "Docker not found"
fi

if command -v docker compose &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version | grep -oP '\d+\.\d+' | head -1)
    log_success "Docker Compose installed: $COMPOSE_VERSION"
else
    log_error "Docker Compose not found"
fi

# ============================================================================
# 2. File Structure Check
# ============================================================================
log_info "2. Checking file structure..."

FILES=(
    "Dockerfile.backend"
    "frontend/Dockerfile"
    "docker-compose.yml"
    ".dockerignore"
    "frontend/.dockerignore"
    "DOCKER_GUIDE.md"
)

for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        log_success "Found: $file"
    else
        log_error "Missing: $file"
    fi
done

# ============================================================================
# 3. Dockerfile Validation
# ============================================================================
log_info "3. Validating Dockerfiles..."

# Check backend Dockerfile
if [[ -f "Dockerfile.backend" ]]; then
    if grep -q "FROM python:3.12" Dockerfile.backend; then
        log_success "Backend: Using Python 3.12"
    else
        log_warning "Backend: Not using Python 3.12"
    fi
    
    if grep -q "USER mahoun" Dockerfile.backend; then
        log_success "Backend: Non-root user configured"
    else
        log_error "Backend: Missing non-root user"
    fi
    
    if grep -q "HEALTHCHECK" Dockerfile.backend; then
        log_success "Backend: Health check configured"
    else
        log_error "Backend: Missing health check"
    fi
    
    if grep -q "multi-stage" Dockerfile.backend; then
        log_success "Backend: Multi-stage build detected"
    else
        log_warning "Backend: Multi-stage build not clearly marked"
    fi
fi

# Check frontend Dockerfile
if [[ -f "frontend/Dockerfile" ]]; then
    if grep -q "FROM node:.*alpine" frontend/Dockerfile; then
        log_success "Frontend: Using Node Alpine"
    else
        log_warning "Frontend: Not using Alpine"
    fi
    
    if grep -q "FROM nginx:.*alpine" frontend/Dockerfile; then
        log_success "Frontend: Using Nginx Alpine"
    else
        log_warning "Frontend: Not using Nginx Alpine"
    fi
    
    if grep -q "HEALTHCHECK" frontend/Dockerfile; then
        log_success "Frontend: Health check configured"
    else
        log_error "Frontend: Missing health check"
    fi
fi

# ============================================================================
# 4. Docker Compose Validation
# ============================================================================
log_info "4. Validating docker-compose.yml..."

if [[ -f "docker-compose.yml" ]]; then
    if grep -q "healthcheck:" docker-compose.yml; then
        log_success "Compose: Health checks configured"
    else
        log_error "Compose: Missing health checks"
    fi
    
    if grep -q "profiles:" docker-compose.yml; then
        log_success "Compose: Profiles configured"
    else
        log_error "Compose: Missing profiles"
    fi
    
    if grep -q "networks:" docker-compose.yml; then
        log_success "Compose: Networks configured"
    else
        log_error "Compose: Missing networks"
    fi
    
    if grep -q "volumes:" docker-compose.yml; then
        log_success "Compose: Named volumes configured"
    else
        log_error "Compose: Missing named volumes"
    fi
    
    # Check for hardcoded passwords
    if grep -E "(password|PASSWORD).*=.*(123|password|secret)" docker-compose.yml | grep -v "changeme" | grep -v "#"; then
        log_error "Compose: Hardcoded passwords detected!"
    else
        log_success "Compose: No hardcoded passwords"
    fi
fi

# ============================================================================
# 5. Environment Configuration Check
# ============================================================================
log_info "5. Checking environment configuration..."

if [[ -f "scripts/docker/generate_env_example.sh" ]]; then
    log_success "Found: generate_env_example.sh script"
    if [[ -x "scripts/docker/generate_env_example.sh" ]]; then
        log_success "Script is executable"
    else
        log_warning "Script is not executable (run: chmod +x scripts/docker/generate_env_example.sh)"
    fi
else
    log_warning "Missing: generate_env_example.sh script"
fi

# ============================================================================
# 6. Build Test (Optional - Commented out for CI safety)
# ============================================================================
if [[ "${RUN_BUILD_TEST:-false}" == "true" ]]; then
    log_info "6. Testing Docker builds..."
    
    if docker compose build backend --no-cache > /dev/null 2>&1; then
        log_success "Backend builds successfully"
    else
        log_error "Backend build failed"
    fi
    
    if docker compose build frontend --no-cache > /dev/null 2>&1; then
        log_success "Frontend builds successfully"
    else
        log_error "Frontend build failed"
    fi
else
    log_info "6. Skipping build test (set RUN_BUILD_TEST=true to enable)"
fi

# ============================================================================
# 7. Documentation Check
# ============================================================================
log_info "7. Checking documentation..."

if [[ -f "DOCKER_GUIDE.md" ]]; then
    if grep -q "Production Deployment" DOCKER_GUIDE.md; then
        log_success "Documentation: Production section exists"
    else
        log_warning "Documentation: Missing production section"
    fi
    
    if grep -q "Troubleshooting" DOCKER_GUIDE.md; then
        log_success "Documentation: Troubleshooting section exists"
    else
        log_warning "Documentation: Missing troubleshooting section"
    fi
fi

# ============================================================================
# 8. Makefile Targets Check
# ============================================================================
log_info "8. Checking Makefile targets..."

if [[ -f "Makefile" ]]; then
    DOCKER_TARGETS=("docker-build" "docker-up" "docker-down" "docker-logs")
    for target in "${DOCKER_TARGETS[@]}"; do
        if grep -q "^${target}:" Makefile; then
            log_success "Makefile: $target target exists"
        else
            log_error "Makefile: Missing $target target"
        fi
    done
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "════════════════════════════════════════════════════════════════"
if [[ $FAILURES -eq 0 ]]; then
    log_success "All validation checks passed!"
    echo ""
    echo "Next steps:"
    echo "  1. Run: make docker-build"
    echo "  2. Run: make docker-up"
    echo "  3. Test: curl http://localhost:8000/system/health"
    exit 0
else
    log_error "$FAILURES validation check(s) failed"
    echo ""
    echo "Please fix the issues above before deploying."
    exit 1
fi

