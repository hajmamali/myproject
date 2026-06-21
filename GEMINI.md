Gemini Agent Hardening Rules for MAHOUN

Objective

Ensure that the Gemini agent remains fully aligned with MAHOUN's kernel, governance, and epistemic constraints, without deviating from the defined workflow, logic, or permissible reasoning space.


---

	1. Core Operating Principles

Governance-First: All actions must pass through the kernel's governance layer. No operation may bypass authority checks.

Deterministic Execution: Outputs must be reproducible given the same inputs; probabilistic reasoning is only allowed in strictly controlled contexts.

Epistemic Integrity: Reasoning outputs must satisfy all invariants, including admissibility, provenance, and semantic legality.



---

	2. Allowed Capabilities

Ingestion: Reading files (PDF, DOCX, TXT), extracting structured text, tagging entities using SLMs.

Parsing & NER: Using controlled SLMs for entity recognition; must produce canonical, deterministic outputs.

Graph Population: Creating nodes and relationships strictly through GovernedNeo4jSession.

Reasoning Engine Interaction: Limited LLM usage under strict kernel supervision and invariant validation.

Audit & Monitoring: Logging all operations, maintaining traceability and full provenance.



---

	3. Forbidden Actions

Direct access to Neo4j or persistence layers outside the governance kernel.

Any reasoning or inference that produces output without passing invariant checks.

Unauthorized schema creation or modification.

Bypassing hallucination control mechanisms.

Introducing probabilistic or non-deterministic reasoning into invariant enforcement or ingestion validation.

Ignoring audit logs or disabling monitoring.



---

	4. Hallucination Control Rules

Any entity or relationship not supported by evidence is rejected.

Conflicts must trigger UNDETERMINED verdicts (G4 invariant).

Deleted entities cannot be resurrected unless formally re-admitted (G3 invariant).

Semantic drift beyond canonical ontology boundaries is prohibited.

LLM outputs are gate-checked for admissibility and provenance before inclusion.



---

	5. Guardrails and Enforcement

Invariant Enforcement: All invariants must be enforced non-bypassably. Guardrails cannot be turned off.

Authority Enforcement: All operations must authenticate against kernel authority before execution.

Context Isolation: ContextVar or equivalent must isolate reasoning per request/session.

Replayability: Every reasoning or ingestion action must be replayable deterministically.

Logging: Every action must be logged with evidence, entity references, and provenance.

Failure Handling: Any violation of invariants must trigger an immediate halt of execution for that transaction.



---

	6. LLM/SLM Usage Guidelines

SLM: Allowed for deterministic parsing, entity extraction, and light semantic tagging.

LLM: Only in reasoning engine, fully controlled, outputs validated against invariants.

No Kernel Breach: LLM or SLM cannot create nodes/relationships outside GovernedNeo4jSession.

Confidence Thresholds: LLM outputs must meet strict confidence/admissibility thresholds.

Hallucination Gate: Any LLM output violating epistemic constraints must be rejected and logged.



---

	7. Audit and Monitoring Protocols

Continuous monitoring of all agent operations.

Immediate alert for any invariant violations, authority bypass attempts, or semantic drift.

Periodic review of all outputs against canonical schemas.

Retain full logs and provenance for all nodes, relationships, and reasoning steps.



---

	8. Operational Discipline

Incremental deployment: Only one subgraph or module at a time.

All updates must pass unit-level and integration-level invariant checks.

Any new capability or plugin must be registered, validated, and supervised.

Kernel authority is ultimate; no external module overrides permissible.



---

	9. Summary

The Gemini agent operating under this configuration will:

Never deviate from kernel governance.

Respect all epistemic and operational invariants.

Use LLMs/SLMs in strictly defined, controlled contexts.

Produce fully traceable, deterministic, and audit-ready outputs.

Function as a safe, compliant, and fully governed extension of MAHOUN's Knowledge Graph pipeline and reasoning architecture.
