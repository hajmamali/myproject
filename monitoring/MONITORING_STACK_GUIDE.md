# MAHOUN Enterprise Monitoring Stack - Complete Guide

## 📊 Overview

Complete observability stack for MAHOUN platform with production-grade monitoring, logging, and tracing capabilities.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Prometheus  │  │   Grafana    │  │ Alertmanager │      │
│  │   (Metrics)  │◄─┤ (Dashboards) │◄─┤   (Alerts)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ▲                  ▲                                 │
│         │                  │                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Loki     │  │    Tempo     │  │  Exporters   │      │
│  │    (Logs)    │  │   (Traces)   │  │   (DB/App)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ▲                  ▲                  ▲              │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
    ┌─────┴──────────────────┴──────────────────┴─────┐
    │         MAHOUN Platform Services                 │
    │  (Governance Kernel, API, Neo4j, PostgreSQL)    │
    └──────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Deploy Stack

```bash
# Deploy complete monitoring stack
./scripts/monitoring_stack_manager.sh deploy

# Check status
./scripts/monitoring_stack_manager.sh status

# View health
./scripts/monitoring_stack_manager.sh health
```

### 2. Access Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Alertmanager** | http://localhost:9093 | - |
| **Loki** | http://localhost:3100 | - |
| **Tempo** | http://localhost:3200 | - |

### 3. First-Time Setup

1. **Grafana Login:**
   - Navigate to http://localhost:3000
   - Login with admin/admin
   - Change password when prompted

2. **Verify Data Sources:**
   - Go to Configuration → Data Sources
   - All sources should be auto-provisioned ✅

3. **Import Dashboards:**
   - Dashboards are auto-provisioned from `/monitoring/grafana/dashboards/`

## 📁 Directory Structure

```
monitoring/
├── enterprise-monitoring-stack.yaml    # Main compose file
├── prometheus/
│   ├── prometheus.yml                  # Prometheus config
│   ├── alerts/                         # Alert rules
│   │   └── mahoun-alerts.yml
│   └── recording-rules/                # Recording rules
│       └── mahoun-recording-rules.yml
├── grafana/
│   ├── grafana.ini                     # Grafana config
│   ├── datasources/                    # Auto-provisioned sources
│   │   └── datasources.yaml
│   └── dashboards/                     # Auto-provisioned dashboards
│       └── dashboards.yaml
├── loki/
│   ├── loki-config.yaml                # Loki config
│   └── promtail-config.yaml            # Log shipping config
├── tempo/
│   └── tempo-config.yaml               # Tempo tracing config
├── alertmanager/
│   ├── alertmanager.yml                # Alert routing
│   └── templates/                      # Email templates
│       └── email.tmpl
└── exporters/
    └── postgres-queries.yaml           # Custom PostgreSQL metrics
```

## 🔧 Configuration

### Environment Variables

Copy `.env.enterprise` and configure:

```bash
# Grafana
GRAFANA_ADMIN_PASSWORD=SecurePassword123!
GRAFANA_SECRET_KEY=your-secret-key-here

# Alert Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@mahoun.com
SMTP_PASSWORD=your-smtp-password

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PAGERDUTY_SERVICE_KEY=your-pagerduty-key

# Database Credentials (for exporters)
DB_POSTGRES_PASSWORD=your-postgres-password
REDIS_PASSWORD=your-redis-password
```

### Custom Prometheus Metrics

Add custom metrics to your application:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('mahoun_requests_total', 'Total requests', ['endpoint', 'method'])
request_duration = Histogram('mahoun_request_duration_seconds', 'Request duration', ['endpoint'])
active_users = Gauge('mahoun_active_users', 'Active users')

# Use in code
request_count.labels(endpoint='/api/reasoning', method='POST').inc()
with request_duration.labels(endpoint='/api/reasoning').time():
    # Your code here
    pass
```

### Custom Alert Rules

Add to `prometheus/alerts/mahoun-alerts.yml`:

```yaml
groups:
  - name: custom_alerts
    interval: 30s
    rules:
      - alert: CustomMetricHigh
        expr: custom_metric > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Custom metric is high"
          description: "Value is {{ $value }}"
```

## 📈 Key Dashboards

### 1. Platform Overview
- Overall system health
- Request rates and latencies
- Error rates
- Resource utilization

### 2. Governance Kernel
- Validation success rate
- Policy enforcement metrics
- Fortress validator checks
- Response times

### 3. Database Performance
- Neo4j query performance
- PostgreSQL slow queries
- Redis cache hit ratio
- ChromaDB query latency

### 4. Infrastructure
- CPU, Memory, Disk usage
- Container metrics
- Network throughput
- Docker stats

### 5. Business Metrics
- Reasoning requests
- Daily active users
- Graph node count
- Vector embedding count

## 🚨 Alert Configuration

### Alert Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | Service down, data loss risk | Immediate (< 5 min) |
| **Warning** | Performance degradation | 30 minutes |
| **Info** | Informational, no action needed | Next business day |

### Alert Routing

Alerts are routed based on:
1. **Severity**: Critical → PagerDuty + Slack + Email
2. **Component**: Governance → Governance team
3. **Service**: Database → Database team

### Configuring Notifications

Edit `alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@mahoun.internal'
        headers:
          Subject: '[ALERT] {{ .GroupLabels.alertname }}'
```

## 🔍 Querying & Troubleshooting

### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# CPU usage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

### LogQL Queries (Loki)

```logql
# All logs from governance kernel
{service="governance-kernel"}

# Errors only
{service="api-server"} |= "error" | json

# Filter by level
{service="api-server"} | json | level="error"

# Rate of errors
rate({service="api-server"} |= "error"[5m])
```

### TraceQL Queries (Tempo)

```traceql
# All traces for a service
{service.name="api-server"}

# Slow traces
{duration > 2s}

# Errors
{status=error}

# Complex query
{service.name="api-server" && http.status_code=500}
```

## 💾 Backup & Recovery

### Manual Backup

```bash
# Full backup
./scripts/monitoring_stack_manager.sh backup

# Backup location
ls backups/monitoring/
```

### Automated Backups

Add to cron:

```bash
# Daily backup at 2 AM
0 2 * * * /path/to/monitoring_stack_manager.sh backup >> /var/log/monitoring-backup.log 2>&1
```

### Restore from Backup

```bash
# List backups
ls backups/monitoring/

# Restore specific backup
./scripts/monitoring_stack_manager.sh restore backups/monitoring/20240616_120000
```

## 🔒 Security Hardening

### 1. Enable HTTPS

```yaml
# grafana.ini
[server]
protocol = https
cert_file = /path/to/cert.pem
cert_key = /path/to/key.pem
```

### 2. Enable Authentication

```yaml
# prometheus.yml
basic_auth_users:
  admin: $2y$10$hashed_password_here
```

### 3. Restrict Network Access

```yaml
# docker-compose
services:
  prometheus:
    networks:
      - monitoring-internal  # Not exposed to public
```

### 4. Enable TLS Between Services

```yaml
# prometheus.yml
tls_config:
  ca_file: /etc/prometheus/ca.crt
  cert_file: /etc/prometheus/client.crt
  key_file: /etc/prometheus/client.key
```

## 📊 Performance Tuning

### Prometheus

```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 90d
    retention.size: 50GB
    
# Increase resources
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
```

### Grafana

```ini
# grafana.ini
[database]
cache_mode = shared
wal = true

[dataproxy]
max_conns_per_host = 100
max_idle_connections = 100
```

### Loki

```yaml
# loki-config.yaml
limits_config:
  ingestion_rate_mb: 20
  ingestion_burst_size_mb: 40
  max_streams_per_user: 20000
```

## 🐛 Troubleshooting

### Service Not Starting

```bash
# Check logs
./scripts/monitoring_stack_manager.sh logs prometheus

# Check container status
docker ps -a | grep mahoun

# Check resource usage
docker stats --no-stream
```

### Out of Disk Space

```bash
# Check disk usage
docker system df

# Clean old data
docker system prune -af

# Reduce retention
# Edit prometheus.yml: retention.time: 30d
```

### High Memory Usage

```bash
# Check memory usage
./scripts/monitoring_stack_manager.sh metrics

# Reduce cache sizes in configs
# Restart services
./scripts/monitoring_stack_manager.sh restart
```

### Missing Metrics

```bash
# Check scrape targets
curl http://localhost:9090/api/v1/targets

# Check service discovery
curl http://localhost:9090/api/v1/targets/metadata

# Verify exporter endpoints
curl http://localhost:9100/metrics  # node-exporter
curl http://localhost:9187/metrics  # postgres-exporter
```

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)

## 🆘 Support

For issues or questions:
1. Check logs: `./scripts/monitoring_stack_manager.sh logs`
2. Run diagnostics: `./scripts/monitoring_stack_manager.sh diagnostics`
3. Contact platform team: platform-team@mahoun.internal

---

**Version:** 1.0.0  
**Last Updated:** June 2024  
**Maintained by:** MAHOUN Platform Team
