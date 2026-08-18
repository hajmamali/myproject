# چک‌لیست متطلبات سیستم MAHOUN
## System Requirements & Dependencies (Beyond Knowledge Graph)

---

## 📋 خلاصه‌ی فوری

| دسته | نیاز | وضعیت | اولویت |
|------|------|--------|--------|
| **Databases** | Neo4j (Graph) + PostgreSQL (Relational) + Redis (Cache) | ⚠️ Partial | P0 |
| **Language Models** | Embedding, NLI, Fine-tuned LLM | ⚠️ Partial | P0 |
| **Document Processing** | OCR, Legal NER, Parser | ✅ Complete | P0 |
| **Legal Data** | Precedents, Statutes, Regulations | ⚠️ Skeleton | P1 |
| **Authentication** | OAuth2, JWT, Role-based access | ✅ Complete | P1 |
| **Infrastructure** | Docker, K8s, Monitoring, Logging | ✅ Complete | P1 |
| **Frontend** | React dashboard, API client | ✅ Complete | P0 |
| **API Gateway** | FastAPI routers, Health checks | ✅ Complete | P0 |

---

## 🗄️ 1. Databases & Storage

### 1.1 Neo4j (Graph Database)

**نقش**: ذخیره‌ی Evidence Graph + Knowledge Graph

**چه چیزهایی ذخیره می‌شود**:
- Evidence nodes: documents, entities (people, companies), claims, dates
- Relationships: causality, contradiction, support, reference, jurisdiction
- Knowledge: legal rules, precedents, applicable statutes
- Provenance: who, when, source, hash

**نیاز برای Production**:
```yaml
Neo4j Setup:
  - Instance: Local (docker) یا Remote (Neo4j Aura)
  - Version: >= 4.4 (APOC support)
  - Credentials: username + password (MUST be set)
  - Storage: 50GB+ initial (scalable)
  - Indexes:
    - document_id (fast evidence lookup)
    - entity_type (fast NER lookups)
    - rule_id (fast precedent matching)
    - hash (provenance verification)
  - Constraints:
    - Unique entity IDs per case
    - Unique evidence references
```

**فایل‌های مرتبط**:
- [mahoun/graph/neo4j/connection.py](../mahoun/graph/neo4j/connection.py)
- [mahoun/graph/neo4j/init_schema.py](../mahoun/graph/neo4j/init_schema.py)
- [mahoun/core/governance/database_init.py](../mahoun/core/governance/database_init.py)

**نحوه‌ی راه‌اندازی**:
```bash
# Option 1: Docker
docker run --name mahoun-neo4j \
  -e NEO4J_AUTH=neo4j/YOUR_SECURE_PASSWORD \
  -p 7687:7687 \
  -v $PWD/neo4j_data:/data \
  neo4j:5.15-community

# Option 2: Neo4j Aura (cloud)
# Sign up at aura.neo4j.io and get connection URI

# Environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=YOUR_SECURE_PASSWORD
export DB_NEO4J_PASSWORD=YOUR_SECURE_PASSWORD
```

---

### 1.2 PostgreSQL (Relational Database)

**نقش**: ذخیره‌ی metadata، audit trails، user accounts

**چه چیزهایی ذخیره می‌شود**:
- Case metadata (ID, title, created_at, updated_at)
- User accounts + roles + permissions
- Audit logs (who did what, when)
- Ledger metadata (commit timestamps, checksums)
- Task queue (ingestion jobs, reasoning tasks)

**نیاز برای Production**:
```yaml
PostgreSQL Setup:
  - Version: >= 13
  - Database: mahoun_db
  - Credentials: mahoun_user + password
  - Tables:
    - users (authentication)
    - cases (case metadata)
    - documents (document registry)
    - audit_logs (governance trails)
    - ledger_commits (transaction log)
    - tasks (async job queue)
  - Backups: Daily snapshots
  - Connection pooling: 20-50 connections
```

**نحوه‌ی راه‌اندازی**:
```bash
# Option 1: Docker
docker run --name mahoun-postgres \
  -e POSTGRES_USER=mahoun_user \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  -e POSTGRES_DB=mahoun_db \
  -p 5432:5432 \
  -v $PWD/postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Option 2: Managed (RDS, Azure Database, etc.)

# Environment variables
export DB_POSTGRES_USER=mahoun_user
export DB_POSTGRES_PASSWORD=YOUR_PASSWORD
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=mahoun_db
```

**فایل‌های مرتبط**:
- [api/database.py](../api/database.py) - Pool management
- [alembic/](../alembic/) - Schema migrations

---

### 1.3 Redis (Cache & Session Store)

**نقش**: Caching، rate limiting، session management

**چه چیزهایی ذخیره می‌شود**:
- RAG cache (Query → Retrieved documents)
- Embedding cache (Text → Vector)
- User sessions (Token → User info)
- Rate limit counters (IP → Request count)

**نیاز برای Production**:
```yaml
Redis Setup:
  - Version: >= 7
  - Mode: Single-instance یا Cluster
  - TTL policies: 1h (sessions), 24h (embeddings)
  - Memory: 4-8GB
  - Persistence: RDB snapshots
  - Authentication: requirepass
```

**نحوه‌ی راه‌اندازی**:
```bash
# Option 1: Docker
docker run --name mahoun-redis \
  -e REDIS_PASSWORD=YOUR_PASSWORD \
  -p 6379:6379 \
  -v $PWD/redis_data:/data \
  redis:7-alpine redis-server --requirepass YOUR_PASSWORD

# Environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=YOUR_PASSWORD
```

---

## 🤖 2. Language Models

### 2.1 Embedding Model

**نقش**: تبدیل متن به vectors برای Dense Retrieval در RAG

**مدل‌های پیشنهادی**:
```yaml
Options:
  1. sentence-transformers/paraphrase-multilingual-mpnet-base-v2
     - Size: 420MB
     - Dims: 768
     - Languages: 50+ (Persian support ✓)
     - Speed: 500 docs/sec on CPU

  2. sentence-transformers/LaBSE (Language-Agnostic BERT)
     - Size: 330MB
     - Dims: 768
     - Languages: 109
     - Best for Persian-English pairs

  3. OpenAI API (Paid)
     - Size: N/A (API-based)
     - Dims: 1536
     - Cost: ~$0.02 per 1K docs
```

**Integration**:
```python
# mahoun/rag/hybrid_rag_service.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
embeddings = model.encode(["document text 1", "document text 2"])
# → shape: (2, 768)
```

**نحوه‌ی Setup**:
```bash
# Option 1: Local
pip install sentence-transformers
export EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2

# Option 2: API-based (OpenAI)
export OPENAI_API_KEY=sk-...
export EMBEDDING_BACKEND=openai
```

---

### 2.2 NLI Model (Natural Language Inference)

**نقش**: تحقق‌کردن اینکه generated text از evidence خارج نمی‌شود

**مدل‌های پیشنهادی**:
```yaml
Options:
  1. microsoft/deberta-v3-large (Best accuracy)
     - Size: 1.2GB
     - Accuracy: 95%+
     - Speed: Slower (GPU recommended)

  2. sentence-transformers/cross-encoder/ms-marco-MiniLM-L-6-v2 (Balanced)
     - Size: 60MB
     - Accuracy: 90%
     - Speed: Fast (CPU-friendly)

  3. facebook/bart-large-mnli (General purpose)
     - Size: 1.6GB
     - Accuracy: 90%
```

**Integration**:
```python
# mahoun/guardrails/ultra_nli_verifier.py
from sentence_transformers import CrossEncoder

model = CrossEncoder('ms-marco-MiniLM-L-6-v2')
scores = model.predict([
    ["Evidence: Company A signed contract on Jan 1, 2024",
     "Generated: Company A is contractually bound"],
    ["Evidence: No prior communication recorded",
     "Generated: Company A was aware of terms"]
])
# → [2.0 (entailment), 0.1 (contradiction)]
```

**نحوه‌ی Setup**:
```bash
pip install sentence-transformers
export NLI_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

---

### 2.3 Fine-tuned Legal Language Model

**نقش**: ترجمه‌ی structured verdict → readable narrative

**گزینه‌ها**:
```yaml
Options:
  1. Local Fine-tuned (Best privacy)
     - Base: Llama 2 7B یا Mistral 7B
     - Training: Persian legal corpus (1M+ docs)
     - Time: 7 days on single GPU
     - Cost: ~$500 (cloud compute)

  2. Fine-tuned via OpenAI API
     - Base: GPT-3.5-turbo
     - Training: Upload corpus, OpenAI trains
     - Cost: ~$1-2 per 1M tokens

  3. Commercial Persian LLM
     - Example: "Alpaca-Persian" یا "Parsi-LLaMA"
     - Size: 7B-13B parameters
     - Pre-trained on Persian
```

**متطلبات Training Data**:
```
Training Data:
  - 1,000+ pairs of (structured_verdict → narrative)
  - Persian legal documents
  - Court decisions
  - Contract analyses
  - Format: JSON with {input: verdict_struct, output: narrative}
```

**نحوه‌ی Setup**:
```bash
# Option 1: Use fine-tuned model (if available)
export LLM_MODEL_PATH=/models/legal-llm-7b-persian
export LLM_BACKEND=local_gpu

# Option 2: OpenAI API
export OPENAI_API_KEY=sk-...
export LLM_BACKEND=openai
```

---

### 2.4 OCR Model

**نقش**: استخراج متن از تصاویر (scanned PDFs)

**مدل**: Paddle OCR (already integrated)
```python
# mahoun/pipelines/ingestion/hardened_paddle_ocr.py
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    lang=['fa', 'en'],  # Persian + English
    use_angle_cls=True,
    use_gpu=False  # Set to True if CUDA available
)
result = ocr.ocr('page_image.png')
# → [{"text": "...", "confidence": 0.95}, ...]
```

**نحوه‌ی Setup**:
```bash
# Already in requirements.txt
pip install paddleocr

# Download models (automatic on first run)
# Models cached in ~/.paddleocr/

export PADDLEOCR_USE_GPU=false  # or true if CUDA available
```

---

## ⚖️ 3. Legal Data & Knowledge

### 3.1 Precedents & Case Law

**نیاز**: مجموعه‌ای از تصمیمات سابقه‌ای برای rule/precedent matching

**منابع**:
```yaml
Sources:
  1. Official Databases
     - دادگاه‌های ایران (Official court decisions)
     - سازمان قضایی (Judiciary portal)
     - Code repository for laws

  2. Commercial Providers
     - WestLaw (International)
     - LexisNexis (International)
     - Tamyiz.ir (Iran-specific)

  3. Open Source
     - GitHub: IR legal-corpus
     - HuggingFace: Persian legal datasets

  4. In-house Collection
     - Scrape + structure relevant cases
     - Digitize from official reports
```

**فرمت ذخیره‌سازی**:
```json
{
  "precedent_id": "IR-2023-001",
  "court": "Supreme Court",
  "date": "2023-05-15",
  "parties": ["Company A", "Company B"],
  "summary": "Contract dispute regarding payment terms",
  "holding": "Seller has right to withhold goods if payment overdue",
  "applicable_rules": ["Iranian Civil Code Article 395"],
  "keywords": ["contract", "payment", "goods"],
  "full_text": "..."
}
```

**Integration in Knowledge Graph**:
```python
# mahoun/reasoning/knowledge_graph.py
graph.add_precedent(
    precedent_id="IR-2023-001",
    holding="Seller has right to withhold goods",
    applicable_to=["payment disputes", "commercial contracts"]
)
```

---

### 3.2 Legal Rules & Statutes

**نیاز**: مجموعه‌ای ساختار‌یافته‌ی قوانین و مقررات

**منابع**:
```yaml
Sources:
  1. Iranian Civil Code (1307 H.)
  2. Commercial Code (1311 H.)
  3. Labor Code (1371 H.)
  4. Administrative Procedures Act
  5. Corporate Governance Regulations
  6. Regional/Sector-specific rules
```

**فرمت ذخیره‌سازی**:
```json
{
  "rule_id": "ICC-395",
  "source": "Iranian Civil Code",
  "article": 395,
  "title": "Seller's Right to Withhold Goods",
  "text": "If buyer fails to pay, seller may withhold goods",
  "conditions": ["payment_overdue", "goods_not_delivered"],
  "consequences": ["can_withhold", "can_seek_damages"],
  "exceptions": ["force_majeure", "buyer_bankruptcy"],
  "jurisdiction": "Iran",
  "effective_date": "1307-01-01"
}
```

---

### 3.3 Entity Dictionary

**نیاز**: لیست recognized entities برای NER بهتری

```json
{
  "companies": [
    {"name": "نفت ایران", "aliases": ["NIOC", "National Iranian Oil Company"]},
    {"name": "بانک مرکزی", "aliases": ["Central Bank of Iran", "CBI"]},
  ],
  "courts": [
    {"name": "دیوان عدالت اداری", "type": "administrative", "jurisdiction": "national"},
  ],
  "legal_terms": [
    {"term": "عقد", "meaning": "contract", "domain": "civil_law"},
  ]
}
```

---

## 🔐 4. Governance & Authentication

### 4.1 OAuth2 / JWT Setup

**فایل‌های مرتبط**:
- [api/auth/](../api/auth/) - Authentication routers
- [api/middleware/](../api/middleware/) - JWT validation

**متطلبات**:
```yaml
Setup:
  - Secret key (for JWT signing)
  - OAuth2 provider (optional): Google, Microsoft, OIDC
  - Role definitions: admin, analyst, reviewer, viewer
  - Permission matrix
```

**نحوه‌ی Configuration**:
```bash
export SECURITY_JWT_SECRET=your_32_char_minimum_secret_key
export JWT_ALGORITHM=HS256
export JWT_EXPIRATION_HOURS=24
```

---

### 4.2 Governance Context

**فایل‌های مرتبط**:
- [mahoun/core/governance/governance_context.py](../mahoun/core/governance/governance_context.py)
- [mahoun/core/governance/mutation_boundary.py](../mahoun/core/governance/mutation_boundary.py)

**متطلبات**: فعال بودن GovernanceContextManager برای هر request

```python
# Example: Every reasoning request must have active context
async with GovernanceContextManager.active_context(
    correlation_id="case-2024-001",
    execution_mode="STRICT",
    actor_id="analyst-123"
) as ctx:
    result = await reasoning_engine.reason(request)
```

---

## 📊 5. Monitoring & Logging

### 5.1 Prometheus Metrics

**فایل**: [mahoun/metrics/](../mahoun/metrics/)

**متریک‌های مهم**:
```python
- mahoun_verdict_generation_duration_seconds
- mahoun_rag_retrieval_latency_seconds
- mahoun_nli_verification_passed_total
- mahoun_graph_queries_total
- mahoun_governance_violations_total
- mahoun_ledger_commits_total
```

### 5.2 Logging

**فایل**: [mahoun/core/fortress_validator.py](../mahoun/core/fortress_validator.py)

**Log levels**:
- DEBUG: Detailed reasoning steps
- INFO: Case processing milestones
- WARNING: Configuration issues
- ERROR: Failed verifications
- CRITICAL: Governance violations

---

## 🚀 6. Infrastructure

### 6.1 Docker Compose (Local Development)

**فایل**: [docker-compose.dev.yml](../docker-compose.dev.yml)

**Services**:
```yaml
services:
  mahoun-api:
    build: .
    ports: [8000:8000]
    env_file: .env
  
  mahoun-neo4j:
    image: neo4j:5.15
    env:
      NEO4J_AUTH: neo4j/password
  
  mahoun-postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: password
  
  mahoun-redis:
    image: redis:7
    command: redis-server --requirepass password
```

### 6.2 Kubernetes (Production)

**فایل‌ها**: [k8s/](../k8s/)

**متطلبات**:
- Helm charts for easy deployment
- Persistent volumes for databases
- Service mesh for inter-pod communication
- Ingress for API gateway

---

## 📋 7. Configuration & Secrets

### 7.1 Environment Variables

```bash
# Database
DB_POSTGRES_USER=mahoun_user
DB_POSTGRES_PASSWORD=<secure>
DB_NEO4J_PASSWORD=<secure>
REDIS_PASSWORD=<secure>

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j

# Models
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
NLI_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
LLM_BACKEND=local_gpu  # or openai

# Mode
MAHOUN_MODE=server_full
MAHOUN_GRAPH_ENABLED=true
MAHOUN_GRAPH_BACKEND=local_full
ENABLE_NEO4J=true

# Security
SECURITY_JWT_SECRET=<32+ chars>
SECURITY_CORS_ORIGINS=https://yourdomain.com

# Optional
OPENAI_API_KEY=<if using OpenAI>
```

### 7.2 .env File Template

```bash
cat > .env << EOF
# Database Credentials
DB_POSTGRES_USER=mahoun_user
DB_POSTGRES_PASSWORD=<generate_secure_password>
DB_POSTGRES_HOST=localhost
DB_POSTGRES_PORT=5432
POSTGRES_DB=mahoun_db

DB_NEO4J_PASSWORD=<generate_secure_password>
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<generate_secure_password>

# Models
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
NLI_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# System
MAHOUN_MODE=server_full
MAHOUN_GRAPH_ENABLED=true
ENABLE_NEO4J=true

# Security
SECURITY_JWT_SECRET=<generate_32_char_secret>
EOF
```

---

## 📝 8. Document Input Pipeline

### 8.1 Scanner Integration

**فایل**: [api/routers/ingest.py](../api/routers/ingest.py)

**Supported formats**:
- PDF (native + scanned)
- TIFF (multi-page)
- JPG/PNG (single page)
- DOCX (Microsoft Word)

**Input methods**:
```python
1. File upload (HTTP POST)
2. Scanner integration (TWAIN/WIA)
3. S3 bucket (cloud storage)
4. Batch processing (zip file)
```

### 8.2 Processing Pipeline

```
Input Document
  ↓
File type detection
  ↓
If PDF: Extract text OR apply OCR
If Image: Apply OCR
If DOCX: Extract text + metadata
  ↓
Language detection (Persian/English/Mixed)
  ↓
Text normalization (diacritics, spacing)
  ↓
Legal NER (extract entities)
  ↓
Ingestion into Graph + Ledger
```

---

## ✅ 9. Pre-flight Checklist

قبل از راه‌اندازی production:

```
DATABASE SETUP
☐ Neo4j instance running + credentials set
☐ PostgreSQL database created + schema migrated
☐ Redis instance running + password secured
☐ Backup strategy configured

MODELS DOWNLOADED
☐ Embedding model cached
☐ NLI model cached
☐ Fine-tuned LLM available (local or API)
☐ OCR models cached

LEGAL DATA LOADED
☐ Precedents imported into Neo4j
☐ Statutes/Rules indexed
☐ Entity dictionary available
☐ Knowledge graph initialized

INFRASTRUCTURE READY
☐ Docker/K8s cluster provisioned
☐ Logging aggregation (ELK/Loki)
☐ Monitoring (Prometheus/Grafana)
☐ Secrets vault configured (Vault/AWS Secrets)

AUTHENTICATION CONFIGURED
☐ JWT secret generated
☐ OAuth2 provider configured (if needed)
☐ CORS origins set correctly
☐ HTTPS certificates issued

TESTING COMPLETED
☐ Unit tests pass
☐ Integration tests pass
☐ End-to-end workflow tested
☐ Performance benchmarked
☐ Security audit passed

DOCUMENTATION
☐ API docs generated (Swagger)
☐ Operator runbooks written
☐ Disaster recovery plan documented
☐ Legal compliance checklist reviewed
```

---

## 🎯 خلاصه‌ی نهایی

برای راه‌اندازی MAHOUN production-ready، نیاز است:

| دسته | موارد | تخمین وقت |
|------|-------|-----------|
| **Databases** | Neo4j + PostgreSQL + Redis setup | 1-2 روز |
| **Models** | Download + Cache 4 models | 4-6 ساعت |
| **Legal Data** | Import precedents + statutes | 2-3 روز |
| **Infrastructure** | Docker/K8s + Monitoring | 3-5 روز |
| **Testing** | Full regression suite | 2-3 روز |
| **Documentation** | APIs, runbooks, SLAs | 2 روز |

**مجموع**: ~2-3 هفته برای یک deployment production-grade.

