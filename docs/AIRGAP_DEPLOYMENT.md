# MAHOUN Air-Gapped Deployment Guide

## 🔒 Overview

This guide covers deploying MAHOUN in **air-gapped environments** (isolated networks without internet access).

**Use Cases:**
- Government/military installations
- Healthcare facilities (HIPAA compliance)
- Financial institutions (regulatory requirements)
- Critical infrastructure
- High-security research facilities

---

## 📋 Prerequisites

### Hardware Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 50GB minimum, 100GB recommended
- **Network**: Isolated network (no internet)

### Software Requirements
- **OS**: Ubuntu 20.04+ or RHEL 8+
- **Python**: 3.11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

---

## 🚀 Quick Start (5 Steps)

### Step 1: Create Deployment Bundle (On Internet-Connected System)

```bash
# Clone repository
git clone https://github.com/your-org/mahoun-platform.git
cd mahoun-platform

# Create air-gapped bundle
./scripts/create_airgap_bundle.sh

# Output: mahoun-airgap-bundle-{version}-{date}.tar.gz
```

### Step 2: Transfer Bundle to Air-Gapped System

```bash
# Copy to USB drive
cp dist/mahoun-airgap-bundle-*.tar.gz /media/usb/

# Or use secure file transfer
# scp mahoun-airgap-bundle-*.tar.gz user@airgap-system:/tmp/
```

### Step 3: Extract and Verify Bundle

```bash
# On air-gapped system
cd /opt/mahoun
tar -xzf /media/usb/mahoun-airgap-bundle-*.tar.gz
cd mahoun-airgap-bundle-*

# Verify integrity
sha256sum -c checksums/SHA256SUMS
```

### Step 4: Install Dependencies

```bash
# Install Python packages (offline)
pip install --no-index --find-links=python-packages -r ../requirements.txt

# Load Docker images (offline)
docker load -i docker-images/mahoun-app.tar
docker load -i docker-images/neo4j.tar
docker load -i docker-images/prometheus.tar
docker load -i docker-images/grafana.tar
```

### Step 5: Configure and Start

```bash
# Generate API keys
python scripts/manage_api_keys.py generate --role admin --name "Admin User"
# Save the generated key: mahoun_key_abc123...

# Configure environment
cp config/env.template .env
nano .env  # Edit configuration

# Start services
docker-compose -f config/docker-compose.prod.yml up -d

# Verify
curl -H "X-API-Key: mahoun_key_abc123..." http://localhost:8000/api/v1/reasoning/health
```

---

## 🔐 Security Configuration

### 1. API Key Management

```bash
# Generate admin key
python scripts/manage_api_keys.py generate \
    --role admin \
    --name "System Administrator" \
    --expires-days 365

# Generate readonly key
python scripts/manage_api_keys.py generate \
    --role readonly \
    --name "Monitoring Service" \
    --expires-days 90

# List all keys
python scripts/manage_api_keys.py list

# Revoke compromised key
python scripts/manage_api_keys.py revoke --key mahoun_key_xyz789
```

### 2. Encrypted Configuration

```bash
# Set master password for encryption
export MAHOUN_MASTER_PASSWORD="your-secure-password"

# Keys will be encrypted at rest
# config/api_keys.json (encrypted)
```

### 3. Network Isolation

```yaml
# docker-compose.prod.yml
networks:
  internal:
    driver: bridge
    internal: true  # No external access
  
  external:
    driver: bridge
    # Only for necessary services
```

---

## 📊 Monitoring (Offline)

### Prometheus + Grafana (Local)

```bash
# Access Grafana
http://localhost:3000
# Default: admin/admin

# Import dashboards
# Located in: monitoring/dashboards/*.json
```

### Log Aggregation (Local)

```bash
# View logs
docker-compose logs -f mahoun-app

# Export logs for analysis
docker-compose logs mahoun-app > logs/mahoun-$(date +%Y%m%d).log
```

---

## 🔄 Updates and Maintenance

### Updating MAHOUN (Air-Gapped)

```bash
# 1. Create new bundle (on internet-connected system)
./scripts/create_airgap_bundle.sh

# 2. Transfer to air-gapped system

# 3. Backup current installation
./scripts/backup.sh

# 4. Stop services
docker-compose down

# 5. Extract new bundle
tar -xzf mahoun-airgap-bundle-new.tar.gz

# 6. Install updates
pip install --no-index --find-links=python-packages --upgrade -r requirements.txt
docker load -i docker-images/mahoun-app.tar

# 7. Start services
docker-compose up -d

# 8. Verify
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/reasoning/health
```

### Key Rotation

```bash
# 1. Generate new keys
python scripts/manage_api_keys.py generate --role admin --name "New Admin"

# 2. Update client applications with new keys

# 3. Revoke old keys
python scripts/manage_api_keys.py revoke --key mahoun_key_old123

# 4. Reload keys without restart
curl -X POST -H "X-API-Key: admin_key" http://localhost:8000/api/admin/reload-keys
```

---

## 🛠️ Troubleshooting

### Issue: API Key Not Working

```bash
# Verify key exists
python scripts/manage_api_keys.py list

# Check if revoked or expired
python scripts/manage_api_keys.py validate --key mahoun_key_abc123

# Check logs
docker-compose logs mahoun-app | grep "Invalid API key"
```

### Issue: Docker Images Not Loading

```bash
# Verify image files
ls -lh docker-images/

# Check Docker
docker images | grep mahoun

# Reload specific image
docker load -i docker-images/mahoun-app.tar
```

### Issue: Database Connection Failed

```bash
# Check Neo4j status
docker-compose ps neo4j

# View Neo4j logs
docker-compose logs neo4j

# Restart Neo4j
docker-compose restart neo4j
```

---

## 📦 Backup and Recovery

### Automated Backup

```bash
# Run backup script
./scripts/backup.sh

# Output: backups/mahoun-backup-{date}.tar.gz
```

### Manual Backup

```bash
# Backup database
docker exec mahoun-neo4j neo4j-admin dump --to=/backups/neo4j-$(date +%Y%m%d).dump

# Backup configuration
tar -czf config-backup.tar.gz config/ .env

# Backup ledger
tar -czf ledger-backup.tar.gz data/ledger/
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore backup
./scripts/restore.sh backups/mahoun-backup-20240227.tar.gz

# Start services
docker-compose up -d
```

---

## 🔍 Health Checks

### System Health

```bash
# API health
curl -H "X-API-Key: ..." http://localhost:8000/api/v1/reasoning/health

# Database health
docker exec mahoun-neo4j cypher-shell "MATCH (n) RETURN count(n) LIMIT 1;"

# Disk space
df -h /opt/mahoun

# Memory usage
docker stats --no-stream
```

### Automated Health Monitoring

```bash
# Add to crontab
*/5 * * * * /opt/mahoun/scripts/health_check.sh >> /var/log/mahoun-health.log
```

---

## 📚 Additional Resources

- **Architecture**: `docs/ARCHITECTURE.md`
- **API Reference**: `docs/api/README.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **Security**: `docs/SECURITY.md`

---

## ⚠️ Important Notes

### Security Best Practices

1. **Change default passwords** immediately
2. **Rotate API keys** every 90 days
3. **Enable audit logging** for compliance
4. **Backup regularly** (daily recommended)
5. **Test restore procedures** quarterly

### Compliance

- **HIPAA**: Enable audit logging, encrypt at rest
- **GDPR**: Configure data retention policies
- **SOC 2**: Enable monitoring and alerting

### Support

For air-gapped environments:
- Refer to offline documentation in `docs/` directory
- Contact support via secure channel
- Emergency: Use offline troubleshooting guide

---

## ✅ Deployment Checklist

- [ ] Bundle created and verified
- [ ] Transferred to air-gapped system
- [ ] Dependencies installed
- [ ] API keys generated
- [ ] Configuration completed
- [ ] Services started
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup scheduled
- [ ] Documentation reviewed
- [ ] Team trained

---

**Last Updated**: 2024-02-27  
**Version**: 1.0.0  
**Status**: Production Ready
