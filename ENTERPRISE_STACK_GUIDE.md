# MAHOUN Enterprise Stack - Complete Guide

## 🚀 **Architecture Overview**

MAHOUN Enterprise Stack یک معماری کاملاً enterprise-grade با ۶ service اصلی:

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAHOUN ENTERPRISE STACK                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Governance  │  │   API        │  │     MCP      │          │
│  │   Kernel     │  │   Server     │  │   Server     │          │
│  │   (87MB)     │  │   (200MB)    │  │   (100MB)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                          │                                      │
│  ┌───────────────────────┼───────────────────────┐              │
│  │        DATA LAYER (Profile: storage)           │              │
│  ├───────────┬───────────┼───────────┬───────────┤              │
│  │   Neo4j   │PostgreSQL │   Redis   │ ChromaDB  │              │
│  │  (Graph)  │  (RDBMS)  │  (Cache)  │ (Vector)  │              │
│  │  8GB RAM  │  4GB RAM  │  2GB RAM  │  4GB RAM  │              │
│  └───────────┴───────────┴───────────┴───────────┘              │
│                                                                  │
│  ┌─────────────────────────────────────────────────┐            │
│  │        MONITORING LAYER (Profile: monitoring)    │            │
│  ├──────────────────────┬──────────────────────────┤            │
│  │     Prometheus       │        Grafana            │            │
│  │    (Metrics)         │      (Dashboards)         │            │
│  └──────────────────────┴──────────────────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 **Service Specifications**

### **1. Governance Kernel (87MB)**
- **Purpose:** Pure governance runtime, zero external dependencies
- **Port:** 8080
- **Features:** 
  - ✅ Non-root container (user 1001)
  - ✅ Read-only filesystem
  - ✅ Health checks every 30s
  - ✅ 512MB memory limit
  - ✅ Independent scaling

### **2. API Server (200MB)**
- **Purpose:** FastAPI endpoints, business logic coordinator
- **Port:** 8000
- **Features:**
  - ✅ Non-root container
  - ✅ Governance Kernel integration
  - ✅ Redis-backed caching
  - ✅ JWT authentication
  - ✅ Rate limiting

### **3. MCP Server (100MB)**
- **Purpose:** Model Context Protocol for AI integrations
- **Port:** 8001
- **Features:**
  - ✅ Lightweight footprint
  - ✅ Governance-aware
  - ✅ Tool registry
  - ✅ Protocol compliance

### **4. Neo4j Enterprise (Profile: storage)**
- **Purpose:** Graph database for legal knowledge graphs
- **Ports:** 7687 (Bolt), 7474 (HTTP), 7473 (HTTPS)
- **Features:**
  - ✅ APOC & GDS plugins enabled
  - ✅ 4GB heap + 2GB page cache
  - ✅ Prometheus metrics on port 2004
  - ✅ Automated backups
  - ✅ Query performance monitoring

### **5. PostgreSQL Enterprise (Profile: storage)**
- **Purpose:** Relational database for structured legal data
- **Port:** 5432
- **Features:**
  - ✅ 1GB shared buffers + 3GB cache
  - ✅ WAL archiving enabled
  - ✅ Row-level security
  - ✅ SCRAM-SHA-256 encryption
  - ✅ Streaming replication ready

### **6. Redis Enterprise**
- **Purpose:** Caching, rate limiting, session management
- **Port:** 6379
- **Features:**
  - ✅ 1GB max memory with LRU eviction
  - ✅ Hybrid persistence (RDB + AOF)
  - ✅ Latency monitoring (100ms threshold)
  - ✅ 4 workers for high concurrency

### **7. ChromaDB Enterprise (Profile: storage)**
- **Purpose:** Vector store for embeddings and RAG
- **Port:** 8001
- **Features:**
  - ✅ Token-based authentication
  - ✅ SQLite WAL mode for performance
  - ✅ Hourly automated backups
  - ✅ 100MB segment optimization
  - ✅ 7-day backup retention

---

## 🎯 **Deployment Profiles**

### **Minimal (Default)**
```bash
docker-compose up -d
```
- **Services:** Governance Kernel + API Server + Redis
- **Total Size:** ~340MB
- **Use Case:** Development, lightweight production
- **Hardware:** 4GB RAM, 2 CPU cores

### **Storage (Full Stack)**
```bash
docker-compose --profile storage up -d
```
- **Services:** All databases + core services
- **Total Size:** ~1.4GB
- **Use Case:** Full feature development, testing
- **Hardware:** 16GB RAM, 8 CPU cores

### **Production (Enterprise)**
```bash
docker-compose -f docker-compose.yml --profile production up -d
```
- **Services:** Everything optimized for production
- **Total Size:** ~1.6GB
- **Use Case:** Production deployment
- **Hardware:** 32GB RAM, 16 CPU cores

---

## ⚙️ **Quick Start Guide**

### **1. Initial Setup**
```bash
# Clone repository
cd KingMahouN

# Create environment file
cp .env.enterprise .env

# EDIT .env AND CHANGE ALL PASSWORDS!
vim .env

# Setup directories and permissions
chmod +x scripts/manage_enterprise_stack.sh
./scripts/manage_enterprise_stack.sh setup
```

### **2. Start Minimal Stack**
```bash
# Start core services only
docker-compose up -d

# Check status
./scripts/manage_enterprise_stack.sh status

# View logs
./scripts/manage_enterprise_stack.sh logs
```

### **3. Start Full Stack**
```bash
# Start with databases
docker-compose --profile storage up -d

# Verify all services healthy
docker-compose ps
```

### **4. Production Deployment**
```bash
# Use production profile
docker-compose --profile production up -d

# Enable monitoring
docker-compose --profile monitoring up -d
```

---

## 🔧 **Management Operations**

### **Database Backups**
```bash
# Backup all databases
./scripts/manage_enterprise_stack.sh backup

# Backup location: ./backups/
# - neo4j/neo4j_backup_YYYYMMDD_HHMMSS.tar.gz
# - postgres/postgres_backup_YYYYMMDD_HHMMSS.sql.gz
# - redis/redis_backup_YYYYMMDD_HHMMSS.rdb
# - chromadb/chromadb_backup_YYYYMMDD_HHMMSS.tar.gz
```

### **Performance Monitoring**
```bash
# Show metrics
./scripts/manage_enterprise_stack.sh metrics

# Example output:
# NAME                      CPU %    MEM USAGE / LIMIT     NET I/O
# mahoun-governance-kernel  2.34%    180MiB / 512MiB      12MB / 8MB
# mahoun-api-server         5.12%    350MiB / 1GiB        45MB / 30MB
# mahoun-neo4j-enterprise   12.5%    2.1GiB / 8GiB        120MB / 80MB
```

### **Security Operations**
```bash
# Run security scan
./scripts/manage_enterprise_stack.sh security-scan

# Check configuration
cat .env | grep PASSWORD  # Verify all changed
ls -la .env               # Should be 600 permissions
```

### **Maintenance**
```bash
# Clean old backups (keep 7 days)
./scripts/manage_enterprise_stack.sh cleanup 7

# Optimize databases
./scripts/manage_enterprise_stack.sh optimize

# View service logs
./scripts/manage_enterprise_stack.sh logs neo4j 200
```

---

## 🛡️ **Security Features**

### **Container Security**
- ✅ All containers run as non-root users
- ✅ Read-only filesystems where applicable
- ✅ Capability dropping (CAP_DROP ALL)
- ✅ No new privileges flag
- ✅ Security scanning with Trivy

### **Network Security**
- ✅ Network segmentation (4 isolated networks)
- ✅ Inter-container communication controlled
- ✅ IP masquerading enabled
- ✅ No IPv6 (reduces attack surface)

### **Data Security**
- ✅ SCRAM-SHA-256 for PostgreSQL
- ✅ Token-based auth for ChromaDB
- ✅ Password-protected Redis
- ✅ Encrypted connections (SSL/TLS ready)
- ✅ Row-level security (PostgreSQL)

### **Backup Security**
- ✅ Automated encrypted backups
- ✅ 30-day default retention
- ✅ Compression enabled
- ✅ Separate backup volumes

---

## 📈 **Performance Tuning**

### **Neo4j Optimization**
```bash
# Adjust in .env
NEO4J_HEAP_INITIAL=2G
NEO4J_HEAP_MAX=4G
NEO4J_PAGECACHE=2G

# Monitor via
curl http://localhost:7474/metrics
```

### **PostgreSQL Tuning**
```bash
# Adjust in .env
POSTGRES_SHARED_BUFFERS=1GB
POSTGRES_EFFECTIVE_CACHE_SIZE=3GB
POSTGRES_WORK_MEM=32MB

# Check performance
docker-compose exec postgres psql -c "SELECT * FROM pg_stat_activity;"
```

### **Redis Optimization**
```bash
# Adjust in .env
REDIS_MAXMEMORY=1gb

# Monitor
docker-compose exec redis redis-cli -a $REDIS_PASSWORD info memory
```

---

## 🚨 **Troubleshooting**

### **Service Won't Start**
```bash
# Check logs
docker-compose logs <service-name>

# Check disk space
df -h

# Check memory
free -h

# Restart service
docker-compose restart <service-name>
```

### **Database Connection Issues**
```bash
# Test Neo4j connection
docker-compose exec neo4j cypher-shell -u neo4j -p $DB_NEO4J_PASSWORD "RETURN 1"

# Test PostgreSQL
docker-compose exec postgres pg_isready -U mahoun_admin

# Test Redis
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping
```

### **Performance Issues**
```bash
# Check resource usage
docker stats

# Check database metrics
./scripts/manage_enterprise_stack.sh metrics

# Optimize
./scripts/manage_enterprise_stack.sh optimize
```

---

## 📝 **Environment Variables Reference**

### **Critical Variables (MUST CHANGE)**
```bash
DB_NEO4J_PASSWORD=        # Neo4j password
DB_POSTGRES_PASSWORD=     # PostgreSQL password
REDIS_PASSWORD=           # Redis password
SECURITY_JWT_SECRET=      # JWT secret (32+ chars)
API_KEY=                  # API key
CHROMA_TOKEN=             # ChromaDB token
GRAFANA_ADMIN_PASSWORD=   # Grafana password
```

### **Performance Variables**
```bash
# Neo4j
NEO4J_HEAP_MAX=4G
NEO4J_PAGECACHE=2G

# PostgreSQL
POSTGRES_SHARED_BUFFERS=1GB
POSTGRES_EFFECTIVE_CACHE_SIZE=3GB

# Redis
REDIS_MAXMEMORY=1gb

# Resource Limits
NEO4J_MEMORY_LIMIT=8G
POSTGRES_MEMORY_LIMIT=4G
```

---

## 🎓 **Best Practices**

### **Development**
1. Use minimal profile for day-to-day work
2. Start storage profile only when needed
3. Clean up old backups weekly
4. Check logs before reporting issues

### **Production**
1. Change ALL default passwords
2. Enable monitoring profile
3. Set up automated backups (cron)
4. Monitor resource usage daily
5. Run security scans weekly
6. Keep backups off-site

### **Security**
1. Never commit .env file
2. Rotate passwords quarterly
3. Review access logs monthly
4. Update images monthly
5. Run vulnerability scans

---

## 📞 **Support**

### **Logs Location**
```bash
./logs/
├── api/              # API server logs
├── neo4j/            # Neo4j logs
├── postgres/         # PostgreSQL logs
├── redis/            # Redis logs
└── chromadb/         # ChromaDB logs
```

### **Common Commands**
```bash
# Full stack status
docker-compose ps

# Service health
docker inspect mahoun-neo4j-enterprise | jq '.[0].State.Health'

# Resource usage
docker stats --no-stream

# Quick restart
docker-compose restart

# Clean slate
docker-compose down -v  # WARNING: Deletes all data!
```

---

**🎯 با این معماری enterprise-grade، MAHOUN آماده production با بالاترین استانداردهای امنیتی و عملکردی است!**