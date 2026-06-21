# MAHOUN API Reference

Welcome to the MAHOUN API reference. This document provides detailed information about the endpoints available in the MAHOUN platform.

## Base URL
The API is typically served at `http://<host>:<port>/api/v1`.

## Authentication
Most endpoints require authentication. Use the `X-API-Key` header with your valid API key.

---

## 1. Core Reasoning (Analysis)
**Router**: `/mahoun`

### [POST] `/upload`
Upload and process documents for analysis.
- **Request**: Multipart/Form-Data
    - `file`: UploadFile (PDF, DOCX, TXT)
    - `doc_type`: Optional string (contract, letter, etc.)
- **Response**: `DocumentUploadResponse`
    - `document_id`: Unique ID for the uploaded doc.
    - `normalized`: Dictionary of extracted/normalized content.

### [POST] `/analyze_delay`
Analyze project delays based on schedules.
- **Request**: `DelayAnalysisRequest`
    - `project_id`: Required string.
    - `baseline_schedule`: Optional dictionary.
- **Response**: `DelayAnalysisResponse`
    - `delays`: List of identified delay events.
    - `critical_path`: List of critical tasks.

### [POST] `/generate_claim`
Generate a legal claim draft.
- **Request**: `ClaimGenerationRequest`
    - `claim_type`: Type of claim.
    - `facts`: Fact description.
- **Response**: `ClaimGenerationResponse`
    - `claim_content`: Generated claim text.
    - `citations`: List of legal citations.

### [POST] `/ask_contract`
Ask questions about a specific contract.
- **Request**: `ContractQueryRequest`
    - `query`: The question.
    - `contract_id`: The document ID.
- **Response**: `ContractQueryResponse`
    - `answer`: Reasoning response.
    - `confidence`: Confidence score (0-1).
    - `verified`: Boolean indicating grounding in evidence.

---

## 2. Ingestion & Jobs
**Router**: `/ingest`

### [POST] `/jobs`
Submit a document for asynchronous ingestion.
- **Request**: Multipart/Form-Data
- **Response**: Returns a `job_id`.

### [GET] `/jobs/{job_id}`
Track the status of an ingestion job.
- **Statuses**: `queued`, `processing`, `completed`, `failed`.

### [GET] `/dlq`
List items in the Dead Letter Queue (failed jobs).

---

## 3. Legal Search
**Router**: `/search`

### [POST] `/verdicts`
Search for legal verdicts using natural language.
- **Request**: `VerdictSearchRequest`
    - `query`: Search string.
    - `filters`: Optional `SearchFilters` (court_level, date_range, etc.)
- **Response**: `VerdictSearchResponse`
    - `results`: List of `VerdictHit` objects with relevance scores.

---

## 4. System Health
**Router**: `/health` (or `/system`)

### [GET] `/health`
Comprehensive health check for all system components.
- **Components**: PostgreSQL, Neo4j, Redis, Vector Store.
- **Response**: Detailed latency and status for each.

### [GET] `/status`
Lightweight API availability check.
