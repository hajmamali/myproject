# Explanation and Provenance Layer Specification

## Purpose

This section defines the Explanation & Provenance Layer for Mahoun as a **non-authoritative infrastructure component** whose sole responsibility is to record, reconstruct, and present the reasoning artifacts produced by the deterministic core. It must never introduce new decision logic, change outcomes, or infer missing reasoning steps.

This layer exists to satisfy three system-level guarantees:

1. **Auditability**: Every verdict can be traced to explicit rules, facts, and graph relations.
2. **Reproducibility**: Identical inputs yield identical outputs, including identical proof traces.
3. **Contestability**: A reviewer can challenge specific steps using explicit references rather than latent similarity.

## Design Rule Compliance

The layer is governed by **DR-EXPL-001: No Feature — Only Proof** and is considered compliant only if it satisfies:

- **Decision Invariance**: disabling the layer does not change verdict, graph, or applied rules.
- **Authority Isolation**: the layer has no veto/override/weighting capability.
- **Determinism Preservation**: outputs are deterministic and do not require randomness or LLM generation.

If any of these invariants is violated, the layer is not infrastructure; it is a feature and must be rejected.

**Test Coverage**: See `tests/test_design_rule_no_feature_only_proof.py` for mandatory invariant tests.

## Scope and Non-Scope

### In Scope

- Capturing and serializing core-produced artifacts:
  - applied rules
  - conflict-resolution outcomes
  - temporal precedence decisions
  - evidence links
  - graph paths used in the decision
- Producing human-facing reports that are strictly derived from recorded artifacts
- Providing an API contract for downstream consumers (UI, export, logging, governance)

### Out of Scope

- Generating explanations "from scratch" (post-hoc narrative generation)
- Using embeddings / similarity to justify a result
- Re-ranking competing conclusions
- Filling gaps in traces with heuristics
- Any component that can influence the core reasoning path

## Architectural Placement

```
Input → Explicit Graph Builder → Rule-Based Reasoning Core → Verdict + Proof Trace
                                                          ↓
                                         Explanation & Provenance Layer (Non-authoritative)
                                                          ↓
                                          Reports / UI / Audit / Export
```

**Authority boundary**: only the Rule-Based Reasoning Core has decision authority.

## Core Concepts

### Decision Artifact vs Explanation Artifact

**Decision Artifacts (authoritative)**:
- Produced by the reasoning core and treated as ground truth.
- Examples: `verdict`, `applied_rules`, `conflict_resolution_steps`, `selected_precedents`.

**Explanation Artifacts (non-authoritative)**:
- Derived presentations of decision artifacts.
- Examples: `human_readable_report`, `visual_trace`, `audit_bundle`.

Explanation artifacts may be regenerated at any time, but must always match the decision artifacts.

## Minimum Data Contract

The reasoning core must emit a **Proof Trace** sufficient for audit without re-executing inference.

A recommended minimal contract:

```python
{
    "verdict": final_decision_object,  # structured
    "trace_id": stable_identifier,
    "inputs_digest": deterministic_hash_of_normalized_inputs,
    "graph_digest": deterministic_hash_of_graph_snapshot,
    "applied_steps": [
        {
            "type": "rule-application" | "contradiction-resolution" | "precedence" | "evidence-link",
            "referenced_node_ids": [...],
            "referenced_edge_ids": [...],
            "referenced_rule_ids": [...],
            "referenced_evidence_ids": [...],
            "outcome": ...
        }
    ],
    "conflicts": [
        {
            "conflict_type": ...,
            "resolution": ...
        }
    ],
    "evidence_links": [...],
    "exceptions": [...],
    "temporal": [...],
    "invariants": [...]  # optional but recommended
}
```

**Determinism requirement**: ordering must be stable. Sort keys must be explicit.

## API Contract

The layer exposes a **read-only** interface:

```python
class ExplanationProvenanceLayer:
    def record(trace: ProofTrace) -> None:
        """Store a proof trace."""
    
    def get(trace_id: str) -> ProofTrace:
        """Retrieve a proof trace by ID."""
    
    def render(trace_id: str, format: Literal["json","md","html","pdf"]) -> bytes|str:
        """Render proof trace in requested format."""
    
    def export_bundle(trace_id: str) -> AuditBundle:
        """Export complete audit bundle."""
```

**Constraints**:
- The layer must never mutate `ProofTrace`.
- The layer must never call into core inference to "complete" missing data.
- The layer must be safe to disable at runtime.

## Storage Model

Two storage tiers are recommended:

### Ephemeral runtime store
- in-memory for debugging, local CLI, dev mode

### Audit store
- append-only persistence (e.g., file-based ledger, DB, or object store)
- Append-only is preferred to prevent retroactive tampering.

Each stored trace should include:
- `created_at`
- `version` (schema version)
- `producer_version` (Mahoun build/version)
- `signature` (optional, for tamper-evidence)

## Security and Privacy

Because proof traces can include sensitive facts:

- Support redaction policies:
  - `public_view`: redacted PII / sensitive facts
  - `internal_view`: full trace
- Redaction must be policy-driven, not heuristic-driven.
- The unredacted trace remains authoritative; redaction is a derived view.

## Failure Modes and Guarantees

If the Explanation & Provenance Layer fails:

- ✅ Core inference must still run.
- ✅ Verdict must still be produced.
- ⚠️ Only reporting/export is degraded.

This is a strict availability requirement aligned with **Decision Invariance**.

## Test Requirements

The following tests are **mandatory** and must remain green:

- `test_decision_invariance` (see `tests/test_design_rule_no_feature_only_proof.py`)
- `test_authority_isolation` (see `tests/test_design_rule_no_feature_only_proof.py`)
- `test_determinism_preservation` (see `tests/test_design_rule_no_feature_only_proof.py`)

Additionally recommended future tests:

- **Trace completeness**: every verdict must reference at least one applied rule and one supporting evidence item (where applicable).
- **Stable ordering**: the same trace regenerated twice yields identical serialized output.
- **Redaction correctness**: redacted views never leak restricted fields.

## Implementation Guidance

1. **Treat explanation as a compiler over proof traces, not a generator.**
2. **Prefer structural logs (JSON) over free-form narratives.**
3. **Keep the layer modular**:
   - `provenance/schema.py` (Pydantic models)
   - `provenance/store.py` (append-only store)
   - `provenance/renderers/` (md/html/pdf)
   - `provenance/redaction.py` (policy)

## Summary

Mahoun's Explanation & Provenance Layer is **not a feature**. It is the system's epistemic contract: a deterministic, audit-grade proof surface that makes every decision explainable without weakening the authority or determinism of the reasoning core.

---

**Related Files**:
- Design Rule Tests: `tests/test_design_rule_no_feature_only_proof.py`
- Core Reasoning: `mahoun/reasoning/`
- Graph Builder: `mahoun/graph/ultra_graph_builder.py`

