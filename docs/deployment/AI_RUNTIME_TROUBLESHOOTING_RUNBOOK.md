# MAHOUN AI Runtime - Troubleshooting Runbook

> **Classification**: OPERATIONAL RUNBOOK / SRE GUIDE  
> **Version**: 1.0.0  
> **Last Updated**: July 2026  
> **On-Call Reference**: Quick diagnostic and resolution procedures

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Critical Alerts](#critical-alerts)
4. [Performance Issues](#performance-issues)
5. [Governance Issues](#governance-issues)
6. [Resource Issues](#resource-issues)
7. [Advanced Debugging](#advanced-debugging)

---

## Quick Diagnostics

### Health Check

```bash
# Check overall health
curl http://localhost:8000/health/v2/ai-runtime

# Check readiness (Kubernetes)
curl http://localhost:8000/health/v2/ai-runtime/readiness

# Check liveness (Kubernetes)
curl http://localhost:8000/health/v2/ai-runtime/liveness
```

### Component Status

```bash
# Check all components
curl http://localhost:8000/health/v2/ai-runtime | jq '.checks'

# Check specific component
curl http://localhost:8000/health/v2/ai-runtime | jq '.checks.model_runtime'
```

### Prometheus Metrics

```bash
# Check runtime status
curl http://localhost:9090/metrics | grep mahoun_ai_runtime_up

# Check component health
curl http://localhost:9090/metrics | grep mahoun_ai_component_health_status

# Check inference rate
curl http://localhost:9090/metrics | grep mahoun_ai_inference_requests_total

# Check memory usage
curl http://localhost:9090/metrics | grep mahoun_ai_runtime_memory_percent
```

---

## Common Issues

### Issue 1: Service Not Starting

**Symptoms:**
- Container exits immediately
- Health check endpoint not responding
- Logs show initialization errors

**Diagnostic Commands:**

```bash
# Check container status
docker ps -a | grep mahoun-ai-runtime

# Check container logs
docker logs mahoun-ai-runtime --tail 100

# Check exit code
docker inspect mahoun-ai-runtime --format='{{.State.ExitCode}}'
```

**Common Causes & Solutions:**

#### Cause 1: Missing Models Directory

**Error Log:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/nexus/models'
```

**Solution:**
```bash
# Verify models directory exists and is mounted
docker exec mahoun-ai-runtime ls -la /nexus/models

# If missing, recreate container with correct volume mount
docker run -v $(pwd)/models:/nexus/models:ro ...
```

#### Cause 2: Missing Environment Variables

**Error Log:**
```
ValueError: MAHOUN_DEPLOYMENT_PROFILE environment variable not set
```

**Solution:**
```bash
# Set required environment variables
export MAHOUN_DEPLOYMENT_PROFILE=DESKTOP_MINIMAL
export MAHOUN_MODELS_DIR=/nexus/models
export MAHOUN_DATA_DIR=/nexus/data

# Or update docker-compose.yml / K8s manifest
```

#### Cause 3: Port Already in Use

**Error Log:**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill conflicting process or change port
docker run -p 8080:8000 ...  # Use different host port
```

---

### Issue 2: No Models Available

**Alert:** `NoModelsAvailable`

**Symptoms:**
- Health check shows `model_count: 0`
- Component status: `degraded` or `unhealthy`
- Inference requests fail with "No models available"

**Diagnostic Commands:**

```bash
# Check models directory
docker exec mahoun-ai-runtime ls -la /nexus/models

# Check for GGUF files
docker exec mahoun-ai-runtime find /nexus/models -name "*.gguf"

# Check health status
curl http://localhost:8000/health/v2/ai-runtime | jq '.system.model_count'
```

**Solutions:**

1. **Verify models are downloaded:**
   ```bash
   ls -lh /path/to/models/*.gguf
   ```

2. **Verify volume mount:**
   ```bash
   docker inspect mahoun-ai-runtime | jq '.[0].Mounts'
   ```

3. **Check file permissions:**
   ```bash
   docker exec mahoun-ai-runtime ls -la /nexus/models
   # Files should be readable by mahoun user (UID 1000)
   ```

4. **Fix permissions if needed:**
   ```bash
   sudo chown -R 1000:1000 /path/to/models
   sudo chmod -R 755 /path/to/models
   ```

---

### Issue 3: High Memory Usage

**Alert:** `AIRuntimeHighMemoryUsage` or `AIRuntimeMemoryExhausted`

**Symptoms:**
- Memory usage > 85%
- OOM kills
- Slow response times

**Diagnostic Commands:**

```bash
# Check memory usage
curl http://localhost:8000/health/v2/ai-runtime | jq '.system.memory_percent'

# Check Prometheus metric
curl http://localhost:9090/metrics | grep mahoun_ai_runtime_memory_percent

# Check container memory
docker stats mahoun-ai-runtime --no-stream
```

**Solutions:**

1. **Check loaded models:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime | jq '.checks.model_runtime'
   ```

2. **Unload unused models** (if dynamic loading is enabled)

3. **Increase container memory limit:**
   ```bash
   # Docker
   docker update --memory=16g mahoun-ai-runtime
   
   # Kubernetes
   kubectl set resources deployment/mahoun-ai-runtime \
     --limits=memory=16Gi
   ```

4. **Switch to smaller models:**
   - Desktop Minimal: Use 1B-3B models
   - Enterprise Full: Use 7B-13B models instead of 70B

5. **Adjust deployment profile:**
   ```bash
   # If using Desktop Minimal, consider Enterprise Full
   export MAHOUN_DEPLOYMENT_PROFILE=ENTERPRISE_FULL
   ```

---

### Issue 4: Air-Gap Compliance Violation

**Alert:** `AirGapComplianceViolation`

**Symptoms:**
- `mahoun_ai_airgap_compliance_status = 0`
- Network calls detected
- Health check shows `network_isolation: degraded`

**Diagnostic Commands:**

```bash
# Check air-gap status
curl http://localhost:8000/health/v2/ai-runtime | jq '.checks.network_isolation'

# Check environment variables
docker exec mahoun-ai-runtime env | grep -E '(TRANSFORMERS|HF_DATASETS|MAHOUN_ENABLE_NETWORK)'

# Check for network calls (Prometheus)
curl http://localhost:9090/metrics | grep mahoun_ai_airgap_network_call_attempts_total
```

**Solutions:**

1. **Verify environment variables:**
   ```bash
   # Required settings
   TRANSFORMERS_OFFLINE=1
   HF_DATASETS_OFFLINE=1
   MAHOUN_ENABLE_NETWORK=false
   ```

2. **Update container environment:**
   ```bash
   # Docker Compose
   # Update docker-compose.yml and restart
   docker-compose restart ai-runtime
   
   # Kubernetes
   kubectl set env deployment/mahoun-ai-runtime \
     TRANSFORMERS_OFFLINE=1 \
     HF_DATASETS_OFFLINE=1 \
     MAHOUN_ENABLE_NETWORK=false
   ```

3. **Verify network isolation** (optional, extreme measure):
   ```bash
   # Block all outbound traffic with iptables
   docker exec mahoun-ai-runtime \
     iptables -A OUTPUT -j DROP
   ```

---

### Issue 5: Governance Violations

**Alert:** `GovernanceViolationDetected`

**Symptoms:**
- `mahoun_ai_governance_violations_total` increasing
- Inference requests fail validation
- Health check shows `governance_validator: unhealthy`

**Diagnostic Commands:**

```bash
# Check governance status
curl http://localhost:8000/health/v2/ai-runtime | jq '.checks.governance_validator'

# Check violations metric
curl http://localhost:9090/metrics | grep mahoun_ai_governance_violations_total

# Check FortressValidator status
curl http://localhost:9090/metrics | grep mahoun_ai_governance_fortress_validator_up
```

**Solutions:**

1. **Verify RedLines.yaml is mounted:**
   ```bash
   docker exec mahoun-ai-runtime cat /nexus/constitution/RedLines.yaml
   ```

2. **Check governance mode:**
   ```bash
   docker exec mahoun-ai-runtime env | grep MAHOUN_GUARD_MODE
   # Should be: MAHOUN_GUARD_MODE=STRICT
   ```

3. **Review violation logs:**
   ```bash
   docker logs mahoun-ai-runtime | grep "governance.*violation"
   ```

4. **Identify violation type:**
   ```bash
   curl http://localhost:9090/metrics | \
     grep mahoun_ai_governance_violations_total | \
     grep -v "^#"
   # Example output:
   # mahoun_ai_governance_violations_total{violation_type="min_agreement_score",severity="HIGH"} 5
   ```

5. **Solutions by violation type:**
   
   - **min_agreement_score**: Symbolic/neural agreement < 85%
     - Check if graph data is loaded
     - Verify retrieval service is operational
     - May indicate model hallucination
   
   - **min_confidence_score**: Verdict confidence < 70%
     - Provide more context in query
     - Check if evidence is available in graph
   
   - **proof_tree_required**: Missing proof tree
     - Check reasoning engine configuration
     - Verify evidence ledger is writable

---

## Critical Alerts

### AIRuntimeDown

**Severity:** CRITICAL  
**Impact:** No AI inference available

**Immediate Actions:**

1. Check if container is running:
   ```bash
   docker ps | grep mahoun-ai-runtime
   ```

2. If not running, check logs and restart:
   ```bash
   docker logs mahoun-ai-runtime --tail 100
   docker restart mahoun-ai-runtime
   ```

3. If still down, check health probe:
   ```bash
   docker exec mahoun-ai-runtime curl -f http://localhost:8000/health/v2/ai-runtime/liveness
   ```

4. If health probe fails, recreate container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

**Escalation:** If issue persists after recreation, page on-call SRE.

---

### AIRuntimeNotReady

**Severity:** CRITICAL  
**Impact:** Pod not receiving traffic (Kubernetes)

**Immediate Actions:**

1. Check readiness probe:
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime/readiness
   ```

2. Check component health:
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime | jq '.checks'
   ```

3. Identify unhealthy components and remediate:
   - `model_runtime`: See [Issue 2: No Models Available](#issue-2-no-models-available)
   - `memory_manager`: See [Issue 3: High Memory Usage](#issue-3-high-memory-usage)

**Escalation:** If readiness does not recover within 5 minutes, restart pod.

---

### AIRuntimeMemoryExhausted

**Severity:** CRITICAL  
**Impact:** OOM kill imminent, service instability

**Immediate Actions:**

1. **DO NOT restart** - will cause cascading failures

2. Check memory usage:
   ```bash
   docker stats mahoun-ai-runtime --no-stream
   ```

3. Increase memory limit (if possible):
   ```bash
   docker update --memory=16g mahoun-ai-runtime
   ```

4. Scale horizontally (Kubernetes):
   ```bash
   kubectl scale deployment/mahoun-ai-runtime --replicas=6
   ```

5. If memory cannot be increased, **gracefully drain traffic**:
   ```bash
   # Kubernetes
   kubectl cordon <node-with-oom-pod>
   kubectl drain <node-with-oom-pod> --ignore-daemonsets
   ```

**Escalation:** Page infrastructure team to provision more resources.

---

## Performance Issues

### High Inference Latency

**Alert:** `AIInferenceHighLatency`

**Symptoms:**
- P95 latency > 10 seconds
- Slow user-facing requests

**Diagnostic Commands:**

```bash
# Check inference latency
curl http://localhost:9090/metrics | grep mahoun_ai_inference_duration_seconds

# Check tokens per second
curl http://localhost:9090/metrics | grep mahoun_ai_inference_tokens_per_second

# Check CPU usage
curl http://localhost:8000/health/v2/ai-runtime | jq '.system.cpu_percent'
```

**Solutions:**

1. **Check CPU throttling:**
   ```bash
   docker stats mahoun-ai-runtime
   ```

2. **Increase CPU allocation:**
   ```bash
   docker update --cpus=8 mahoun-ai-runtime
   ```

3. **Enable GPU acceleration** (if available):
   ```bash
   export MAHOUN_ENABLE_GPU=true
   export CUDA_VISIBLE_DEVICES=0
   ```

4. **Use smaller/quantized models:**
   - Q4_K_M quantization for 4-bit
   - Q5_K_M for balance between speed and quality

5. **Check graph/retrieval performance:**
   ```bash
   # Retrieval should be < 100ms
   docker logs mahoun-ai-runtime | grep "retrieval_duration"
   ```

---

### Low Cache Hit Rate

**Alert:** `LowEmbeddingCacheHitRate`

**Symptoms:**
- Cache hit rate < 50%
- High embedding generation load

**Diagnostic Commands:**

```bash
# Check cache metrics
curl http://localhost:9090/metrics | grep mahoun_ai_embedding_cache

# Check cache size
curl http://localhost:8000/health/v2/ai-runtime | jq '.system' | grep cache
```

**Solutions:**

1. **Increase cache size** (if memory allows)

2. **Warm up cache** with common queries

3. **Check cache eviction policy**

---

## Governance Issues

### Frequent Validation Failures

**Alert:** `GovernanceValidationFailures`

**Symptoms:**
- > 10% of validations failing
- Users reporting blocked requests

**Diagnostic Commands:**

```bash
# Check validation metrics
curl http://localhost:9090/metrics | grep mahoun_ai_governance_validations_total

# Check logs for specific failures
docker logs mahoun-ai-runtime | grep "validation.*failed"
```

**Solutions:**

1. **Review RedLines.yaml thresholds:**
   ```bash
   docker exec mahoun-ai-runtime cat /nexus/constitution/RedLines.yaml
   ```

2. **Check if thresholds are too strict:**
   - `min_agreement_score`: Default 0.85 (consider 0.80 for development)
   - `min_confidence_score`: Default 0.70 (consider 0.65)

3. **Verify graph data quality:**
   ```bash
   # Check if graph is populated
   curl http://localhost:8000/health/v2/ai-runtime | jq '.checks.model_runtime'
   ```

---

## Resource Issues

### Disk Space Exhausted

**Alert:** `AIRuntimeDiskFull`

**Symptoms:**
- Disk usage > 95%
- Cannot write cache or logs

**Diagnostic Commands:**

```bash
# Check disk usage
curl http://localhost:8000/health/v2/ai-runtime | jq '.system.disk_percent'

# Check cache size
docker exec mahoun-ai-runtime du -sh /nexus/data/cache
```

**Solutions:**

1. **Clear cache:**
   ```bash
   docker exec mahoun-ai-runtime rm -rf /nexus/data/cache/*
   ```

2. **Rotate logs:**
   ```bash
   docker exec mahoun-ai-runtime find /nexus/data/logs -name "*.log" -mtime +7 -delete
   ```

3. **Increase persistent volume size** (Kubernetes):
   ```bash
   kubectl patch pvc ai-runtime-data-pvc -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
   ```

---

## Advanced Debugging

### Enable Debug Logging

```bash
# Set log level to DEBUG
docker exec mahoun-ai-runtime \
  bash -c 'export LOG_LEVEL=DEBUG && supervisorctl restart mahoun'
```

### Capture Trace

```bash
# Enable distributed tracing
export MAHOUN_ENABLE_TRACING=true
export JAEGER_AGENT_HOST=localhost
export JAEGER_AGENT_PORT=6831
```

### Profile Performance

```bash
# Enable Python profiling
docker exec mahoun-ai-runtime \
  python -m cProfile -o profile.stats api/main.py

# Analyze profile
docker exec mahoun-ai-runtime \
  python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

### Memory Profiling

```bash
# Install memory profiler
docker exec mahoun-ai-runtime pip install memory_profiler

# Profile memory usage
docker exec mahoun-ai-runtime \
  python -m memory_profiler mahoun/ai/runtime_manager.py
```

---

## Escalation Matrix

| Issue Severity | Response Time | Escalation Path |
|----------------|---------------|-----------------|
| **Critical** (Service Down) | < 5 min | On-call SRE → Engineering Lead |
| **High** (Degraded Performance) | < 15 min | On-call SRE → Team Lead |
| **Medium** (Component Degraded) | < 1 hour | On-call Engineer |
| **Low** (Info Alert) | Next business day | Team backlog |

---

## Support Contacts

- **On-Call SRE**: pager +1-XXX-XXX-XXXX
- **Engineering Lead**: email engineering-lead@mahoun.internal
- **Platform Team Slack**: #mahoun-platform
- **Incident Channel**: #mahoun-incidents

---

**Document Version**: 1.0.0  
**Last Reviewed**: July 4, 2026  
**Next Review**: October 2026
