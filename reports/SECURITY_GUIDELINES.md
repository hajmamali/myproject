# MAHOUN Platform - Security Guidelines

**Classification:** MISSION-CRITICAL  
**Last Updated:** 2026-05-13  
**Status:** ACTIVE

---

## 🔒 Overview

This document outlines security practices for the MAHOUN platform to protect sensitive data, credentials, and proprietary logic when transitioning from private to public repository.

---

## 🚨 Critical Security Rules

### NEVER COMMIT:

1. **Credentials & Secrets**
   - API keys (OpenAI, Anthropic, HuggingFace, etc.)
   - Database passwords
   - JWT secrets
   - OAuth tokens
   - Service account credentials
   - Cloud provider credentials (AWS, Azure, GCP)

2. **Cryptographic Material**
   - Private keys (`.key`, `.pem`, `id_rsa`, etc.)
   - Certificates (`.crt`, `.p12`, `.pfx`)
   - Keystores
   - SSL/TLS private keys

3. **Environment Files**
   - `.env` (actual environment files)
   - `.env.local`
   - `.env.production`
   - Any file containing actual configuration values

4. **Database Files**
   - SQLite databases (`.sqlite`, `.db`)
   - Database dumps
   - Neo4j data directories
   - Vector store data

5. **Proprietary Data**
   - Customer data
   - PII (Personally Identifiable Information)
   - Medical records
   - Financial data
   - Internal business logic marked as confidential

6. **Large Binary Files**
   - Model weights (`.pt`, `.pth`, `.ckpt`, `.safetensors`)
   - Embeddings
   - Large datasets
   - Video/audio files

---

## ✅ Safe to Commit

1. **Example Files**
   - `.env.example` (with placeholder values)
   - `.env.backend.example`
   - `config.example.json`
   - Template files with `REPLACE_ME` or `YOUR_KEY_HERE`

2. **Documentation**
   - README files
   - Architecture documentation
   - API documentation
   - Setup guides

3. **Source Code**
   - Application logic (non-proprietary)
   - Tests
   - Configuration templates
   - Build scripts

4. **Configuration**
   - Docker Compose templates
   - CI/CD workflows
   - Linting/formatting configs

---

## 🛡️ Security Checklist Before Public Release

### Pre-Release Audit

- [ ] Review all `.env` files - ensure only `.example` versions exist
- [ ] Search for hardcoded credentials in source code
- [ ] Verify no API keys in configuration files
- [ ] Check git history for accidentally committed secrets
- [ ] Scan for proprietary/confidential markers
- [ ] Review database connection strings
- [ ] Verify no customer/PII data in test fixtures
- [ ] Check for internal URLs/endpoints
- [ ] Review comments for sensitive information
- [ ] Verify `.gitignore` is comprehensive

### Commands to Run

```bash
# 1. Check for potential secrets in tracked files
git grep -iE 'api[_-]?key|secret[_-]?key|password|token' -- '*.py' '*.json' '*.yaml' '*.yml'

# 2. Check for environment files
find . -name "*.env" -not -name "*.env.example" -not -path "*/venv/*" -not -path "*/node_modules/*"

# 3. Check for private keys
find . -name "*.key" -o -name "*.pem" -o -name "id_rsa*" -not -path "*/venv/*"

# 4. Check git history for secrets (requires git-secrets)
git secrets --scan-history

# 5. Run security audit script
.github/scripts/security-audit-pre-commit.sh

# 6. Check what would be committed
git status
git diff --cached
```

---

## 🔍 Detecting Secrets in Git History

If secrets were previously committed, they exist in git history even after deletion.

### Clean Git History (DESTRUCTIVE - Use with Caution)

```bash
# Option 1: Using BFG Repo-Cleaner (recommended)
# Download from: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files '*.env'
java -jar bfg.jar --replace-text passwords.txt  # File with secrets to replace
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Option 2: Using git-filter-repo
pip install git-filter-repo
git filter-repo --path-glob '*.env' --invert-paths
git filter-repo --replace-text passwords.txt

# Option 3: Using git filter-branch (legacy)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

**⚠️ WARNING:** These commands rewrite git history. All collaborators must re-clone.

---

## 🔐 Secure Configuration Management

### Using Environment Variables

```python
# ✅ GOOD: Load from environment
import os
from dotenv import load_dotenv

load_dotenv()  # Loads from .env (not committed)

API_KEY = os.getenv("OPENAI_API_KEY")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
```

```python
# ❌ BAD: Hardcoded secrets
API_KEY = "sk-proj-abc123xyz789"  # NEVER DO THIS
DB_PASSWORD = "mypassword123"     # NEVER DO THIS
```

### Example .env File Structure

```bash
# .env (NEVER COMMIT - in .gitignore)
OPENAI_API_KEY=sk-proj-actual-key-here
DATABASE_PASSWORD=actual-password-here
NEO4J_PASSWORD=actual-neo4j-password
MCP_API_KEY=actual-mcp-key
```

```bash
# .env.example (SAFE TO COMMIT)
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
DATABASE_PASSWORD=YOUR_PASSWORD_HERE
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD
MCP_API_KEY=YOUR_MCP_KEY_HERE
```

---

## 🚀 Pre-Commit Hooks

Install the security audit as a pre-commit hook:

```bash
# Copy the hook
cp .github/scripts/security-audit-pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Or use pre-commit framework
pip install pre-commit
pre-commit install
```

---

## 📊 Security Scanning Tools

### Recommended Tools

1. **git-secrets** (AWS)
   ```bash
   brew install git-secrets  # macOS
   git secrets --install
   git secrets --register-aws
   ```

2. **truffleHog** (Secret scanning)
   ```bash
   pip install truffleHog
   trufflehog filesystem /path/to/repo
   ```

3. **detect-secrets** (Yelp)
   ```bash
   pip install detect-secrets
   detect-secrets scan > .secrets.baseline
   ```

4. **gitleaks** (Secret detection)
   ```bash
   brew install gitleaks  # macOS
   gitleaks detect --source . --verbose
   ```

---

## 🔄 Rotating Compromised Secrets

If a secret is accidentally committed:

1. **Immediately rotate the secret**
   - Generate new API key
   - Change password
   - Revoke old credentials

2. **Remove from git history** (see above)

3. **Update all environments**
   - Development
   - Staging
   - Production

4. **Notify team members**

5. **Review access logs** for unauthorized usage

---

## 📝 Code Review Checklist

Before approving PRs, verify:

- [ ] No hardcoded credentials
- [ ] No `.env` files (except `.example`)
- [ ] No private keys or certificates
- [ ] No database files
- [ ] No large binary files
- [ ] No proprietary markers
- [ ] No customer/PII data
- [ ] Environment variables used correctly
- [ ] Secrets loaded from environment, not hardcoded

---

## 🆘 Incident Response

### If a Secret is Exposed:

1. **IMMEDIATE:** Rotate the compromised credential
2. **URGENT:** Remove from git history
3. **HIGH:** Review access logs for unauthorized usage
4. **MEDIUM:** Notify security team
5. **LOW:** Document incident and lessons learned

### Contact

- Security Team: [security@mahoun.ai](mailto:security@mahoun.ai)
- Emergency: [Use internal incident response protocol]

---

## 📚 Additional Resources

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Git Security Best Practices](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)

---

## 📄 License & Compliance

This security guideline is part of the MAHOUN platform and must be followed by all contributors.

**Last Review:** 2026-05-13  
**Next Review:** 2026-08-13  
**Owner:** Security Team
