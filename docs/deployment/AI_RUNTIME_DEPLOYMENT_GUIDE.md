# MAHOUN AI Runtime - Production Deployment Guide

> **Classification**: NEXUS-CLASS DEPLOYMENT DOCUMENTATION  
> **Version**: 2.0.0-NEXUS  
> **Last Updated**: July 2026  
> **Target Audience**: DevOps Engineers, SREs, Platform Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Profiles](#deployment-profiles)
4. [Container Image](#container-image)
5. [Environment Configuration](#environment-configuration)
6. [Model Preparation](#model-preparation)
7. [Deployment Methods](#deployment-methods)
8. [Health Checks](#health-checks)
9. [Monitoring](#monitoring)
10. [Security](#security)
11. [Troubleshooting](#troubleshooting)

---

## Overview

MAHOUN AI Runtime is a production-grade, air-gap compliant AI inference system designed for high-stakes decision-making environments. It provides:

- **Local GGUF model execution** (Llama, Qwen, Mistral families)
- **Air-gap compliance** (zero network dependencies)
- **Deployment profile unity** (single codebase, environment-driven limits)
- **Governance integration** (FortressValidator, RedLines.yaml enforcement)
- **Comprehensive monitoring** (Prometheus metrics, Grafana dashboards, AlertManager)

### Key Features

✅ **Contract-First Architecture** - Frozen G-0 interfaces  
✅ **Memory-Centric Intelligence** - Graph + Retrieval > Model Size  
✅ **Semantic Equivalence** - Desktop Minimal ≡ Enterprise Full (functionality)  
✅ **Zero Network Calls** - Complete offline operation  
✅ **Full Auditability** - Evidence ledger + proof trees

---

## Prerequisites

### System Requirements

#### Desktop Minimal Profile
- **CPU**: 4 cores (x86-64 with AVX2 or ARM64)
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk**: 20 GB free space (models + cache)
- **OS**: Linux (Ubuntu 22.04+, RHEL 8+, or compatible)
- **Container Runtime**: Docker 24.0+ or Podman 4.0+

#### Enterprise Full Profile
- **CPU**: 32+ cores (x86-64 with AVX-512 recommended)
- **RAM**: 128 GB minimum, 256 GB+ recommended
- **Disk**: 500 GB+ SSD/NVMe (models + cache)
- **OS**: Linux (Ubuntu 22.04 LTS or RHEL 8+)
- **Container Runtime**: Docker 24.0+ or Kubernetes 1.27+
- **GPU** (optional): NVIDIA GPU with CUDA 12.1+ for acceleration

### Software Dependencies

The Docker image includes all dependencies. For bare-metal deployment:

```bash
# Python 3.12+
python --version  # Should be >= 3.12

# Required system packages (Ubuntu/Debian)
sudo apt-get install -y \
    build-essential \
    cmake \
    libjemalloc2 \
    libopenblas-dev

# Required system packages (RHEL/CentOS)
sudo yum install -y \
    gcc-c++ \
    cmake \
    jemalloc \
    openblas-devel
```

---

## Deployment Profiles

MAHOUN AI Runtime supports **two deployment profiles** with **identical functionality** but different resource limits.

### Profile Comparison

| Feature | Desktop Minimal | Enterprise Full |
|---------|----------------|-----------------|
| Max Memory | 8 GB | 512 GB |
| Max Concurrent Requests | 10 | 1000 |
| Max Graph Nodes | 100K | 100M |
| Supported Model Sizes | 1B-7B | 1B-70B+ |
| GPU Acceleration | Optional (CPU preferred) | Recommended |
| Use Case | Development, Testing, Edge | Production, High-throughput |

### Selecting a Profile

Set via environment variable:

```bash
export MAHOUN_DEPLOYMENT_PROFILE=DESKTOP_MINIMAL  # or ENTERPRISE_FULL
```

---

## Container Image

### Image: `mahoun/ai-runtime:2.0.0-nexus`

The production image is a **7-stage multi-stage build** with advanced optimizations:

- **Base Stage**: Minimal Ubuntu 22.04 with security patches
- **Builder Stage**: Compile dependencies with PGO (Profile-Guided Optimization)
- **Fortress Stage**: Security hardening (non-root user, capability dropping)
- **Quantum Stage**: AVX-512 optimizations, jemalloc allocator
- **Sentinel Stage**: Runtime monitoring hooks
- **Titan Stage**: Application code + dependency installation
- **Observatory Stage**: Health check instrumentation

### Image Layers

```dockerfile
FROM ubuntu:22.04-slim                    # Base
RUN compile_with_pgo                      # Builder
RUN security_hardening                    # Fortress
RUN performance_tuning                    # Quantum
RUN monitoring_setup                      # Sentinel
COPY mahoun/ /nexus/mahoun                # Titan
HEALTHCHECK CMD python health_probe.py    # Observatory
```

### Build Command

```bash
docker build \
  -f Dockerfile.ai-runtime \
  -t mahoun/ai-runtime:2.0.0-nexus \
  --target observatory \
  .
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Deployment Profile (REQUIRED)
MAHOUN_DEPLOYMENT_PROFILE=DESKTOP_MINIMAL  # or ENTERPRISE_FULL

# Model Paths (REQUIRED)
MAHOUN_MODELS_DIR=/nexus/models
MAHOUN_DATA_DIR=/nexus/data

# Air-Gap Compliance (REQUIRED for production)
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
MAHOUN_ENABLE_NETWORK=false

# Governance (REQUIRED)
MAHOUN_GUARD_MODE=STRICT
MAHOUN_ENV=production
```

### Optional Environment Variables

```bash
# Resource Limits (auto-detected from profile if not set)
MAHOUN_MAX_MEMORY_MB=8192
MAHOUN_MAX_CONCURRENT_REQUESTS=10

# Model Configuration
MAHOUN_DEFAULT_MODEL=llama-3.2-1b-instruct
MAHOUN_ENABLE_GPU=false

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Complete `.env` Example

```bash
# Profile
MAHOUN_DEPLOYMENT_PROFILE=ENTERPRISE_FULL

# Paths
MAHOUN_MODELS_DIR=/nexus/models
MAHOUN_DATA_DIR=/nexus/data

# Air-Gap
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
MAHOUN_ENABLE_NETWORK=false

# Governance
MAHOUN_GUARD_MODE=STRICT
MAHOUN_ENV=production
SECURITY_JWT_SECRET=<generate-with-openssl-rand-base64-32>

# Resources
MAHOUN_MAX_MEMORY_MB=131072  # 128 GB
MAHOUN_MAX_CONCURRENT_REQUESTS=1000

# GPU
MAHOUN_ENABLE_GPU=true
CUDA_VISIBLE_DEVICES=0,1

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Model Preparation

### Supported Models

MAHOUN supports **GGUF format** models from:

- **Llama family**: Llama-3.2 (1B, 3B), Llama-3.1 (8B, 70B)
- **Qwen family**: Qwen2.5 (0.5B, 1.5B, 3B, 7B, 14B, 32B)
- **Mistral family**: Mistral-7B, Mixtral-8x7B

### Downloading Models

Models must be **pre-downloaded** before deployment (air-gap requirement).

```bash
# Create models directory
mkdir -p /nexus/models

# Download from HuggingFace (on a machine WITH internet)
huggingface-cli download \
  TheBloke/Llama-3.2-1B-Instruct-GGUF \
  llama-3.2-1b-instruct.Q4_K_M.gguf \
  --local-dir /nexus/models

# Verify checksum
sha256sum /nexus/models/llama-3.2-1b-instruct.Q4_K_M.gguf
# Compare with expected checksum from model card
```

### Embedding Models

```bash
# Download sentence-transformers models
mkdir -p /nexus/models/embeddings

# BGE Small (recommended for Desktop Minimal)
huggingface-cli download \
  BAAI/bge-small-en-v1.5 \
  --local-dir /nexus/models/embeddings/bge-small-en-v1.5

# BGE Base (recommended for Enterprise Full)
huggingface-cli download \
  BAAI/bge-base-en-v1.5 \
  --local-dir /nexus/models/embeddings/bge-base-en-v1.5
```

### Model Directory Structure

```
/nexus/models/
├── llama-3.2-1b-instruct.Q4_K_M.gguf
├── llama-3.2-3b-instruct.Q4_K_M.gguf
├── qwen2.5-1.5b-instruct.Q4_K_M.gguf
└── embeddings/
    ├── bge-small-en-v1.5/
    │   ├── config.json
    │   ├── pytorch_model.bin
    │   └── tokenizer.json
    └── bge-base-en-v1.5/
        ├── config.json
        ├── model.safetensors
        └── tokenizer.json
```

---

## Deployment Methods

### Method 1: Docker Compose (Recommended for Development)

```yaml
# docker-compose.ai-runtime.yml
version: '3.8'

services:
  ai-runtime:
    image: mahoun/ai-runtime:2.0.0-nexus
    container_name: mahoun-ai-runtime
    restart: unless-stopped
    
    environment:
      MAHOUN_DEPLOYMENT_PROFILE: DESKTOP_MINIMAL
      MAHOUN_MODELS_DIR: /nexus/models
      MAHOUN_DATA_DIR: /nexus/data
      TRANSFORMERS_OFFLINE: "1"
      HF_DATASETS_OFFLINE: "1"
      MAHOUN_ENABLE_NETWORK: "false"
      MAHOUN_GUARD_MODE: STRICT
      MAHOUN_ENV: production
    
    volumes:
      - ./models:/nexus/models:ro
      - ./data:/nexus/data
      - ./constitution:/nexus/constitution:ro
    
    ports:
      - "8000:8000"      # API
      - "9090:9090"      # Metrics
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/v2/ai-runtime/liveness"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

**Deploy:**

```bash
docker-compose -f docker-compose.ai-runtime.yml up -d
```

### Method 2: Docker CLI

```bash
docker run -d \
  --name mahoun-ai-runtime \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 9090:9090 \
  -v $(pwd)/models:/nexus/models:ro \
  -v $(pwd)/data:/nexus/data \
  -v $(pwd)/constitution:/nexus/constitution:ro \
  -e MAHOUN_DEPLOYMENT_PROFILE=DESKTOP_MINIMAL \
  -e MAHOUN_MODELS_DIR=/nexus/models \
  -e MAHOUN_DATA_DIR=/nexus/data \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_DATASETS_OFFLINE=1 \
  -e MAHOUN_ENABLE_NETWORK=false \
  -e MAHOUN_GUARD_MODE=STRICT \
  -e MAHOUN_ENV=production \
  --memory=8g \
  --cpus=4 \
  mahoun/ai-runtime:2.0.0-nexus
```

### Method 3: Kubernetes (Recommended for Production)

```yaml
# ai-runtime-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mahoun-ai-runtime
  namespace: mahoun
  labels:
    app: ai-runtime
    component: inference
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-runtime
  template:
    metadata:
      labels:
        app: ai-runtime
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: ai-runtime
        image: mahoun/ai-runtime:2.0.0-nexus
        imagePullPolicy: IfNotPresent
        
        env:
        - name: MAHOUN_DEPLOYMENT_PROFILE
          value: "ENTERPRISE_FULL"
        - name: MAHOUN_MODELS_DIR
          value: "/nexus/models"
        - name: MAHOUN_DATA_DIR
          value: "/nexus/data"
        - name: TRANSFORMERS_OFFLINE
          value: "1"
        - name: HF_DATASETS_OFFLINE
          value: "1"
        - name: MAHOUN_ENABLE_NETWORK
          value: "false"
        - name: MAHOUN_GUARD_MODE
          value: "STRICT"
        - name: MAHOUN_ENV
          value: "production"
        
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        - name: metrics
          containerPort: 9090
          protocol: TCP
        
        volumeMounts:
        - name: models
          mountPath: /nexus/models
          readOnly: true
        - name: data
          mountPath: /nexus/data
        - name: constitution
          mountPath: /nexus/constitution
          readOnly: true
        
        resources:
          requests:
            memory: "64Gi"
            cpu: "16"
          limits:
            memory: "128Gi"
            cpu: "32"
        
        livenessProbe:
          httpGet:
            path: /health/v2/ai-runtime/liveness
            port: http
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health/v2/ai-runtime/readiness
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
      
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ai-runtime-models-pvc
      - name: data
        persistentVolumeClaim:
          claimName: ai-runtime-data-pvc
      - name: constitution
        configMap:
          name: mahoun-constitution
```

**Deploy:**

```bash
kubectl apply -f ai-runtime-deployment.yaml
kubectl apply -f ai-runtime-service.yaml
kubectl apply -f ai-runtime-ingress.yaml
```

---

## Health Checks

### Endpoints

| Endpoint | Purpose | Response Time |
|----------|---------|---------------|
| `/health/v2/ai-runtime` | Comprehensive health | < 1s |
| `/health/v2/ai-runtime/readiness` | Kubernetes readiness | < 100ms |
| `/health/v2/ai-runtime/liveness` | Kubernetes liveness | < 50ms |

### Comprehensive Health Check

```bash
curl http://localhost:8000/health/v2/ai-runtime
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-07-04T10:30:00Z",
  "uptime_seconds": 3600.5,
  "version": "2.0.0-NEXUS",
  "checks": {
    "model_runtime": {
      "status": "healthy",
      "message": "5 models available",
      "latency_ms": 45.2
    },
    "embedding_service": {
      "status": "healthy",
      "message": "2 embedding models available",
      "latency_ms": 12.5
    },
    "memory_manager": {
      "status": "healthy",
      "message": "Memory healthy: 45.2% used",
      "latency_ms": 5.1
    },
    "governance_validator": {
      "status": "healthy",
      "message": "Governance validator operational",
      "latency_ms": 8.3
    },
    "network_isolation": {
      "status": "healthy",
      "message": "Air-gap compliance verified",
      "latency_ms": 2.1
    }
  },
  "system": {
    "cpu_percent": 35.5,
    "memory_used_mb": 3584.2,
    "memory_percent": 45.2,
    "disk_used_gb": 18.5,
    "disk_percent": 9.2,
    "model_count": 5
  },
  "latency_ms": 73.2
}
```

### Status Codes

- **200 OK**: All components healthy
- **503 Service Unavailable**: One or more components unhealthy

---

## Monitoring

### Prometheus Metrics

AI Runtime exports **40+ Prometheus metrics** on port `9090`:

#### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `mahoun_ai_runtime_up` | Gauge | Service availability (1=up, 0=down) |
| `mahoun_ai_component_health_status` | Gauge | Component health (0=unknown, 1=healthy, 2=degraded, 3=unhealthy) |
| `mahoun_ai_models_available_total` | Gauge | Number of available GGUF models |
| `mahoun_ai_inference_requests_total` | Counter | Total inference requests |
| `mahoun_ai_inference_duration_seconds` | Histogram | Inference latency distribution |
| `mahoun_ai_governance_violations_total` | Counter | Governance violations detected |
| `mahoun_ai_airgap_compliance_status` | Gauge | Air-gap compliance (1=compliant, 0=non-compliant) |

**Scrape Config:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-runtime'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana Dashboard

Import the pre-built dashboard:

```bash
# Location: monitoring/grafana-dashboard-ai-runtime.json
# Dashboard UID: ai-runtime-nexus
```

**Dashboard includes:**

- 🚀 AI Runtime Status Overview
- 🧠 Component Health Status
- 📊 System Resource Overview
- 🤖 Model Availability & Performance
- ⚡ Inference Request Rate & Latency
- 🔍 Embedding Service Performance
- 🛡️ Governance & Compliance Status
- 💾 Memory & Disk Utilization

### AlertManager Rules

Alert rules are defined in `monitoring/prometheus/ai-runtime-alerts.yml`:

**Critical Alerts:**
- AIRuntimeDown
- AIRuntimeNotReady
- NoModelsAvailable
- AIRuntimeMemoryExhausted
- GovernanceViolationDetected
- AirGapComplianceViolation

**Warning Alerts:**
- AIComponentDegraded
- AIRuntimeHighMemoryUsage
- AIInferenceHighLatency
- FrequentModelLoadFailures

---

## Security

### Container Security

1. **Non-root user**: Container runs as `mahoun:mahoun` (UID 1000)
2. **Read-only filesystem**: Root filesystem is read-only
3. **No capabilities**: All Linux capabilities dropped
4. **No network**: Network disabled in air-gap mode

### Secrets Management

**DO NOT** hardcode secrets in environment variables. Use:

- **Kubernetes Secrets** for K8s deployments
- **Docker Secrets** for Docker Swarm
- **HashiCorp Vault** for enterprise deployments

```bash
# Generate JWT secret
openssl rand -base64 32

# Store in Kubernetes secret
kubectl create secret generic mahoun-secrets \
  --from-literal=jwt-secret=$(openssl rand -base64 32)
```

### Network Isolation

Verify air-gap compliance:

```bash
# Check environment variables
docker exec mahoun-ai-runtime env | grep -E '(TRANSFORMERS|HF_DATASETS|MAHOUN_ENABLE_NETWORK)'

# Should output:
# TRANSFORMERS_OFFLINE=1
# HF_DATASETS_OFFLINE=1
# MAHOUN_ENABLE_NETWORK=false
```

---

## Troubleshooting

See [AI Runtime Troubleshooting Runbook](./AI_RUNTIME_TROUBLESHOOTING_RUNBOOK.md) for detailed troubleshooting procedures.

### Quick Diagnostics

```bash
# Check service status
curl http://localhost:8000/health/v2/ai-runtime | jq '.status'

# Check model availability
curl http://localhost:8000/health/v2/ai-runtime | jq '.system.model_count'

# Check memory usage
curl http://localhost:8000/health/v2/ai-runtime | jq '.system.memory_percent'

# Check governance status
curl http://localhost:8000/health/v2/ai-runtime | jq '.checks.governance_validator.status'

# View Prometheus metrics
curl http://localhost:9090/metrics | grep mahoun_ai

# Check container logs
docker logs mahoun-ai-runtime --tail 100

# Check container resource usage
docker stats mahoun-ai-runtime
```

---

## Support & Documentation

- **Runbook**: [AI Runtime Troubleshooting Runbook](./AI_RUNTIME_TROUBLESHOOTING_RUNBOOK.md)
- **API Documentation**: [Reasoning API Spec](../api/reasoning-api.yaml)
- **Governance Documentation**: [RedLines.yaml](../../constitution/RedLines.yaml)
- **Monitoring Guide**: [Monitoring Stack Guide](../../monitoring/MONITORING_STACK_GUIDE.md)

---

**Document Version**: 1.0.0  
**Last Reviewed**: July 4, 2026  
**Next Review**: January 2027
