# MahouN — Canonical Architecture Map
### Classification: MANDATORY PRE-READ / CONSTITUTIONAL DOCUMENT

---
### IMPORTANT: Never produce any type of document, report, text, or file unless requested by the user.
## ⚠️ THIS FILE MUST BE READ BEFORE ANY OF THE FOLLOWING ACTIONS

- Writing a new class
- Writing a new module or package
- Adding a new import to any file
- "Refactoring" an existing component
- Writing a new audit, test, or remediation report

**The single most expensive recurring failure pattern in this codebase has
been agents writing a second implementation of something that already exists,
not knowing it exists, and leaving the codebase with two parallel paths where
one is weaker or untested. Every section below is a direct record of where
this has already happened. Do not let it happen again.**

Before writing any new class, run this check:

```bash
grep -rn "class <YourClassName>" --include="*.py" .
```

If you get any result outside of `tests/` or `examples/`, **stop**. Open
that file. Extend or fix what is there. Do not create a new one.

---

## RULE 0 — On Reports and Audit Files

This repository contains 141+ markdown audit/report files. **They are NOT
evidence of the current state of the code.** Many directly contradict each
other. Several claim "MISSION ACCOMPLISHED" on issues that were later found
still open.

- Do NOT read a report file and assume the code matches it.
- Do NOT write a new report file as a deliverable. Deliverables are code
  and tests, not markdown.
- Do NOT claim an issue is resolved without a `file:line` citation pointing
  to the actual fix in source code, and a passing test you can name.
- If you are uncertain about the current state of something, grep the code.
  The code is the truth. Nothing else is.

---

## PART 1 — Canonical Implementations (the single source of truth for each concern)

### 1-A. Neo4j Database Connection

**Canonical:** `mahoun/graph/neo4j/connection.py`
**Entry point:** `get_connection()` → returns `Neo4jConnection`
**Write path:** `Neo4jConnection._raw_execute()` — this is the ONLY method
that may execute Cypher against the database. It contains the
`MutationAuthorizationBoundary.inspect()` call that enforces governance.

**FORBIDDEN:**
- Do NOT instantiate `GraphDatabase.driver()` anywhere outside this file.
  Any module that does so bypasses the entire governance enforcement chain.
  If you find such a call, it is a confirmed bypass vulnerability, not a
  "legacy pattern."
- Do NOT write a `Neo4jConnectionManager` or any wrapper that holds its
  own driver instance. Route through `get_connection()`.

**Known exception (documented, not to be replicated):**
- `tests/fixtures/seed_data.py:96` — test-only seed fixture uses a raw driver.
  This is acceptable ONLY for test seed data and ONLY if it never runs in a
  production path. Do not use this as justification for adding another
  raw-driver call anywhere else.

---

### 1-A2. Bootstrap Runtime — Service Registry Initialization (CRITICAL)

**Canonical:** `mahoun/bootstrap/runtime.py`
**Entry point:** `bootstrap_runtime()` → returns `Dict[str, Any]` (SERVICE_REGISTRY)
**Startup location:** `api/main.py` lifespan function (line ~138)

**CRITICAL INVARIANT (P0):**
`bootstrap_runtime()` MUST be called during app startup. Without this call,
SERVICE_REGISTRY remains empty and graph-enhanced retrieval silently fails.

**Registry contents:**
- `"query"` → GraphQueryService
- `"gnn"` → GNNGraphBuilder
- `"graph_retriever"` → GraphEnhancedRetriever (**CRITICAL for RAG**)
- `"graph_vector_sync"` → GraphVectorSync
- `"legal_query_executor"` → LegalQueryExecutor

**Usage pattern:**
```python
from mahoun.bootstrap.runtime import get_service

graph_retriever = get_service("graph_retriever")
```

**FORBIDDEN:**
- Do NOT assume SERVICE_REGISTRY is populated without calling `bootstrap_runtime()`
- Do NOT use `get_service()` to satisfy constructor dependencies — use constructor
  injection instead. `get_service()` is for lifecycle/observability only.

**CI Enforcement:**
`ci/gates/gate_bootstrap_enforcement.sh` verifies bootstrap is called in `api/main.py`.

**Fixed bugs:**
- B1+B8: Bootstrap was NEVER called → SERVICE_REGISTRY empty → graph_retriever=None
- B2+B7: Silent exception catch in adapters allowed degradation

---

### 1-B. Governance Enforcement (Mutation Authorization)

**Canonical package:** `mahoun/core/governance/`

**The three classes you will actually use:**

| What you need | Class | File |
|---|---|---|
| Execute a write inside an authorized context | `GovernedNeo4jSession` | `mutation_boundary.py` |
| Check if current context is authorized | `is_authorized()` | `authorization_state.py` |
| Classify a Cypher string for mutation intent | `classify_cypher(query: str) -> bool` | `mutation_boundary.py` |

**`mahoun/core/governance/authorization_state.py` is the single ContextVar
source.** Both `mutation_boundary.py` and `kernel.py` import from it. It
contains the docstring: "There exists exactly one `_authorized_write_ctx`
object in the entire process." That invariant must remain true.

**`GovernedNeo4jSession` usage pattern — the ONLY acceptable way to mutate:**
```python
from mahoun.core.governance.mutation_boundary import GovernedNeo4jSession
from mahoun.core.governance.governance_context import GovernanceContext

ctx = GovernanceContext(
    actor_id="...",
    correlation_id="...",
    operation_type="...",
    provenance_chain=[...],
)
with GovernedNeo4jSession(connection, ctx) as session:
    session._execute_authorized("CREATE ...", params)
```

**FORBIDDEN:**
- Do NOT create a class named `GovernanceContext` outside
  `mahoun/core/governance/governance_context.py`. There is already one in
  `mahoun/ledger/write_gate.py` (now correctly named `LedgerWriteContext`)
  that caused months of confusion. One naming collision is one too many.
- Do NOT create a class named `MutationAuthorizationBoundary` outside
  `mahoun/core/governance/mutation_boundary.py`.
- Do NOT call `classify_cypher()` from a new location — if you need
  classification logic, import the existing function, do not rewrite it.
- Do NOT use `mahoun/core/governance_kernel/__init__.py`'s Legacy Simple
  Interface (`enforce_governance`, `get_governance_context`, etc.). This
  interface performs no real Cypher inspection. It exists only for
  backward compatibility of one remaining caller (`governance_kernel/server.py`)
  and is scheduled for removal. Any new code that imports from it will be
  rejected in review.

**`mahoun/core/governance_kernel/kernel.py` — status:**
This file contains `KernelMutationBoundary` which is a thin delegating
wrapper around the canonical `classify_cypher()` and `authorization_state`.
It is acceptable to use for `graph_query_service.py`'s internal calls.
It must NOT grow its own classification logic — if you find it doing so,
that is a regression.

---

### 1-C. Ledger Write Integrity (Separate Concern from 1-B)

**Canonical:** `mahoun/ledger/write_gate.py`
**Key class:** `LedgerWriteContext` (NOT GovernanceContext — that rename was intentional)
**Entry class:** `LedgerWriteGate`
**Writer:** `mahoun/ledger/writer.py` → `EvidenceLedgerWriter`

This is **not** a duplicate of 1-B. It enforces a different invariant:
that every `EvidencePackage` written to the ledger has complete provenance
chain, evidence refs, and proof hash **before** persistence. It does not
inspect Cypher. These two concerns (mutation authorization vs. ledger
integrity) must remain separated.

**Do not merge them. Do not create a "unified write context" that tries
to be both.**

---

### 1-D. RAG / Retrieval

**There are multiple retrieval files. Only these are canonical for
production paths:**

| Concern | Canonical class | File |
|---|---|---|
| Hybrid (BM25 + Dense + Rerank) retrieval | `HybridRAGService` | `mahoun/rag/hybrid_rag_service.py` |
| Legal-domain aware retrieval | `LegalAwareRetrievalService` | `mahoun/rag/legal_aware_retrieval.py` |
| External search endpoint wrapper | `LegalSearchService` | `services/search/legal_search_service.py` |
| Vector store lifecycle management | `VectorStoreManager` | `mahoun/pipelines/vector_store/manager.py` |

**`HybridRAGService.retrieve(query, mode, top_k)` is the canonical retrieval
call.** It is accessible from `EvidenceLinkedVerdictEngine` via
`self.container.rag_service` (see 1-E below). Use that path.

**Protocol that all retrieval services must satisfy:**
`RAGServiceProtocol` in `mahoun/core/protocols.py`

**FORBIDDEN:**
- Do NOT write a new retrieval class without first checking if
  `HybridRAGService` or `LegalAwareRetrievalService` can be extended.
  This codebase already had three parallel retrieval implementations at
  one point. That cost weeks of remediation work.
- Do NOT bypass the protocol. If your new retrieval class doesn't satisfy
  `RAGServiceProtocol`, it cannot be injected through the DI container.

**Known non-production path:**
`mahoun/retrieval/hybrid_search_v2.py` — this is used only via
`mahoun/mcp/tools/rag.py` (MCP tool path), not from the main verdict
engine. Do not add new direct references to it from production routers.

---

### 1-E. Dependency Injection / Container

**Canonical:** `mahoun/reasoning/adapters.py`
**Class:** `ReasoningDependencyContainer`

This is the single place where concrete services are wired to protocol
interfaces. It exposes:
- `.rag_service` → `RAGServiceProtocol` (backed by `HybridRAGService`)
- `.query_router` → `QueryRouterProtocol`
- `.contradiction_detector` → `ContradictionDetectorProtocol`

**`EvidenceLinkedVerdictEngine` receives this container at construction time.**
To access a service from inside the verdict engine, use `self.container.<service>`.

**FORBIDDEN:**
- Do NOT instantiate concrete service classes (e.g. `HybridRAGService()`)
  directly inside a router, engine, or agent. Go through the container.
- Do NOT add a new service to the verdict engine without adding it to
  `ReasoningDependencyContainer` first and defining its protocol in
  `mahoun/core/protocols.py`.
- Do NOT use `MockDependencyContainer` in anything other than tests.

---

### 1-F. Verdict Engine

**Canonical:** `mahoun/reasoning/evidence_linked_verdict.py`
**Class:** `EvidenceLinkedVerdictEngine`
**Instantiation:** `api/routers/reasoning.py` → `get_verdict_engine()`

This is the core reasoning component. All legal question answering goes
through here. It currently has the following pipeline (in order):

1. Privacy filter (`filter_facts_for_ledger`)
2. RAG augmentation (`self.container.rag_service.retrieve`) — optional, fails
   gracefully if container is None or retrieval fails
3. Case graph build (`_build_case_graph`)
4. Rule matching (`knowledge_graph.find_applicable_rules`)
5. Precedent matching (`knowledge_graph.find_similar_precedents`)
6. Symbolic reasoning + contradiction detection
7. Ledger write via `LedgerWriteGate`
8. Cryptographic proof generation

**Known gap (not yet fixed):** RAG-retrieved evidence in step 2 is merged
as raw text into `fact_texts`. Its `source`, `score`, and `metadata` are not
propagated into the final proof tree. This means retrieved evidence is not
fully auditable in the ledger. Until this is fixed, retrieved evidence has
weaker provenance guarantees than graph-linked evidence. Do not claim
otherwise in reports.

**FORBIDDEN:**
- Do NOT add a second reasoning engine. `GraphEnhancedReasoning` was removed
  because it was orphaned. It should not be resurrected without explicit
  architectural approval and a confirmed call site in production code.
- Do NOT instantiate `EvidenceLinkedVerdictEngine` anywhere except
  `get_verdict_engine()` in `api/routers/reasoning.py`.

---

### 1-G. Knowledge Graph (Legal Rules and Precedents)

**Canonical:** `mahoun/reasoning/knowledge_graph.py`
**Class:** `LegalKnowledgeGraph`

This holds `LegalRule` and `LegalPrecedent` objects and provides
`find_applicable_rules(facts)` and `find_similar_precedents(facts)`.

Do not confuse with the graph database layer (`mahoun/graph/`). The
knowledge graph is an in-memory reasoning structure. The graph database
(Neo4j) is the persistence layer. They are separate concerns.

---

### 1-H. Self-Improvement System

**Status: INTENTIONALLY DISABLED FOR RELEASE**

The self-improvement capability exists in `mahoun/self_improve/` but has
been deliberately deactivated. This was a conscious architectural decision
by the project owner — not an oversight, not a bug.

**Do NOT:**
- Re-enable it without explicit instruction from the project owner.
- Add new callers to `mahoun.self_improve.ultra_self_improvement_system`
  from production paths.
- Treat its presence in `mahoun/infrastructure/health_checker.py` as
  evidence that it is active — that check only verifies the import succeeds,
  it does not activate the system.

**Known leftover to clean up (low priority, not blocking release):**
`api/__init__.py` has a fallback that tries to import
`mahoun.self_improve.api.main:app`. This is dead code (the file doesn't
exist) but it is also harmless because all production entrypoints use
`api.main:app` directly. Leave it until after release unless it causes
an import error.

---

## PART 2 — What Does NOT Exist (Do Not Invent These)

The following things do not exist and must not be assumed to exist:

- A unified `LegalOntologyGate` at the schema level for Neo4j. OntologyEnforcer
  (`mahoun/core/governance/ontology_enforcer.py`) validates labels at write
  time but there is no schema-level gate. This is a known architectural gap,
  not a hidden feature.
- A production-ready self-improvement loop. See 1-H.
- Any unit test that covers the full `EvidenceLinkedVerdictEngine` pipeline
  including RAG augmentation. Tests for the new RAG-augmented path are
  pending and should be written before release.

---

## PART 3 — The Pattern That Has Cost the Most Time

**Every time this happened, it cost at least one full remediation cycle:**

An agent is asked to implement or fix X. The agent does not grep for existing
implementations of X. The agent writes a new implementation of X. The new
implementation has weaker validation than the existing one (because it was
written without the full context of why the original was designed the way it
was). The new implementation gets wired into a production path. The original
implementation is now partially orphaned. A future audit finds two
implementations and has to reconcile them.

This happened with: GovernanceContext (×2), MutationAuthorizationBoundary
(×2), HybridSearch/RAG retrieval (×3), and GraphEnhancedReasoning (×1,
removed in July 2026).

**The fix is one command before writing any new class:**

```bash
grep -rn "class <WhatYouAreAboutToWrite>" --include="*.py" .
```

If it returns anything, read it before writing a single line.

---

## PART 4 — Governance Compliance Verification

Before any commit that touches `mahoun/core/governance/`, `mahoun/graph/`,
`mahoun/ledger/`, or `api/routers/`, run:

```bash
python scripts/validate_governance_compliance.py
```

This script checks:
1. No `GraphDatabase.driver()` calls outside `mahoun/graph/neo4j/connection.py`
   (except the documented test fixture)
2. No class named `GovernanceContext` outside `mahoun/core/governance/`
3. No class named `MutationAuthorizationBoundary` outside `mahoun/core/governance/`
4. `_authorized_write_ctx` is only instantiated once (in `authorization_state.py`)

If this script does not exist yet or does not run cleanly, fixing it is
higher priority than any feature work. It is the primary defense against
the pattern described in Part 3.

---

*Last verified against codebase: July 2026 build (MahouNjuly.zip)*
*Verified by: independent code audit (line-by-line, no reliance on prior
report files)*
*Next required update: before any major structural change to mahoun/core/,
mahoun/rag/, or mahoun/reasoning/*

