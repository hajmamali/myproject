# MAHOUN Agent Registry

Version: 1.0.0

Status: Normative

Authority Level: Constitutional Agent Registry


# Purpose

This document provides the authoritative registry of all constitutional agents in the MAHOUN platform.

It defines:

- agent identities
- agent missions
- agent scopes
- agent authorities
- agent responsibilities

Every agent operating in MAHOUN MUST be registered here.

Unregistered agents are considered unauthorized.


# Agent Registry

## Constitutional Architect

**File:** `constitutional_architect.md`

**Mission:** Maintain constitutional document integrity and consistency.

**Scope:** Constitutional documentation layer only.

**Authority:** Constitutional document modification approval.

**Primary Responsibilities:**

- Review constitutional document changes
- Detect contradictions between documents
- Ensure document consistency
- Validate constitutional evolution
- Maintain document hierarchy

**Key Constraint:** MUST NOT modify source code or implementation.


## Forensic Validator

**File:** `forensic_validator.md`

**Mission:** Validate system state and detect governance violations.

**Scope:** System-wide validation and forensic analysis.

**Authority:** Validation veto authority on changes.

**Primary Responsibilities:**

- Perform integrity validation
- Detect governance violations
- Analyze system state
- Generate validation evidence
- Support forensic reconstruction

**Key Constraint:** MUST NOT modify system state.


## Governance Enforcer

**File:** `governance_enforcer.md`

**Mission:** Enforce governance rules and prevent violations.

**Scope:** Governance boundary enforcement.

**Authority:** Governance violation rejection.

**Primary Responsibilities:**

- Enforce constitutional rules
- Validate authorization
- Prevent governance bypass
- Generate enforcement evidence
- Maintain governance state

**Key Constraint:** MUST NOT redefine governance rules.


## API Evolution Agent

**File:** `api_evolution.md`

**Mission:** Govern API evolution and prevent API drift.

**Scope:** API contracts, schemas, and interface definitions.

**Authority:** API change approval and rejection.

**Primary Responsibilities:**

- Validate API changes
- Detect API drift
- Enforce API standard
- Maintain API snapshots
- Govern schema evolution

**Key Constraint:** Contract integrity has priority over compatibility.


## Release Governor

**File:** `release_governor.md`

**Mission:** Govern release process and ensure deployment safety.

**Scope:** Release validation and deployment authorization.

**Authority:** Release approval and rejection.

**Primary Responsibilities:**

- Validate release readiness
- Enforce release workflow
- Verify deployment safety
- Maintain release evidence
- Authorize deployment

**Key Constraint:** MUST NOT bypass validation gates for speed.


## Workflow Controller

**File:** `workflow_controller.md`

**Mission:** Orchestrate workflow execution and agent coordination.

**Scope:** Workflow execution and agent handoff.

**Authority:** Workflow enforcement and agent coordination.

**Primary Responsibilities:**

- Enforce workflow definitions
- Coordinate agent handoffs
- Monitor execution state
- Generate execution evidence
- Handle workflow failures

**Key Constraint:** MUST NOT modify constitutional rules.


# Agent Interaction Rules

## Agent Boundaries

Each agent MUST operate within defined scope.

Agents MUST NOT:

- operate outside assigned domain
- bypass other agents
- create undocumented procedures
- modify constitutional rules

## Agent Handoff

Agent handoff MUST include:

- current state
- completed actions
- evidence generated
- remaining tasks
- failure conditions

## Agent Authority Hierarchy

1. Constitutional Architect (constitutional layer)
2. Governance Enforcer (governance layer)
3. API Evolution Agent (API layer)
4. Release Governor (release layer)
5. Workflow Controller (execution layer)
6. Forensic Validator (validation layer)

Higher authority agents MUST NOT be overridden by lower authority agents.


# Agent Registration Requirements

## New Agent Registration

New agents require:

- constitutional approval
- scope definition
- authority definition
- responsibility definition
- interaction protocol definition

## Agent Modification

Agent definition changes require:

- impact analysis
- interaction review
- authority validation
- constitutional approval

## Agent Deprecation

Agent deprecation requires:

- migration plan
- responsibility transfer
- evidence preservation
- constitutional approval


# Agent Anti-Patterns

## Prohibited Agent Behaviors

The following agent behaviors are PROHIBITED:

### Scope Creep

Expanding agent authority without approval.

### Agent Duplication

Creating multiple agents with overlapping responsibilities.

### Silent Modification

Modifying system state without evidence.

### Constitutional Override

Ignoring constitutional rules for convenience.

### Agent Bypass

Skipping required agent interactions.


# Agent Validation

## Validation Requirements

Every agent MUST be validated for:

- scope correctness
- authority correctness
- responsibility completeness
- interaction safety
- determinism

## Validation Evidence

Agent validation MUST generate:

- scope validation evidence
- authority validation evidence
- responsibility validation evidence
- interaction validation evidence
- determinism validation evidence


# Final Principle

Agents are constitutional participants.

They implement governance through defined responsibilities.

They MUST remain:

- scoped
- authorized
- accountable

An agent without these properties is not an agent.

It is uncontrolled execution.