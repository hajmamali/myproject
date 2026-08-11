# MahouN — Canonical Component Map
### Classification: MANDATORY PRE-READ / SUBORDINATE TO CONSTITUTIONAL AUTHORITY

---

## ⚠️ THIS FILE IS NOT THE HIGHEST AUTHORITY IN THIS REPOSITORY

**Before reading anything else in this file, you MUST first read:**

```
mahoun/constitutional/README.md
mahoun/constitutional/constitution/CONSTITUTION.md
```

`mahoun/constitutional/` is the **highest-level governance authority** in this
repository. It defines the constitutional principles, the AI agent authority
hierarchy, the fail-closed rule, and the conflict-resolution order that
govern every action in this codebase — architectural, security, API, and
workflow. This file (`AGENTS.md`) does **not** override, duplicate, or
compete with that authority. Per `CONSTITUTION.md` Section 7 ("Source of
Truth Principle"): *"Every important system concept MUST have one
authoritative source. Duplicated definitions are forbidden when they can
create divergence."*

**The division of labor between the two is deliberate and must stay
distinct:**

| | `mahoun/constitutional/` | `AGENTS.md` (this file) |
|---|---|---|
| Scope | Principles, authority hierarchy, agent roles, workflows | Concrete, current, file:line component map |
| Content | WHY and WHO decides | WHERE things actually live right now |
| Authority | Highest — binding, normative | Subordinate — practical reference only |
| Changes | Require Constitutional Architect + Governance Enforcer approval per `workflows/governance.md` | Should be updated whenever a canonical component's location changes |

If anything in this file appears to conflict with `mahoun/constitutional/`,
**the constitutional documents always win** (`CONSTITUTION.md` Section 4).
Report the conflict; do not silently pick one.

For anything not covered concretely below — architectural philosophy,
security principles, API evolution rules, agent behavioral constraints,
workflow definitions — **go to `mahoun/constitutional/` for the details.**
This file intentionally does not repeat that content.

---

## ⚠️ WHY THIS FILE EXISTS ANYWAY

`mahoun/constitutional/constitution/ARCHITECTURE.md` defines architectural
*principles* (dependency rules, anti-patterns, duplicate-responsibility
prevention). It does **not** — by design — tell you which specific file
currently implements the canonical `GovernanceContext`, or which OCR class
is actually wired into production versus which one is a well-built orphan.
That concrete, evidence-based, frequently-stale-if-unmaintained information
is this file's job. Read the constitution for the rules. Read this file for
the current facts on the ground.

Before writing any new class, run this check:
```bash
grep -rn "class <YourClassName>" --include="*.py" .
```
If you get a result outside `tests/`/`examples/`, stop, open it, extend it.
Do not create a second implementation. This has already happened repeatedly
in this codebase (see Part 3) and cost real remediation time every time.

---

## RULE 0 — On Reports, Audits, and This File Itself

This repository has, at various points, accumulated 60+ markdown
audit/report files in its root. **Report files are not evidence of current
state.** Several have directly contradicted each other or claimed
completion on issues later found still open. This file itself was once
deleted from the repository entirely during a cleanup pass and had to be
reconstructed — treat even this document as something to re-verify against
actual code when the stakes are high, not as infallible.

- Do NOT write a new root-level audit/completion report as a deliverable.
  Deliverables are code, tests, and (when directly relevant) updates to
  this file or, for principle-level changes, a proper constitutional
  governance-change proposal per `mahoun/constitutional/workflows/governance.md`.
- Do NOT claim an issue is resolved without a `file:line` citation to the
  actual fix.
- The code is the truth. This file is a map of the code, kept as accurate
  as the last person who updated it bothered to make it. Verify before
  trusting.

---

## PART 1 — Canonical Implementations

### 1-A. Neo4j Database Connection

**Canonical:** `mahoun/graph/neo4j/connection.py`, entry point `get_connection()`.
**Write path:** `Neo4jConnection._raw_execute()` is the ONLY method permitted
to execute Cypher. It invokes `MutationAuthorizationBoundary.inspect()`
(see 1-B) before any write proceeds.

**FORBIDDEN:** instantiating `GraphDatabase.driver()` anywhere outside this
file. This has been a confirmed, repeatedly-reintroduced bypass vector —
grep for it before every governance-adjacent change:
```bash
grep -rn "GraphDatabase.driver(" --include="*.py" . | grep -v test | grep -v connection.py
```
This must return zero results. If it does not, treat it as a P0 finding
per `mahoun/constitutional/constitution/SECURITY.md`, not a style issue.

---

### 1-B. Governance Enforcement (Mutation Authorization)

**Canonical package:** `mahoun/core/governance/`

| Need | Symbol | File |
|---|---|---|
| Execute a governed write | `GovernedNeo4jSession` | `mutation_boundary.py` |
| Check/set authorization state | `is_authorized()` / the `_authorized_write_ctx` `ContextVar` | `authorization_state.py` |
| Classify Cypher for mutation intent | `classify_cypher(query: str) -> bool` | `mutation_boundary.py` (`CypherLexer`) |

**This project has, at four separate points, accumulated independent,
non-communicating copies of this boundary** (a duplicate `ContextVar`, a
duplicate classifier, or both) in `mahoun/core/governance_kernel/kernel.py`
and `mahoun/core/governance_kernel/__init__.py`. Each time, one copy was
weaker than the canonical one and was, at least once, the one actually
reachable from a real production request path
(`mahoun/graph/graph_query_service.py`). This has been fixed more than once
and has regressed more than once. Before touching anything in this area:

```bash
grep -rn "ContextVar" --include="*.py" mahoun/core/
grep -rn "class.*MutationBoundary\|def classify_.*query\|def classify_cypher" --include="*.py" .
```
There must be exactly **one** `_authorized_write_ctx` object and exactly
**one** Cypher classification function in the entire process. If
`mahoun/core/governance/authorization_state.py`'s
`_assert_no_duplicate_contextvar()` guard exists, confirm it is actually
invoked by a test that runs in default CI — a guard function that is never
called is not a guard.

**FORBIDDEN:** a class named `GovernanceContext` or
`MutationAuthorizationBoundary` anywhere outside
`mahoun/core/governance/governance_context.py` and
`mahoun/core/governance/mutation_boundary.py` respectively.
`mahoun/ledger/write_gate.py`'s ledger-integrity context is a legitimately
separate concern and is named `LedgerWriteContext` specifically to avoid
this collision — do not rename it back.

---

### 1-C. Ledger Write Integrity (Separate from 1-B)

**Canonical:** `mahoun/ledger/write_gate.py` (`LedgerWriteContext`,
`LedgerWriteGate`), writer: `mahoun/ledger/writer.py`
(`EvidenceLedgerWriter`).

Enforces completeness of `EvidencePackage` (provenance chain, evidence
refs, proof hash) before persistence. Does not inspect Cypher. Do not merge
this with 1-B — they enforce different invariants and have been kept
separate deliberately.

---

### 1-D. RAG / Retrieval

| Concern | Canonical class | File |
|---|---|---|
| Hybrid (BM25 + Dense + Rerank) retrieval | `HybridRAGService` | `mahoun/rag/hybrid_rag_service.py` |
| Legal-domain-aware retrieval | `LegalAwareRetrievalService` | `mahoun/rag/legal_aware_retrieval.py` |
| Search API wrapper | `LegalSearchService` | `services/search/legal_search_service.py` |
| Retrieval provenance carrier | `RAGEvidenceNode` | `mahoun/reasoning/rag_evidence.py` |

Protocol: `RAGServiceProtocol` in `mahoun/core/protocols.py`. Access from
the verdict engine via `self.container.rag_service` — never instantiate a
retrieval service directly inside a router or engine.

**Known non-canonical / non-production paths (documented so they are not
"rediscovered" as mysteries by a future agent):**
- `mahoun/retrieval/hybrid_search_v2.py` — used only via the MCP tool
  (`mahoun/mcp/tools/rag.py`), not the main verdict path.
- `mahoun/pipelines/ingestion/ocr_ensemble.py`'s `OCREnsemble` — a fully
  built multi-engine-voting OCR system (majority/weighted/best-confidence/
  unanimous strategies). Confirmed **zero production importers**. This is a
  deliberate, documented future option, not an oversight — do not wire it
  in without an explicit decision, since running N OCR engines per page has
  real cost implications on constrained (BASE-tier) hardware.
- `mahoun/execution/controller.py`'s `ExecutionController` — provides
  deterministic seed management, request replay, and checksum computation.
  Confirmed **zero production importers** in the verdict generation path
  (`api/routers/reasoning.py`). The existing GovernanceContextManager +
  Fortress + LedgerCommitService stack already provides auditability and
  ledger safety. ExecutionController remains available as a utility for
  other entry points (batch processing, admin APIs) but is not wired into
  the main verdict path — this is a deliberate architectural decision per
  Phase A investigation (2026-08-09).

---

### 1-E. Dependency Injection Container

**Canonical:** `mahoun/reasoning/adapters.py`, `ReasoningDependencyContainer`.
Exposes `.rag_service`, `.query_router`, `.contradiction_detector`. The
verdict engine receives this container at construction — never instantiate
a concrete service class directly inside a router, engine, or agent.

**Regression history:** the verdict engine's constructor call
(`api/routers/reasoning.py`) has been found reverted to `container=None`
more than once, silently disabling RAG augmentation. A regression test
(`test_verdict_engine_container_not_none`) exists specifically to catch
this — confirm it is present, is not marked skip/slow, and runs in default
CI before assuming this wiring is stable.

---

### 1-F. Verdict Engine

**Canonical:** `mahoun/reasoning/evidence_linked_verdict.py`,
`EvidenceLinkedVerdictEngine`, instantiated only in
`api/routers/reasoning.py`'s `get_verdict_engine()`.

Pipeline order: privacy filter → RAG augmentation (optional, must degrade
gracefully, never silently) → case graph build → rule/precedent matching →
symbolic reasoning + contradiction detection → **text-grounding
verification** → ledger write → cryptographic proof.

**Text-grounding verification is a hard requirement, not an optional
polish step.** The final human-readable verdict text is generated by a
small local model acting purely as a JSON-to-text renderer. It MUST NOT
introduce any fact, name, date, or figure not present in the structured
evidence. This is enforced by `mahoun/guardrails/ultra_nli_verifier.py`'s
ensemble NLI verifier via `.verify(context=facts, answer=generated_text)`.
If entailment fails or contradiction is detected, **the verdict request
must hard-fail** — per `mahoun/constitutional/constitution/CONSTITUTION.md`
Section 10 (Fail-Closed Principle): missing/failed verification evidence
is a blocking condition, not something to log-and-continue past.

**WIRING STATUS (verified 2025-01-XX):** Text-grounding verification IS
ACTIVE in production mode. Implementation in
`mahoun/reasoning/reasoning_chain.py` lines 515-650 performs:
1. Context extraction from reasoning steps/evidence/nodes
2. NLI ensemble verification (entailment/neutral/contradiction classification)
3. Fail-closed rejection on contradiction or verification failure
4. Thread-safe statistics tracking via `AtomicCounter`/`AtomicFloat`
5. Default mode: `ReasoningMode.STRICT` (enforces all checks)

Comprehensive test coverage: `tests/reasoning/test_nli_text_grounding_enforced.py`
+ extreme stress tests in `tests/stress/test_reasoning_chain_thread_safety_extreme.py`.

**FORBIDDEN:** instantiating `EvidenceLinkedVerdictEngine` anywhere except
`get_verdict_engine()`. Resurrecting a second reasoning engine
(`GraphEnhancedReasoning`, previously removed as orphaned) without an
explicit architectural decision and a confirmed production call site.

---

### 1-G. Document Ingestion & OCR

**Canonical entrypoint:** `api/routers/ingest.py`'s
`get_ingestion_pipeline()` → `mahoun.pipelines.ingestion.pipeline.IngestionPipeline`
(thin wrapper) → `IngestionPipelineV2` in
`mahoun/pipelines/ingestion/base_pipeline.py` (the real logic; ~4 worker
`ThreadPoolExecutor` by default).

**Text extraction dispatch:** `mahoun/pipelines/ingestion/document_handlers.py`'s
`extract_document_text()` — native extraction first, OCR fallback for
scanned PDFs.

**OCR — verify current wiring before assuming which path is active.** This
codebase built a substantially more capable OCR component,
`mahoun/pipelines/ingestion/hardened_paddle_ocr.py`'s `HardenedPaddleOCR`
(checkpoint/resume via `ocr_pdf_hardened()`, document-level Merkle-tree
integrity proof via `get_document_merkle_root()`, Persian-legal-specific
confidence weighting) that has, at least once, had **zero production
importers**, while `document_handlers.py`'s OCR fallback called a bare
`paddleocr.PaddleOCR(use_angle_cls=True, lang='fa')` directly — meaning
large scanned documents were processed with no checkpoint/resume and no
integrity proof, despite the hardened tool already existing. Check which
one is actually invoked before making claims about OCR reliability or
checkpoint/resume capability to anyone, especially in a security/compliance
context.

**Legal entity extraction:** `mahoun/pipelines/ingestion/legal_ner.py`'s
`LegalNEREngine`, reached via `HardenedLegalPipeline`
(`hardened_legal_pipeline.py`), which `IngestionPipelineV2` instantiates.
Confirmed reachable — unlike the OCR situation above, this one has been
verified wired correctly.

**Atomic graph write (governance-native):** `mahoun/core/governance/ingestion_runtime.py`'s
`GovernedIngestionRuntime.ingest_document_atomic(doc_id, text, metadata, author_id)`.
This is the canonical replacement for the legacy `UnifiedLoader` and
performs a single capability-scoped governed graph write via
`GovernedNeo4jSession.begin_transaction().commit()`. **Provenance is
established through `GovernanceContextManager.require_provenance(source, author)`**
— the only canonical provenance factory; do NOT reintroduce a
`ProvenanceMetadata.create_evidence(...)` call (no such method exists).
Requires (a) an active `GovernanceContextManager.active_context(...)`
scope, (b) a wired audit sink via
`set_audit_sink(compose_default_filesystem_sink())`, and (c) a
`GovernedNeo4jSession` produced by `connection.governed_session(...)`.

**Legacy `UnifiedLoader` is a phantom — `mahoun.orchestrator.unified_loader`
has never existed in any git commit in this repo.** The earlier audit's
"legacy manual path" verdict was incomplete: the script was broken by
construction, not merely abandoned. The current
`scripts/unified_ingest.py` is now wired to `GovernedIngestionRuntime`
via the canonical path above; its docstring carries the audit history.

**Outstanding related debt (NOT addressed by the script fix):** the
production router `api/routers/ingest.py:37,399,468` still references a
`get_unified_loader()` symbol and a `_unified_loader` global that have
no definition in the codebase (the mypy baseline at
`ci/mypy/baseline.txt:1196-1197` records this as `name-defined`). Any
request that hits `/dlq/{job_id}/retry` or the DLQ delete endpoint will
raise `NameError` at request time. This is a separate, larger blast-
radius fix; do not assume the ingestion entry-points are healthy based
on the CLI fix alone.

---

### 1-H. Knowledge Graph (In-Memory Reasoning Structure)

**Canonical:** `mahoun/reasoning/knowledge_graph.py`, `LegalKnowledgeGraph`.
Holds `LegalRule`/`LegalPrecedent`, provides `find_applicable_rules()` /
`find_similar_precedents()`. Distinct from the Neo4j persistence layer
(`mahoun/graph/`) — do not conflate the two.

---

### 1-I. Self-Improvement System

**Status: INTENTIONALLY DISABLED FOR RELEASE.** `mahoun/self_improve/`
exists but is a deliberate architectural decision by the project owner, not
an oversight. Do not re-enable, do not add new production callers, without
explicit instruction. Per `CONSTITUTION.md` Section 8: agents "MUST NOT
invent architecture" — reactivating a deliberately-disabled subsystem
without authorization falls squarely under that prohibition.

### 1-J. Frontend Canonical Patterns

**Canonical clean component:** `frontend/src/components/LegalSearchPage.tsx`
is the reference implementation: imports from `../api/client`, calls a real
`await searchVerdicts(...)` (or equivalent client method), and handles
loading/error states. Every new frontend component rendering data presented
as model/API output must follow this pattern.

**Fabrication violation:** A frontend component that imports from `../api/`
but replaces the real call with a hardcoded string, `setTimeout` simulation,
or static data structure is a fabrication violation. It will be caught by
`ci/first_step/gate_4b_frontend_antimock.sh` (Phase B of Round 10).

**Suppression marker convention:**
```tsx
// fabrication-check-ok: <mandatory one-line reason>
```
Any file/line with this marker is excluded from fabrication detection. The
reason is **required** — a bare suppression without reason fails the gate.
Reasons like "placeholder for now" are **NOT** acceptable. All active
suppressions are logged in gate output so they are visible to reviewers, not
hidden.

**API contract matching:** `scripts/check_api_contracts.py` (Phase E, Round 10)
statically verifies that every `fetch('/api/...')` or `await *Client.*()` call
in `frontend/src/` has a matching backend route in `api/routers/`. Path
parameters are normalized (`/users/${id}`, `/users/:id`, `/users/{id}` all
match `/users/{param}`); query strings are stripped before matching.
Unresolved dynamic endpoints (e.g. `fetch(baseUrl + dynamicPath)`) are
reported as warnings, not violations.

---

## PART 2 — Things That Do Not Exist (Do Not Assume Them)

- A schema-level ontology gate for Neo4j (only write-time label validation
  exists via `OntologyEnforcer`).
- A production-ready self-improvement loop (see 1-I).
- A completed, always-correct text-grounding guarantee — verify 1-F's
  wiring status before repeating "zero-hallucination" as an established
  fact rather than a target under active enforcement.
- Full test coverage of the RAG-augmented verdict pipeline end-to-end.

---

## PART 3 — The Pattern That Has Cost the Most Time

A recurring, specific failure mode in this codebase: an agent is asked to
fix or extend X, does not check for an existing implementation of X, and
builds a second one — usually weaker, because it lacks the context that
shaped the original. The second implementation gets partially wired in,
the first becomes partially orphaned, and a future audit has to reconcile
both.

Confirmed instances: `GovernanceContext` (×2+), `MutationAuthorizationBoundary`
(×2+), RAG/retrieval implementations (×3), `GraphEnhancedReasoning` (built,
later removed), Cypher-mutation classifiers (×4 at one point). The inverse
pattern has also occurred: a strong component built correctly and then
never wired into production at all (`HardenedPaddleOCR`, the NLI
text-grounding verifier, `OCREnsemble`).

**Before writing any new class or component:**
```bash
grep -rn "class <WhatYouAreAboutToWrite>" --include="*.py" .
```
**Before assuming an existing component is active in production:**
```bash
grep -rln "<ClassName>" --include="*.py" . | grep -v test
```
Then trace at least one real caller up to a confirmed API entrypoint. A
component existing in the tree is not evidence it runs.

---

## PART 4 — Automated Compliance Verification

The enforcement chain has three layers (Amendment E):

**EARLY FEEDBACK (pre-commit — local, bypassable):**
- `gate_1_lint.sh` — ruff check+format on modified Python files
- `gate_2_types.sh` — mypy/pyright non-regression
- `gate_4b_frontend_antimock.sh` — fabrication marker scan (fast grep)
- `ci/gate_md_count.sh` — root `.md` count ≤ 3

**LOCAL PUSH ENFORCEMENT (pre-push — local, bypassable with --no-verify):**
- `gate_0_integrity.sh` — pass/TODO/NotImplementedError stubs in core paths
- `gate_3_reality.sh` — 137 pytest reality tests
- `gate_4_antimock.sh` + `gate_4b_frontend_antimock.sh` — Python AST anti-mock + frontend fabrication
- `gate_5_determinism.sh` — test determinism proof
- `gate_6_artifacts.sh` — artifact generation
- `gate_7_architecture.sh` — Python import boundary enforcement
- `gate_8_contracts.sh` — contract file + test existence
- `gate_9_governance.sh` — governance test suite
- `gate_9_mypy_non_regression.sh` — mypy non-regression
- `scripts/validate_governance_compliance.py` — backend structural check
- `scripts/check_api_contracts.py` — frontend/backend API contract matching
- `gate_10_constitutional_integrity.sh` — constitutional change detection (sealed manifest)
- `scripts/check_enforcement_integrity.py` — enforcement surface self-protection
- `ci/gate_md_count.sh` — redundant final guard

**AUTHORITATIVE ENFORCEMENT (CI platform — non-bypassable for merge):**
- `.github/workflows/kernel-governance.yml` runs on push/PR to main/develop/release
  touching governance, constitutional, CI, or enforcement files.
- This workflow is the merge-blocking layer when branch protection requires it.

**Note on authority:** Local hooks (pre-commit/pre-push) are bypassable and
do NOT provide authoritative enforcement. The CI platform workflow is the
only non-bypassable enforcement layer. If CI is not configured as a required
status check in branch protection, the project has no authoritative merge
enforcement.

Before any commit touching `mahoun/core/governance/`, `mahoun/graph/`,
`mahoun/ledger/`, or `api/routers/`, run:
```bash
python scripts/validate_governance_compliance.py
```
This checks for raw `GraphDatabase.driver()` usage outside the canonical
connection module and duplicate governance class definitions. If this
script's violation count increases from its last-known value without an
explicit, reviewed justification recorded in this file, treat that as a
regression requiring the same scrutiny as a failed test.

Root-directory markdown clutter is checked by `ci/gate_md_count.sh`
(threshold: 3 files). **Confirm this is actually wired into the real CI
pipeline (Makefile / `ci/` orchestration) and not merely present in the
tree** — it has, at least once, existed correctly written but
disconnected from anything that actually runs it, which is exactly the
"built but not wired" pattern described in Part 3, applied to governance
tooling itself.

---

## PART 5 — Constitutional Cross-Reference

For anything beyond the concrete component map above:

- **Architectural principles, anti-patterns, dependency rules:**
  `mahoun/constitutional/constitution/ARCHITECTURE.md`
- **Governance change process, authority hierarchy:**
  `mahoun/constitutional/constitution/GOVERNANCE.md`
- **Security principles:** `mahoun/constitutional/constitution/SECURITY.md`
- **API evolution and drift rules:**
  `mahoun/constitutional/constitution/API_STANDARD.md`
- **Workflow definitions (release, governance change, API evolution):**
  `mahoun/constitutional/workflows/`
- **Agent role definitions and the full agent registry:**
  `mahoun/constitutional/agents/REGISTRY.md`

If a question is about **why** a rule exists, **who** must approve a
change, or **how** a workflow is supposed to run — the answer is in
`mahoun/constitutional/`, not here. If the question is **where a specific
canonical implementation currently lives** — that is this file's job, and
if this file is wrong or stale, fix this file with the same rigor as fixing
a bug, citing file:line evidence for the correction.

---

*This file documents concrete, current, evidence-based component locations.
It is subordinate to `mahoun/constitutional/` for all matters of principle,
authority, and process. Keep it accurate; it is only useful if it reflects
reality.*
## Development Environment

**Repository Root**

Always perform all development, code modifications, testing, and Git operations from the project repository root. Do not work from subdirectories unless explicitly required.

**Python Virtual Environment**

Before running any Python command, activate the project's virtual environment:

```bash
source venv/bin/activate
```

All development tools, scripts, tests, and package installations must be executed with this virtual environment activated unless explicitly instructed otherwise.