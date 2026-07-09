# AGENTS.md

# Enterprise Governance Platform

This document defines the engineering constitution of this repository.

Every contributor—human or AI—must read this file before making any change.

Violation of these rules is considered an architectural defect.

======================================================================
MISSION
======================================================================

This repository implements an Enterprise Architecture Governance Platform.

It is NOT

• a linter

• a code formatter

• a style checker

• a syntax validator

It is an architecture analysis platform.

Always optimize for

correctness

extensibility

maintainability

architectural quality

rather than writing the smallest amount of code.

======================================================================
ARCHITECTURAL PRINCIPLE
======================================================================

Never build architecture around detectors.

Always build architecture around a shared model.

The architecture is

Repository

↓

Parser

↓

AST

↓

Project Model

↓

Graphs

↓

Detectors

↓

Reports

Detectors are consumers.

They are never producers.

======================================================================
SINGLE SOURCE OF TRUTH
======================================================================

The ProjectModel is the only authoritative representation of the repository.

No detector may build its own representation.

======================================================================
NO DUPLICATE ANALYSIS
======================================================================

AST parsing must happen exactly once.

Import resolution must happen exactly once.

Call graph construction must happen exactly once.

Dependency graph construction must happen exactly once.

Detectors consume shared structures.

======================================================================
GRAPH-FIRST DESIGN
======================================================================

Whenever possible, operate on graphs rather than syntax.

Preferred order

Semantic Graph

↓

Call Graph

↓

Dependency Graph

↓

AST

↓

Raw source code

======================================================================
PLUGIN FIRST
======================================================================

New functionality should be implemented as plugins.

Avoid modifying the engine unless absolutely necessary.

======================================================================
BACKWARD COMPATIBILITY
======================================================================

Public APIs must remain stable.

Breaking changes require explicit justification.

======================================================================
PATCH DISCIPLINE
======================================================================

Every change must represent one logical architectural objective.

Do not mix unrelated work.

Small, atomic patches are preferred.

======================================================================
NO SHORTCUTS
======================================================================

Never bypass

Parser

ProjectModel

Graph Builder

Rule Engine

Detector Registry

======================================================================
TESTING
======================================================================

Every architectural change requires

unit tests

integration tests

regression tests

======================================================================
DOCUMENTATION
======================================================================

Architecture documentation must evolve together with the implementation.

Code without documentation is considered incomplete.

======================================================================
PERFORMANCE
======================================================================

Always assume repositories may contain

100,000+

Python files.

Design for scalability from the beginning.

======================================================================
QUALITY BAR
======================================================================

The quality target is comparable to

CodeQL

Semgrep Enterprise

SonarQube Enterprise

Google Tricorder

Meta Infer

Palantir Internal Tooling

Never optimize for speed of implementation.

Optimize for engineering quality.

======================================================================
FINAL RULE
======================================================================

If you are unsure whether a change improves the architecture,

STOP.

Perform an architecture review.

Explain the trade-offs.

Only then proceed with implementation.
