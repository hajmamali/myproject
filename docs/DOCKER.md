# 🐳 MAHOUN Platform - Docker Architecture & Operations

**Document**: Production Docker Architecture  
**Version**: 2.0  
**Last Updated**: 2024-12-29  
**Status**: Production-Ready

---

## Overview

This document describes the production-grade Docker architecture for the MAHOUN Platform, including:
- Container security and hygiene
- Multi-stage builds
- Profile-based deployments
- Health monitoring
- Disaster recovery

For quick-start instructions, see [DOCKER_GUIDE.md](../DOCKER_GUIDE.md).

---

## Architecture Principles

### 1. Security First
- ✅ All containers run as non-root users
- ✅ Multi-stage builds (minimal attack surface)
- ✅ No secrets in images or compose files
- ✅ Read-only filesystems where possible
- ✅ Network isolation via internal bridge

### 2. Deterministic Builds
- ✅ Pinned base image versions
- ✅ Lockfile-based dependency installation
- ✅ Reproducible builds across environments
- ✅ BuildKit caching for speed

### 3. Production Hygiene
- ✅ Health checks on all services
- ✅ Graceful shutdown handling
- ✅ Resource limits (CPU/memory)
- ✅ Proper log management
- ✅ Volume-based persistence

### 4. Developer Experience
- ✅ One-command startup: `make docker-up`
- ✅ Profile-based deployment (minimal/full)
- ✅ Hot-reload compatible (local dev)
- ✅ CI-friendly (no GPU, external service requirements)

---

## Container Images

### Backend Image (`mahoun/backend:latest`)

**Base**: `python:3.12.7-slim-bookworm`  
**Size**: ~450 MB  
**User**: `mahoun` (uid=1000, gid=1000)

**Build Strategy**:
```dockerfile
Stage 1: Builder
  - Install build dependencies (gcc, g++, libpq-dev)
  - Copy requirements.txt
  - Install Python packages to ~/.local

Stage 2: Runtime
  - Install only runtime dependencies (curl, libpq5)
  - Copy Python packages from builder
  - Copy application code
  - Run as non-root user
```

**Healthcheck**: `curl -f http://localhost:8000/system/health`  
**Startup Time**: ~30-60s  
**Dependencies**: requirements.txt (pinned versions)

**Environment Variables**:
- `PYTHONUNBUFFERED=1` - Real-time logging
- `PYTHONDONTWRITEBYTECODE=1` - No .pyc files
- `PYTHONHASHSEED=random` - Security

### Frontend Image (`mahoun/frontend:latest`)

**Base**: `node:20.12.2-alpine3.19` (build), `nginx:1.27.3-alpine` (runtime)  
**Size**: ~60 MB  
**User**: `nginx` (uid=101)

**Build Strategy**:
```dockerfile
Stage 1: Dependencies
  - Copy package.json, package-lock.json
  - npm ci (clean install from lockfile)

Stage 2: Builder
  - Copy node_modules from deps stage
  - Copy source code
  - npm run build (Vite)

Stage 3: Runtime
  - Copy dist/ from builder
  - Copy nginx.conf
  - Run as nginx user
```

**Healthcheck**: `curl -f http://localhost/`  
**Startup Time**: ~5-10s  
**Dependencies**: package-lock.json (pinned versions)

---

## Service Profiles

### `default` (Always Active)
```yaml
services:
  - backend (FastAPI)
  - frontend (Nginx)
```

**Use Case**: Local development, CI, minimal testing  
**RAM**: 1-2 GB  
**Startup**: `docker compose up -d`

### `full` Profile
```yaml
services:
  - backend
  - frontend
  - neo4j (Graph database)
  - postgres (Relational database)
  - redis (Cache/sessions)
  - chromadb (Vector store)
```

**Use Case**: Full-stack development, staging, production  
**RAM**: 6-8 GB  
**Startup**: `docker compose --profile full up -d`

### `monitoring` Profile
```yaml
services:
  - prometheus (Metrics collection)
  - grafana (Monitoring dashboard)
```

**Use Case**: Production monitoring  
**RAM**: +1-2 GB  
**Startup**: `docker compose --profile full --profile monitoring up -d`

---

## Networking

### Internal Network
```yaml
networks:
  mahoun-internal:
    driver: bridge
    subnet: 172.28.0.0/16
```

**Service Discovery**:
- Backend → `http://backend:8000`
- Frontend → `http://frontend:80`
- Neo4j → `bolt://neo4j:7687`
- Postgres → `postgres:5432`
- Redis → `redis:6379`
- ChromaDB → `chromadb:8000`

**External Exposure**:
- Frontend: `0.0.0.0:80` → `frontend:80`
- Backend: `0.0.0.0:8000` → `backend:8000`
- Neo4j Browser: `0.0.0.0:7474` → `neo4j:7474`
- Neo4j Bolt: `0.0.0.0:7687` → `neo4j:7687`

---

## Data Persistence

### Named Volumes
```yaml
volumes:
  mahoun_neo4j_data:     # Neo4j graph data
  mahoun_postgres_data:  # PostgreSQL data
  mahoun_redis_data:     # Redis snapshots
  mahoun_chromadb_data:  # Vector embeddings
  mahoun_prometheus_data: # Metrics history
  mahoun_grafana_data:   # Grafana config
```

### Host Mounts
```yaml
./data:/app/data                    # Application data
./uploads:/app/uploads              # User uploads
./vector_store_data:/app/vector_store_data  # ChromaDB (alternative)
./output:/app/output                # Generated reports
./runtime:/app/runtime              # Traces, profiles
```

**Backup Strategy**:
1. Named volumes → Docker volume backup
2. Host mounts → Standard filesystem backup
3. Databases → pg_dump, neo4j-admin dump

---

## Health Monitoring

### Service Health Checks

| Service    | Endpoint                            | Interval | Timeout | Retries |
|------------|-------------------------------------|----------|---------|---------|
| Backend    | `GET /system/health`                | 30s      | 5s      | 3       |
| Frontend   | `GET /`                             | 30s      | 3s      | 3       |
| Neo4j      | `cypher-shell RETURN 1`             | 15s      | 10s     | 5       |
| Postgres   | `pg_isready`                        | 10s      | 5s      | 5       |
| Redis      | `redis-cli ping`                    | 10s      | 3s      | 3       |
| ChromaDB   | `GET /api/v1/heartbeat`             | 15s      | 5s      | 3       |
| Prometheus | `GET /-/healthy`                    | 30s      | 5s      | 3       |
| Grafana    | `GET /api/health`                   | 30s      | 5s      | 3       |

### Dependency Management

```yaml
backend:
  depends_on:
    # Services NOT in depends_on - backend is graceful
    # It will work without external services in desktop_minimal mode
```

**Design Principle**: Backend starts independently, gracefully handles missing services.

---

## Resource Limits

### Laptop-Safe Defaults

```yaml
backend:
  limits:
    cpus: '2.0'
    memory: 2G
  reservations:
    cpus: '0.5'
    memory: 512M

neo4j:
  limits:
    cpus: '2.0'
    memory: 4G
  reservations:
    cpus: '0.5'
    memory: 2G

redis:
  limits:
    cpus: '1.0'
    memory: 1G
  reservations:
    cpus: '0.1'
    memory: 128M
```

**Tuning**:
- Development: Use defaults
- Production: Increase limits based on load testing
- Low-RAM systems: Reduce Neo4j heap size

---

## Security Model

### Container Users

| Service    | User       | UID  | Home Directory        |
|------------|------------|------|-----------------------|
| Backend    | mahoun     | 1000 | /home/mahoun          |
| Frontend   | nginx      | 101  | /var/cache/nginx      |
| Neo4j      | neo4j      | 7474 | /var/lib/neo4j        |
| Postgres   | postgres   | 70   | /var/lib/postgresql   |
| Redis      | redis      | 999  | /data                 |

### Secrets Management

**Environment Variables** (`.env` - gitignored):
```bash
NEO4J_PASSWORD=<generated>
POSTGRES_PASSWORD=<generated>
JWT_SECRET_KEY=<generated>
REDIS_PASSWORD=<generated>
```

**Generation**:
```bash
openssl rand -base64 32  # Passwords
openssl rand -base64 64  # JWT secret
```

**Production**: Use Docker secrets or external secret manager (Vault, AWS Secrets Manager).

### Network Security

1. **Internal Network**: Services communicate via bridge network
2. **Firewall**: Only necessary ports exposed to host
3. **SSL/TLS**: Terminate SSL at load balancer (nginx/traefik)
4. **CORS**: Configured in backend for allowed origins

---

## CI/CD Integration

### Build in CI
```bash
# .github/workflows/docker.yml
docker compose build --no-cache
docker compose up -d
docker compose exec -T backend pytest
docker compose down
```

### Image Registry
```bash
# Tag and push
docker tag mahoun/backend:latest registry.company.com/mahoun/backend:v1.0.0
docker push registry.company.com/mahoun/backend:v1.0.0

# Pull and deploy
docker pull registry.company.com/mahoun/backend:v1.0.0
docker compose up -d
```

---

## Disaster Recovery

### Backup Procedures

**Daily Backups**:
```bash
#!/bin/bash
# scripts/docker/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${DATE}"
mkdir -p "$BACKUP_DIR"

# Neo4j
docker compose exec neo4j neo4j-admin database dump neo4j --to-stdout \
  > "${BACKUP_DIR}/neo4j.dump"

# Postgres
docker compose exec postgres pg_dump -U mahoun mahoun \
  > "${BACKUP_DIR}/postgres.sql"

# Application data
tar czf "${BACKUP_DIR}/app_data.tar.gz" data/ uploads/ vector_store_data/

echo "✅ Backup complete: ${BACKUP_DIR}"
```

**Restore Procedures**:
```bash
# Neo4j
cat backups/20241229/neo4j.dump | \
  docker compose exec -T neo4j neo4j-admin database load neo4j --from-stdin

# Postgres
cat backups/20241229/postgres.sql | \
  docker compose exec -T postgres psql -U mahoun mahoun

# Application data
tar xzf backups/20241229/app_data.tar.gz
```

### High Availability

**Production Setup**:
1. Load balancer (nginx/traefik) → Multiple backend replicas
2. Neo4j cluster (causal clustering)
3. Postgres replication (streaming)
4. Redis Sentinel (HA)
5. Shared storage (NFS/S3) for uploads

---

## Monitoring & Observability

### Prometheus Metrics
- Container CPU/memory usage
- HTTP request rates
- Response times
- Error rates
- Database connection pools

### Grafana Dashboards
- System overview
- Service health
- Resource utilization
- Custom application metrics

### Logging
```bash
# View logs
docker compose logs -f backend

# JSON logs (production)
docker compose logs --json backend | jq

# Send to central logging
# Configure log driver in docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## Troubleshooting Guide

See [DOCKER_GUIDE.md](../DOCKER_GUIDE.md#troubleshooting) for detailed troubleshooting steps.

**Common Issues**:
1. Port conflicts → Change ports in `.env`
2. Out of memory → Reduce Neo4j heap size
3. Health check failures → Check logs, increase start_period
4. Build failures → Clear cache: `docker builder prune -af`

### Legacy Container/Volume Cleanup

**Problem**: Containers created with manual `docker run` commands (instead of Docker Compose) can cause:
- Wrong volume prefixes (`platform33_*` instead of `mahoun_*`)
- Outdated credentials (e.g., `mahoun123` instead of `.env` values)
- Port conflicts and configuration drift
- Health check failures due to mismatched environment variables

**Symptoms**:
```bash
$ docker ps
CONTAINER      CREATED        STATUS
mahoun-neo4j   12 days ago    Up 2 hours (unhealthy)

$ docker volume ls | grep neo4j
platform33_neo4j_data      # ❌ Wrong prefix
mahoun_neo4j_data          # ✅ Correct prefix
```

**Solution**: Use the cleanup script
```bash
# Check for legacy state
./scripts/docker/clean_legacy_state.sh

# Remove legacy containers/volumes
./scripts/docker/clean_legacy_state.sh --force

# Recreate with Docker Compose
COMPOSE_PROFILES=full docker compose up -d
```

**Standard Commands**:
```bash
# Bring up full stack (all databases)
COMPOSE_PROFILES=full docker compose up -d

# Rebuild and restart
COMPOSE_PROFILES=full docker compose up -d --build

# Verify configuration
docker compose config

# Check container health
docker ps --filter "name=mahoun" --format "table {{.Names}}\t{{.Status}}"
```

**Standard Volume Naming**:
- All volumes use `mahoun_` prefix
- Examples: `mahoun_postgres_data`, `mahoun_neo4j_data`, `mahoun_redis_data`
- Any `platform33_*` volumes are legacy and should be removed

---

## Performance Tuning

### Build Optimization
- BuildKit inline cache
- Layer caching (copy dependencies first)
- Multi-stage builds
- Parallel builds: `docker compose build --parallel`

### Runtime Optimization
- Resource limits tuned to workload
- Connection pooling (Postgres, Redis)
- Nginx caching (static assets)
- Health check intervals optimized

---

## Migration Guide

### From Old Docker Setup
```bash
# 1. Stop old stack
docker-compose down

# 2. Backup data
./scripts/docker/backup.sh

# 3. Update files
git pull

# 4. Rebuild
docker compose build --no-cache

# 5. Start new stack
docker compose up -d

# 6. Validate
curl http://localhost:8000/system/health
```

---

## Appendix

### File Structure
```
Platform/
├── Dockerfile.backend          # Backend container
├── docker-compose.yml          # Orchestration
├── .dockerignore               # Backend build context exclusions
├── DOCKER_GUIDE.md             # User-facing guide
├── docs/
│   └── DOCKER.md               # This file (architecture)
├── frontend/
│   ├── Dockerfile              # Frontend container
│   └── .dockerignore           # Frontend build context exclusions
└── scripts/
    └── docker/
        ├── backup.sh           # Backup script
        ├── generate_env_example.sh  # Environment template
        └── validate_docker_setup.sh # Validation script
```

### References
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Compose File Reference](https://docs.docker.com/compose/compose-file/)

---

**Document Owner**: Platform Team  
**Review Cycle**: Quarterly

