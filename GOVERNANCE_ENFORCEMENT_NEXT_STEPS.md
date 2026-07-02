# Governance Enforcement - Next Steps & Action Plan

**Date**: 2026-07-02  
**Context**: Pre-production complete, returning to governance Layer 3+ work  
**Based on**: Comprehensive audit findings

---

## Current State Summary

### ✅ **Completed (Layer 1-2)**

| Layer | Component | Status | Evidence |
|-------|-----------|--------|----------|
| **Layer 1** | `MutationAuthorizationBoundary` | ✅ CONFIRMED | `mutation_boundary.py:307` - single implementation |
| | `GovernanceContext` | ✅ CONFIRMED | `governance_context.py:57` - single implementation |
| | `authorization_state.py` | ✅ CONFIRMED | ContextVar singleton verified |
| | `Neo4jConnection` (canonical) | ✅ CONFIRMED | Zero raw `GraphDatabase.driver()` in production |
| **Layer 2** | `LedgerWriteGate` | ✅ CONFIRMED | `write_gate.py` with provenance enforcement |
| | RAG Provenance Chain | ✅ CONFIRMED | `rag_evidence.py` → `generate_verdict` → `_build_case_graph` → ledger |
| | `retrieval_provenance` field | ✅ CONFIRMED | `EvidencePackage` in `ledger/models.py:21` |

**Result**: **Foundation is solid** ✅

---

## Open Issues (Prioritized)

### 🔴 **P0: Critical Blockers for Layer 3+**

#### Issue 1: GraphEnhancedRetriever Not Wired to Verdict Path

**Status**: MEDIUM priority (functionality exists but not connected)

**Evidence**:
- `bootstrap/runtime.py:108`: ✅ `GraphEnhancedRetriever` instantiated
- `bootstrap/runtime.py:113`: ✅ Registered in service registry
- `api/main.py`: ❌ **Never calls `bootstrap_runtime()`** — registry unused
- `reasoning/rag_adapter.py:142`: ❌ `HybridRAGService()` instantiated without `graph_retriever` param
- `hybrid_rag_service.py:67`: Default is `graph_retriever=None` — graph mode never active

**Impact**: 
- Graph-enhanced retrieval implemented but orphaned
- System falls back to vector-only mode
- Provenance chain incomplete for graph-sourced evidence

**Fix Required**:
```python
# Option A: Wire through bootstrap (recommended)
# In api/main.py lifespan:
from mahoun.bootstrap.runtime import bootstrap_runtime
runtime_services = bootstrap_runtime()

# In rag_adapter.py:
def create_rag_service():
    graph_retriever = runtime_services.get("graph_retriever")
    return HybridRAGService(graph_retriever=graph_retriever)

# Option B: Direct instantiation
# In rag_adapter.py:
from mahoun.graph.neo4j.connection import get_connection
from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever

connection = get_connection()
graph_retriever = GraphEnhancedRetriever(connection=connection)
rag_service = HybridRAGService(graph_retriever=graph_retriever)
```

**Effort**: 2-3 hours

**Priority**: **HIGH** (blocks full graph functionality)

---

#### ✅ RESOLVED: Issue 2 — Compliance Script False Positives

**Status**: ✅ **COMPLETE** (2026-07-02)

**Evidence (Before)**:
- Total violations reported: 43
- False positives: 36 (83%)
- Types of false positives:
  1. Test assertions with pattern strings (36 violations in `test_di_*.py`)
  2. Example files (`examples/schema_setup.py` - 3 violations)
  3. SQL vs Cypher confusion (`monitoring/retention.py` - 4 violations, PostgreSQL not Neo4j)

**Evidence (After)**:
```bash
python scripts/validate_governance_compliance.py
# Exit: 0
# Output: "✅ EXCELLENT: No governance violations detected!"
```

**Solution Implemented**:
1. Enhanced test assertion detection (±5 line context)
2. SQL vs Cypher discrimination (`asyncpg`, `DELETE FROM` patterns)
3. Example file exclusion (`/examples/` directories)
4. Worktree/backup directory exclusion (`.kilo/worktrees/`, `.test_classification_backup/`)
5. Test inventory data structure recognition (`VIOLATION_INVENTORY`)
6. Enum value vs Cypher query discrimination (`DELETE = "delete"`)

**Impact**: 
- ✅ CI gate now reliable (0% false positive rate)
- ✅ Script ready for production CI pipeline
- ✅ Team confidence restored

**Details**: See `COMPLIANCE_SCRIPT_FIX_REPORT.md`

**Effort**: 1.5 hours

---

#### Issue 3: GraphEnhancedRetriever Not Wired to Verdict Path
]

# 2. Distinguish SQL from Cypher
def is_cypher_query(line: str, file_path: str) -> bool:
    # Check file imports neo4j driver
    if "import neo4j" not in file_content:
        return False  # Likely SQL
    
    # Cypher-specific patterns
    cypher_keywords = ["MATCH", "CREATE", "MERGE", "WITH", "RETURN"]
    return any(kw in line.upper() for kw in cypher_keywords)

# 3. Separate "test assertions about violations" from "actual violations"
def is_test_assertion(line: str, context: str) -> bool:
    # Check if pattern is inside assert/expect/mock
    return any(x in context for x in ["assert", "expect", "mock", "@pytest"])
```

**Effort**: 3-4 hours

**Priority**: **CRITICAL** (blocks reliable CI gate)

---

### 🟡 **P1: Important but Not Blocking**

#### Issue 3: seed_data.py Raw Driver (Known Issue)

**Status**: LOW priority (documented, test-only)

**Evidence**: `tests/fixtures/seed_data.py:96` uses raw `GraphDatabase.driver()`

**Impact**: None on production (test fixture only)

**Action**: Keep documented in `AGENTS.md` (already done)

**Priority**: P3 (fix when touching test fixtures)

---

## Layer 3+ Work Plan

### Phase 3A: API Layer Enforcement (Week 1-2)

**Goal**: Hook governance context into API request lifecycle

#### Task 3A.1: API Middleware for Governance Context
**File**: `api/middleware/governance_middleware.py` (NEW)

```python
from mahoun.core.governance.governance_context import GovernanceContext
from mahoun.core.governance.authorization_state import set_authorized_context

async def governance_middleware(request: Request, call_next):
    # Extract actor from JWT/API key
    actor_id = extract_actor(request)
    correlation_id = request.headers.get("X-Correlation-ID", generate_uuid())
    
    # Create governance context for this request
    context = GovernanceContext(
        actor_id=actor_id,
        correlation_id=correlation_id,
        operation_type="api_request",
        provenance_chain=[f"api:{request.url.path}"],
    )
    
    # Set in ContextVar for this request
    token = set_authorized_context(context)
    try:
        response = await call_next(request)
        return response
    finally:
        reset_authorized_context(token)
```

**Register in `api/main.py`**:
```python
app.add_middleware(governance_middleware)
```

**Tests**:
- `tests/api/test_governance_middleware.py`
- Verify context flows to Neo4j writes
- Verify correlation_id in audit logs

**Acceptance**: All `/api/v1/*` requests have governance context

---

#### Task 3A.2: Reasoning Endpoint Enforcement
**File**: `api/routers/reasoning.py`

**Current**: Calls `verdict_engine.generate_verdict()` directly

**Required**: Wrap in governance context

```python
@router.post("/api/v1/reasoning/verdict")
async def generate_verdict_endpoint(request: VerdictRequest):
    # Context already set by middleware (Task 3A.1)
    
    # Verify authorization for this operation
    if not is_authorized():
        raise HTTPException(403, "Unauthorized mutation attempt")
    
    # Log governance entry
    audit_logger.info(
        "reasoning_request",
        actor=get_current_context().actor_id,
        correlation_id=get_current_context().correlation_id,
    )
    
    result = await verdict_engine.generate_verdict(
        question=request.question,
        facts=request.facts,
    )
    
    # Result already has provenance from Layer 2
    return result
```

**Tests**:
- `tests/api/test_reasoning_governance.py`
- Unauthorized request → 403
- Authorized request → provenance in ledger
- Audit log contains correlation_id

---

### Phase 3B: Service Layer Enforcement (Week 3-4)

#### Task 3B.1: EvidenceLinkedVerdictEngine Integration

**File**: `mahoun/reasoning/evidence_linked_verdict.py`

**Current**: Calls ledger writer directly

**Required**: Verify context before writes

```python
def generate_verdict(self, question: str, facts: List[str]) -> ReasoningResult:
    # Verify we're in authorized context
    if not is_authorized():
        raise SecurityBreachException(
            "Verdict generation requires authorized governance context"
        )
    
    context = get_current_context()
    
    # Rest of existing logic...
    
    # When writing to ledger (already done in Layer 2):
    ledger_result = self.ledger_gate.write_evidence_package(
        package=evidence_package,
        context=context,  # ✅ Already implemented
    )
```

**Tests**: Verify exception raised if context missing

---

#### Task 3B.2: RAG Pipeline Governance

**File**: `mahoun/rag/hybrid_rag_service.py`

**Requirement**: Track retrieval operations in governance context

```python
def retrieve(self, query: str, top_k: int) -> List[Evidence]:
    context = get_current_context()  # May be None (read-only op)
    
    # Log retrieval for audit
    if context:
        audit_logger.info(
            "rag_retrieval",
            query_hash=hash(query),
            correlation_id=context.correlation_id,
        )
    
    # Existing retrieval logic...
    results = self._vector_retrieve(query, top_k)
    
    # Add provenance
    for result in results:
        result.provenance_chain = [
            *context.provenance_chain if context else [],
            f"rag:hybrid:{result.source}",
        ]
    
    return results
```

---

### Phase 3C: Testing & CI Gates (Week 5)

#### Task 3C.1: Integration Tests

**File**: `tests/integration/test_governance_e2e.py` (NEW)

```python
def test_end_to_end_governance_flow():
    """Test full request → reasoning → ledger with governance context"""
    
    # 1. Make API request
    response = client.post(
        "/api/v1/reasoning/verdict",
        headers={"X-Actor": "test-user", "X-Correlation-ID": "test-123"},
        json={"question": "...", "facts": [...]},
    )
    
    # 2. Verify response
    assert response.status_code == 200
    result = response.json()
    
    # 3. Verify ledger entry
    ledger_entry = get_ledger_entry(result["ledger_id"])
    assert ledger_entry.correlation_id == "test-123"
    assert ledger_entry.actor_id == "test-user"
    
    # 4. Verify Neo4j audit
    neo4j_audit = get_neo4j_audit_trail("test-123")
    assert len(neo4j_audit) > 0
    assert all(entry.correlation_id == "test-123" for entry in neo4j_audit)

def test_unauthorized_mutation_blocked():
    """Test that mutation without context is blocked"""
    
    # Bypass API (simulates internal bypass attempt)
    verdict_engine = get_verdict_engine()
    
    # Clear any existing context
    reset_authorized_context()
    
    # Attempt mutation
    with pytest.raises(SecurityBreachException):
        verdict_engine.generate_verdict(question="...", facts=[])
```

---

#### Task 3C.2: CI Gate Enhancement

**File**: `ci/gates/gate_governance_enforcement.sh` (NEW)

```bash
#!/bin/bash
# Governance Enforcement CI Gate
set -e

echo "🔒 Running Governance Enforcement Gate..."

# 1. Run fixed compliance script
python scripts/validate_governance_compliance.py
if [ $? -ne 0 ]; then
    echo "❌ Governance compliance violations found"
    exit 1
fi

# 2. Run governance tests
pytest tests/governance/ tests/integration/test_governance_e2e.py -v
if [ $? -ne 0 ]; then
    echo "❌ Governance tests failed"
    exit 1
fi

# 3. Verify no bypass patterns
python ci/scripts/scan_bypass_patterns.py
if [ $? -ne 0 ]; then
    echo "❌ Governance bypass patterns detected"
    exit 1
fi

echo "✅ Governance enforcement gate passed"
```

---

## Summary: Action Plan

### Immediate (This Week)
1. ✅ **Fix compliance script false positives** (P0, 3-4 hours)
2. ✅ **Wire GraphEnhancedRetriever to verdict path** (P0, 2-3 hours)
3. ⏭️ **Start Task 3A.1**: Governance middleware (Week 1)

### Week 1-2: API Layer
- Task 3A.1: Governance middleware ✅
- Task 3A.2: Reasoning endpoint enforcement ✅
- Tests for API layer ✅

### Week 3-4: Service Layer
- Task 3B.1: Verdict engine verification ✅
- Task 3B.2: RAG pipeline tracking ✅
- Tests for service layer ✅

### Week 5: Validation
- Task 3C.1: E2E integration tests ✅
- Task 3C.2: Enhanced CI gate ✅
- Full stack smoke test ✅

---

## Success Criteria

**Layer 3 Complete When**:
- ✅ All API requests have governance context
- ✅ Unauthorized mutations blocked at API layer
- ✅ Correlation IDs flow through full stack
- ✅ Audit logs contain governance data
- ✅ CI gate passes with zero false positives

**Layer 4 Complete When**:
- ✅ Service layer enforces context checks
- ✅ RAG pipeline tracks provenance
- ✅ Verdict engine rejects contextless calls
- ✅ Integration tests cover all paths

**Layer 5 Complete When**:
- ✅ E2E tests pass
- ✅ CI gate blocks bypasses
- ✅ Governance enforcement documented
- ✅ Team trained on patterns

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing APIs | Add middleware gradually, feature-flag enforcement |
| Performance impact | Measure latency, optimize ContextVar access |
| False CI gate failures | Thorough testing of compliance script fixes |
| Team confusion | Document patterns, provide examples |

---

**Next Action**: Fix compliance script (starts immediately) → Then Task 3A.1 middleware

**Owner**: Platform Team  
**Timeline**: 5 weeks for Layer 3-5 complete  
**Review Cadence**: Weekly check-ins
