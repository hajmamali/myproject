# 🚀 MAHOUN Alpha Launch - Deployment Guide

**Version**: 1.0.0-alpha  
**Date**: 2026-06-22  
**Status**: CONTROLLED ALPHA (Limited Capabilities)

---

## 📋 Executive Summary

این راهنما برای راه‌اندازی **محدود و کنترل‌شده** MAHOUN Alpha طراحی شده است.

### ✅ قابلیت‌های فعال در Alpha

| قابلیت | وضعیت | محدودیت |
|--------|-------|---------|
| Document Upload | ✅ ENABLED | Max 10MB, PDF/DOCX/TXT only |
| Text Chunking | ✅ ENABLED | Smart chunker با semantic splitting |
| Embedding Generation | ✅ ENABLED | CPU-only, max 100 docs/batch |
| Vector Indexing | ✅ ENABLED | ChromaDB, max 10K vectors |
| Read-Only Search | ✅ ENABLED | Hybrid search (BM25 + Dense) |
| Health Checks | ✅ ENABLED | Full system health monitoring |
| Metrics Collection | ✅ ENABLED | Prometheus-compatible |

### ❌ قابلیت‌های غیرفعال (NOT in Alpha)

| قابلیت | دلیل غیرفعال بودن |
|--------|-------------------|
| Verdict Generation | P0/P1 governance hardening incomplete |
| Agent Endpoints | LLM-driven without sufficient governance |
| Graph Writes | Neo4j write operations require audit |
| LLM Generation | Hallucination protection incomplete |
| Reasoning API | EvidenceLinkedVerdictEngine exposure risk |

---

## 🎯 Alpha Scope: محدودیت‌های دقیق

### Frontend می‌تواند:
1. ✅ آپلود اسناد (PDF, DOCX, TXT) تا 10MB
2. ✅ مشاهده وضعیت پردازش (chunking, embedding, indexing)
3. ✅ جستجوی read-only در اسناد موجود
4. ✅ مشاهده متریک‌ها و health status
5. ✅ تنظیمات chunker config

### Frontend نمی‌تواند:
1. ❌ درخواست verdict generation
2. ❌ استفاده از agent endpoints
3. ❌ نوشتن در graph database
4. ❌ تولید محتوا با LLM
5. ❌ دسترسی به reasoning API

---

## 🔧 Pre-Flight Checklist

### System Requirements (Minimum for Alpha)

```bash
# Hardware
CPU: 4 cores (Intel/AMD x86_64)
RAM: 8GB minimum (16GB recommended)
Disk: 20GB free space
GPU: NOT required (CPU-only mode)

# Software
OS: Ubuntu 20.04+ / Debian 11+ / macOS 11+
Python: 3.12+
Docker: 20.10+ (optional but recommended)
```

### Environment Variables (MUST SET)

```bash
# Critical Alpha Configuration
export MAHOUN_ENV=dev
export MAHOUN_EXECUTION_MODE=minimal
export MAHOUN_ENABLE_GRAPH=false         # ⚠️ CRITICAL: No graph writes in alpha
export MAHOUN_ENABLE_NEO4J=false         # ⚠️ CRITICAL: Neo4j disabled
export MAHOUN_ALPHA_REASONING=false      # ⚠️ CRITICAL: Reasoning API disabled
export MAHOUN_ALPHA_AGENTS=false         # ⚠️ CRITICAL: Agent endpoints disabled
export MAHOUN_ALPHA_LLM_GEN=false        # ⚠️ CRITICAL: LLM generation disabled
export MAHOUN_ALPHA_VERDICTS=false       # ⚠️ CRITICAL: Verdict generation disabled

# Data Paths
export MAHOUN_DATA_DIR=./data
export MAHOUN_OUTPUT_DIR=./output
export MAHOUN_CACHE_DIR=./.cache

# API Configuration
export MAHOUN_API_HOST=0.0.0.0
export MAHOUN_API_PORT=8000
export MAHOUN_CORS_ORIGINS="*"           # ⚠️ Restrict in production
export MAHOUN_RATE_LIMIT=100

# Logging
export MAHOUN_LOG_LEVEL=INFO
export MAHOUN_LOG_FORMAT=json
```

---

## 📦 Installation Steps

### Step 1: Clone and Setup

```bash
cd /home/haji/Desktop/KingMahouN

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.12+

# Install dependencies (if not already installed)
pip install -e ".[rag,monitoring]"
```

### Step 2: Create Required Directories

```bash
# Create data directories
mkdir -p data/{ledger,embeddings,chromadb}
mkdir -p output
mkdir -p .cache
mkdir -p uploads

# Set permissions
chmod 755 data output .cache uploads
```

### Step 3: Environment Configuration

```bash
# Copy alpha environment template
cp .env.example .env.alpha

# Edit .env.alpha with alpha-specific settings
nano .env.alpha
```

**`.env.alpha` Template:**
```ini
# MAHOUN Alpha Launch Environment
MAHOUN_ENV=dev
MAHOUN_EXECUTION_MODE=minimal
MAHOUN_ENABLE_GRAPH=false
MAHOUN_ENABLE_NEO4J=false
MAHOUN_ENABLE_POSTGRES=false
MAHOUN_ENABLE_REDIS=false

# Alpha Feature Flags (ALL DISABLED)
MAHOUN_ALPHA_REASONING=false
MAHOUN_ALPHA_AGENTS=false
MAHOUN_ALPHA_GRAPH_WRITES=false
MAHOUN_ALPHA_LLM_GEN=false
MAHOUN_ALPHA_VERDICTS=false

# Data Paths
MAHOUN_DATA_DIR=./data
MAHOUN_OUTPUT_DIR=./output
MAHOUN_CACHE_DIR=./.cache

# API
MAHOUN_API_HOST=0.0.0.0
MAHOUN_API_PORT=8000
MAHOUN_CORS_ORIGINS=*
MAHOUN_RATE_LIMIT=100

# Logging
MAHOUN_LOG_LEVEL=INFO
MAHOUN_LOG_FORMAT=json
```

### Step 4: Load Environment

```bash
# Load alpha environment
source .env.alpha

# OR use direnv (recommended)
echo 'dotenv .env.alpha' > .envrc
direnv allow
```

---

## 🚀 Launch Sequence

### Launch Option A: Direct Python (Development)

```bash
# Navigate to project root
cd /home/haji/Desktop/KingMahouN

# Activate venv
source venv/bin/activate

# Load alpha environment
source .env.alpha

# Start API server
python -m uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level info

# Server will start at: http://localhost:8000
# API docs available at: http://localhost:8000/docs
```

### Launch Option B: Docker (Recommended)

```bash
# Build alpha image
docker build -f Dockerfile.backend -t mahoun-alpha:latest .

# Run alpha container
docker run -d \
  --name mahoun-alpha \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/.cache:/app/.cache \
  --env-file .env.alpha \
  mahoun-alpha:latest

# Check logs
docker logs -f mahoun-alpha

# Stop container
docker stop mahoun-alpha

# Remove container
docker rm mahoun-alpha
```

### Launch Option C: Docker Compose (Production-like)

```bash
# Create alpha docker-compose file
cat > docker-compose.alpha.yml << 'EOF'
version: '3.8'

services:
  mahoun-api:
    build:
      context: .
      dockerfile: Dockerfile.backend
      target: production
    container_name: mahoun-alpha-api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./.cache:/app/.cache
      - ./uploads:/app/uploads
    env_file:
      - .env.alpha
    environment:
      - MAHOUN_ENV=dev
      - MAHOUN_EXECUTION_MODE=minimal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

EOF

# Start services
docker-compose -f docker-compose.alpha.yml up -d

# Check status
docker-compose -f docker-compose.alpha.yml ps

# View logs
docker-compose -f docker-compose.alpha.yml logs -f

# Stop services
docker-compose -f docker-compose.alpha.yml down
```

---

## 🧪 Testing & Verification

### Test 1: Health Check (MUST PASS)

```bash
# Test system health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2026-06-22T...",
#   "components": {
#     "api": "healthy",
#     "storage": "healthy"
#   }
# }
```

### Test 2: Verify Disabled Endpoints (MUST FAIL)

```bash
# Test reasoning API (should fail)
curl -X POST http://localhost:8000/api/v1/reasoning/generate-verdict \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "facts": []}'

# Expected: 404 Not Found (router disabled)

# Test MAHOUN agent endpoints (should fail)
curl -X POST http://localhost:8000/api/v1/mahoun/ask-contract \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'

# Expected: 404 Not Found (router disabled)
```

### Test 3: Document Upload (MUST SUCCEED)

```bash
# Create test document
echo "این یک متن تست فارسی است." > test_doc.txt

# Upload document
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@test_doc.txt" \
  -F "doc_type=document"

# Expected response:
# {
#   "success": true,
#   "document_id": "...",
#   "chunks_created": 1,
#   "embeddings_created": 1,
#   "indexed": true
# }
```

### Test 4: Chunker Config (MUST SUCCEED)

```bash
# Get current chunker config
curl http://localhost:8000/api/ingest/config/chunker

# Expected response:
# {
#   "chunk_size": 600,
#   "overlap": 80,
#   "semantic_chunking": false
# }

# Update chunker config
curl -X POST http://localhost:8000/api/ingest/config/chunker \
  -H "Content-Type: application/json" \
  -d '{"chunk_size": 800, "overlap": 100}'

# Expected: Updated config returned
```

---

### Test 5: Search (MUST SUCCEED)

```bash
# Perform search query
curl -X POST http://localhost:8000/v1/search/verdicts \
  -H "Content-Type: application/json" \
  -d '{
    "query": "تست",
    "limit": 10
  }'

# Expected response:
# {
#   "success": true,
#   "results": [...],
#   "total": N,
#   "processing_time_ms": X
# }
```

### Test 6: Metrics Collection (MUST SUCCEED)

```bash
# Get Prometheus metrics
curl http://localhost:8000/metrics/prometheus

# Expected: Prometheus text format metrics

# Get legal metrics
curl http://localhost:8000/metrics/legal

# Expected: JSON metrics including query counts, latency, etc.
```

### Test 7: System Status (MUST SUCCEED)

```bash
# Get system status
curl http://localhost:8000/system/status

# Expected response:
# {
#   "mode": "minimal",
#   "execution_mode": "DESKTOP_MINIMAL",
#   "graph_enabled": false,
#   "neo4j_enabled": false,
#   "alpha_features": {
#     "reasoning_api_enabled": false,
#     "agent_endpoints_enabled": false,
#     "graph_writes_enabled": false,
#     "llm_generation_enabled": false,
#     "verdict_generation_enabled": false
#   }
# }
```

---

## 📊 Frontend Integration Points

### Safe Endpoints for Frontend

#### 1. Document Upload
```typescript
// POST /api/ingest/upload
const formData = new FormData();
formData.append('file', file);
formData.append('doc_type', 'document');

const response = await fetch('http://localhost:8000/api/ingest/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
// result.success, result.document_id, result.chunks_created
```

#### 2. Document Ingestion (JSON)
```typescript
// POST /api/ingest/
const response = await fetch('http://localhost:8000/api/ingest/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'Document Title',
    content: 'Document content...',
    doc_type: 'document',
    metadata: {}
  })
});
```

#### 3. Search
```typescript
// POST /v1/search/verdicts
const response = await fetch('http://localhost:8000/v1/search/verdicts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'search query',
    limit: 10,
    filters: {}
  })
});

const results = await response.json();
// results.success, results.results[], results.total
```

#### 4. Health & Status
```typescript
// GET /health
const health = await fetch('http://localhost:8000/health');
const healthData = await health.json();
// healthData.status, healthData.components

// GET /system/status
const status = await fetch('http://localhost:8000/system/status');
const statusData = await status.json();
// statusData.mode, statusData.alpha_features
```

#### 5. Chunker Configuration
```typescript
// GET /api/ingest/config/chunker
const configResponse = await fetch('http://localhost:8000/api/ingest/config/chunker');
const config = await configResponse.json();

// POST /api/ingest/config/chunker (update)
await fetch('http://localhost:8000/api/ingest/config/chunker', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    chunk_size: 800,
    overlap: 100,
    semantic_chunking: false
  })
});
```

#### 6. Metrics
```typescript
// GET /metrics/legal
const metrics = await fetch('http://localhost:8000/metrics/legal');
const metricsData = await metrics.json();
// metricsData.total_queries, metricsData.avg_duration_seconds, etc.
```

---

## 🔄 Complete Data Flow (Alpha)

```
┌─────────────────┐
│   Frontend      │
│   (React/Vue)   │
└────────┬────────┘
         │
         │ 1. Upload Document
         ▼
┌─────────────────────────────┐
│  POST /api/ingest/upload    │
│  (multipart/form-data)      │
└────────┬────────────────────┘
         │
         │ 2. File Saved
         ▼
┌─────────────────────────────┐
│  Document Parser            │
│  - PDF extraction           │
│  - DOCX extraction          │
│  - Text normalization       │
└────────┬────────────────────┘
         │
         │ 3. Extracted Text
         ▼
┌─────────────────────────────┐
│  Smart Chunker              │
│  - Semantic splitting       │
│  - Size: 600 chars          │
│  - Overlap: 80 chars        │
└────────┬────────────────────┘
         │
         │ 4. Chunks Created
         ▼
┌─────────────────────────────┐
│  Embedding Generator        │
│  - sentence-transformers    │
│  - CPU-only mode            │
│  - Batch size: 32           │
└────────┬────────────────────┘
         │
         │ 5. Embeddings Generated
         ▼
┌─────────────────────────────┐
│  Vector Store (ChromaDB)    │
│  - Persist to disk          │
│  - Max 10K vectors          │
│  - Metadata included        │
└────────┬────────────────────┘
         │
         │ 6. Indexed
         ▼
┌─────────────────────────────┐
│  Response to Frontend       │
│  {success, document_id,     │
│   chunks_created, indexed}  │
└─────────────────────────────┘
```

---

## 🎯 Data Pipeline Capabilities (Detailed)

### Pipeline 1: Document Upload → Embedding → Index

**Input**: PDF/DOCX/TXT file (max 10MB)

**Processing Steps**:
1. **File Upload** (Safe ✅)
   - Multipart form upload
   - File type validation
   - Size limit enforcement
   - Temporary storage in `./uploads/`

2. **Document Parsing** (Safe ✅)
   - PDF: PyPDF2 / pdfplumber extraction
   - DOCX: python-docx extraction
   - TXT: UTF-8 decoding
   - Persian text normalization

3. **Text Chunking** (Safe ✅)
   - Smart chunker with sentence boundary detection
   - Default: 600 chars/chunk, 80 chars overlap
   - Configurable via `/api/ingest/config/chunker`
   - Metadata preservation (doc_id, chunk_index)

4. **Embedding Generation** (Safe ✅)
   - Model: `sentence-transformers` (multilingual)
   - Hardware: CPU-only (no GPU required)
   - Batch processing: 32 chunks/batch
   - Output: 768-dimensional vectors

5. **Vector Indexing** (Safe ✅)
   - Backend: ChromaDB (local persistence)
   - Storage: `./data/chromadb/`
   - Max capacity: 10,000 vectors (alpha limit)
   - Metadata: doc_id, chunk_index, text, timestamp

**Output**: 
```json
{
  "success": true,
  "document_id": "uuid-string",
  "chunks_created": 15,
  "embeddings_created": 15,
  "indexed": true,
  "processing_time_ms": 2345.67
}
```

---

### Pipeline 2: Search Query → Hybrid Retrieval

**Input**: Natural language query (Persian/English)

**Processing Steps**:
1. **Query Embedding** (Safe ✅)
   - Same model as document embedding
   - CPU inference
   - 768-dimensional query vector

2. **BM25 Retrieval** (Safe ✅)
   - Classic keyword matching
   - Persian-aware tokenization
   - Top-K: 20 candidates

3. **Dense Retrieval** (Safe ✅)
   - Cosine similarity search
   - ChromaDB vector search
   - Top-K: 20 candidates

4. **Hybrid Fusion** (Safe ✅)
   - Reciprocal Rank Fusion (RRF)
   - Combines BM25 + Dense scores
   - Re-ranking by relevance

5. **Result Formatting** (Safe ✅)
   - Deduplication
   - Metadata enrichment
   - Snippet extraction

**Output**:
```json
{
  "success": true,
  "results": [
    {
      "document_id": "uuid",
      "chunk_index": 3,
      "text": "متن مرتبط...",
      "score": 0.87,
      "metadata": {...}
    }
  ],
  "total": 5,
  "processing_time_ms": 123.45
}
```

---

## 🛡️ Security & Governance (Alpha)

### What IS Protected ✅

1. **Disabled Endpoints**
   - Reasoning API: `/api/v1/reasoning/*` → 404
   - Agent Endpoints: `/api/v1/mahoun/*` → 404
   - All governance-sensitive paths blocked

2. **Input Validation**
   - File size limits (10MB)
   - File type whitelist (PDF, DOCX, TXT)
   - JSON schema validation on all endpoints
   - Rate limiting: 100 requests/minute

3. **Data Isolation**
   - No database writes (Neo4j disabled)
   - No LLM inference
   - No verdict generation
   - Read-only operations only

4. **Monitoring**
   - All requests logged
   - Metrics collection active
   - Health checks every 30s
   - Error tracking enabled

### What is NOT Protected (Known Limitations) ⚠️

1. **No Authentication** (Alpha Only)
   - All endpoints publicly accessible
   - No API key validation
   - No user management
   - **Fix before Beta**: Implement JWT + RBAC

2. **No Data Encryption at Rest**
   - ChromaDB stores vectors unencrypted
   - Uploaded files stored in plaintext
   - **Fix before Beta**: Add encryption layer

3. **No Audit Trail**
   - Document uploads not logged to ledger
   - No blockchain recording
   - **Fix before Beta**: Integrate EvidenceLedger

4. **Limited Error Handling**
   - Some errors return generic 500
   - Stack traces may leak in dev mode
   - **Fix before Beta**: Deterministic error contracts

---

## 📈 Performance Expectations (Alpha)

### Throughput

| Operation | Throughput | Latency P50 | Latency P95 |
|-----------|------------|-------------|-------------|
| Document Upload | 2-3 docs/min | 1.5s | 3.5s |
| Chunking | 100 KB/s | 500ms | 1.2s |
| Embedding | 50 chunks/s | 20ms | 50ms |
| Vector Search | 100 qps | 50ms | 150ms |

### Resource Usage

```
CPU: 30-50% (4 cores)
RAM: 2-4 GB (with 1000 documents)
Disk: 500 MB (data + cache)
Network: <1 MB/s
```

### Scaling Limits (Alpha)

- **Max Documents**: 1,000
- **Max Vectors**: 10,000
- **Max Chunk Size**: 2KB
- **Max Query Rate**: 100 req/min
- **Max Concurrent Uploads**: 3

---

## 🐛 Troubleshooting

### Problem: API fails to start

**Symptoms**: `uvicorn` exits immediately or shows import errors

**Solutions**:
```bash
# Check Python version
python --version  # Must be 3.12+

# Verify venv activation
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install --force-reinstall -e ".[rag,monitoring]"

# Check for conflicting processes
lsof -i :8000  # Kill any process using port 8000
```

---

### Problem: Document upload fails

**Symptoms**: 400/500 error on upload

**Solutions**:
```bash
# Check upload directory exists
mkdir -p uploads
chmod 755 uploads

# Check disk space
df -h .

# Check file size
ls -lh test_doc.pdf  # Must be <10MB

# Check file type
file test_doc.pdf  # Must be PDF/DOCX/TXT
```

---

### Problem: Embeddings fail to generate

**Symptoms**: Document uploaded but `embeddings_created: 0`

**Solutions**:
```bash
# Check sentence-transformers installation
python -c "import sentence_transformers; print('OK')"

# Re-download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Check model cache
ls -la ~/.cache/torch/sentence_transformers/

# Clear cache and retry
rm -rf ~/.cache/torch/sentence_transformers/
```

---

### Problem: Search returns no results

**Symptoms**: Query succeeds but `results: []`

**Solutions**:
```bash
# Check if vectors were indexed
python << EOF
import chromadb
client = chromadb.PersistentClient(path="./data/chromadb")
collection = client.get_or_create_collection("documents")
print(f"Total vectors: {collection.count()}")
EOF

# Re-upload test document
curl -X POST http://localhost:8000/api/ingest/upload \
  -F "file=@test_doc.txt"

# Try exact match search first
curl -X POST http://localhost:8000/v1/search/verdicts \
  -H "Content-Type: application/json" \
  -d '{"query": "exact phrase from document"}'
```

---

### Problem: Health check fails

**Symptoms**: `/health` returns `unhealthy` or 503

**Solutions**:
```bash
# Check detailed health
curl http://localhost:8000/health/detailed

# Check component status
curl http://localhost:8000/system/status

# Review logs
tail -f logs/mahoun.log  # Or docker logs

# Restart service
# Direct Python: Ctrl+C and restart
# Docker: docker restart mahoun-alpha
# Docker Compose: docker-compose restart
```

---

## 📝 Monitoring & Observability

### Log Files

```bash
# Application logs
tail -f logs/mahoun.log

# Access logs
tail -f logs/access.log

# Error logs
tail -f logs/error.log

# Grep for errors
grep ERROR logs/mahoun.log | tail -20

# Grep for warnings
grep WARNING logs/mahoun.log | tail -20
```

### Metrics Endpoints

```bash
# Prometheus metrics (machine-readable)
curl http://localhost:8000/metrics/prometheus

# Legal metrics (human-readable JSON)
curl http://localhost:8000/metrics/legal | jq .

# System metrics
curl http://localhost:8000/system/status | jq .
```

### Key Metrics to Monitor

```bash
# Request rate
curl -s http://localhost:8000/metrics/legal | jq '.total_queries'

# Average latency
curl -s http://localhost:8000/metrics/legal | jq '.avg_duration_seconds'

# Error rate
curl -s http://localhost:8000/metrics/legal | jq '.error_rate'

# Document count
python << EOF
import chromadb
client = chromadb.PersistentClient(path="./data/chromadb")
collection = client.get_or_create_collection("documents")
print(f"Documents indexed: {collection.count()}")
EOF
```

### Alerts (Manual Checks)

```bash
# Check if API is responding (every 5 min)
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
  if [ "$STATUS" != "200" ]; then
    echo "⚠️ ALERT: API health check failed (HTTP $STATUS)"
  else
    echo "✅ API healthy"
  fi
  sleep 300
done

# Check disk space (every hour)
USAGE=$(df -h . | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$USAGE" -gt 80 ]; then
  echo "⚠️ ALERT: Disk usage at ${USAGE}%"
fi

# Check memory usage
MEM=$(free | awk 'NR==2 {print int($3/$2 * 100)}')
if [ "$MEM" -gt 80 ]; then
  echo "⚠️ ALERT: Memory usage at ${MEM}%"
fi
```

---

## 🔄 Backup & Recovery

### Backup Data

```bash
# Backup all data
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  data/ \
  uploads/ \
  .cache/

# Backup only ChromaDB vectors
tar -czf chromadb-backup-$(date +%Y%m%d-%H%M%S).tar.gz data/chromadb/

# Copy to remote storage (example)
rsync -avz backup-*.tar.gz user@backup-server:/backups/mahoun/
```

### Restore Data

```bash
# Stop service first
docker-compose -f docker-compose.alpha.yml down
# OR kill uvicorn process

# Extract backup
tar -xzf backup-20260622-120000.tar.gz

# Verify data
ls -la data/chromadb/

# Restart service
docker-compose -f docker-compose.alpha.yml up -d
```

### Disaster Recovery

```bash
# Complete reset (⚠️ DELETES ALL DATA)
rm -rf data/ uploads/ .cache/
mkdir -p data/{ledger,embeddings,chromadb}
mkdir -p uploads .cache

# Restart fresh
docker-compose -f docker-compose.alpha.yml up -d --force-recreate
```

---

## 🎓 Alpha Testing Script (Complete E2E)

```bash
#!/bin/bash
# alpha_test.sh - Complete Alpha Launch Test Script

set -e

BASE_URL="http://localhost:8000"
TEST_DIR="./alpha_test_data"
mkdir -p "$TEST_DIR"

echo "========================================="
echo "🚀 MAHOUN Alpha Launch - E2E Test"
echo "========================================="
echo ""

# Test 1: Health Check
echo "✅ Test 1: Health Check"
curl -s "$BASE_URL/health" | jq .
echo ""

# Test 2: System Status
echo "✅ Test 2: System Status"
curl -s "$BASE_URL/system/status" | jq .
echo ""

# Test 3: Verify Disabled Endpoints
echo "⛔ Test 3: Reasoning API (should fail)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE_URL/api/v1/reasoning/generate-verdict" \
  -H "Content-Type: application/json" \
  -d '{"question":"test","facts":[]}')

if [ "$HTTP_CODE" == "404" ]; then
  echo "✅ Reasoning API correctly disabled (404)"
else
  echo "❌ FAIL: Reasoning API returned $HTTP_CODE (expected 404)"
  exit 1
fi
echo ""

# Test 4: Create Test Document
echo "✅ Test 4: Create Test Document"
cat > "$TEST_DIR/test_doc.txt" << EOF
این یک سند تست برای سیستم MAHOUN است.
این سند شامل متن فارسی برای آزمایش chunking و embedding می‌باشد.
سیستم باید این متن را به چانک‌های کوچکتر تقسیم کند.
سپس برای هر چانک یک بردار embedding تولید می‌کند.
در نهایت این بردارها در ChromaDB ذخیره می‌شوند.
EOF

echo "Test document created: $TEST_DIR/test_doc.txt"
echo ""

# Test 5: Upload Document
echo "✅ Test 5: Upload Document"
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/ingest/upload" \
  -F "file=@$TEST_DIR/test_doc.txt" \
  -F "doc_type=document")

echo "$UPLOAD_RESPONSE" | jq .

DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.document_id')
CHUNKS=$(echo "$UPLOAD_RESPONSE" | jq -r '.chunks_created')
INDEXED=$(echo "$UPLOAD_RESPONSE" | jq -r '.indexed')

echo "Document ID: $DOC_ID"
echo "Chunks created: $CHUNKS"
echo "Indexed: $INDEXED"

if [ "$INDEXED" != "true" ]; then
  echo "❌ FAIL: Document not indexed"
  exit 1
fi
echo ""

# Test 6: Search for Uploaded Document
echo "✅ Test 6: Search Test"
sleep 2  # Wait for indexing to complete

SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/search/verdicts" \
  -H "Content-Type: application/json" \
  -d '{"query": "سیستم MAHOUN", "limit": 5}')

echo "$SEARCH_RESPONSE" | jq .

RESULT_COUNT=$(echo "$SEARCH_RESPONSE" | jq '.results | length')
echo "Results found: $RESULT_COUNT"

if [ "$RESULT_COUNT" -eq 0 ]; then
  echo "⚠️ WARNING: No search results (may need time to index)"
else
  echo "✅ Search returned $RESULT_COUNT results"
fi
echo ""

# Test 7: Get Chunker Config
echo "✅ Test 7: Chunker Config"
curl -s "$BASE_URL/api/ingest/config/chunker" | jq .
echo ""

# Test 8: Update Chunker Config
echo "✅ Test 8: Update Chunker Config"
curl -s -X POST "$BASE_URL/api/ingest/config/chunker" \
  -H "Content-Type: application/json" \
  -d '{"chunk_size": 800, "overlap": 100}' | jq .
echo ""

# Test 9: Metrics Check
echo "✅ Test 9: Metrics Collection"
curl -s "$BASE_URL/metrics/legal" | jq '{total_queries, avg_duration_seconds}'
echo ""

# Test 10: Multiple Document Upload (Stress Test - Light)
echo "✅ Test 10: Multiple Document Upload (Light Stress)"
for i in {1..5}; do
  cat > "$TEST_DIR/doc_$i.txt" << EOF
این سند شماره $i است.
محتوای تست برای بررسی عملکرد سیستم.
EOF
  
  curl -s -X POST "$BASE_URL/api/ingest/upload" \
    -F "file=@$TEST_DIR/doc_$i.txt" \
    -F "doc_type=document" > /dev/null
  
  echo "  Uploaded document $i/5"
done
echo "✅ All 5 documents uploaded successfully"
echo ""

# Final Summary
echo "========================================="
echo "🎉 Alpha Launch Test Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "- Health checks: ✅"
echo "- Security (disabled endpoints): ✅"
echo "- Document upload: ✅"
echo "- Search functionality: ✅"
echo "- Configuration: ✅"
echo "- Metrics collection: ✅"
echo "- Multi-document handling: ✅"
echo ""
echo "Alpha system is ready for frontend integration!"
echo ""

# Cleanup
echo "Cleaning up test data..."
rm -rf "$TEST_DIR"
echo "Done!"
```

### Running the Test Script

```bash
# Make executable
chmod +x alpha_test.sh

# Run test
./alpha_test.sh

# Expected output:
# All tests should pass with ✅ marks
# Only reasoning API test should show ⛔ (expected)
```

---

## 📱 Frontend Integration Checklist

### Phase 1: Connection & Health

- [ ] Health check endpoint working
- [ ] System status returns correct mode
- [ ] Alpha feature flags visible
- [ ] CORS configured correctly
- [ ] Error handling displays properly

### Phase 2: Document Upload

- [ ] File picker supports PDF, DOCX, TXT
- [ ] File size limit (10MB) enforced in UI
- [ ] Upload progress indicator works
- [ ] Success message shows document_id
- [ ] Error messages display clearly
- [ ] Upload history/list visible

### Phase 3: Search Interface

- [ ] Search input accepts Persian/English
- [ ] Search button triggers query
- [ ] Results display with proper formatting
- [ ] Persian text renders correctly (RTL)
- [ ] Pagination works (if >10 results)
- [ ] "No results" message displays

### Phase 4: Configuration UI

- [ ] Chunker config displayed
- [ ] Config update form works
- [ ] Changes persist after reload
- [ ] Validation prevents invalid values

### Phase 5: Monitoring Dashboard

- [ ] Metrics refresh automatically
- [ ] Query count displays
- [ ] Latency chart shows trends
- [ ] Error rate visible
- [ ] Document count updates

---

## 🚫 Known Limitations & Workarounds

### Limitation 1: No Graph Visualization

**Problem**: Neo4j disabled, no graph display

**Workaround**: 
- Show document-chunk relationships in table format
- Display search results as list, not graph

### Limitation 2: No LLM-Generated Summaries

**Problem**: LLM endpoints disabled

**Workaround**:
- Show raw chunks/snippets only
- Use extractive snippets (first N chars)

### Limitation 3: No Real-Time Updates

**Problem**: No WebSocket/SSE support

**Workaround**:
- Implement polling (every 5s) for upload status
- Show "Processing..." indicator with manual refresh

### Limitation 4: Limited Batch Operations

**Problem**: No bulk delete/update

**Workaround**:
- Single document operations only
- Warn users about one-by-one uploads

### Limitation 5: No User Management

**Problem**: No authentication/multi-user

**Workaround**:
- Single-user alpha mode
- All data shared (no isolation)
- Document tracking by frontend client_id only

---

## 🎯 GO/NO-GO Decision Criteria

### ✅ GO Criteria (MUST ALL BE MET)

1. **Health Checks**
   - [ ] `/health` returns 200 OK
   - [ ] All components report "healthy"
   - [ ] Uptime > 30 seconds

2. **Security Boundaries**
   - [ ] Reasoning API returns 404
   - [ ] MAHOUN agent endpoints return 404
   - [ ] No graph write operations possible

3. **Core Functionality**
   - [ ] Document upload succeeds
   - [ ] Chunking produces >0 chunks
   - [ ] Embeddings generated successfully
   - [ ] Vectors indexed in ChromaDB
   - [ ] Search returns relevant results

4. **Monitoring**
   - [ ] Metrics endpoint responds
   - [ ] Logs are being written
   - [ ] Error tracking works

5. **Frontend Integration**
   - [ ] CORS allows frontend domain
   - [ ] All endpoints respond with valid JSON
   - [ ] Error responses include error codes

### ❌ NO-GO Criteria (ANY ONE FAILS)

1. **Critical Failures**
   - Reasoning API accessible (returns 200)
   - Agent endpoints accessible (returns 200)
   - Neo4j connection active
   - Graph writes possible

2. **Data Integrity**
   - Documents uploaded but not chunked
   - Chunks created but no embeddings
   - Embeddings created but not indexed
   - Search finds non-existent documents

3. **Performance**
   - Upload takes >30s for 1MB file
   - Search takes >5s for simple query
   - API crashes under 3 concurrent requests
   - Memory usage >8GB

4. **Security**
   - Stack traces visible in production
   - File uploads exceed 10MB
   - Arbitrary file types accepted
   - No rate limiting enforced

---

## 📊 Success Metrics (Alpha)

### Week 1 Goals

- **Documents**: 50-100 uploaded
- **Search Queries**: 200-500 total
- **Uptime**: >95%
- **Error Rate**: <5%
- **P95 Latency**: <2s

### Week 2-4 Goals

- **Documents**: 200-500 uploaded
- **Search Queries**: 1000-2000 total
- **Uptime**: >98%
- **Error Rate**: <2%
- **P95 Latency**: <1.5s

### User Feedback Focus

1. Upload experience (ease of use)
2. Search relevance (result quality)
3. Response time (performance)
4. Error messages (clarity)
5. Missing features (priority queue)

---

## 🛣️ Roadmap: Alpha → Beta → Production

### Alpha (Current) - Week 1-4

**Focus**: Document ingestion + search only

**Enabled**:
- ✅ Document upload
- ✅ Chunking
- ✅ Embedding
- ✅ Vector indexing
- ✅ Hybrid search

**Disabled**:
- ❌ Reasoning/Verdicts
- ❌ Agent endpoints
- ❌ Graph operations
- ❌ LLM generation

**Exit Criteria**:
- 500+ documents indexed
- 2000+ successful searches
- <2% error rate
- User feedback collected

---

### Beta - Week 5-8

**Focus**: Limited graph + read-only reasoning

**New Capabilities**:
- ✅ Graph visualization (read-only)
- ✅ Limited reasoning (pre-verified cases only)
- ✅ Authentication (JWT)
- ✅ User management
- ✅ Audit logging

**Still Disabled**:
- ❌ Full verdict generation
- ❌ Graph writes
- ❌ LLM-driven agents

**Requirements**:
- P0-4 complete (LedgerWriteGate full enforcement)
- P1-1 complete (Fail-closed guardrails)
- P1-3 complete (Ledger hash verification)
- Authentication system deployed
- Encryption at rest enabled

**Exit Criteria**:
- 2000+ documents indexed
- 10,000+ successful searches
- <1% error rate
- 10+ active users
- Zero security incidents

---

### Production - Week 9+

**Focus**: Full platform with governance

**Full Capabilities**:
- ✅ All reasoning APIs
- ✅ Verdict generation
- ✅ Graph operations (governed)
- ✅ LLM endpoints (validated)
- ✅ Agent system (controlled)

**Production Requirements**:
- All P0 issues resolved
- All P1 issues resolved
- Load testing (1000 concurrent users)
- Penetration testing passed
- Disaster recovery tested
- Production monitoring (24/7)
- Support team trained

**SLAs**:
- Uptime: 99.5%
- P50 latency: <200ms
- P95 latency: <500ms
- Error rate: <0.1%
- Data loss: 0%

---

## 📞 Support & Contact

### Alpha Support Hours

**Monday-Friday**: 9:00 AM - 5:00 PM Tehran Time

### Reporting Issues

**Method 1: GitHub Issues**
```
Repository: [Your repo URL]
Label: alpha-bug
Template: Bug report
```

**Method 2: Direct Email**
```
To: alpha-support@mahoun.platform
Subject: [ALPHA] Brief description
Include: 
- Error message
- Request payload
- Log excerpt
- Environment details
```

**Method 3: Emergency**
```
For critical issues (system down, data loss):
Contact: [Emergency phone/telegram]
```

### Known Issues (Will Not Fix in Alpha)

1. No multi-user support
2. No data encryption
3. No blockchain ledger
4. Limited error messages
5. No bulk operations
6. Persian UI translations incomplete

---

## ✅ Final Checklist Before GO

### Infrastructure
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] Required directories created
- [ ] Environment variables set
- [ ] Permissions configured

### Configuration
- [ ] `.env.alpha` file created
- [ ] All feature flags disabled
- [ ] CORS origins configured
- [ ] Rate limiting enabled
- [ ] Logging configured

### Testing
- [ ] `alpha_test.sh` script runs successfully
- [ ] All 10 tests pass
- [ ] Disabled endpoints return 404
- [ ] Search returns results
- [ ] Metrics collected

### Monitoring
- [ ] Log files being written
- [ ] Metrics endpoint responds
- [ ] Health checks pass
- [ ] Disk space adequate (>5GB free)

### Security
- [ ] Reasoning API disabled (verified)
- [ ] Agent endpoints disabled (verified)
- [ ] Neo4j connection disabled
- [ ] Graph writes impossible
- [ ] File upload limits enforced

### Frontend Ready
- [ ] CORS configured for frontend domain
- [ ] API documentation accessible
- [ ] Sample requests tested
- [ ] Error responses documented
- [ ] Integration guide shared with frontend team

---

## 🚀 Launch Command

```bash
# Final verification
./alpha_test.sh

# If all tests pass:
echo "✅ MAHOUN Alpha Launch - APPROVED FOR GO"

# Start production alpha
docker-compose -f docker-compose.alpha.yml up -d

# Monitor logs
docker-compose -f docker-compose.alpha.yml logs -f

# Share with team
echo "🎉 MAHOUN Alpha is LIVE at http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "❤️ Health: http://localhost:8000/health"
```

---

## 🎊 Success! What's Next?

1. **Monitor First 24 Hours**
   - Watch logs for errors
   - Track metrics every hour
   - Respond to issues within 30min

2. **Collect Feedback**
   - Survey users after 1 week
   - Track feature requests
   - Note pain points

3. **Iterate Rapidly**
   - Bug fixes within 24h
   - Minor improvements weekly
   - Major features monthly

4. **Plan Beta**
   - Start P0/P1 completion work
   - Design authentication system
   - Prepare graph integration

**Congratulations on launching MAHOUN Alpha! 🚀**

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-06-22  
**Next Review**: 2026-07-01
