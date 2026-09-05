# CASE ISOLATION CONTRACT v1.0

## CLASSIFICATION: ARCHITECTURAL BOUNDARY CONTRACT

**Status**: DRAFT - Pending Approval  
**Version**: 1.0  
**Date**: 2025-01-27  
**Authority**: Derived from Phase 2C Forensic Audit findings  

**Purpose**: Define the formal contract for case isolation in MahouN to ensure:
- Private case data never leaks across cases
- Shared system knowledge remains accessible to all cases
- Authorization precedes all case-scoped operations

---

## CONTRACT PRINCIPLES

### Principle 1: Case Scope is a Security Boundary

**Definition**: Case Scope is NOT metadata; it is a **security boundary** that MUST be enforced at every layer.

**Invariant**:
```
∀ operation ∈ {read, write, retrieve, reason}:
    IF operation.accesses(private_case_data)
    THEN operation.MUST_HAVE(authorized_case_scope)
```

**Violation**: Any operation accessing private case data without authorization is a **security violation**, not a feature gap.

---

### Principle 2: Identity Taxonomy

**Multiple identity types exist and MUST NOT be conflated**:

| Identity Type | Purpose | Generation | Example |
|---------------|---------|------------|---------|
| **Case Identity** | Legal case identifier | User-provided or system-assigned | `CASE-2024-001` |
| **Request Correlation ID** | Track request through system | System-generated UUID | `550e8400-e29b-41d4-a716-446655440000` |
| **Document Identity** | Identify specific document | Hash or ID | `DOC-123` or `sha256:abc...` |
| **Content Fingerprint** | Detect duplicate content | Deterministic hash | `sha256(content)` |
| **Verdict Identity** | Unique verdict ID | System-generated | `verdict_550e8400...` |

**Invariant**:
```
case_id ≠ correlation_id ≠ document_id ≠ content_fingerprint
```

**Rationale**: Same facts in different cases are **different legal matters**.

**Example**:
```
Case A: Employee X sues Company Y for breach
Case B: Employee Z sues Company Y for breach (same facts, different case)
```

Both have identical facts but are **separate cases** with **separate case IDs**.

---

### Principle 3: Case Authorization

**Invariant**: Possession of `case_id` ≠ Authorization to access case

**Contract**:
```python
def access_case(user: User, case_id: str) -> CaseScope:
    # MANDATORY authorization check
    if not authorize_case_access(user, case_id):
        raise UnauthorizedCaseAccess(user, case_id)
    
    return CaseScope(case_id, authorized=True)
```

**Forbidden**:
```python
def access_case(case_id: str) -> CaseScope:
    # ❌ NO authorization check
    return CaseScope(case_id)  # VIOLATION
```

**Enforcement Points**:
- API request handler
- Reasoning engine entry
- Ledger query
- RAG retrieval
- Graph query

---

### Principle 4: Read Isolation

**Invariant**: Case-scoped query results MUST contain ONLY authorized case data + shared system knowledge

**Contract**:
```python
def query_case_data(scope: AuthorizedCaseScope) -> Results:
    results = []
    for item in all_data:
        if item.is_shared_knowledge():
            results.append(item)  # ✅ Shared knowledge OK
        elif item.case_id == scope.case_id:
            results.append(item)  # ✅ Same case OK
        else:
            # ❌ Different case - SKIP
            pass
    return results
```

**Test Oracle**:
```python
# Golden rule test
results = query_case_data(authorized_scope)
for item in results:
    assert item.is_shared_knowledge() or item.case_id == scope.case_id
```

---

### Principle 5: Write Isolation

**Invariant**: Case-scoped mutations MUST be consistent with authorized scope

**Contract**:
```python
def write_case_data(scope: AuthorizedCaseScope, data: CaseData):
    # Verify consistency
    if data.case_id != scope.case_id:
        raise CaseScopeViolation(
            f"Cannot write case {data.case_id} data to scope {scope.case_id}"
        )
    
    # Verify authorization
    if not scope.authorized:
        raise UnauthorizedWrite(scope)
    
    # Write with scope binding
    persist(data)
```

**Immutability Contract**:
```python
# After creation, case association is immutable
ledger_entry.case_id  # Frozen, cannot change
```

---

### Principle 6: Shared Knowledge Distinction

**Definition**: System Legal Knowledge is **shared** across all cases; Private Case Data is **isolated**

**Shared System Knowledge** (accessible to all cases):
```
- Legal statutes (قانون مدنی، قانون تجارت)
- Legal articles (مواد قانونی)
- Public legal precedents (آرای وحدت رویه)
- Advisory opinions (نظریات مشورتی)
- Legal principles (اصول حقوقی)
```

**Private Case Data** (case-scoped):
```
- Case documents
- Case evidence
- Case claims  
- Case facts
- Case reasoning steps
- Case verdicts
```

**Schema Distinction**:
```python
# Graph node properties
node.scope: Literal["SHARED", "CASE_SCOPED"]
node.case_id: Optional[str]  # Only for case-scoped nodes

# Invariant
if node.scope == "SHARED":
    assert node.case_id is None
if node.scope == "CASE_SCOPED":
    assert node.case_id is not None
```

---

### Principle 7: Reasoning Isolation

**Invariant**: Reasoning MUST use ONLY authorized inputs

**Contract**:
```python
async def reason_case(scope: AuthorizedCaseScope, question: str, facts: list):
    # Retrieve ONLY authorized evidence
    evidence = retrieve_evidence(
        query=question,
        scope=scope,  # ← Enforces isolation
        include_shared_knowledge=True
    )
    
    # Verify evidence scope
    for e in evidence:
        assert e.is_shared_knowledge() or e.case_id == scope.case_id
    
    # Reason with isolated context
    verdict = reason(question, facts, evidence)
    
    # Bind verdict to case
    verdict.case_id = scope.case_id
    
    return verdict
```

**Forbidden**:
```python
async def reason_case(case_id: str, question: str, facts: list):
    # ❌ No scope enforcement
    evidence = retrieve_all_evidence(query=question)  # LEAKAGE
    verdict = reason(question, facts, evidence)
    verdict.case_id = case_id  # Too late - already leaked
    return verdict
```

---

### Principle 8: RAG Isolation

**Invariant**: Retrieval MUST be scope-aware for private documents

**Contract**:
```python
def retrieve_documents(
    query: str, 
    scope: AuthorizedCaseScope,
    include_shared: bool = True
) -> list[Document]:
    
    # Build filters
    filters = []
    
    if include_shared:
        filters.append({"scope": "SHARED"})
    
    filters.append({
        "scope": "CASE_SCOPED",
        "case_id": scope.case_id
    })
    
    # Query with scope enforcement
    results = vector_db.query(
        embedding=embed(query),
        filter={"$or": filters}
    )
    
    return results
```

**Metadata Schema**:
```python
# Every document in vector store must have:
{
    "document_id": str,
    "scope": Literal["SHARED", "CASE_SCOPED"],
    "case_id": Optional[str],  # Required if CASE_SCOPED
    "content": str,
    "embedding": vector
}
```

---

### Principle 9: Graph Isolation

**Invariant**: Graph queries for case-private nodes MUST be scope-filtered

**Contract**:
```cypher
// Case-scoped query
MATCH (n:CaseDocument)
WHERE n.case_id = $authorized_case_id
RETURN n

// Shared knowledge query (no case filter needed)
MATCH (n:LegalArticle)
WHERE n.article_number = $article_num
RETURN n

// Mixed query (case + shared)
MATCH (case_node:CaseEvidence)-[:CITES]->(law:LegalArticle)
WHERE case_node.case_id = $authorized_case_id
RETURN case_node, law
```

**Node Schema**:
```python
# All graph nodes MUST have scope property
CREATE (n:Node {
    scope: "SHARED" | "CASE_SCOPED",
    case_id: Optional[str]  # Required if CASE_SCOPED
})

// Constraint
CREATE CONSTRAINT scope_case_id_consistency
FOR (n:Node)
REQUIRE (n.scope = "SHARED" AND n.case_id IS NULL) OR
        (n.scope = "CASE_SCOPED" AND n.case_id IS NOT NULL)
```

---

### Principle 10: Ledger Isolation

**Invariant**: Ledger operations MUST be scope-authorized

**Read Contract**:
```python
def get_case_ledger(user: User, case_id: str) -> list[LedgerEntry]:
    # MANDATORY authorization
    scope = authorize_case_access(user, case_id)
    
    # Query with validated scope
    entries = blockchain.get_entries_by_case(scope.case_id)
    
    return entries
```

**Write Contract**:
```python
def write_ledger_entry(scope: AuthorizedCaseScope, entry: LedgerEntry):
    # Verify scope consistency
    if entry.case_id != scope.case_id:
        raise CaseScopeViolation()
    
    # Verify authorization
    if not scope.authorized:
        raise UnauthorizedWrite()
    
    # Write
    blockchain.append(entry)
```

---

## SEMANTIC CONTRACTS

### Contract 1: `case_id = None` Semantics

**Problem**: Current inconsistency between API and Engine

**Resolution**:

| Layer | `case_id=None` Behavior | Rationale |
|-------|-------------------------|-----------|
| **API** | Require explicit case_id or reject | User MUST provide case context |
| **Engine** | Use provided case_id | Never generate case_id internally |
| **CLI** | Require explicit case_id | Governance operations need case context |

**New Contract**:
```python
# API Layer
if request.case_id is None:
    raise MissingCaseID("case_id is required")

# Engine Layer  
if case_id is None:
    raise ValueError("case_id must be provided by caller")

# NO automatic generation at any layer
```

**Exception**: System-level operations (health checks, monitoring) can use `case_id="SYSTEM"` as a reserved value.

---

### Contract 2: Case Lifecycle States

**States**:
```python
class CaseState(Enum):
    CREATED = "CREATED"      # Initial state
    ACTIVE = "ACTIVE"        # Accepting mutations
    UNDER_REVIEW = "UNDER_REVIEW"  # Read-only for users, writable by reviewers
    CLOSED = "CLOSED"        # Read-only, no mutations
    ARCHIVED = "ARCHIVED"    # Read-only, may be offline
```

**State Transitions**:
```
CREATED → ACTIVE → UNDER_REVIEW → CLOSED → ARCHIVED
```

**Mutation Rules**:
```python
def can_mutate_case(case: Case, user: User) -> bool:
    if case.state == CaseState.CREATED:
        return user.role in [Role.OWNER, Role.ADMIN]
    elif case.state == CaseState.ACTIVE:
        return user.role in [Role.OWNER, Role.CONTRIBUTOR, Role.ADMIN]
    elif case.state == CaseState.UNDER_REVIEW:
        return user.role in [Role.REVIEWER, Role.ADMIN]
    elif case.state in [CaseState.CLOSED, CaseState.ARCHIVED]:
        return False  # No mutations
    
    return False
```

---

## ADVERSARIAL TEST MATRIX

### Category 1: Authorization Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_unauthorized_case_read` | User A tries to read Case B | Raises `UnauthorizedCaseAccess` |
| `test_unauthorized_case_write` | User A tries to write to Case B | Raises `UnauthorizedWrite` |
| `test_missing_case_id` | Request without case_id | Raises `MissingCaseID` |
| `test_invalid_case_id` | Request with non-existent case_id | Raises `CaseNotFound` |
| `test_case_id_injection` | Malicious case_id (SQL injection attempt) | Rejected safely |

### Category 2: Isolation Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_cross_case_read_denied` | Query Case A, verify no Case B data | All results.case_id == "A" |
| `test_cross_case_rag_isolation` | RAG retrieval for Case A | No Case B documents retrieved |
| `test_cross_case_graph_isolation` | Graph query for Case A nodes | No Case B nodes returned |
| `test_cross_case_evidence_isolation` | Reasoning evidence for Case A | No Case B evidence used |
| `test_cross_case_ledger_isolation` | Ledger query for Case A | No Case B entries returned |

### Category 3: Semantic Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_shared_knowledge_accessible` | Case A accesses shared legal articles | Access granted |
| `test_case_private_data_isolated` | Case A cannot access Case B documents | Access denied |
| `test_case_id_immutable` | Attempt to change case_id after creation | Raises `ImmutableFieldError` |
| `test_case_state_transitions` | Valid state transition | Succeeds |
| `test_case_state_invalid_transition` | Invalid state transition (CLOSED → ACTIVE) | Rejected |

### Category 4: Consistency Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_request_case_id_matches_verdict` | request.case_id == verdict.case_id | True |
| `test_verdict_case_id_matches_ledger` | verdict.case_id == ledger_entry.case_id | True |
| `test_case_scope_propagation` | Scope consistent through pipeline | All components see same case_id |
| `test_100_cases_no_leakage` | Create 100 cases, query each, verify isolation | Zero cross-case data |

### Category 5: Write-Side Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_write_scope_consistency` | Write data with mismatched scope | Raises `CaseScopeViolation` |
| `test_write_authorization_required` | Write without authorization | Raises `UnauthorizedWrite` |
| `test_case_id_binding_immutable` | Ledger entry case_id cannot change | Immutable |

---

## IMPLEMENTATION CHECKLIST

**DO NOT IMPLEMENT until this contract is approved.**

### Phase 1: Authorization Infrastructure (P0)

- [ ] Define `AuthorizedCaseScope` type
- [ ] Implement `authorize_case_access(user, case_id)`
- [ ] Add authorization middleware to API
- [ ] Wire authorization checks in all entry points

### Phase 2: Scope Propagation (P0)

- [ ] Add `scope` parameter to all case-scoped operations
- [ ] Remove automatic case_id generation
- [ ] Fix semantic inconsistency (None handling)
- [ ] Ensure scope propagates through entire pipeline

### Phase 3: RAG Isolation (P0)

- [ ] Add `scope` and `case_id` to vector metadata
- [ ] Implement scope-aware retrieval
- [ ] Add scope filtering to queries
- [ ] Test cross-case retrieval prevention

### Phase 4: Graph Isolation (P1)

- [ ] Add `scope` property to relevant graph nodes
- [ ] Add scope constraints to schema
- [ ] Update queries to include scope filters
- [ ] Test cross-case graph query prevention

### Phase 5: Adversarial Testing (P0)

- [ ] Implement all tests from test matrix
- [ ] Verify 100% pass rate
- [ ] Add to CI/CD pipeline
- [ ] Make tests non-skippable

### Phase 6: Documentation (P1)

- [ ] Document case identity semantics
- [ ] Update API documentation
- [ ] Create developer guide for case scoping
- [ ] Update architectural diagrams

---

## APPROVAL CRITERIA

This contract is approved when:

1. **Technical Review**: Architecture team agrees on contracts
2. **Security Review**: Security team validates authorization model
3. **Legal Review** (if applicable): Legal team confirms isolation meets requirements
4. **Test Design**: Adversarial test matrix is comprehensive
5. **Implementation Plan**: Checklist is complete and sequenced

**Approvers**:
- [ ] Technical Architect
- [ ] Security Lead
- [ ] Product Owner
- [ ] (Optional) Legal Counsel

---

## MIGRATION STRATEGY

### Backward Compatibility

**Breaking Changes**:
- `case_id` becomes required (was optional)
- Authorization required for case access (was unrestricted)

**Migration Path**:
1. Add deprecation warnings (2 weeks)
2. Enable enforcement in staging (1 week)
3. Enable enforcement in production (after validation)

### Rollout Plan

1. **Week 1**: Deploy contract + authorization infrastructure (read-only enforcement)
2. **Week 2**: Deploy RAG isolation
3. **Week 3**: Deploy graph isolation
4. **Week 4**: Enable full enforcement + adversarial testing

---

## ENFORCEMENT

**Contract Violations**:
- Raise exceptions (fail-fast)
- Log security events
- Alert on violations
- Never silently degrade

**Monitoring**:
- Track unauthorized access attempts
- Monitor cross-case query attempts
- Audit scope propagation integrity

---

## VERSION HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-27 | Forensic Audit | Initial contract based on Phase 2C findings |

---

**CONTRACT STATUS: DRAFT - PENDING APPROVAL**

**Next Steps**:
1. Review and approve this contract
2. Design adversarial test suite
3. Implement Phase 1 (Authorization Infrastructure)
4. Verify with tests before deploying

**No implementation until approval.**
