# ============================================================================
# MAHOUN Platform - Makefile
# ============================================================================
# Quick commands for Docker operations
# ============================================================================

.PHONY: help
help: ## Show this help message
	@echo "MAHOUN Platform - Docker Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Development Commands
# ============================================================================

.PHONY: dev
dev: ## Start development environment (backend + frontend only)
	docker-compose -f docker-compose.dev.yml up

.PHONY: dev-build
dev-build: ## Build and start development environment
	docker-compose -f docker-compose.dev.yml up --build

.PHONY: dev-full
dev-full: ## Start development with all databases
	docker-compose -f docker-compose.dev.yml --profile database up

.PHONY: dev-down
dev-down: ## Stop development environment
	docker-compose -f docker-compose.dev.yml down

.PHONY: dev-clean
dev-clean: ## Stop and remove all development containers and volumes
	docker-compose -f docker-compose.dev.yml down -v
	docker volume prune -f

# ============================================================================
# Production Commands
# ============================================================================

.PHONY: prod
prod: ## Start production environment (minimal)
	docker-compose -f docker-compose.prod.yml up -d

.PHONY: prod-build
prod-build: ## Build and start production environment
	docker-compose -f docker-compose.prod.yml up -d --build

.PHONY: prod-full
prod-full: ## Start production with all services
	docker-compose -f docker-compose.prod.yml --profile full --profile monitoring up -d

.PHONY: prod-down
prod-down: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

.PHONY: prod-logs
prod-logs: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

.PHONY: prod-restart
prod-restart: ## Restart production services
	docker-compose -f docker-compose.prod.yml restart

# ============================================================================
# Build Commands
# ============================================================================

.PHONY: build-backend
build-backend: ## Build backend image only
	docker build -t mahoun/backend:latest -f Dockerfile.backend --target production .

.PHONY: build-backend-dev
build-backend-dev: ## Build backend development image
	docker build -t mahoun/backend:dev -f Dockerfile.backend --target development .

.PHONY: build-all
build-all: ## Build all images
	docker-compose -f docker-compose.prod.yml build

# ============================================================================
# Testing Commands
# ============================================================================

.PHONY: test
test: ## Run tests in Docker
	docker build -t mahoun/backend:test -f Dockerfile.backend --target testing .
	docker run --rm mahoun/backend:test

.PHONY: test-local
test-local: ## Run tests locally (requires Python 3.12+)
	pytest tests/ -v --tb=short

# ============================================================================
# Database Commands
# ============================================================================

.PHONY: db-backup
db-backup: ## Backup all databases
	@echo "Backing up databases..."
	docker exec mahoun-postgres-prod pg_dump -U mahoun mahoun > backup_postgres_$$(date +%Y%m%d_%H%M%S).sql
	docker exec mahoun-neo4j-prod neo4j-admin database dump neo4j --to-path=/tmp
	@echo "Backup complete!"

.PHONY: db-restore
db-restore: ## Restore databases (requires backup files)
	@echo "Restore not implemented yet. Use manual restore."

# ============================================================================
# Monitoring Commands
# ============================================================================

.PHONY: logs
logs: ## Show logs for all services
	docker-compose -f docker-compose.prod.yml logs -f

.PHONY: logs-backend
logs-backend: ## Show backend logs only
	docker-compose -f docker-compose.prod.yml logs -f backend

.PHONY: logs-neo4j
logs-neo4j: ## Show Neo4j logs only
	docker-compose -f docker-compose.prod.yml logs -f neo4j

.PHONY: stats
stats: ## Show container resource usage
	docker stats

# ============================================================================
# Maintenance Commands
# ============================================================================

.PHONY: clean
clean: ## Remove all stopped containers and unused images
	docker container prune -f
	docker image prune -f

.PHONY: clean-all
clean-all: ## Remove everything (containers, images, volumes, networks)
	@echo "WARNING: This will remove ALL Docker resources!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f docker-compose.prod.yml down -v; \
		docker-compose -f docker-compose.dev.yml down -v; \
		docker system prune -af --volumes; \
	fi

.PHONY: ps
ps: ## Show running containers
	docker-compose -f docker-compose.prod.yml ps

.PHONY: shell-backend
shell-backend: ## Open shell in backend container
	docker exec -it mahoun-backend-prod /bin/bash

.PHONY: shell-neo4j
shell-neo4j: ## Open Neo4j cypher-shell
	docker exec -it mahoun-neo4j-prod cypher-shell -u neo4j

# ============================================================================
# Health Check Commands
# ============================================================================

.PHONY: health
health: ## Check health of all services
	@echo "Checking service health..."
	@docker-compose -f docker-compose.prod.yml ps
	@echo "\nBackend health:"
	@curl -s http://localhost:8000/system/health | jq . || echo "Backend not responding"
	@echo "\nNeo4j health:"
	@curl -s http://localhost:7474 > /dev/null && echo "Neo4j: OK" || echo "Neo4j: DOWN"

# ============================================================================
# Security Commands
# ============================================================================

.PHONY: scan
scan: ## Scan images for vulnerabilities
	docker scan mahoun/backend:latest || echo "Docker scan not available"

.PHONY: generate-secrets
generate-secrets: ## Generate random secrets for .env
	@echo "# Generated secrets - Add these to your .env file"
	@echo "SECURITY_JWT_SECRET=$$(openssl rand -base64 32)"
	@echo "API_KEY=$$(openssl rand -base64 32)"
	@echo "DB_NEO4J_PASSWORD=$$(openssl rand -base64 32)"
	@echo "DB_POSTGRES_PASSWORD=$$(openssl rand -base64 32)"
	@echo "REDIS_PASSWORD=$$(openssl rand -base64 32)"
	@echo "GRAFANA_ADMIN_PASSWORD=$$(openssl rand -base64 32)"

# ============================================================================
# CI/CD Commands
# ============================================================================

.PHONY: ci-build
ci-build: ## Build for CI/CD
	docker build -t mahoun/backend:${VERSION} -f Dockerfile.backend --target production .

.PHONY: ci-test
ci-test: ## Run tests in CI/CD
	docker build -t mahoun/backend:test -f Dockerfile.backend --target testing .
	docker run --rm mahoun/backend:test pytest tests/ -v --tb=short --timeout=90

.PHONY: ci-push
ci-push: ## Push images to registry (requires login)
	docker push mahoun/backend:${VERSION}
	docker push mahoun/frontend:${VERSION}


# ============================================================================
# Verification Test Commands (Full Stack Integration)
# ============================================================================

.PHONY: verify
verify: ## Run verification tests with full stack (Neo4j, Postgres, Redis, ChromaDB)
	@echo "🚀 Starting Full Stack Verification Tests..."
	docker-compose -f docker-compose.verification.yml up --build --abort-on-container-exit
	docker-compose -f docker-compose.verification.yml down

.PHONY: verify-super-extreme
verify-super-extreme: ## Run SUPER EXTREME tests (100+ concurrent, adversarial attacks)
	@echo "🔥 Starting SUPER EXTREME Tests..."
	docker-compose -f docker-compose.verification.yml up --build super-extreme-tests --abort-on-container-exit
	docker-compose -f docker-compose.verification.yml down

.PHONY: verify-all
verify-all: ## Run ALL verification tests (normal + super extreme)
	@echo "🎯 Running ALL Verification Tests..."
	docker-compose -f docker-compose.verification.yml up --build --abort-on-container-exit
	docker-compose -f docker-compose.verification.yml down

.PHONY: verify-clean
verify-clean: ## Clean verification test environment
	docker-compose -f docker-compose.verification.yml down -v
	docker volume prune -f

.PHONY: verify-logs
verify-logs: ## Show verification test logs
	docker-compose -f docker-compose.verification.yml logs -f verification-tests

.PHONY: verify-coverage
verify-coverage: ## Extract coverage reports from verification tests
	@echo "📊 Extracting coverage reports..."
	docker-compose -f docker-compose.verification.yml up -d verification-tests
	docker cp $$(docker-compose -f docker-compose.verification.yml ps -q verification-tests):/tmp/coverage ./coverage-reports
	docker-compose -f docker-compose.verification.yml down
	@echo "✅ Coverage reports extracted to ./coverage-reports"

# ============================================================================
# Quick Test Commands (No Docker)
# ============================================================================

.PHONY: test-verify-local
test-verify-local: ## Run verification tests locally (requires local setup)
	MAHOUN_DETERMINISTIC_TESTING=true pytest tests/verification/ -v --tb=short

.PHONY: test-super-extreme-local
test-super-extreme-local: ## Run super extreme tests locally
	MAHOUN_DETERMINISTIC_TESTING=true pytest tests/verification/test_category_4_super_extreme.py -v -s

.PHONY: test-category-1
test-category-1: ## Run Category 1 (Easy) tests locally
	MAHOUN_DETERMINISTIC_TESTING=true pytest tests/verification/test_category_1_easy.py -v

.PHONY: test-category-2
test-category-2: ## Run Category 2 (Medium) tests locally
	MAHOUN_DETERMINISTIC_TESTING=true pytest tests/verification/test_category_2_medium.py -v

.PHONY: test-category-3
test-category-3: ## Run Category 3 (Extreme) tests locally
	MAHOUN_DETERMINISTIC_TESTING=true pytest tests/verification/test_category_3_extreme.py -v

.PHONY: test-category-4
test-category-4: ## Run Category 4 (Super Extreme) tests locally
	MAHOUN_DETERMINISTIC_TESTING=true pytest tests/verification/test_category_4_super_extreme.py -v -s
