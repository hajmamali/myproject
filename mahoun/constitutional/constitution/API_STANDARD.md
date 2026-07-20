# MAHOUN API Standard

Version: 1.0.0

Status: Normative

Authority Level: Constitutional API Document


# 1. Purpose

This document defines the API governance model of the MAHOUN platform.

It establishes:

- API contract integrity rules
- API evolution governance
- Schema baseline authority
- Breaking change handling
- Interface stability requirements
- API approval requirements
- Versioning rules
- Migration rules
- Rollback rules
- Verification requirements

APIs are architectural contracts, not implementation details.

Every exported interface becomes part of the architectural constitution.


# 2. API Constitutional Authority

API changes are architectural changes.

No API modification is accepted only because tests pass.

Contract integrity has priority over compatibility.

The following authority hierarchy applies to API governance:

1. Constitutional Principles
2. API Standard (this document)
3. API Evolution Agent
4. Implementation
5. External tooling defaults


# 3. API Drift Governance

API drift MUST be continuously detected and prevented.

## Drift Categories

The following drift types MUST be monitored:

- API Surface Drift
- Schema Drift
- DTO Drift
- Response Drift
- Serialization Drift
- Signature Drift
- Semantic Drift
- Behavior Drift
- Governance Drift
- Documentation Drift
- Protocol Drift
- Version Drift
- Dependency Drift
- Snapshot Drift
- Manifest Drift
- Proof Drift

## Drift Handling

When drift is detected:

- NEVER patch symptoms
- Locate the constitutional cause
- Apply governance correction
- Verify root cause resolution


# 4. API Snapshot Authority

API snapshots are constitutional records.

## Snapshot Requirements

API snapshots MUST:

- represent the authoritative contract state
- be cryptographically verifiable
- maintain provenance lineage
- include governance attestation

## Snapshot Governance

Snapshots MUST NOT be regenerated merely to:

- silence CI failures
- hide breaking changes
- bypass validation
- accelerate releases

## Snapshot Update Requirements

Before updating any snapshot, verify:

- Change was intentional
- Governance was reviewed
- Architecture was approved
- Backward compatibility was evaluated
- Provenance was preserved
- Determinism was verified


# 5. Schema Baseline Authority

Schemas are constitutional artifacts.

## Schema Modification Requirements

Every schema modification requires validation of:

- field additions
- field removals
- field renames
- field ordering
- validation rules
- nullable changes
- enum evolution
- serialization impact
- deserialization impact
- hash stability
- contract compatibility

## Schema Governance

Undocumented schema evolution is PROHIBITED.

Schema changes MUST:

- have explicit authorization
- maintain backward compatibility OR have migration plan
- update all dependent contracts
- preserve hash stability when required


# 6. Contract Ownership

API contracts have single authoritative ownership.

## Contract Layers

All contract layers MUST describe exactly the same interface:

- Router
- Service
- Validator
- DTO
- Response Model
- Documentation
- API Snapshot
- Contract Definition
- Manifest
- Kernel Policy

## Contract Consistency

Disagreement between contract layers is a governance violation.

Contract consistency MUST be verified before API changes are accepted.


# 7. Breaking Change Handling

Breaking changes require constitutional approval.

## Breaking Change Definition

A breaking change is any modification that:

- removes or renames public APIs
- changes method signatures
- alters response structures
- modifies validation rules
- changes serialization format
- modifies error behavior
- changes authorization requirements

## Breaking Change Requirements

Breaking changes MUST include:

- migration plan
- compatibility analysis
- downstream impact assessment
- version strategy
- governance approval
- updated snapshot
- updated manifest
- updated attestation

No exceptions.


# 8. Interface Stability Rules

## Stability Guarantees

Public interfaces MUST maintain stability according to their declared stability level.

## Stability Levels

### Stable

Changes MUST be backward compatible.

### Experimental

Changes MAY break without migration.

### Deprecated

Changes are PROHIBITED except for removal preparation.

### Internal

No stability guarantees apply.


# 9. API Approval Requirements

## Approval Authority

API changes require approval from:

- API Evolution Agent
- Governance Authority
- Architecture Authority

## Approval Evidence

Approval MUST be documented with:

- approver identity
- approval timestamp
- approval reasoning
- impact analysis
- validation evidence


# 10. Versioning Rules

## Semantic Versioning

Version numbers reflect constitutional impact:

### PATCH

Implementation-only changes.

### MINOR

Compatible API expansion.

### MAJOR

Breaking constitutional evolution.

## Version Governance

Breaking changes MUST NOT be hidden inside minor versions.

Version increments MUST be intentional and documented.


# 11. Migration Rules

## Migration Planning

Breaking changes MUST include migration plans.

## Migration Requirements

Migration plans MUST specify:

- affected consumers
- migration steps
- timeline
- rollback procedure
- validation requirements

## Migration Execution

Migrations MUST be:

- traceable
- reversible
- validated
- auditable


# 12. Rollback Rules

## Rollback Authority

API rollbacks require governance authorization.

## Rollback Requirements

Rollbacks MUST:

- preserve provenance
- document rollback reason
- update governance state
- validate post-rollback state

## Rollback Limitations

Rollbacks MUST NOT:

- hide security fixes
- bypass governance
- create inconsistent state


# 13. Verification Requirements

## Pre-Deployment Verification

API changes MUST pass:

- contract validation
- schema validation
- compatibility validation
- governance validation
- security validation
- determinism validation

## Post-Deployment Verification

API deployments MUST be verified for:

- runtime behavior
- performance impact
- error rates
- consumer compatibility


# 14. Critical Interface Protection

The following interfaces are constitutionally protected:

- GovernanceContext
- GovernanceLock
- MutationAuthorizationBoundary
- KernelMutationBoundary
- ProofCarryingResponse
- FortressValidator
- GovernanceViolation
- GovernanceViolationError
- ExecutionPolicy
- PolicyResolver
- Kernel Guard
- Architecture Guard
- API Guard
- Constitution Manifest
- Kernel Manifest
- Kernel Lock
- API Snapshot
- Runtime Attestation

## Protection Requirements

Critical interface modifications require:

- explicit approval
- impact analysis
- security review
- governance attestation

## Prohibited Actions

- Silent modifications
- Hidden compatibility wrappers
- Alias-based deception


# 15. API Naming Policy

## Naming Consistency

Every public symbol MUST have one constitutional name.

## Prohibited Naming Patterns

- Multiple names for identical concepts
- Semantic aliases
- Historical leftovers
- Mixed terminology
- Ambiguous prefixes
- Inconsistent suffixes

## Naming Conflicts

If inconsistent names exist:

- Recommend migration
- NEVER use silent duplication


# 16. Runtime API Governance

## Runtime Requirements

Every runtime API MUST preserve:

- Governance Context
- Authorization State
- Execution Policy
- Mutation Boundary
- Proof Chain
- Cryptographic Lineage
- Audit Trail
- Attestation Metadata

## Runtime Shortcuts

Runtime shortcuts are PROHIBITED.

No API may bypass governance for performance or convenience.


# 17. Determinism Requirements

## Prohibited Behaviors

API evolution MUST NOT introduce:

- non-deterministic ordering
- unstable serialization
- unstable hashes
- implicit timestamps
- hidden randomness
- context leakage
- environment-dependent behavior

## Determinism Violations

Any non-deterministic behavior is a governance violation.


# 18. API Evolution Categories

Every API modification MUST belong to exactly one category.

## Category A: Compatible Extension

Allowed without special approval.

Examples:

- optional fields
- additive endpoints
- additive methods
- additive enums
- additive metadata

## Category B: Behavioral Evolution

Allowed only if behavior, contract, governance, documentation, and tests evolve together.

## Category C: Breaking Change

Requires constitutional approval and full breaking change requirements.


# 19. Forbidden Actions

The following actions are PROHIBITED:

- Rename APIs without migration
- Regenerate snapshots blindly
- Modify schemas without review
- Hide breaking changes
- Inject compatibility hacks
- Create alias layers
- Monkeypatch interfaces
- Disable validators
- Weaken governance
- Weaken fail-closed behavior
- Ignore API drift
- Ignore schema drift
- Ignore snapshot drift
- Ignore manifest drift
- Ignore provenance
- Ignore attestation
- Accept undocumented public APIs


# 20. API Governance Priorities

Always preserve, in order:

1. Constitutional Integrity
2. Governance Enforcement
3. Contract Correctness
4. Schema Integrity
5. Deterministic Behavior
6. Provenance Lineage
7. Runtime Validation
8. Backward Compatibility
9. Developer Convenience

NEVER reverse this order.


# Final Principle

APIs are constitutional contracts.

Implementation may evolve.

Contracts must evolve intentionally.

Never accidentally.
