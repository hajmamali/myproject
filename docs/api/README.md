# MAHOUN Reasoning API Documentation

## Overview

MAHOUN Reasoning API provides zero-hallucination legal reasoning with cryptographic proofs and blockchain audit trails.

## Quick Start

### 1. Get API Key

Contact support@mahoun.ai to obtain an API key.

### 2. Make Your First Request

```bash
curl -X POST https://api.mahoun.ai/v1/reasoning/generate-verdict \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Is contract termination valid under Article 219?",
    "facts": [
      {"value": "Contract signed on 2024-01-01"},
      {"value": "Termination notice sent on 2024-06-01"}
    ],
    "generate_proof": true
  }'
```

### 3. Verify Response

```json
{
  "success": true,
  "verdict_id": "verdict_abc123",
  "final_verdict": "Contract termination is valid under Article 219",
  "confidence_score": 0.95,
  "proof": {
    "graph_state_hash": "a1b2c3...",
    "signature": "j0k1l2..."
  }
}
```

## Core Concepts

### Evidence-Linked Reasoning

Every conclusion is explicitly linked to graph evidence:

```
Verdict Step → Evidence References → Graph Nodes
```

### Zero-Hallucination Guarantee

- ✅ All reasoning grounded in knowledge graph
- ✅ No LLM free-text generation
- ✅ Deterministic contradiction resolution
- ✅ Runtime guardrails enforcement

### Blockchain Audit Trail

- ✅ Immutable ledger
- ✅ Complete history
- ✅ Tamper-evident
- ✅ Regulatory compliant

### Cryptographic Proofs

- ✅ Non-repudiation
- ✅ Tamper detection
- ✅ Independent verification
- ✅ Legal evidence

## API Endpoints

### Generate Verdict

```http
POST /reasoning/generate-verdict
```

Generate evidence-linked verdict with cryptographic proof.

**Request:**
```json
{
  "question": "string",
  "facts": [
    {
      "value": "string",
      "type": "string",
      "confidence": 1.0
    }
  ],
  "generate_proof": true
}
```

**Response:**
```json
{
  "success": true,
  "verdict_id": "string",
  "final_verdict": "string",
  "steps": [...],
  "confidence_score": 0.95,
  "proof": {...}
}
```

### Verify Verdict

```http
POST /reasoning/verify-verdict
```

Verify cryptographic proof of verdict.

**Request:**
```json
{
  "verdict_id": "string",
  "proof": {...}
}
```

**Response:**
```json
{
  "success": true,
  "is_valid": true,
  "verification_details": {...}
}
```

### Query Ledger

```http
POST /reasoning/query-ledger
```

Query blockchain ledger for audit trail.

**Request:**
```json
{
  "case_id": "string"
}
```

**Response:**
```json
{
  "success": true,
  "entries": [...],
  "total_count": 10
}
```

### Health Check

```http
GET /reasoning/health
```

Check system health and availability.

**Response:**
```json
{
  "status": "healthy",
  "mode": "ENTERPRISE_FULL",
  "components": {...}
}
```

## Authentication

All endpoints (except health check) require API key authentication:

```http
Authorization: Bearer YOUR_API_KEY
```

## Error Handling

All errors follow consistent structure:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "details": {...},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Codes

- `invalid_request` (400): Invalid request parameters
- `unauthorized` (401): Missing or invalid API key
- `forbidden` (403): Insufficient permissions
- `resource_not_found` (404): Resource not found
- `rate_limit_exceeded` (429): Rate limit exceeded
- `internal_error` (500): Internal server error
- `service_unavailable` (503): Service unavailable

## Rate Limits

- **Default**: 100 requests per minute
- **Burst**: 10 requests per second
- **Daily**: 10,000 requests per day

Contact support for higher limits.

## Modes

### ENTERPRISE_FULL (Production)

- ✅ Full graph reasoning
- ✅ Blockchain ledger
- ✅ Cryptographic proofs
- ✅ All features enabled

### DESKTOP_MINIMAL (Development)

- ❌ Limited graph operations
- ❌ Reasoning API unavailable
- ✅ Syntax validation only

**Note**: Reasoning API requires ENTERPRISE_FULL mode.

## Best Practices

### 1. Batch Facts

Group related facts in single request:

```json
{
  "question": "...",
  "facts": [
    {"value": "Fact 1"},
    {"value": "Fact 2"},
    {"value": "Fact 3"}
  ]
}
```

### 2. Cache Proofs

Store cryptographic proofs for verification:

```python
proof = response["proof"]
# Store proof in database
db.save_proof(verdict_id, proof)
```

### 3. Verify Periodically

Verify proofs to detect tampering:

```python
# Verify proof
verify_response = client.post(
    "/reasoning/verify-verdict",
    json={"verdict_id": verdict_id, "proof": proof}
)
assert verify_response["is_valid"]
```

### 4. Query Ledger

Use ledger for audit trails:

```python
# Get all verdicts for case
ledger_response = client.post(
    "/reasoning/query-ledger",
    json={"case_id": case_id}
)
```

### 5. Handle Errors

Implement retry logic with exponential backoff:

```python
import time

def generate_verdict_with_retry(request, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.post("/reasoning/generate-verdict", json=request)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
```

## SDKs

### Python

```bash
pip install mahoun-sdk
```

```python
from mahoun import ReasoningClient

client = ReasoningClient(api_key="YOUR_API_KEY")

verdict = client.generate_verdict(
    question="Is contract termination valid?",
    facts=["Contract signed on 2024-01-01"]
)

print(verdict.final_verdict)
print(verdict.confidence_score)
```

### JavaScript/TypeScript

```bash
npm install @mahoun/sdk
```

```typescript
import { ReasoningClient } from '@mahoun/sdk';

const client = new ReasoningClient({ apiKey: 'YOUR_API_KEY' });

const verdict = await client.generateVerdict({
  question: 'Is contract termination valid?',
  facts: [{ value: 'Contract signed on 2024-01-01' }]
});

console.log(verdict.finalVerdict);
console.log(verdict.confidenceScore);
```

## Examples

### Contract Analysis

```bash
curl -X POST https://api.mahoun.ai/v1/reasoning/generate-verdict \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Can the contract be terminated early?",
    "facts": [
      {"value": "Contract duration: 2 years", "type": "CONTRACT_TERM"},
      {"value": "Early termination clause exists", "type": "CONTRACT_CLAUSE"},
      {"value": "6 months notice required", "type": "CONTRACT_REQUIREMENT"}
    ],
    "generate_proof": true
  }'
```

### Compliance Check

```bash
curl -X POST https://api.mahoun.ai/v1/reasoning/generate-verdict \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Is the transaction compliant with AML regulations?",
    "facts": [
      {"value": "Transaction amount: $15,000", "type": "TRANSACTION"},
      {"value": "Customer KYC completed", "type": "COMPLIANCE"},
      {"value": "Source of funds verified", "type": "COMPLIANCE"}
    ],
    "generate_proof": true
  }'
```

## Support

- **Email**: support@mahoun.ai
- **Documentation**: https://docs.mahoun.ai
- **Status**: https://status.mahoun.ai
- **GitHub**: https://github.com/mahoun/platform

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
- [reasoning-api.yaml](./reasoning-api.yaml)
- Interactive docs: https://api.mahoun.ai/docs

## Changelog

### v1.0.0 (2024-01-15)

- Initial release
- Evidence-linked verdict generation
- Cryptographic proof verification
- Blockchain ledger queries
- Health check endpoint

## License

Proprietary - Contact sales@mahoun.ai for licensing information.
