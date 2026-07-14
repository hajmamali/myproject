# MAHOUN AI Runtime - Operational Procedures

> **Classification**: OPERATIONAL GUIDE / DAY-TO-DAY PROCEDURES  
> **Version**: 1.0.0  
> **Last Updated**: July 2026  
> **Target Audience**: Platform Operators, DevOps Engineers

---

## Daily Operations

### Morning Health Check (15 minutes)

1. **Check service availability:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime | jq '.status'
   # Expected: "healthy" or "degraded"
   ```

2. **Review Grafana dashboard:**
   - Open: https://grafana.mahoun.internal/d/ai-runtime-nexus
   - Check: CPU, Memory, Disk usage trends
   - Verify: No active critical alerts

3. **Check model availability:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime | jq '.system.model_count'
   # Expected: >= 1
   ```

4. **Review alert history** (past 24 hours):
   ```bash
   # Prometheus query:
   ALERTS{alertname=~"AI.*"}
   ```

5. **Check logs for errors:**
   ```bash
   docker logs mahoun-ai-runtime --since 24h | grep -i error | wc -l
   # Expected: < 10 errors/day
   ```

---

## Weekly Operations

### Performance Review (30 minutes)

1. **Analyze inference latency trends:**
   - Prometheus query: `histogram_quantile(0.95, rate(mahoun_ai_inference_duration_seconds_bucket[7d]))`
   - Acceptable: P95 < 5 seconds

2. **Check memory usage trends:**
   - Prometheus query: `avg_over_time(mahoun_ai_runtime_memory_percent[7d])`
   - Threshold: < 80%

3. **Review cache performance:**
   - Prometheus query: `rate(mahoun_ai_embedding_cache_hits_total[7d]) / (rate(mahoun_ai_embedding_cache_hits_total[7d]) + rate(mahoun_ai_embedding_cache_misses_total[7d]))`
   - Target: > 70% hit rate

4. **Check governance compliance:**
   - Prometheus query: `rate(mahoun_ai_governance_violations_total[7d])`
   - Expected: 0 critical violations

---

## Monthly Operations

### Capacity Planning (2 hours)

1. **Review resource utilization trends:**
   - CPU, Memory, Disk usage over 30 days
   - Identify growth patterns

2. **Project resource needs:**
   - Estimate requirements for next 3 months
   - Plan scaling strategy

3. **Model inventory audit:**
   ```bash
   docker exec mahoun-ai-runtime ls -lh /nexus/models/*.gguf
   ```
   - Remove unused models
   - Download new recommended models

4. **Update documentation:**
   - Review and update runbooks
   - Document any operational changes

---

## Model Management

### Adding a New Model

1. **Download model** (on internet-connected machine):
   ```bash
   huggingface-cli download \
     TheBloke/Llama-3.2-3B-Instruct-GGUF \
     llama-3.2-3b-instruct.Q4_K_M.gguf \
     --local-dir /tmp/models
   ```

2. **Verify checksum:**
   ```bash
   sha256sum /tmp/models/llama-3.2-3b-instruct.Q4_K_M.gguf
   # Compare with model card checksum
   ```

3. **Transfer to production** (air-gap transfer):
   ```bash
   # Use approved transfer mechanism (USB drive, secure file transfer)
   rsync -avz /tmp/models/ production-server:/nexus/models/
   ```

4. **Verify model is detected:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime | jq '.system.model_count'
   ```

5. **Test inference with new model:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/reasoning \
     -H "Content-Type: application/json" \
     -d '{
       "query": "test query",
       "model": "llama-3.2-3b-instruct"
     }'
   ```

### Removing a Model

1. **Verify model is not in use:**
   ```bash
   curl http://localhost:9090/metrics | grep 'mahoun_ai_inference_requests_total.*model_name="old-model"'
   ```

2. **Remove model file:**
   ```bash
   docker exec mahoun-ai-runtime rm /nexus/models/old-model.gguf
   ```

3. **Verify removal:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime | jq '.system.model_count'
   ```

---

## Deployment Procedures

### Rolling Update (Zero Downtime)

**For Kubernetes deployments:**

1. **Update deployment manifest:**
   ```yaml
   image: mahoun/ai-runtime:2.1.0-nexus  # New version
   ```

2. **Apply update:**
   ```bash
   kubectl apply -f ai-runtime-deployment.yaml
   ```

3. **Monitor rollout:**
   ```bash
   kubectl rollout status deployment/mahoun-ai-runtime
   ```

4. **Verify new pods:**
   ```bash
   kubectl get pods -l app=ai-runtime
   ```

5. **Check health:**
   ```bash
   kubectl exec deployment/mahoun-ai-runtime -- \
     curl -f http://localhost:8000/health/v2/ai-runtime/readiness
   ```

6. **Rollback if needed:**
   ```bash
   kubectl rollout undo deployment/mahoun-ai-runtime
   ```

### Blue-Green Deployment

1. **Deploy green environment:**
   ```bash
   kubectl apply -f ai-runtime-deployment-green.yaml
   ```

2. **Wait for green to be ready:**
   ```bash
   kubectl wait --for=condition=available --timeout=300s \
     deployment/mahoun-ai-runtime-green
   ```

3. **Run smoke tests on green:**
   ```bash
   ./scripts/smoke-test.sh green
   ```

4. **Switch traffic to green:**
   ```bash
   kubectl patch service mahoun-ai-runtime \
     -p '{"spec":{"selector":{"version":"green"}}}'
   ```

5. **Monitor for issues** (30 minutes)

6. **Decommission blue** (if green is stable):
   ```bash
   kubectl delete deployment mahoun-ai-runtime-blue
   ```

---

## Backup & Recovery

### Backup Procedures

**What to backup:**
- Configuration files (environment variables, secrets)
- RedLines.yaml governance config
- Model checksums and metadata
- Persistent data volumes (cache, logs)

**Backup commands:**

```bash
# Backup configuration
docker inspect mahoun-ai-runtime > backup/config-$(date +%Y%m%d).json

# Backup RedLines.yaml
cp constitution/RedLines.yaml backup/RedLines-$(date +%Y%m%d).yaml

# Backup data volume
docker run --rm \
  -v mahoun-ai-data:/data \
  -v $(pwd)/backup:/backup \
  ubuntu tar czf /backup/data-$(date +%Y%m%d).tar.gz /data

# Kubernetes: Backup PVC
kubectl exec deployment/mahoun-ai-runtime -- \
  tar czf - /nexus/data > backup/data-$(date +%Y%m%d).tar.gz
```

### Recovery Procedures

1. **Stop service:**
   ```bash
   docker stop mahoun-ai-runtime
   # or
   kubectl scale deployment/mahoun-ai-runtime --replicas=0
   ```

2. **Restore data:**
   ```bash
   docker run --rm \
     -v mahoun-ai-data:/data \
     -v $(pwd)/backup:/backup \
     ubuntu tar xzf /backup/data-20260704.tar.gz -C /
   ```

3. **Restore configuration:**
   ```bash
   # Review backup/config-20260704.json
   # Recreate container with correct configuration
   ```

4. **Start service:**
   ```bash
   docker start mahoun-ai-runtime
   # or
   kubectl scale deployment/mahoun-ai-runtime --replicas=3
   ```

5. **Verify recovery:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime
   ```

---

## Scaling Procedures

### Horizontal Scaling (Kubernetes)

1. **Scale up:**
   ```bash
   kubectl scale deployment/mahoun-ai-runtime --replicas=6
   ```

2. **Verify pods:**
   ```bash
   kubectl get pods -l app=ai-runtime
   ```

3. **Monitor load distribution:**
   ```bash
   # Prometheus query:
   sum(rate(mahoun_ai_inference_requests_total[5m])) by (instance)
   ```

### Vertical Scaling

1. **Update resource limits:**
   ```bash
   kubectl set resources deployment/mahoun-ai-runtime \
     --limits=cpu=32,memory=128Gi \
     --requests=cpu=16,memory=64Gi
   ```

2. **Trigger rolling restart:**
   ```bash
   kubectl rollout restart deployment/mahoun-ai-runtime
   ```

---

## Security Procedures

### Secret Rotation

**JWT Secret Rotation:**

1. **Generate new secret:**
   ```bash
   NEW_SECRET=$(openssl rand -base64 32)
   ```

2. **Update Kubernetes secret:**
   ```bash
   kubectl create secret generic mahoun-secrets-new \
     --from-literal=jwt-secret=$NEW_SECRET
   ```

3. **Update deployment to use new secret:**
   ```yaml
   env:
   - name: SECURITY_JWT_SECRET
     valueFrom:
       secretKeyRef:
         name: mahoun-secrets-new
         key: jwt-secret
   ```

4. **Apply update:**
   ```bash
   kubectl apply -f ai-runtime-deployment.yaml
   ```

5. **Wait for rollout:**
   ```bash
   kubectl rollout status deployment/mahoun-ai-runtime
   ```

6. **Delete old secret** (after 24 hours):
   ```bash
   kubectl delete secret mahoun-secrets
   ```

### Certificate Renewal

*If using TLS/HTTPS for AI Runtime API:*

1. **Obtain new certificate**

2. **Update secret:**
   ```bash
   kubectl create secret tls mahoun-tls-new \
     --cert=path/to/cert.pem \
     --key=path/to/key.pem
   ```

3. **Update ingress:**
   ```yaml
   tls:
   - secretName: mahoun-tls-new
     hosts:
     - ai-runtime.mahoun.internal
   ```

4. **Apply update:**
   ```bash
   kubectl apply -f ai-runtime-ingress.yaml
   ```

---

## Monitoring Procedures

### Adding Custom Alerts

1. **Edit alert rules:**
   ```bash
   vim monitoring/prometheus/ai-runtime-alerts.yml
   ```

2. **Add new rule:**
   ```yaml
   - alert: CustomAlert
     expr: mahoun_ai_custom_metric > 100
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: "Custom condition detected"
   ```

3. **Validate YAML:**
   ```bash
   yamllint monitoring/prometheus/ai-runtime-alerts.yml
   ```

4. **Reload Prometheus config:**
   ```bash
   curl -X POST http://prometheus:9090/-/reload
   ```

### Creating Custom Dashboards

1. **Export existing dashboard:**
   ```bash
   curl http://grafana:3000/api/dashboards/uid/ai-runtime-nexus > custom-dashboard.json
   ```

2. **Modify dashboard JSON**

3. **Import new dashboard:**
   ```bash
   curl -X POST http://grafana:3000/api/dashboards/db \
     -H "Content-Type: application/json" \
     -d @custom-dashboard.json
   ```

---

## Compliance Procedures

### Air-Gap Compliance Audit

**Run quarterly:**

1. **Verify environment variables:**
   ```bash
   docker exec mahoun-ai-runtime env | \
     grep -E '(TRANSFORMERS_OFFLINE|HF_DATASETS_OFFLINE|MAHOUN_ENABLE_NETWORK)'
   ```

2. **Check for network calls:**
   ```bash
   curl http://localhost:9090/metrics | \
     grep mahoun_ai_airgap_network_call_attempts_total
   # Expected: 0
   ```

3. **Review access logs** for external destinations

4. **Document findings** in compliance report

### Governance Compliance Audit

**Run monthly:**

1. **Check governance violations:**
   ```bash
   curl http://localhost:9090/metrics | \
     grep mahoun_ai_governance_violations_total
   # Expected: 0 critical violations
   ```

2. **Review RedLines.yaml changes:**
   ```bash
   git log constitution/RedLines.yaml
   ```

3. **Verify FortressValidator operational:**
   ```bash
   curl http://localhost:9090/metrics | \
     grep mahoun_ai_governance_fortress_validator_up
   # Expected: 1
   ```

4. **Audit sample of inference responses** for proof trees

---

## Emergency Procedures

### Emergency Shutdown

**When to use**: Critical security incident, data breach suspicion

1. **Stop all traffic immediately:**
   ```bash
   # Kubernetes
   kubectl scale deployment/mahoun-ai-runtime --replicas=0
   
   # Docker
   docker stop mahoun-ai-runtime
   ```

2. **Preserve evidence:**
   ```bash
   docker logs mahoun-ai-runtime > incident-logs-$(date +%Y%m%d-%H%M%S).txt
   docker inspect mahoun-ai-runtime > incident-config-$(date +%Y%m%d-%H%M%S).json
   ```

3. **Notify security team**

4. **Begin incident response procedures**

### Emergency Restart

**When to use**: Service completely unresponsive

1. **Capture diagnostics:**
   ```bash
   docker logs mahoun-ai-runtime > pre-restart-logs.txt
   docker stats mahoun-ai-runtime --no-stream > pre-restart-stats.txt
   ```

2. **Force restart:**
   ```bash
   docker restart mahoun-ai-runtime
   ```

3. **Monitor restart:**
   ```bash
   docker logs -f mahoun-ai-runtime
   ```

4. **Verify health:**
   ```bash
   curl http://localhost:8000/health/v2/ai-runtime
   ```

5. **Create post-incident report**

---

## Contact & Escalation

### Support Channels

- **Platform Team Slack**: #mahoun-platform
- **On-Call Pager**: +1-XXX-XXX-XXXX
- **Email**: platform-team@mahoun.internal

### Escalation Matrix

| Time Since Incident | Action |
|---------------------|--------|
| 0-5 min | On-call engineer investigates |
| 5-15 min | Team lead notified |
| 15-30 min | Engineering manager notified |
| 30+ min | VP Engineering notified |

---

**Document Version**: 1.0.0  
**Last Reviewed**: July 4, 2026  
**Next Review**: October 2026
