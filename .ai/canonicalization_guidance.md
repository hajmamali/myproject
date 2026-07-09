# Canonicalization Guidance

## Purpose
This document defines how canonical implementations should be selected in this repository when multiple versions, variants, or competing implementations exist.

## Scope
It applies to consolidation work, duplicate resolution, architecture cleanup, and any decision involving choosing a primary implementation.

## Core Principle
When choosing a canonical implementation, quality and system accuracy must take priority over convenience, speed, or local simplicity.

## Selection Criteria
The preferred implementation should be the one that best satisfies the following criteria:
1. Correctness and semantic accuracy
2. Alignment with the repository architecture and ProjectModel
3. Maintainability and long-term clarity
4. Lower structural risk and lower duplication
5. Better support for future evolution

## Decision Rule
If multiple implementations appear viable, select the version that:
- preserves the highest level of correctness,
- fits the shared architectural model most cleanly,
- reduces ambiguity and duplication,
- and minimizes future maintenance risk.

## Required Review Questions
Before finalizing a canonical choice, the agent should answer:
- What is the real responsibility of this implementation?
- Which version is more accurate and complete?
- Which version is more compatible with the existing architecture?
- Which version introduces less hidden complexity or drift?
- What is the migration risk if this version becomes canonical?

## Rules
- Do not select a version merely because it is simpler to replace.
- Do not choose a version that weakens architectural clarity.
- Do not canonicalize without a clear rationale.
- Prefer a version that improves system quality even if it requires more careful migration.

## Expected Behavior
Agents should make canonicalization decisions as disciplined architecture choices rather than as quick cleanup actions.

## Anti-Patterns
- Choosing the fastest implementation without validating correctness.
- Selecting a duplicate because it appears easier to preserve.
- Treating canonicalization as a purely mechanical rename or merge.

## Quality Criteria
A canonical decision is acceptable only when it improves correctness, architectural coherence, maintainability, and future trust in the system.
