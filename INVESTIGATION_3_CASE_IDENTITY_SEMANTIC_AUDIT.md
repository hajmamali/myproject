# INVESTIGATION 3: CASE IDENTITY SEMANTIC AUDIT

**Classification**: EVIDENCE COLLECTION / SEMANTIC ANALYSIS  
**Date**: 2025-01-09  
**Status**: COMPLETED  
**Parent Document**: `PHASE_2B_2C_FINAL_PATCH_SPECIFICATION.md` (Section 3 blocker resolution)

---

## EXECUTIVE SUMMARY

Comprehensive semantic audit of all `case_id` usage across MahouN codebase to determine:
1. Whether `case_id` refers to external legal case references or internal MahouN case identities
2. Semantic conflicts between different identifier types
3. Clear taxonomy of identity types for implementation guidance

### VERDICT: **SEMANTIC AMBIGUITY CONFIRMED**

**Finding**: `case_id` has **THREE DISTINCT SEMANTIC MEANINGS** across the codebase, causing architectural ambiguity:

1. **External Legal Case Reference** (`LegalPrecedent.case_id`) — Public legal case identifier
2. **MahouN Internal Case Identity** (API/Ledger `case_id`) — Private user case UUID/identifier  
3. **Graph Case Node ID** (`EntityLinker.case_id`) — Document/case grouping identifier

**Impact**: This semantic overloading blocks safe implementation of case isolation without refactoring.

---

## METHODOLOGY

### Phase A: Comprehensive Identifier Discovery
- Searched all `case_id` occurrences in production code
- Excluded tests/demos/scripts for semantic purity
- Focused on: API layer, Ledger, Reasoning, Graph modules

### Phase B: Semantic Classification
- Analyzed creation sites of `case_id` values
- Traced data flow: API → Adapter → Engine → Ledger → Graph
- Examined actual usage context and comments

### Phase C: Evidence Collection
- Repository file inspections with line-level citations
- Code pattern analysis
- Semantic conflict detection

---

## FINDINGS: THREE SEMANTIC MEANINGS OF `case_id`

### Semantic Type 1: **External Legal Case Reference**

**Location**: `mahoun/reasoning/knowledge_graph.py:57`

```python
@dataclass
class LegalPrecedent:
    """Legal precedent case"""
    case_id: str  # ← EXTERNAL LEGAL CASE REFERENCE
    facts: List[str]
    decision: str
    court: str
    ...
```

**Evidence from usage**:

```python
# demos/financial_aml.py:82-84
kg.add_precedent(
    case_id="FINRA_2022_AML_CASE",  # ← Legal case identifier
    facts=["Multiple cash deposits under $10k", "Short time window"],
    decision="$5M fine for failing to detect structuring",
    court="FINRA",
)
```

```python
# test_knowledge_graph_updated.py:21-26
prec = kg.add_precedent(
    case_id="case_1",  # ← Generic test case identifier
    facts=["Person was employed", "Violation occurred"],
    decision="Labor law violation confirmed",
    court="Labor Court"
)
```

**Semantic Meaning**:
- **External reference** to a published legal case/precedent
- Examples: "FINRA_2022_AML_CASE", "Supreme_Court_2020_123"
- Scope: **PUBLIC / SHARED** (legal knowledge accessible to all)
- Usage: Retrieved by reasoning engine to support verdicts

**Neo4j Storage** (`mahoun/reasoning/knowledge_graph.py:215`):
```cypher
MERGE (p:LegalPrecedent {case_id: $case_id})
SET p.facts = $facts, p.decision = $decision, ...
```

**Classification**: This is **NOT private case data** — it's shared legal knowledge.

---

### Semantic Type 2: **MahouN Internal Case Identity**

**Location**: `api/routers/reasoning.py:119,417`

```python
class VerdictRequest(BaseModel):
    question: str
    facts: list[FactInput]
    case_id: str | None = Field(None, description="Case identifier (optional)")  # ← INTERNAL CASE

# Usage in verdict endpoint:
user_case_id = request.case_id or str(uuid.uuid4())  # ← Generates UUID if missing
```

**Evidence from data flow**:

```python
# api/routers/reasoning.py:425-426
await replay_service.store_execution_context(
    facts=facts_list,
    correlation_id=ctx.correlation_id,
    case_id=user_case_id,  # ← Flows to ExecutionContext
    ...
)
```

```python
# mahoun/execution/replay_service.py:64
@dataclass
class ExecutionContext:
    question: str
    facts: List[str]
    correlation_id: str
    case_id: str  # ← INTERNAL MAHOUN CASE
    timestamp: str
    user_id: Optional[str] = None
    ...
```

**Ledger Storage** (`mahoun/ledger/models.py:53`):
```python
@dataclass
class LedgerEntry:
    # Core identifiers
    verdict_id: str
    case_id: str  # ← INTERNAL CASE (user's private case)
    ...
```

**Ledger Query** (`mahoun/ledger/blockchain.py:223-238`):
```python
def get_entries_by_case(self, case_id: str) -> List[LedgerEntry]:
    """
    Get all entries for a case
    
    Args:
        case_id: Case identifier  # ← INTERNAL CASE
    """
    results = []
    for block in self.chain[1:]:
        if block.data and block.data.case_id == case_id:
            results.append(block.data)
    return results
```

**Semantic Meaning**:
- **Internal MahouN case identifier** for user's private case
- Examples: UUID "550e8400-e29b-41d4-a716-446655440000" or user-provided string
- Scope: **PRIVATE / CASE-SCOPED** (user's confidential legal case)
- Usage: Groups verdicts/evidence for a user's legal matter

**Classification**: This **IS private case data** requiring isolation.

---

### Semantic Type 3: **Graph Case Node ID**

**Location**: `mahoun/graph/builders/entity_linker.py:32,166`

```python
# Docstring:
"""
Graph Schema Contract:
    NODES:
        (:Case { case_id, title, date, court, … })  # ← Graph case node
        ...
"""

def link(
    self,
    entities: Dict[str, List[Dict[str, Any]]],
    case_id: str,  # ← Unique case/document identifier
    case_metadata: Optional[Dict[str, Any]] = None
) -> Tuple[List[GraphNodeSpec], List[GraphEdgeSpec]]:
    """
    Args:
        entities: NER output dictionary with entity lists
        case_id: Unique case/document identifier  # ← DOCUMENT GROUPING ID
        case_metadata: Optional metadata for the case node
    """
```

**Graph Node Creation** (`mahoun/graph/builders/entity_linker.py:281,298`):
```python
def _create_case_node(
    self,
    case_id: str,  # ← Graph node identifier
    metadata: Optional[Dict[str, Any]] = None
) -> GraphNodeSpec:
    """Create Case node specification"""
    properties = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat()
    }
    ...
    return GraphNodeSpec(
        label="Case",
        node_id=f"case_{case_id}",  # ← Prefixed for graph
        properties=properties,
        source_case_id=case_id
    )
```

**Entity Linking** (`mahoun/graph/builders/entity_linker.py:355,408`):
```python
# Person → Case edge
edges.append(GraphEdgeSpec(
    from_id=node_id,
    to_label="Case",
    to_id=f"case_{case_id}",  # ← Links to case node
    relationship_type="PARTY_IN",
    ...
))

# Organization → Case edge
edges.append(GraphEdgeSpec(
    from_id=node_id,
    to_label="Case",
    to_id=f"case_{case_id}",
    relationship_type="PARTY_IN",
    ...
))
```

**Semantic Meaning**:
- **Document/case grouping identifier** in graph
- Usage: Links entities (Person, Organization, Court) to a Case node
- Purpose: Structural organization of graph entities
- Ambiguous: Could be internal case ID OR document ID

**Classification**: **UNCERTAIN** — depends on whether graph contains:
- Private case entities (CASE-SCOPED)
- Public legal document entities (SHARED)

---

## SEMANTIC CONFLICT ANALYSIS

### Conflict 1: LegalPrecedent.case_id vs Ledger.case_id

| Aspect | LegalPrecedent.case_id | Ledger.case_id |
|--------|------------------------|----------------|
| Semantic | External legal case reference | Internal MahouN case identity |
| Scope | PUBLIC / SHARED | PRIVATE / CASE-SCOPED |
| Example | "FINRA_2022_AML_CASE" | UUID "550e8400-..." |
| Data Type | Published legal precedents | User's private verdicts |
| Security | No isolation needed | **Requires authorization** |

**Impact**: Same field name, completely different meanings.

### Conflict 2: EntityLinker.case_id Ambiguity

**Problem**: `EntityLinker.case_id` parameter meaning is unclear:

- **Interpretation A**: Internal MahouN case (private) → Graph contains private data → **P0 isolation required**
- **Interpretation B**: Document identifier (public legal docs) → Graph contains shared data → **No isolation needed**

**Evidence Gap**: Cannot determine which interpretation is correct without:
1. Inspecting actual Neo4j graph data
2. Tracing entity linker usage in ingestion pipeline
3. Verifying if private case entities are stored

---

## DATA FLOW ANALYSIS

### Flow 1: API → Ledger (Internal Case)

```text
API Request
    ↓
case_id: str | None (user-provided or None)
    ↓
user_case_id = request.case_id or str(uuid.uuid4())  # Generate if missing
    ↓
ExecutionContext(case_id=user_case_id)  # Internal case identity
    ↓
LedgerEntry(case_id=user_case_id)  # Stored in blockchain
    ↓
get_entries_by_case(case_id)  # Query by internal case
```

**Semantic**: Internal MahouN case (PRIVATE)

### Flow 2: Knowledge Graph → Neo4j (External Case)

```text
kg.add_precedent(case_id="FINRA_2022_AML_CASE", ...)
    ↓
LegalPrecedent(case_id="FINRA_2022_AML_CASE")
    ↓
MERGE (p:LegalPrecedent {case_id: $case_id})  # Neo4j write
```

**Semantic**: External legal precedent (PUBLIC)

### Flow 3: Entity Linker → Neo4j (UNCERTAIN)

```text
link_entities_to_graph(entities, case_id="case_001")
    ↓
EntityLinker.link(entities, case_id="case_001")
    ↓
GraphNodeSpec(label="Case", node_id=f"case_{case_id}")
    ↓
(:Case {case_id: "case_001"}) in Neo4j
```

**Semantic**: **UNKNOWN** — could be internal case or document ID

---

## ADDITIONAL IDENTIFIER TYPES DISCOVERED

### 1. `verdict_id`

**Location**: `mahoun/ledger/models.py:53`, `api/routers/reasoning.py:466`

**Semantic**: Unique identifier for a generated verdict

**Scope**: CASE-SCOPED (belongs to a specific case)

**Example**: UUID or `f"verdict_{timestamp}"`

### 2. `correlation_id`

**Location**: Throughout governance context

**Semantic**: Request tracking identifier

**Scope**: REQUEST (ephemeral, not persistent)

**Purpose**: Trace single API request through system

### 3. `doc_id` / `document_id`

**Location**: `api/models/core.py`, ingestion pipeline

**Semantic**: Ingested document identifier

**Scope**: Depends on document (SHARED for public laws, CASE-SCOPED for private docs)

### 4. `execution_id`

**Location**: `mahoun/execution/replay_service.py`

**Semantic**: Execution replay identifier

**Scope**: System-level execution tracking

### 5. Party.case_id

**Location**: `mahoun/graph/neo4j/models.py:260`

```python
@dataclass
class Party:
    """Party (طرف دعوا) node model"""
    id: str = Field(..., description="Unique identifier")
    case_id: str = Field(..., description="Parent case ID")  # ← References parent case
    party_type: PartyType
    name_hash: str = Field(..., description="Hashed name for privacy")
```

**Semantic**: Reference to parent Case node

**Scope**: Same as parent case (PRIVATE if case is private)

---

## IDENTITY TAXONOMY (REFINED)

Based on evidence, here is the corrected taxonomy:

| Identity Type | Semantic Meaning | Example | Scope | Security Requirement |
|---------------|------------------|---------|-------|---------------------|
| **External Legal Case Reference** | Published legal precedent identifier | "FINRA_2022_AML_CASE" | SHARED (public) | No isolation |
| **MahouN Internal Case** | User's private case in MahouN | UUID "550e8400-..." | CASE-SCOPED (private) | **Authorization required** |
| **Graph Case Node ID** | Case node identifier in Neo4j | "case_001" | **UNCERTAIN** | **Depends on data** |
| **Request Correlation ID** | Single API request tracking | "req-2025-01-09-001" | REQUEST (ephemeral) | No persistence |
| **Document Identity** | Ingested document identifier | "verdict_doc_789" | Depends on doc type | Context-dependent |
| **Content Fingerprint** | SHA256 of facts/text | "a3f5..." | DERIVED | Not an identity |
| **Verdict Identity** | Generated verdict record ID | UUID "verdict-abc-123" | CASE-SCOPED | Same as parent case |
| **Execution Identity** | Replay execution identifier | "exec-xyz-456" | SYSTEM | Internal tracking |

---

## SEMANTIC CONFLICTS BLOCKING IMPLEMENTATION

### Critical Blocker 1: LegalPrecedent.case_id Field Name

**Problem**: `LegalPrecedent.case_id` is semantically an **external legal case reference**, NOT an internal MahouN case identity.

**Correct naming**:
```python
@dataclass
class LegalPrecedent:
    legal_case_reference: str  # Or: external_case_id, precedent_id
    # NOT: case_id (conflicts with internal case)
```

**Impact**: Cannot safely add `case_id` scope filtering to graph queries without semantic confusion.

### Critical Blocker 2: EntityLinker.case_id Parameter

**Problem**: `EntityLinker.link(entities, case_id="...")` parameter meaning is undefined.

**Questions**:
1. Does this represent the **MahouN internal case** (private)?
2. Or does it represent a **document grouping ID** (could be public)?
3. Are private case entities being written to Neo4j?

**Required Investigation**: Trace `EntityLinker` usage in ingestion pipeline to determine actual values passed as `case_id`.

### Critical Blocker 3: Neo4j Graph Data Classification

**Problem**: Cannot determine if Neo4j graph contains:
- **Only shared legal knowledge** (LegalPrecedent, LegalRule, Law nodes) → No isolation needed
- **Private case-specific entities** (Party, Case nodes with private data) → **P0 isolation required**

**Required Investigation**: Query actual Neo4j database and inspect:
```cypher
MATCH (c:Case) RETURN c.case_id LIMIT 10
MATCH (p:Party) RETURN p.case_id LIMIT 10
MATCH (lp:LegalPrecedent) RETURN lp.case_id LIMIT 10
```

---

## RECOMMENDED REFACTORING (Pre-Implementation)

### Option A: Rename LegalPrecedent Field (Low-Risk)

```python
@dataclass
class LegalPrecedent:
    precedent_id: str  # RENAMED from case_id
    # OR: legal_case_reference: str
    # OR: external_case_id: str
    facts: List[str]
    decision: str
    court: str
    ...
```

**Impact**:
- ✅ Eliminates semantic conflict
- ✅ Clarifies public vs private distinction
- ⚠️ Requires updating ~20 usage sites
- ⚠️ Requires Neo4j schema migration

**Effort**: Medium (1-2 hours refactoring + testing)

### Option B: Distinguish Case Types (Higher-Risk)

```python
@dataclass  
class InternalCase:
    """MahouN user's private case"""
    internal_case_id: str  # UUID
    ...

@dataclass
class LegalPrecedent:
    """Published legal precedent"""
    legal_case_id: str  # External reference
    ...

@dataclass
class GraphCaseNode:
    """Neo4j Case node"""
    graph_case_id: str
    case_type: Literal["internal_private", "external_public"]
    ...
```

**Impact**:
- ✅ Complete semantic separation
- ✅ Type-safe disambiguation
- ❌ Major refactoring across multiple modules
- ❌ Backward compatibility concerns

**Effort**: High (4-8 hours refactoring + testing + migration)

### Option C: Add Semantic Metadata (Minimal-Risk)

```python
@dataclass
class LegalPrecedent:
    case_id: str  # Keep field name
    case_id_type: Literal["external_legal_reference"] = "external_legal_reference"  # NEW
    ...

@dataclass
class LedgerEntry:
    case_id: str  # Keep field name
    case_id_type: Literal["internal_mahoun_case"] = "internal_mahoun_case"  # NEW
    ...
```

**Impact**:
- ✅ No field renames
- ✅ Backward compatible
- ✅ Runtime semantic verification possible
- ⚠️ Doesn't solve naming confusion

**Effort**: Low (30 minutes)

---

## BLOCKING QUESTIONS FOR NEXT INVESTIGATION

Cannot proceed with case isolation implementation until these are resolved:

### Question 1: Graph Data Classification

**Investigation Required**: `INVESTIGATION_1_GRAPH_SCOPE_CLASSIFICATION`

**Action**:
```bash
# Connect to Neo4j
# Query Case nodes
MATCH (c:Case) RETURN c.case_id, c LIMIT 50

# Query Party nodes  
MATCH (p:Party) RETURN p.case_id, p LIMIT 50

# Query LegalPrecedent nodes
MATCH (lp:LegalPrecedent) RETURN lp.case_id LIMIT 50
```

**Determine**:
- Are `Case.case_id` values UUIDs (internal) or document IDs (external)?
- Do `Party` nodes contain private user data?
- Is the graph purely shared legal knowledge or mixed?

**Classification Target**: [SHARED_ONLY | CASE_SCOPED | MIXED | UNCERTAIN]

### Question 2: EntityLinker Usage in Production

**Investigation Required**: Trace `EntityLinker.link()` calls in ingestion

**Action**:
```bash
grep -rn "link_entities_to_graph\|EntityLinker" mahoun/pipelines/ingestion/
# Inspect actual case_id values passed
```

**Determine**:
- What values are passed as `case_id` parameter?
- Are these internal case UUIDs or document IDs?
- Does ingestion create private Case nodes?

### Question 3: Existing Data Scope

**Investigation Required**: `INVESTIGATION_2_EXISTING_DATA_CLASSIFICATION`

**Action**:
- Query vector store for existing documents
- Check metadata for case_id fields
- Classify as SHARED / CASE-SCOPED / UNCLASSIFIED

**Determine**:
- How much existing data lacks scope metadata?
- What heuristics can classify existing data safely?
- What data must be quarantined as UNCLASSIFIED?

---

## FINAL VERDICT

### Status: **SEMANTIC AMBIGUITY CONFIRMED**

**Three distinct semantic meanings of `case_id` exist**:
1. External legal case reference (LegalPrecedent) — PUBLIC
2. Internal MahouN case identity (Ledger/API) — PRIVATE
3. Graph case node ID (EntityLinker) — UNCERTAIN

### Blockers Preventing Implementation:

❌ **Blocker 1**: `LegalPrecedent.case_id` semantic conflict with internal case  
❌ **Blocker 2**: Graph data classification unknown (SHARED vs CASE-SCOPED)  
❌ **Blocker 3**: `EntityLinker.case_id` parameter meaning undefined  

### Required Actions Before Implementation:

**Action 1**: Execute `INVESTIGATION_1_GRAPH_SCOPE_CLASSIFICATION`
- Query Neo4j database
- Inspect actual case_id values
- Classify graph as SHARED_ONLY, CASE_SCOPED, or MIXED

**Action 2**: Refactor semantic conflicts (choose option A, B, or C)
- Recommendation: **Option A (Rename LegalPrecedent field)** — clearest solution
- Alternative: **Option C (Add metadata)** — if backward compatibility critical

**Action 3**: Execute `INVESTIGATION_2_EXISTING_DATA_CLASSIFICATION`
- After graph classification complete
- After semantic refactoring decided

### Estimated Remediation Effort:

- **Option A (Rename)**: 2-4 hours (refactoring + testing + Neo4j migration)
- **Option C (Metadata)**: 30 minutes (add fields + update tests)
- **Graph Investigation**: 30-60 minutes (query + analysis)
- **Total**: 3-5 hours before implementation can begin

### Recommendation:

**DO NOT proceed with case isolation implementation** until:
1. Semantic conflicts resolved via refactoring
2. Graph data classification determined
3. Clear identity taxonomy established and documented

**The current semantic ambiguity makes it impossible to write correct authorization logic** — any implementation would conflate public legal precedents with private user cases.

---

**End of Investigation 3: Case Identity Semantic Audit**

**Next Investigation**: `INVESTIGATION_1_GRAPH_SCOPE_CLASSIFICATION`  
**Authority**: Constitutional Architect + Governance Enforcer  
**Date**: 2025-01-09
