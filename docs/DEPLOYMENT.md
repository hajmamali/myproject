# Mahoun Deployment Guide 🚀

This guide explains how to deploy the Mahoun platform in various environments.

## 1. Local Development (Docker)

The fastest way to get started is using Docker Compose.

```bash
# Clone and enter
git clone https://github.com/your-org/mahoun.git
cd mahoun

# Setup environment
cp .env.example .env
# EDIT .env WITH YOUR SECRETS

# Start everything
./scripts/quickstart.sh
```

## 2. Production Hardening

When deploying to production, follow these security steps:

### Secrets Management
Do NOT store production passwords in `.env` files. Use:
- AWS Secrets Manager
- HashiCorp Vault
- GitHub Actions Secrets (for CI/CD)

### Networking
Ensure the following ports are NOT exposed to the public internet:
- `7687` (Neo4j Bolt)
- `9090` (Prometheus)
- `3000` (Grafana) - Access via VPN or SSH tunnel only.

Only port `8000` (FastAPI/MCP) should be exposed via a Reverse Proxy (Nginx/Traefik).

### Resource Scaling
For high-traffic deployments:
1. Use Neo4j Enterprise Cluster.
2. Run multiple `mahoun-mcp` containers behind a load balancer.
3. Increase `WORKERS` in `.env`.

---

## 3. Monitoring & Maintenance

### Backup
Schedule daily backups of Neo4j data:
```bash
docker exec mahoun-neo4j neo4j-admin database dump neo4j --to-path=/backups
```

### Log Rotation
Docker handles log rotation by default if configured in `daemon.json`. Ensure you have:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```
---

## 4. Troubleshooting

| Issue | Solution |
|-------|----------|
| Neo4j connection refused | Ensure Neo4j container is healthy and `NEO4J_URI` is correct. |
| Rate limit 429 errors | Check IP load and adjust settings in `mahoun/mcp/server.py`. |
| Auth errors | Ensure `X-API-Key` matches the `MCP_API_KEY` in environment. |
```
