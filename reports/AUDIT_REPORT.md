# MAHOUN Invariant Destruction Audit Report

## Phase 1 — Formal Specification

### I1: Every verdict must have evidence
**Formal Property:**  
∀v: Verdict, ∃e: Evidence such that e supports v ∧ e is retrievable ∧ e existed before v was finalized.

**Preconditions:**  
- System receives a question and facts.
- Graph builder and knowledge graph are operational.

**Postconditions:**  
- Verdict is created with at least one evidence reference.
- Ledger entry contains evidence references.

**Enforcement Points:**  
- `mahoun/reasoning/evidence_linked_verdict.py::generate_verdict` (lines 302-304, 515-530)
- `mahoun/ledger/guards.py::validate_entry` (lines 36-37)

**Failure Conditions:**  
- No facts provided.
- Evidence references list empty after reasoning.
- Ledger write fails (in production).

**Implicit Assumptions:**  
- Facts provided are sufficient to generate evidence via graph construction.
- Graph builder will produce nodes that can be referenced as evidence.

### I2: Every evidence must have provenance
**Formal Property:**  
∀e: Evidence, ∃p: Provenance such that p documents origin of e ∧ p is immutable ∧ p is accessible during audit.

**Preconditions:**  
- Evidence node created in graph.

**Postconditions:**  
- Evidence node contains non-empty provenance (e.g., source_documents, timestamp, source system).

**Enforcement Points:**  
- None found. Provenance not captured during node creation.

**Failure Conditions:**  
- Evidence node created without provenance metadata.

**Implicit Assumptions:**  
- The graph itself is the provenance and is immutable.
- Source documents are tracked at graph ingestion layer (not verified here).

### I3: Every decision must be auditable
**Formal Property:**  
∀d: Decision, ∃a: AuditRecord such that a records d ∧ a is tamper-evident ∧ a is retrievable ∧ a includes inputs, reasoning, and output.

**Preconditions:**  
- Verdict generation process initiated.

**Postconditions:**  
- Ledger entry written with cryptographic hash chain.
- Verdict object includes ledger_hash and verdict_id.

**Enforcement Points:**  
- `mahoun/reasoning/evidence_linked_verdict.py::generate_verdict` (lines 491-543, ledger write before verdict creation)
- `mahoun/ledger/writer.py::EvidenceLedgerWriter.write` (lines 433-473)

**Failure Conditions:**  
- Ledger write fails and exception is not caught (in production, verdict creation blocked).
- System crash after ledger write but before verdict return (ledger entry still exists as audit).

**Implicit Assumptions:**  
- Ledger backend is configured correctly (blockchain, JSONL, SQLite) and not NoOp in production.
- Hash chain or blockchain provides tamper evidence.

### I4: No hidden reasoning path
**Formal Property:**  
∀r: ReasoningStep in verdict generation, r is exposed in verdict steps ∧ each r has explicit evidence references ∧ no inference occurs outside observed steps.

**Preconditions:**  
- Question and facts provided.

**Postconditions:**  
- Verdict steps list contains all reasoning steps with evidence references.

**Enforcement Points:**  
- `mahoun/reasoning/evidence_linked_verdict.py::_build_verdict_steps` (lines 398-406)
- Guard G1_EvidenceStepHasEvidence (line 409)
- Guard G2_EvidenceReferencesResolve (line 415)

**Failure Conditions:**  
- Reasoning step without evidence reference.
- Evidence reference that does not resolve to a graph node.

**Implicit Assumptions:**  
- ChainOfThoughtReasoner and semantic matcher do not introduce hidden inference.
- All reasoning steps are captured in the verdict steps structure.

## Phase 2 — Enforcement Verification

| Invariant | Enforcement | Mandatory? | Bypassable? | Verified by Tests? | Only in Docs? | Status |
|-----------|-------------|------------|-------------|-------------------|---------------|--------|
| I1 | Ledger guard, verdict generation check | Yes (in prod) | Only in dev mode (empty evidence) | Likely | No | Partially Enforced |
| I2 | None | No | Always | No | No | Unenforced |
| I3 | Ledger write before verdict creation | Yes (in prod) | Ledger misconfiguration to NoOp in prod (blocked) | Likely | No | Enforced |
| I4 | Verdict steps with evidence guards | Yes | Possible if guards disabled or reasoning bypassed | Likely | No | Partially Enforced |

## Phase 3 — Attack Surface Analysis

### I1 Attack Paths
1. **Runtime failure in evidence extraction**: If graph builder returns no nodes due to bug, evidence lists empty, but in dev mode verdict still created (no ledger write). Impact: Verdict without evidence. Detection: Medium (check ledger hash).
2. **Environment misconfiguration**: Setting `MAHOUN_DETERMINISTIC_TESTING=true` in prod does not bypass I1, but if combined with empty facts, prod will still block. However, if the fact filtering removes all facts (privacy filter) and empty facts list, prod raises error. So minimal.
3. **Direct LLM invocation**: Not applicable; system does not use LLM for reasoning.

### I2 Attack Paths
1. **Missing provenance**: Evidence nodes created without source_documents. Any evidence used in verdict lacks provenance. Impact: Cannot trace evidence origin. Detection: High (inspect node properties).
2. **Graph ingestion layer not tracked**: Assuming provenance is at ingestion layer, but if ingestion does not populate source_documents, then missing. Detection: High.

### I3 Attack Paths
1. **Ledger backend misconfiguration**: If operator configures NoOpLedgerBackend in prod, the backend raises RuntimeError (lines 295-302). So blocked.
2. **Ledger write failure after partial write**: If system crashes after ledger write but before verdict return, ledger entry exists (auditable) but verdict object not returned to caller. Impact: Audit trail exists without verdict object; still auditable. Detection: Low.
3. **Event loss in async write**: The ledger write is run in a thread pool; if the thread pool fails silently, exception would be raised and caught (line 466-473). So unlikely.

### I4 Attack Paths
1. **Guardrails disabled**: If guardrails module fails to import in prod, system raises ImportError (lines 68-78). So blocked.
2. **Reasoning outside steps**: ChainOfThoughtReasoner may perform internal steps not reflected in verdict steps. Impact: Hidden reasoning. Detection: Medium (requires internal tracing).
3. **Semantic matcher hallucination**: Semantic matcher uses deterministic rules; no hallucination.

## Phase 4 — Counterexample Construction

### I1 Counterexamples (5)
1. **Scenario**: Developer runs system in DEVELOPMENT mode with empty facts list.  
   **Execution Path**: `generate_verdict` → facts empty → skip RuntimeError (line 304) → build case graph → no evidence references → ledger write skipped (lines 525-536) → verdict created with ledger_hash=None.  
   **Invariant Violation**: Verdict created without evidence references.  
   **Observable Symptoms**: Verdict object has ledger_hash=None, no ledger entry.  
   **Impact**: Hallucinated legal conclusion without audit trail.  
   **Detection Difficulty**: Medium (requires checking ledger hash).

2. **Scenario**: Graph builder bug returns no nodes for facts, rules, precedents.  
   **Execution Path**: Similar to above but with non-empty facts; evidence lists empty → dev mode skips ledger write.  
   **Invariant Violation**: Verdict without evidence.  
   **Observable Symptoms**: Same as above.  
   **Impact**: Verdict not grounded in any evidence.  
   **Detection Difficulty**: Medium.

3. **Scenario**: Privileged actor modifies `guard_mode` to bypass validation (if possible).  
   **Execution Path**: Not feasible; guard_mode is just metadata.  
   **Skip**.

4. **Scenario**: Race condition where ledger write succeeds but verdict creation fails due to OOM, and retry mechanism creates new verdict with same evidence but different ID? Not a direct I1 violation.  
   **Skip**.

5. **Scenario**: System clock tampering affecting deterministic testing flag? Not relevant.  
   **Skip**.

### I2 Counterexamples (5)
1. **Scenario**: Evidence node created from fact without source_documents.  
   **Execution Path**: `_build_case_graph` creates GraphNode with properties but source_documents default empty list.  
   **Invariant Violation**: Evidence node has empty provenance.  
   **Observable Symptoms**: Node.properties lacks source_documents or similar.  
   **Impact**: Cannot verify evidence origin.  
   **Detection Difficulty**: High (requires inspecting node).

2. **Scenario**: Rule node created without source_documents.  
   **Execution Path**: `_create_rule_nodes` sets properties but not source_documents.  
   **Same as above**.

3. **Scenario**: Precedent node created without source_documents.  
   **Same**.

4. **Scenario**: Graph ingestion pipeline does not populate source_documents (assumed elsewhere).  
   **Execution Path**: If upstream pipeline fails to set source_documents, nodes lack provenance.  
   **Impact**: Same.  
   **Detection Difficulty**: High.

5. **Scenario**: Operator mistakenly believes source_documents is populated but field is never written.  
   **Same**.

### I3 Counterexamples (5)
1. **Scenario**: Ledger write succeeds but system crashes before returning verdict to user; ledger entry exists but caller never gets verdict object.  
   **Execution Path**: Ledger write async succeeds, then crash.  
   **Invariant Violation**: Decision made (ledger entry written) but not auditable by caller? Actually ledger entry is audit trail; decision is auditable via ledger. So not a violation.  
   **Skip**.

2. **Scenario**: Ledger backend misconfigured to NoOp in prod due to environment variable error (e.g., `get_environment_name()` returns wrong value).  
   **Execution Path**: NoOpLedgerBackend raises RuntimeError in prod (lines 295-302).  
   **Invariant Violation**: System crashes, no verdict, no ledger write.  
   **Impact**: Denial of service, not auditability violation.  
   **Detection Difficulty**: Low (crash logs).

3. **Scenario**: Hash chain collision allowing undetected tampering.  
   **Execution Path**: Extremely unlikely with SHA-256.  
   **Skip**.

4. **Scenario**: Ledger write bypassed via direct database manipulation (if using SQLite backend).  
   **Execution Path**: If attacker has DB access, they could insert ledger entry without going through writer.  
   **Invariant Violation**: Audit trail can be forged.  
   **Impact**: Tampering undetected if hash not verified.  
   **Detection Difficulty**: High (requires hash verification).

5. **Scenario**: System time manipulated affecting ledger timestamp but not hash chain.  
   **Same as above**.

### I4 Counterexamples (5)
1. **Scenario**: ChainOfThoughtReasoner performs internal reasoning step not reflected in verdict steps.  
   **Execution Path**: Internal LLM-like reasoning (if any) but system claims no LLM.  
   **Impact**: Hidden reasoning.  
   **Detection Difficulty**: Medium (requires tracing reasoner).

2. **Scenario**: Semantic matcher uses external knowledge not in graph.  
   **Execution Path**: SemanticMatcher uses synonym dictionary; if dictionary contains unexpected relations, could infer new links.  
   **Impact**: Reasoning based on external data not exposed as evidence.  
   **Detection Difficulty**: Medium.

3. **Scenario**: Guardrails disabled via environment variable in prod (if possible).  
   **Execution Path**: If guardrails import fails in prod, system raises ImportError (lines 68-78).  
   **Impact**: System crashes, no verdict.  
   **Detection Difficulty**: Low.

4. **Scenario**: Reasoning step added after ledger write but before verdict creation that does not affect evidence lists.  
   **Execution Path**: Not in current code.  
   **Skip**.

5. **Scenario**: Deterministic testing flag alters reasoning (only affects timestamp).  
   **No impact on reasoning path**.

## Phase 5 — Audit Trail Verification

| Item | Reconstructable? | Justification |
|------|------------------|---------------|
| Original request | Partially | Question and facts are in ledger entry via case_id hash but not stored verbatim. |
| Prompt template | Not Reconstructable | No prompt template stored; reasoning is graph-based. |
| Runtime used | Partially | invariant_version and guard_mode stored in ledger entry. |
| Model used | Not Reconstructable | No model used; reasoning is symbolic/graph-based. |
| Memory state | Not Reconstructable | Graph state not stored; only node IDs in ledger. |
| Evidence set | Partially | Ledger entry contains referenced_ltm_nodes and referenced_facts (node IDs). | 
| Graph state | Not Reconstructable | Full graph not stored; only references. |
| Reasoning chain | Partially | Verdict steps stored in memory but not persisted; only ledger hash. |
| Governance decisions | Partially | guard_mode stored. |
| Final verdict | Partially | final_verdict string not in ledger; only ID and hash. |

## Phase 6 — Missing Invariants Review

| Missing Invariant | Risk Level | Exploitation Scenario | Recommended Enforcement |
|-------------------|------------|-----------------------|--------------------------|
| Every evidence must be immutable | MEDIUM | Evidence node mutated after verdict but before ledger write? Nodes are in-memory; if mutated, ledger entry would reference changed node. | Make GraphNode immutable after creation; store hash of node in ledger. |
| Every audit event must be append-only | LOW | Ledger backend could be rewritten if file permissions wrong. | Enforce append-only via OS permissions; use blockchain. |
| Every verdict must be reproducible | MEDIUM | Non-deterministic elements (e.g., timestamps) cause different verdicts for same input. | Use deterministic timestamps (e.g., hour bucket) and lock versions. |
| Every model invocation must be logged | LOW | No model used. | N/A |
| Every graph mutation must be traceable | HIGH | Graph updated mid-reasoning causing inconsistency. | Lock graph during verdict generation; log mutations. |
| Every memory update must be attributable | MEDIUM | Internal caches poisoned. | Attribute updates to component. |
| Every policy violation must generate an audit event | MEDIUM | Guardrail violation not logged to ledger. | Emit ledger entry for policy violations. |
| No component may bypass governance | HIGH | Direct LLM invocation bypassing graph. | Enforce via API gateway; disable LLM paths. |
| Every reasoning artifact must be traceable | MEDIUM | Intermediate reasoning steps not stored. | Store reasoning steps in ledger or separate audit log. |
| Every provenance record must be cryptographically verifiable | HIGH | Provenance tampered undetectable. | Sign provenance with key; store signature. |
| Every deployment profile must preserve semantic behavior | MEDIUM | Dev mode allows verdicts without evidence. | Remove dev mode bypasses; same code path in all envs. |
| No runtime substitution may alter compliance guarantees | HIGH | Swapping ledger backend to NoOp via config. | Validate backend type at startup; reject NoOp in prod. |
| Every verdict must have deterministic audit reconstruction | MEDIUM | Ledger hash depends on non-deterministic serialization. | Use canonical serialization (already done). |
| Every evidence reference must remain resolvable | LOW | Node deleted from graph after ledger write. | Make graph nodes immutable or tombstone with retention. |
| Every governance decision must be explainable | LOW | Governance decision not linked to evidence. | Store governance rationale in ledger. |

## Phase 7 — Production Adversarial Assessment

Assumptions: Malicious operators, faulty infrastructure, model drift (not applicable), corrupted memory, incomplete logs.

**Failure Mode**: If operator deploys with NoOpLedgerBackend in production due to misconfiguration (e.g., environment variable spoofed), system will crash at startup (RuntimeError). So no silent failure.

**Blast Radius**: Crash leads to denial of service; no verdicts produced.

**Overall**: System remains compliant in production if configured correctly. However, development mode bypasses create risk if dev config accidentally used in prod.

## Phase 8 — Formal Strength Scoring

| Invariant | Strength Score | Justification |
|-----------|----------------|---------------|
| I1 | 75 | Enforced in production; development mode bypass is a weakness but not exploitable in prod without misconfiguration. |
| I2 | 10 | No enforcement; provenance not captured. |
| I3 | 80 | Strong enforcement; ledger write before verdict creation; tamper-evident. |
| I4 | 60 | Reasoning steps exposed but internal algorithms may hide some reasoning. |

## Phase 9 — Evidence-Based Verdict

Only executable enforcement, runtime guarantees, observable behavior, formal constraints, verified audit trails are valid evidence.

- I1: Enforced via code (guards, verdict generation) – executable.
- I2: No executable evidence; only assumptions.
- I3: Executable evidence (ledger write before verdict creation).
- I4: Partially executable (guards on steps); but internal reasoning not fully observable.

## Required Final Report

| Invariant | Strength Score | Breakable | Enforcement Status | Attack Surface | Production Ready |
|-----------|----------------|-----------|--------------------|----------------|------------------|
| I1 | 75 | Yes (in dev/misconfig) | Partially Enforced | Medium (dev mode, misconfiguration) | Yes (if prod configured) |
| I2 | 10 | Always | Unenforced | High (missing provenance) | No |
| I3 | 80 | No (in prod) | Enforced | Low (ledger tampering requires DB access) | Yes |
| I4 | 60 | Yes (if guards bypassed) | Partially Enforced | Medium (reasoning bypass, guardrails disable) | Yes (with guards) |

## Final Executive Verdict

**ARCHITECTURAL RISK LEVEL**: HIGH  
**Compliance Survivability**: NO (due to I2 missing provenance)  
**Governance Survivability**: YES (if guards enabled)  
**Auditability Survivability**: YES (ledger provides audit trail)  
**Legal-Tech Production Certification**: I DO NOT CERTIFY  

**Detailed Justification**:  
The system fails to enforce invariant I2 (evidence provenance) entirely, rendering evidence untraceable to its source. This creates unacceptable legal risk as evidence cannot be verified for authenticity or chain of custody. While I1, I3, and I4 are largely enforced in production, the presence of development mode bypasses and potential misconfiguration paths introduces unnecessary risk. The absence of provenance tracking is a critical flaw that cannot be overlooked in a legal-tech system.  

---  