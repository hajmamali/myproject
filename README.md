# Mahoun

## Air-Gapped Legal Reasoning Platform

Mahoun is an evidence-centric legal reasoning platform designed for
high-trust and security-sensitive environments.

The system is engineered for operation in fully air-gapped deployments,
where external network access, cloud dependencies, and runtime third-party
services are prohibited.

Unlike conventional Legal AI systems that primarily rely on retrieval and
large language model prompting, Mahoun focuses on:

- Evidence-linked reasoning
- Governance-enforced execution
- Provenance preservation
- Graph-based legal knowledge representation
- Deterministic verification workflows
- Offline operation

---

# Core Principles

## 1. Air-Gapped First

The platform is designed to function without internet connectivity.

Operational assumptions:

- No cloud APIs
- No external inference services
- No runtime dependency on online resources
- No remote telemetry
- No hidden network requirements

The system must remain functional in isolated government, judicial,
defense, regulatory, and enterprise environments.

---

## 2. Evidence Before Verdict

Every conclusion should be traceable to supporting evidence.

The platform is designed around evidence-linked decision generation rather
than opaque answer generation.

Objectives:

- Evidence traceability
- Explainable reasoning
- Auditable conclusions
- Reconstructable decision chains

---

## 3. Governance by Design

Governance is treated as a runtime requirement rather than an optional
feature.

Governance controls:

- Context enforcement
- Scope enforcement
- Reasoning authorization
- Execution boundaries
- Audit trails

The system follows a fail-closed philosophy.

---

## 4. Provenance Preservation

Reasoning outputs are expected to preserve lineage information.

The platform maintains provenance chains that support:

- Traceability
- Verification
- Auditability
- Forensic analysis

---

## 5. Graph-Based Legal Knowledge

Legal information is represented through structured graph models.

Capabilities include:

- Entity representation
- Relationship modeling
- Evidence linkage
- Legal concept mapping
- Knowledge traversal

---

# Architecture

```text
                 ┌──────────────┐
                 │ Legal Inputs │
                 └──────┬───────┘
                        │
                        ▼
           ┌────────────────────────┐
           │ Ingestion & Validation │
           └───────────┬────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │ Legal Knowledge Graph  │
           └───────────┬────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │ Reasoning Layer        │
           └───────────┬────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │ Governance Layer       │
           └───────────┬────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │ Provenance Generation  │
           └───────────┬────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │ Verdict Construction   │
           └────────────────────────┘
Security Model

Mahoun is intended for environments where:

Data confidentiality is critical
Network isolation is mandatory
Auditability is required
Regulatory compliance is required

Security goals include:

Fail-closed execution
Governance enforcement
Query hardening
Provenance integrity
Tamper detection
Intended Deployment Environments

Examples include:

Judicial institutions
Government agencies
Regulatory authorities
Defense environments
Critical infrastructure operators
Enterprise legal departments
Current Focus

Recent developments have finalized strict layer-2 governance hardening, including:

- **EL-I3 Enforcement (Deep Validation)**: Blocks non-existent evidence from being verified or written to the Ledger.
- **EL-I4 Constraints (Confidence Bounds)**: Enforces dynamic confidence limits, demanding multi-fact consensus (>= 3 facts) for high confidence (>0.9) verdicts.
- **EL-I8 Guards (Tombstone Security)**: Automatic rejection of previously deleted, redacted, or soft-deleted evidence to maintain absolute privacy and integrity.
- **End-to-End RAG Provenance**: Unbroken metadata tracking directly from initial RAG retrieval (Document ID, Score, Source) through the Graph down to cryptographic ledger proof generation.
- **Chaos-Tested Concurrency**: The reasoning engine and `LedgerWriteGate` possess proven, isolated asynchronous execution that gracefully handles severe network, data, and logic faults without compromising strict governance boundaries.

Project Status

Mahoun has successfully matured into a strict, fail-closed legal reasoning platform rather than a general-purpose legal chatbot. 

The primary objective remains: unwavering, trustworthy reasoning in highly constrained, air-gapped environments backed by non-bypassable architectural safeguards.
